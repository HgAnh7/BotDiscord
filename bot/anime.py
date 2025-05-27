import io
import random
import discord
import requests
from discord.ext import commands

def register_anime(bot: commands.Bot):
    @bot.command(name='anime')
    async def anime(ctx):
        try:
            # Đường dẫn tới tệp chứa danh sách URL video
            file_path = "bot/url/anime.txt"
            
            # Đọc tệp và loại bỏ các dòng trống
            with open(file_path, "r", encoding="utf-8") as file:
                video_urls = [line.strip() for line in file if line.strip()]

            # Chọn ngẫu nhiên một URL trong danh sách
            selected_video_url = random.choice(video_urls)

            # Tải video từ URL đã chọn
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/98.0.4758.102 Safari/537.36"
                )
            }
            video_response = requests.get(selected_video_url, headers=headers, timeout=30)
            video_response.raise_for_status()  # Nếu có lỗi HTTP thì ném exception

            # Xác định phần mở rộng file dựa trên header Content-Type, mặc định là 'mp4'
            ext = "mp4"
            content_type = video_response.headers.get("Content-Type", "")
            if "video/mp4" in content_type:
                ext = "mp4"
            elif "video/webm" in content_type:
                ext = "webm"
            elif "video/ogg" in content_type:
                ext = "ogg"

            # Tạo file video từ nội dung tải được (sử dụng io.BytesIO để không cần lưu ra đĩa)
            video_file = discord.File(
                io.BytesIO(video_response.content),
                filename=f"anime_video.{ext}"
            )

            # Gửi tin nhắn cùng với file video; khi người dùng mở video, nếu kích hoạt thì có âm thanh
            await ctx.send(f"Đây là video đã tải về cho {ctx.author.mention}:", file=video_file)
        
        except Exception as e:
            await ctx.send(f"Lỗi: {e}")
