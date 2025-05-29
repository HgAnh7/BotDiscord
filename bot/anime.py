import io
import random
import discord
import requests
from discord.ext import commands
from typing import List, Tuple, Optional
from dataclasses import dataclass

# =============================================================================
# CONSTANTS & CONFIGURATION
# =============================================================================

@dataclass
class Config:
    ERROR_CHANNEL_ID: int = 1377693583741812867
    MAX_FILE_SIZE_MB: int = 8
    MAX_RETRIES: int = 5
    REQUEST_TIMEOUT: int = 30
    ANIME_FILE_PATH: str = "bot/url/anime.txt"
    
    # User Agent
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/98.0.4758.102 Safari/537.36"
    )

# Error Messages
class ErrorMessages:
    EMPTY_VIDEO_LIST = "❌ Danh sách video anime trống!"
    NO_DATA_AVAILABLE = "Danh sách video chưa có dữ liệu!"
    SYSTEM_ERROR = "❌ Lỗi hệ thống. Vui lòng liên hệ admin!"
    UNEXPECTED_ERROR = "❌ Đã xảy ra lỗi không mong muốn!"
    FILE_NOT_FOUND = "File anime.txt không tồn tại!"
    NO_SUITABLE_VIDEO = (
        "❌ Không thể tải video anime lúc này. "
        "Tất cả video hiện tại đều quá lớn hoặc có lỗi. "
        "Vui lòng thử lại sau!"
    )

# Success Messages
class SuccessMessages:
    VIDEO_SENT = "🎬 Video anime cho {user} (Kích thước: {size:.2f}MB):"

# Log Messages
class LogMessages:
    URL_HEAD_ERROR = "**URL Anime Lỗi (HEAD):** {url}\nStatus Code: {status}\nUser: {user} ({user_id})"
    URL_TOO_LARGE = "**URL Anime Quá Lớn:** {url}\nKích thước: {size:.2f}MB (> {max_size}MB)\nUser: {user} ({user_id})"
    URL_TOO_LARGE_ACTUAL = "**URL Anime Quá Lớn (Thực tế):** {url}\nKích thước thực: {size:.2f}MB (> {max_size}MB)\nUser: {user} ({user_id})"
    URL_CONNECTION_ERROR = "**URL Anime Lỗi Kết Nối:** {url}\nLỗi: {error}\nUser: {user} ({user_id})"
    URL_OTHER_ERROR = "**URL Anime Lỗi Khác:** {url}\nLỗi: {error}\nUser: {user} ({user_id})"
    SUCCESS_AFTER_RETRIES = "**Anime Bot - Thành công sau {retries} lần thử**\nURL: {url}\nUser: {user} ({user_id})"
    COMPLETE_FAILURE = "**Anime Bot - Thất bại hoàn toàn**\nĐã thử {retries} URLs\nUser: {user} ({user_id})\nURLs đã thử: {urls}"
    SYSTEM_ERROR = "**Lỗi Bot Anime - System:**\nLỗi: {error}\nUser: {user} ({user_id})"
    FILE_ERROR = "**Lỗi Bot Anime - File:** {error}"

# =============================================================================
# ANIME VIDEO HANDLER CLASS
# =============================================================================

