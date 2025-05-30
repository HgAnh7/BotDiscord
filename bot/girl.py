import io
import random
import discord
import requests
from discord.ext import commands

# Cấu hình
ERROR_CHANNEL_ID = 1377693583741812867
MAX_FILE_SIZE_MB = 8
MAX_RETRIES = 5

def load_urls():
    """Load URLs với validation cơ bản"""
    try:
        with open("bot/url/girl.txt", "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip() and line.startswith('http')]
        return urls if urls else []
    except UnicodeDecodeError:
        with open("bot/url/girl.txt", "r", encoding="utf-8-sig") as f:
            return [line.strip() for line in f if line.strip() and line.startswith('http')]

def get_extension(content_type):
    """Xác định extension từ content-type"""
    if "webm" in content_type: return "webm"
    if "ogg" in content_type: return "ogg"
    return "mp4"

def register_girl(bot: commands.Bot):
    @bot.tree.command(name="girl", description="Gửi video gái ngẫu nhiên")
    async def girl(interaction: discord.Interaction):
        await interaction.response.defer()
        
        error_channel = bot.get_channel(ERROR_CHANNEL_ID)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        try:
            video_urls = load_urls()
            if not video_urls:
                if error_channel:
                    await error_channel.send("❌ Danh sách video girl trống!")
                return await interaction.followup.send("Danh sách video chưa có dữ liệu!")
            
            # Shuffle để random tốt hơn
            random.shuffle(video_urls)
            used_urls = []
            
            for attempt in range(min(MAX_RETRIES, len(video_urls))):
                url = video_urls[attempt]
                used_urls.append(url)
                
                try:
                    # Kiểm tra HEAD request
                    head_resp = requests.head(url, headers=headers, timeout=10)
                    if head_resp.status_code != 200:
                        continue
                    
                    # Kiểm tra size từ header
                    content_length = head_resp.headers.get('Content-Length')
                    if content_length and int(content_length) > MAX_FILE_SIZE_MB * 1024 * 1024:
                        continue
                    
                    # Download với stream để kiểm tra size
                    resp = requests.get(url, headers=headers, timeout=30, stream=True)
                    resp.raise_for_status()
                    
                    # Download chunks và check size
                    content = b''
                    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
                    
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            content += chunk
                            if len(content) > max_bytes:
                                raise Exception("File too large during download")
                    
                    # Success - gửi file
                    actual_size_mb = len(content) / (1024 * 1024)
                    ext = get_extension(resp.headers.get("Content-Type", ""))
                    
                    video_file = discord.File(
                        io.BytesIO(content), 
                        filename=f"girl_video.{ext}"
                    )
                    
                    await interaction.followup.send(
                        f"🎬 Video girl cho {interaction.user.mention} ({actual_size_mb:.2f}MB):", 
                        file=video_file
                    )
                    return  # Success!
                    
                except Exception as e:
                    # Log lỗi và thử URL tiếp theo
                    if error_channel:
                        await error_channel.send(
                            f"**URL Error:** {url}\n{str(e)[:100]}\n"
                            f"User: {interaction.user.mention}"
                        )
                    continue
            
            # Thất bại hoàn toàn
            await interaction.followup.send(
                f"❌ Không thể tải video girl. Đã thử {len(used_urls)} video nhưng đều lỗi!"
            )
            
        except FileNotFoundError:
            await interaction.followup.send("❌ File cấu hình không tồn tại!")
        except Exception as e:
            if error_channel:
                await error_channel.send(f"**System Error:** {str(e)}")
            await interaction.followup.send("❌ Lỗi hệ thống!")
