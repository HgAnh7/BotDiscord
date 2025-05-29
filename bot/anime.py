import io
import random
import discord
import requests
from discord.ext import commands

# Cấu hình
ERROR_CHANNEL_ID = 1375700436593672222  # Thay bằng ID channel báo lỗi thực tế
MAX_FILE_SIZE_MB = 8  # Discord free tier limit (hoặc 25 cho Nitro)
MAX_RETRIES = 5  # Số lần thử tối đa

def register_anime(bot: commands.Bot):
    @bot.tree.command(name="anime", description="Gửi video anime ngẫu nhiên")
    async def anime(interaction: discord.Interaction):
        # Xác nhận tương tác ngay để được thêm thời gian xử lý.
        await interaction.response.defer()
        
        error_channel = bot.get_channel(ERROR_CHANNEL_ID)
        
        try:
            with open("bot/url/anime.txt", "r", encoding="utf-8") as f:
                video_urls = [line.strip() for line in f if line.strip()]
            
            if not video_urls:
                error_msg = "❌ Danh sách video anime trống!"
                if error_channel:
                    await error_channel.send(f"**Lỗi Bot Anime:** {error_msg}")
                return await interaction.followup.send("Danh sách video chưa có dữ liệu!")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/98.0.4758.102 Safari/537.36"
                )
            }
            
            used_urls = []  # Lưu các URL đã thử
            retry_count = 0
            
            while retry_count < MAX_RETRIES and len(used_urls) < len(video_urls):
                # Chọn URL chưa thử
                available_urls = [url for url in video_urls if url not in used_urls]
                if not available_urls:
                    break
                    
                selected_video_url = random.choice(available_urls)
                used_urls.append(selected_video_url)
                retry_count += 1
                
                try:
                    # Kiểm tra kích thước file trước khi tải
                    head_resp = requests.head(selected_video_url, headers=headers, timeout=10)
                    
                    if head_resp.status_code != 200:
                        # Báo lỗi URL không hoạt động
                        if error_channel:
                            await error_channel.send(
                                f"**URL Anime Lỗi (HEAD):** {selected_video_url}\n"
                                f"Status Code: {head_resp.status_code}\n"
                                f"User: {interaction.user.mention} ({interaction.user.id})"
                            )
                        continue
                    
                    # Lấy kích thước file
                    content_length = head_resp.headers.get('Content-Length')
                    if content_length:
                        file_size_mb = int(content_length) / (1024 * 1024)
                        
                        if file_size_mb > MAX_FILE_SIZE_MB:
                            # Báo lỗi file quá lớn
                            if error_channel:
                                await error_channel.send(
                                    f"**URL Anime Quá Lớn:** {selected_video_url}\n"
                                    f"Kích thước: {file_size_mb:.2f}MB (> {MAX_FILE_SIZE_MB}MB)\n"
                                    f"User: {interaction.user.mention} ({interaction.user.id})"
                                )
                            continue
                    
                    # Tải file nếu kích thước phù hợp
                    resp = requests.get(selected_video_url, headers=headers, timeout=30)
                    resp.raise_for_status()
                    
                    # Kiểm tra kích thước thực tế khi tải xong
                    actual_size_mb = len(resp.content) / (1024 * 1024)
                    if actual_size_mb > MAX_FILE_SIZE_MB:
                        if error_channel:
                            await error_channel.send(
                                f"**URL Anime Quá Lớn (Thực tế):** {selected_video_url}\n"
                                f"Kích thước thực: {actual_size_mb:.2f}MB (> {MAX_FILE_SIZE_MB}MB)\n"
                                f"User: {interaction.user.mention} ({interaction.user.id})"
                            )
                        continue
                    
                    # Xác định phần mở rộng file
                    content_type = resp.headers.get("Content-Type", "")
                    ext = ("webm" if "video/webm" in content_type 
                           else "ogg" if "video/ogg" in content_type 
                           else "mp4")
                    
                    # Gửi file thành công
                    video_file = discord.File(io.BytesIO(resp.content), filename=f"anime_video.{ext}")
                    await interaction.followup.send(
                        f"🎬 Video anime cho {interaction.user.mention} (Kích thước: {actual_size_mb:.2f}MB):", 
                        file=video_file
                    )
                    
                    # Ghi log thành công nếu cần
                    if error_channel and retry_count > 1:
                        await error_channel.send(
                            f"**Anime Bot - Thành công sau {retry_count} lần thử**\n"
                            f"URL: {selected_video_url}\n"
                            f"User: {interaction.user.mention} ({interaction.user.id})"
                        )
                    
                    return  # Thành công, thoát khỏi vòng lặp
                    
                except requests.exceptions.RequestException as e:
                    # Báo lỗi kết nối/tải file
                    if error_channel:
                        await error_channel.send(
                            f"**URL Anime Lỗi Kết Nối:** {selected_video_url}\n"
                            f"Lỗi: {str(e)}\n"
                            f"User: {interaction.user.mention} ({interaction.user.id})"
                        )
                    continue
                
                except Exception as e:
                    # Báo lỗi khác
                    if error_channel:
                        await error_channel.send(
                            f"**URL Anime Lỗi Khác:** {selected_video_url}\n"
                            f"Lỗi: {str(e)}\n"
                            f"User: {interaction.user.mention} ({interaction.user.id})"
                        )
                    continue
            
            # Nếu đã thử hết mà không thành công
            error_msg = f"Không thể tìm video phù hợp sau {retry_count} lần thử!"
            if error_channel:
                await error_channel.send(
                    f"**Anime Bot - Thất bại hoàn toàn**\n"
                    f"Đã thử {retry_count} URLs\n"
                    f"User: {interaction.user.mention} ({interaction.user.id})\n"
                    f"URLs đã thử: {', '.join(used_urls[:3])}{'...' if len(used_urls) > 3 else ''}"
                )
            
            await interaction.followup.send(
                "❌ Không thể tải video anime lúc này. "
                "Tất cả video hiện tại đều quá lớn hoặc có lỗi. "
                "Vui lòng thử lại sau!"
            )
            
        except FileNotFoundError:
            error_msg = "File anime.txt không tồn tại!"
            if error_channel:
                await error_channel.send(f"**Lỗi Bot Anime - File:** {error_msg}")
            await interaction.followup.send("❌ Lỗi hệ thống. Vui lòng liên hệ admin!")
            
        except Exception as e:
            # Lỗi không mong muốn
            if error_channel:
                await error_channel.send(
                    f"**Lỗi Bot Anime - System:**\n"
                    f"Lỗi: {str(e)}\n"
                    f"User: {interaction.user.mention} ({interaction.user.id})"
                )
            await interaction.followup.send("❌ Đã xảy ra lỗi không mong muốn!")