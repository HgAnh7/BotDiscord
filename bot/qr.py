import qrcode
import discord
from io import BytesIO
from discord import app_commands
from discord.ext import commands

class QRCode(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="qr", description="Tạo QR Code từ văn bản")
    async def generate_qr(self, interaction: discord.Interaction, text: str):
        # Kiểm tra độ dài text
        if len(text) > 2000:
            await interaction.response.send_message(
                "❌ Văn bản quá dài! Tối đa 2000 ký tự.", 
                ephemeral=True
            )
            return
        
        # Kiểm tra text trống
        if not text.strip():
            await interaction.response.send_message(
                "❌ Vui lòng nhập văn bản để tạo QR code!", 
                ephemeral=True
            )
            return
        
        buffer = None
        try:
            # Tạo QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=2,
            )
            qr.add_data(text)
            qr.make(fit=True)
            
            # Tạo image
            img = qr.make_image(fill_color="#d777f7", back_color="white")
            
            # Lưu vào buffer
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            
            # Gửi response
            await interaction.response.send_message(
                content=f"✅ QR code cho: `{text[:50]}{'...' if len(text) > 50 else ''}`",
                file=discord.File(fp=buffer, filename="qrcode.png")
            )
            
        except Exception as e:
            await interaction.response.send_message(
                "❌ Có lỗi khi tạo QR code. Vui lòng thử lại!",
                ephemeral=True
            )
            print(f"QR Code Error: {e}")  # Log lỗi cho admin
            
        finally:
            # Đóng buffer để tránh memory leak
            if buffer:
                buffer.close()

# Cách đăng ký Cog chuẩn
async def setup(bot):
    await bot.add_cog(QRCode(bot))

# Hoặc sử dụng hàm register cũ (nếu cần thiết)
def register_qr(bot):
    import asyncio
    asyncio.create_task(bot.add_cog(QRCode(bot)))
