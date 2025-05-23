import os
import discord
from discord.ext import commands
import requests

# Lấy token từ biến môi trường
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True  # Phải bật để đọc nội dung tin nhắn

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot đã đăng nhập với tên: {bot.user}")

@bot.command()
async def anime(ctx):
    try:
        # Gọi API lấy video
        api_url = "https://api-anime-0rz7.onrender.com/api/anime"
        response = requests.get(api_url, timeout=10).json()
        video_url = response['video_url']

        try:
            # Gửi video
            await ctx.send(video_url)
        except:
            await ctx.send(f"Không gửi được video. Link lỗi: {video_url}")

    except:
        await ctx.send("Lỗi khi gọi API!")

# Chạy bot
bot.run(TOKEN)