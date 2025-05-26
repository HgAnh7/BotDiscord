import random
import discord
from discord.ext import commands

def register_girl(bot: commands.Bot):
    @bot.command(name='girl')
    async def girl(ctx):
        try:
            file_path = "bot/url/girl.txt"
            with open(file_path, "r", encoding="utf-8") as file:
                video_urls = [line.strip() for line in file if line.strip()]

            if not video_urls:
                await ctx.send("Danh sách video chưa có dữ liệu!")
                return

            selected_video = random.choice(video_urls)
            # Nếu selected_video là URL, Discord sẽ tự động tạo preview nếu có.
            await ctx.send(selected_video)
        except Exception as e:
            await ctx.send(f"Lỗi: {e}")
