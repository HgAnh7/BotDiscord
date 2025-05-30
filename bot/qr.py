import os
import qrcode
import discord
from io import BytesIO
from discord.ext import commands

def register_qr(bot: commands.Bot):
    @bot.tree.command(name="qr", description="Tạo QR code từ nội dung được cung cấp.")
    async def slash_qr(interaction: discord.Interaction, content: str):
        # Defer response để tránh timeout
        await interaction.response.defer()
        
        try:
            # Kiểm tra độ dài content
            if len(content) > 2000:
                await interaction.followup.send("❌ Nội dung quá dài! Tối đa 2000 ký tự.", ephemeral=True)
                return
            
            if not content.strip():
                await interaction.followup.send("❌ Vui lòng nhập nội dung để tạo QR code!", ephemeral=True)
                return
            
            # Tạo QR code với cấu hình tối ưu
            qr_obj = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,  # Tăng error correction
                box_size=10,
                border=2,  # Tăng border để dễ scan hơn
            )
            
            qr_obj.add_data(content)
            qr_obj.make(fit=True)
            
            # Tạo ảnh với màu tùy chỉnh
            img = qr_obj.make_image(fill_color="#d777f7", back_color="white")
            
            # Lưu ảnh vào buffer
            buffer = BytesIO()
            img.save(buffer, format="PNG", optimize=True)
            buffer.seek(0)
            
            # Tạo file Discord
            file = discord.File(fp=buffer, filename=f"qr_{interaction.user.id}.png")
            
            # Tạo embed đẹp mắt
            embed = discord.Embed(
                title="🔳 QR Code",
                description=f"QR code cho: `{content[:100]}{'...' if len(content) > 100 else ''}`",
                color=0xd777f7
            )
            embed.set_footer(text=f"Tạo bởi {interaction.user.display_name}")
            
            await interaction.followup.send(embed=embed, file=file)
            
        except qrcode.exceptions.DataOverflowError:
            await interaction.followup.send("❌ Nội dung quá phức tạp hoặc quá dài để tạo QR code!", ephemeral=True)
        except Exception as e:
            print(f"Lỗi tạo QR code: {e}")
            await interaction.followup.send("❌ Có lỗi xảy ra khi tạo QR code. Vui lòng thử lại!", ephemeral=True)
        finally:
            # Đảm bảo đóng buffer
            try:
                buffer.close()
            except:
                pass

# Thêm command để tạo QR code với URL
def register_qrurl(bot: commands.Bot):
    @bot.tree.command(name="qrurl", description="Tạo QR code từ URL.")
    async def slash_qr_url(interaction: discord.Interaction, url: str):
        await interaction.response.defer()
        
        try:
            # Kiểm tra URL format cơ bản
            if not (url.startswith('http://') or url.startswith('https://')):
                url = 'https://' + url
            
            # Tạo QR code cho URL
            qr_obj = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=2,
            )
            
            qr_obj.add_data(url)
            qr_obj.make(fit=True)
            
            img = qr_obj.make_image(fill_color="#4CAF50", back_color="white")
            
            buffer = BytesIO()
            img.save(buffer, format="PNG", optimize=True)
            buffer.seek(0)
            
            file = discord.File(fp=buffer, filename=f"qr_url_{interaction.user.id}.png")
            
            embed = discord.Embed(
                title="🌐 QR Code - URL",
                description=f"QR code cho: {url}",
                color=0x4CAF50
            )
            embed.set_footer(text=f"Tạo bởi {interaction.user.display_name}")
            
            await interaction.followup.send(embed=embed, file=file)
            
        except Exception as e:
            print(f"Lỗi tạo QR URL: {e}")
            await interaction.followup.send("❌ Có lỗi xảy ra khi tạo QR code URL!", ephemeral=True)
        finally:
            try:
                buffer.close()
            except:
                pass
