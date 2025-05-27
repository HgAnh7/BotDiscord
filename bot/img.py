# bot/img.py
import io
import requests
import discord
from discord.ext import commands

def register_img(bot):
    @bot.command(name="img")
    async def img(ctx, url: str = None):
        if url is None:
            await ctx.send("Vui lòng cung cấp URL của ảnh. Ví dụ: `/img https://example.com/anh.jpg`")
            return

        # Thêm header User-Agent để tránh bị chặn
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/98.0.4758.102 Safari/537.36"
            )
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()  # Kiểm tra lỗi HTTP nếu có
        except Exception as e:
            await ctx.send(f"Không thể tải ảnh từ URL: {e}")
            return

        # Xác định phần mở rộng file từ header Content-Type (mặc định là jpg)
        ext = "jpg"
        content_type = response.headers.get("Content-Type", "")
        if "image/png" in content_type:
            ext = "png"
        elif "image/jpeg" in content_type:
            ext = "jpg"
        elif "image/gif" in content_type:
            ext = "gif"

        # Tạo file đính kèm từ nội dung ảnh ở bộ nhớ, không cần lưu ra đĩa
        image_file = discord.File(io.BytesIO(response.content), filename=f"downloaded_image.{ext}")
        
        # Gửi tin nhắn kèm theo file ảnh; dùng ctx.author.mention để tag người dùng
        await ctx.send(f"Đây là ảnh đã tải về cho {ctx.author.mention}:", file=image_file)
        
        # Xóa tin nhắn của người dùng đã sử dụng lệnh /img
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            print("Bot không có quyền xóa tin nhắn của người dùng.")
        except Exception as e:
            print(f"Xuất hiện lỗi khi xóa tin nhắn: {e}")
