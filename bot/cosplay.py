import io
import random
import discord
import requests
from discord.ext import commands

def register_cosplay(bot: commands.Bot):
    @bot.command(name='media')
    async def media(ctx):
        try:
            # Đọc danh sách URL từ file; file này chứa cả URL ảnh và video
            with open("bot/url/cosplay.txt", "r", encoding="utf-8") as f:
                urls = [line.strip() for line in f if line.strip()]
            if not urls:
                return await ctx.send("Danh sách media chưa có dữ liệu!")
            
            selected_url = random.choice(urls)
            
            # Thiết lập header User-Agent
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/98.0.4758.102 Safari/537.36"
                )
            }
            resp = requests.get(selected_url, headers=headers, timeout=30)
            resp.raise_for_status()
            
            # Xác định Content-Type và chọn file extension phù hợp
            content_type = resp.headers.get("Content-Type", "").lower()
            if "image/png" in content_type:
                ext = "png"
            elif "image/jpeg" in content_type:
                ext = "jpg"
            elif "image/gif" in content_type:
                ext = "gif"
            elif "video/mp4" in content_type:
                ext = "mp4"
            elif "video/webm" in content_type:
                ext = "webm"
            elif "video/ogg" in content_type:
                ext = "ogg"
            else:
                ext = "dat"  # Nếu không nhận dạng được, dùng một extension chung
            
            # Xác định kiểu file: nếu content_type chứa "video" thì là video, ngược lại là ảnh
            file_type = "video" if "video" in content_type else "ảnh"
            filename = f"{file_type}_file.{ext}"
            
            # Tạo file đính kèm từ nội dung tải về (không lưu ra đĩa)
            file_attachment = discord.File(io.BytesIO(resp.content), filename=filename)
            
            # Gửi file kèm theo thông báo tag người dùng
            await ctx.send(f"Đây là {file_type} đã tải về cho {ctx.author.mention}:", file=file_attachment)
            
            # Xóa tin nhắn lệnh của người dùng (nếu bot có quyền Manage Messages)
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                print("Bot không có quyền xóa tin nhắn của người dùng.")
            except Exception as e:
                print(f"Lỗi khi xóa tin nhắn: {e}")
                
        except Exception as e:
            await ctx.send(f"Lỗi: {e}")
