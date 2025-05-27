import os
import discord
from discord.ext import commands
#from bot.nct import register_nct
from bot.scl import register_scl
from bot.img import register_img
from bot.girl import register_girl
from bot.anime import register_anime
from bot.emoji import register_emoji
from bot.images import register_images
from bot.cosplay import register_cosplay

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True  # Cần bật nếu bạn muốn đọc nội dung tin nhắn
bot = commands.Bot(command_prefix="/", intents=intents)

# Bảng ánh xạ tên slash command -> danh sách các channel ID được phép sử dụng
# Lưu ý: Tên này phải khớp với tên command khi bạn đăng ký chúng (không phân biệt chữ hoa thường)
slash_command_allowed_channels = {
    "scl": [1375498235832959097, 1375707367051886654],  # Thay bằng ID thực tế của kênh cho lệnh scl_command
    #"img": [987654321098765432],    # Tương tự với lệnh img_command
    "girl": [1375498235832959097, 1375707367051886654],
    "anime": [1375498235832959097, 1375707367051886654],
    # Thêm các lệnh slash khác nếu cần.
    # Nếu một lệnh không có mục mapping ở đây, lệnh đó sẽ không bị hạn chế.
}

# Định nghĩa hàm check toàn cục cho slash commands
async def global_slash_commands_channel_check(interaction: discord.Interaction) -> bool:
    # Nếu lệnh chưa được xác định (thường là các tương tác không liên quan đến lệnh), cho phép luôn.
    if interaction.command is None:
        return True

    cmd_name = interaction.command.name.lower()  # Lấy tên lệnh, chuyển về chữ thường để thống nhất
    allowed_channels = slash_command_allowed_channels.get(cmd_name)

    # Nếu không có cài đặt hạn chế cho lệnh này, cho phép dùng ở mọi kênh.
    if allowed_channels is None:
        return True

    # Kiểm tra nếu kênh hiện tại nằm trong danh sách cho phép hay không
    if interaction.channel and (interaction.channel.id in allowed_channels):
        return True
    else:
        # Gửi thông báo lỗi cho người dùng nếu giao diện chưa được phản hồi
        try:
            await interaction.response.send_message(
                "Lệnh này không được sử dụng tại kênh hiện tại!", ephemeral=True
            )
        except discord.InteractionResponded:
            # Nếu đã phản hồi rồi, bỏ qua.
            pass
        return False

# Đăng ký global check cho tất cả slash commands
bot.tree.add_check(global_slash_commands_channel_check)

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
register_images(bot)
register_cosplay(bot)

if __name__ == '__main__':
    print("Bot Discord đang hoạt động...")
    bot.run(TOKEN)