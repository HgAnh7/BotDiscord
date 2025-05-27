import io
import random
import discord
import requests
from discord.ext import commands

def register_anime(bot: commands.Bot):
    @bot.command(name='anime')
    async def anime(ctx):
        try:
            with open("bot/url/anime.txt", "r", encoding="utf-8") as f:
                video_urls = [line.strip() for line in f if line.strip()]
            if not video_urls:
                return await ctx.send("Danh sách video chưa có dữ liệu!")
            
            # Chọn ngẫu nhiên một URL và tải video
            selected_video_url = random.choice(video_urls)
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/98.0.4758.102 Safari/537.36"
                )
            }
            resp = requests.get(selected_video_url, headers=headers, timeout=30)
            resp.raise_for_status()
            
            # Xác định phần mở rộng file dựa trên Content-Type (mặc định là 'mp4')
            content_type = resp.headers.get("Content-Type", "")
            ext = ("webm" if "video/webm" in content_type 
                   else "ogg" if "video/ogg" in content_type 
                   else "mp4")
            
            # Tạo file từ nội dung video tải được
            video_file = discord.File(io.BytesIO(resp.content), filename=f"anime_video.{ext}")
            await ctx.send(f"Đây là video đã tải về cho {ctx.author.mention}:", file=video_file)

        except Exception as e:
            await ctx.send(f"Lỗi: {e}")

    # Lệnh slash
    @bot.tree.command(name="anime", description="Gửi video anime ngẫu nhiên")
    async def anime_slash(interaction: discord.Interaction):
        try:
            with open("bot/url/anime.txt", "r", encoding="utf-8") as f:
                video_urls = [line.strip() for line in f if line.strip()]
            if not video_urls:
                return await interaction.response.send_message("Danh sách video chưa có dữ liệu!")
            
            # Chọn ngẫu nhiên một URL và tải video
            selected_video_url = random.choice(video_urls)
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/98.0.4758.102 Safari/537.36"
                )
            }
            resp = requests.get(selected_video_url, headers=headers, timeout=30)
            resp.raise_for_status()
            
            # Xác định phần mở rộng file dựa trên Content-Type (mặc định là 'mp4')
            content_type = resp.headers.get("Content-Type", "")
            ext = ("webm" if "video/webm" in content_type 
                   else "ogg" if "video/ogg" in content_type 
                   else "mp4")
            
            video_file = discord.File(io.BytesIO(resp.content), filename=f"anime_video.{ext}")
            await interaction.response.send_message(f"Đây là video đã tải về cho {interaction.user.mention}:", file=video_file)
            
        except Exception as e:
            await interaction.response.send_message(f"Lỗi: {e}")