import os

# try:
#     import bs4, discord, colorama, requests
# except ImportError:
#     os.system('pip3 install -r requirements.txt')
#     os.system('cls' if os.name == 'nt' else 'clear')

import discord
from discord.ext import commands
#from bot.nct import register_nct
from bot.scl import register_scl
from bot.img import register_img
from bot.girl import register_girl
from bot.anime import register_anime
from bot.emoji import register_emoji
from bot.images import register_images
from bot.smsvip import register_smsvip
from bot.cosplay import register_cosplay

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True  # Cần bật nếu bạn muốn đọc nội dung tin nhắn
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    print(f'Bot {bot.user} đã đăng nhập thành công trên Discord!')
    try:
        # Đồng bộ các lệnh slash (application commands) với Discord
        synced = await bot.tree.sync()
        print(f"Đã đồng bộ {len(synced)} lệnh slash!")
    except Exception as e:
        print(f"Lỗi khi đồng bộ lệnh slash: {e}")

# Đăng ký các lệnh/sự kiện từ các module (các hàm register_ cần được chuyển hướng theo discord.py)
#register_nct(bot)
register_scl(bot)
register_img(bot)
register_girl(bot)
register_anime(bot)
register_emoji(bot)
register_smsvip(bot)
register_images(bot)
register_cosplay(bot)

if __name__ == '__main__':
    print("Bot Discord đang hoạt động...")
    bot.run(TOKEN)
