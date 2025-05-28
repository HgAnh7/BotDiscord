import re
import discord
import requests
import asyncio
from bs4 import BeautifulSoup
from discord.ext import commands

def schedule_deletion(message: discord.Message, delay: int = 60):
    """Lên lịch xoá tin nhắn sau delay giây mà không block luồng chính."""
    async def delete_task():
        await asyncio.sleep(delay)
        await message.delete()
    asyncio.create_task(delete_task())

async def send_and_schedule_deletion(ctx, content: str, delay: int = 60):
    """
    Gửi tin nhắn followup; trả về ngay sau khi gửi được message,
    đồng thời lên lịch xoá tin nhắn sau delay giây.
    """
    msg = await ctx.followup.send(content, wait=True)
    schedule_deletion(msg, delay)

def register_images(bot: commands.Bot):
    @bot.tree.command(name="images", description="Lấy tất cả URL ảnh từ một trang web")
    async def images(ctx: discord.Interaction, url: str):
        # Kiểm tra URL hợp lệ
        if not re.match(r'^https?://', url):
            await ctx.response.send_message(
                "URL không hợp lệ. Hãy bắt đầu bằng http:// hoặc https://",
                ephemeral=True
            )
            return

        # Gửi tin nhắn thông báo đang tải trang (ephemeral: chỉ hiển thị riêng cho người dùng)
        await ctx.response.send_message(f"Đang tải trang: {url}", ephemeral=True)

        headers = {
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36")
        }
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            # Nếu có lỗi, gửi tin nhắn lỗi và lên lịch xoá (sẽ hiển thị ngay)
            await send_and_schedule_deletion(ctx, f"Không thể tải trang: {e}", delay=30)
            return

        # Phân tích dữ liệu HTML để thu thập URL ảnh
        soup = BeautifulSoup(resp.text, "html.parser")
        image_urls = []

        # Thu thập từ thẻ <img>
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src")
            if src:
                full_url = requests.compat.urljoin(resp.url, src)
                image_urls.append(full_url)

        # Thu thập từ thuộc tính style chứa cú pháp url(...)
        for tag in soup.find_all(style=True):
            style = tag.get("style", "")
            # Dùng regex bắt đúng cú pháp CSS: url("...") hoặc url('...')
            matches = re.findall(r'url["\']?(.*?)["\']?', style)
            for match in matches:
                full_url = requests.compat.urljoin(resp.url, match)
                image_urls.append(full_url)

        # Loại bỏ các URL trùng lặp, giữ nguyên thứ tự xuất hiện
        image_urls = list(dict.fromkeys(image_urls))

        # Xoá tin nhắn thông báo "Đang tải trang: {url}" khi tải thành công
        await ctx.delete_original_response()

        # Nếu không có URL nào được thu thập
        if not image_urls:
            await send_and_schedule_deletion(ctx, f"Không tìm thấy URL ảnh nào từ trang {url}", delay=30)
            return

        # Đánh số các URL và chia thành các nhóm (chunk) không vượt quá 2000 ký tự mỗi tin nhắn
        numbered = [f"{i+1}. <{img_url}>" for i, img_url in enumerate(image_urls)]
        chunks = []
        current_chunk = ""
        for line in numbered:
            if len(current_chunk) + len(line) + 1 > 2000:
                chunks.append(current_chunk)
                current_chunk = line + "\n"
            else:
                current_chunk += line + "\n"
        if current_chunk:
            chunks.append(current_chunk)

        # Gửi tất cả các tin nhắn chứa URL ngay lập tức (không block lẫn nhau nhờ việc lên lịch xoá nền)
        tasks = [asyncio.create_task(send_and_schedule_deletion(ctx, chunk, delay=300))
                 for chunk in chunks]
        # Nếu cần chờ các task hoàn thành, có thể gather()
        await asyncio.gather(*tasks)