import os
import discord
from discord.ext import commands
from notification import register_notification
from bot.qr import register_qr, register_qrurl
#from bot.nct import register_nct
from bot.scl import register_scl
from bot.img import register_img
from bot.nude import register_nude
from bot.girl import register_girl
from bot.anime import register_anime
from bot.emoji import register_emoji
from bot.images import register_images
from bot.smsvip import register_smsvip
from bot.bancheck import register_bancheck
from bot.cosplay import register_cosplay
from bot.sourceweb import register_sourceweb

TOKEN = os.getenv("DISCORD_TOKEN")

# intents = discord.Intents.default()
# intents.message_content = True  # Cần bật nếu bạn muốn đọc nội dung tin nhắn
# intents.members = True  # Quan trọng: bắt sự kiện join/leave

intents = discord.Intents.all()
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
register_qr(bot)
#register_nct(bot)
register_scl(bot)
register_img(bot)
register_nude(bot)
register_girl(bot)
register_qrurl(bot)
register_anime(bot)
register_emoji(bot)
register_smsvip(bot)
register_images(bot)
register_bancheck(bot)
register_cosplay(bot)
register_sourceweb(bot)
register_notification(bot)

if __name__ == '__main__':
    print("Bot Discord đang hoạt động...")
    bot.run(TOKEN)
