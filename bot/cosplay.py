import io
import random
import discord
import requests
from discord.ext import commands

def register_cosplay(bot: commands.Bot):
    @bot.tree.command(name="cosplay", description="Gửi ảnh cosplay ngẫu nhiên")
    async def cosplay(interaction: discord.Interaction):
        # Xác nhận tương tác ngay để được thêm thời gian xử lý.
        await interaction.response.defer()
        try:
            # Đọc danh sách URL ảnh từ file
            with open("bot/url/cosplay.txt", "r", encoding="utf-8") as f:
                image_urls = [line.strip() for line in f if line.strip()]
            if not image_urls:
                return await interaction.followup.send("Danh sách ảnh chưa có dữ liệu!")
            
            # Chọn ngẫu nhiên một URL và tải ảnh
            selected_image_url = random.choice(image_urls)
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/98.0.4758.102 Safari/537.36"
                )
            }
            resp = requests.get(selected_image_url, headers=headers, timeout=30)
            resp.raise_for_status()
            
            # Xác định phần mở rộng file dựa trên Content-Type của ảnh
            content_type = resp.headers.get("Content-Type", "")
            if "image/png" in content_type:
                ext = "png"
            elif "image/jpeg" in content_type:
                ext = "jpg"
            elif "image/gif" in content_type:
                ext = "gif"
            elif "image/webp" in content_type:
                ext = "webp"
            else:
                ext = "jpg"  # Mặc định nếu không xác định được
            
            image_file = discord.File(io.BytesIO(resp.content), filename=f"cosplay_image.{ext}")
            await interaction.followup.send(f"Đây là ảnh cosplay ngẫu nhiên cho {interaction.user.mention}:", file=image_file)
            
        except Exception as e:
            await interaction.followup.send(f"Lỗi: {e}")