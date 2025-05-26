import os
import discord
from discord.ext import commands
#from bot.nct import register_nct
#from bot.scl import register_scl
from bot.girl import register_girl
from bot.anime import register_anime
from bot.images import register_images

# Lấy token Discord từ biến môi trường (đặt tên biến là DISCORD_TOKEN)
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("Không tìm thấy biến môi trường DISCORD_TOKEN!")

# Khởi tạo intents và bot với prefix là "!"
intents = discord.Intents.default()
intents.message_content = True  # Cần bật nếu bạn muốn đọc nội dung tin nhắn
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    print(f'Bot {bot.user} đã đăng nhập thành công trên Discord!')

# Đăng ký các lệnh/sự kiện từ các module (các hàm register_ cần được chuyển hướng theo discord.py)
#register_nct(bot)
#register_scl(bot)
register_girl(bot)
register_anime(bot)
register_images(bot)

if __name__ == '__main__':
    print("Khởi động bot Discord...")
    bot.run(TOKEN)