class AnimeVideoHandler:
    def __init__(self, config: Config):
        self.config = config
        self.headers = {"User-Agent": config.USER_AGENT}
    
    def load_video_urls(self) -> List[str]:
        """Load video URLs from file."""
        try:
            with open(self.config.ANIME_FILE_PATH, "r", encoding="utf-8") as f:
                urls = [line.strip() for line in f if line.strip()]
            return urls
        except FileNotFoundError:
            raise FileNotFoundError(ErrorMessages.FILE_NOT_FOUND)
    
    def check_file_size_header(self, url: str) -> Tuple[bool, Optional[float]]:
        """Check file size via HEAD request. Returns (is_valid, size_mb)."""
        try:
            head_resp = requests.head(url, headers=self.headers, timeout=10)
            
            if head_resp.status_code != 200:
                return False, None
            
            content_length = head_resp.headers.get('Content-Length')
            if content_length:
                try:
                    file_size_mb = int(content_length) / (1024 * 1024)
                    return file_size_mb <= self.config.MAX_FILE_SIZE_MB, file_size_mb
                except (ValueError, TypeError):
                    return True, None  # Cannot determine size, allow download
            
            return True, None  # No content-length header, allow download
            
        except requests.exceptions.RequestException:
            return False, None
    
    def download_video(self, url: str) -> Tuple[bool, Optional[bytes], Optional[float]]:
        """Download video content. Returns (success, content, size_mb)."""
        try:
            resp = requests.get(url, headers=self.headers, timeout=self.config.REQUEST_TIMEOUT)
            resp.raise_for_status()
            
            # Check actual file size
            actual_size_mb = len(resp.content) / (1024 * 1024)
            if actual_size_mb > self.config.MAX_FILE_SIZE_MB:
                return False, None, actual_size_mb
            
            return True, resp.content, actual_size_mb
            
        except requests.exceptions.RequestException:
            return False, None, None
    
    def get_file_extension(self, response_headers: dict) -> str:
        """Determine file extension from content type."""
        content_type = response_headers.get("Content-Type", "").lower()
        
        if "video/webm" in content_type:
            return "webm"
        elif "video/ogg" in content_type:
            return "ogg"
        elif "video/mp4" in content_type:
            return "mp4"
        else:
            return "mp4"  # Default fallback
    
    async def log_error(self, error_channel: discord.TextChannel, message: str):
        """Log error to designated channel."""
        if error_channel:
            try:
                await error_channel.send(message)
            except discord.DiscordException:
                pass  # Ignore logging failures
    
    async def try_single_url(self, url: str, error_channel: discord.TextChannel, 
                           user: discord.User) -> Tuple[bool, Optional[bytes], Optional[float], Optional[str]]:
        """Try to download from a single URL. Returns (success, content, size_mb, extension)."""
        
        # Check file size via HEAD request
        is_size_valid, header_size = self.check_file_size_header(url)
        
        if not is_size_valid:
            if header_size is None:
                # HEAD request failed
                await self.log_error(error_channel, LogMessages.URL_HEAD_ERROR.format(
                    url=url, status="Failed", user=user.mention, user_id=user.id
                ))
            else:
                # File too large
                await self.log_error(error_channel, LogMessages.URL_TOO_LARGE.format(
                    url=url, size=header_size, max_size=self.config.MAX_FILE_SIZE_MB,
                    user=user.mention, user_id=user.id
                ))
            return False, None, None, None
        
        # Download the file
        success, content, actual_size = self.download_video(url)
        
        if not success:
            if actual_size is not None:
                # File too large after download
                await self.log_error(error_channel, LogMessages.URL_TOO_LARGE_ACTUAL.format(
                    url=url, size=actual_size, max_size=self.config.MAX_FILE_SIZE_MB,
                    user=user.mention, user_id=user.id
                ))
            else:
                # Connection/download error
                await self.log_error(error_channel, LogMessages.URL_CONNECTION_ERROR.format(
                    url=url, error="Download failed", user=user.mention, user_id=user.id
                ))
            return False, None, actual_size, None
        
        # Determine file extension (we need to make another request to get headers)
        try:
            head_resp = requests.head(url, headers=self.headers, timeout=10)
            extension = self.get_file_extension(head_resp.headers)
        except:
            extension = "mp4"  # Fallback
        
        return True, content, actual_size, extension
    
    async def get_random_video(self, error_channel: discord.TextChannel, 
                             user: discord.User) -> Tuple[bool, Optional[bytes], Optional[float], Optional[str]]:
        """Get a random video that meets size requirements."""
        
        # Load URLs
        try:
            video_urls = self.load_video_urls()
        except FileNotFoundError as e:
            await self.log_error(error_channel, LogMessages.FILE_ERROR.format(error=str(e)))
            raise
        
        if not video_urls:
            await self.log_error(error_channel, LogMessages.FILE_ERROR.format(error=ErrorMessages.EMPTY_VIDEO_LIST))
            raise ValueError(ErrorMessages.EMPTY_VIDEO_LIST)
        
        # Try multiple URLs
        used_urls = []
        retry_count = 0
        
        while retry_count < self.config.MAX_RETRIES and len(used_urls) < len(video_urls):
            # Select unused URL
            available_urls = [url for url in video_urls if url not in used_urls]
            if not available_urls:
                break
            
            selected_url = random.choice(available_urls)
            used_urls.append(selected_url)
            retry_count += 1
            
            # Try this URL
            success, content, size, extension = await self.try_single_url(
                selected_url, error_channel, user
            )
            
            if success:
                # Log success if we had to retry
                if retry_count > 1:
                    await self.log_error(error_channel, LogMessages.SUCCESS_AFTER_RETRIES.format(
                        retries=retry_count, url=selected_url, 
                        user=user.mention, user_id=user.id
                    ))
                return True, content, size, extension
        
        # Complete failure
        urls_display = ', '.join(used_urls[:3])
        if len(used_urls) > 3:
            urls_display += '...'
        
        await self.log_error(error_channel, LogMessages.COMPLETE_FAILURE.format(
            retries=retry_count, user=user.mention, user_id=user.id, urls=urls_display
        ))
        
        return False, None, None, None

# =============================================================================
# DISCORD COMMAND REGISTRATION
# =============================================================================

def register_anime(bot: commands.Bot):
    config = Config()
    handler = AnimeVideoHandler(config)
    
    @bot.tree.command(name="anime", description="Gửi video anime ngẫu nhiên")
    async def anime(interaction: discord.Interaction):
        # Defer response to get more processing time
        await interaction.response.defer()
        
        error_channel = bot.get_channel(config.ERROR_CHANNEL_ID)
        
        try:
            # Get random video
            success, content, size_mb, extension = await handler.get_random_video(
                error_channel, interaction.user
            )
            
            if not success:
                return await interaction.followup.send(ErrorMessages.NO_SUITABLE_VIDEO)
            
            # Send the video
            video_file = discord.File(
                io.BytesIO(content), 
                filename=f"anime_video.{extension}"
            )
            
            await interaction.followup.send(
                SuccessMessages.VIDEO_SENT.format(
                    user=interaction.user.mention, 
                    size=size_mb
                ),
                file=video_file
            )
            
        except FileNotFoundError:
            await interaction.followup.send(ErrorMessages.SYSTEM_ERROR)
            
        except ValueError as e:
            if str(e) == ErrorMessages.EMPTY_VIDEO_LIST:
                await interaction.followup.send(ErrorMessages.NO_DATA_AVAILABLE)
            else:
                await interaction.followup.send(ErrorMessages.UNEXPECTED_ERROR)
                
        except Exception as e:
            # Log unexpected system errors
            if error_channel:
                await handler.log_error(error_channel, LogMessages.SYSTEM_ERROR.format(
                    error=str(e), user=interaction.user.mention, user_id=interaction.user.id
                ))
            await interaction.followup.send(ErrorMessages.UNEXPECTED_ERROR)