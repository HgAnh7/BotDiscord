import re
import discord
import requests
import asyncio
from bs4 import BeautifulSoup
from discord.ext import commands

async def send_and_delete(ctx, content: str, delay: int = 60):
    # Gửi tin nhắn followup và chờ nhận được đối tượng Message
    msg = await ctx.followup.send(content, wait=True)
    # Đợi delay giây rồi xoá tin nhắn đó
    await asyncio.sleep(delay)
    await msg.delete()

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

        # Gửi tin nhắn thông báo đang tải trang (ephemeral: chỉ hiển thị cho người dùng)
        await ctx.response.send_message(f"Đang tải trang: {url}", ephemeral=True)

        headers = {
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36")
        }
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            # Nếu có lỗi, gửi tin nhắn lỗi và tự xoá sau 60 giây
            await send_and_delete(ctx, f"Không thể tải trang: {e}", delay=60)
            return

        # Phân tích nội dung trang với BeautifulSoup và thu thập các URL ảnh
        soup = BeautifulSoup(resp.text, "html.parser")
        image_urls = []

        # Lấy các ảnh từ thẻ <img>
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src")
            if src:
                full_url = requests.compat.urljoin(resp.url, src)
                image_urls.append(full_url)

        # Lấy các ảnh từ thuộc tính style có chứa url(...)
        for tag in soup.find_all(style=True):
            style = tag.get("style", "")
            # Dùng regex bắt đúng cú pháp CSS: url("...") hoặc url('...')
            matches = re.findall(r'url["\']?(.*?)["\']?', style)
            for match in matches:
                full_url = requests.compat.urljoin(resp.url, match)
                image_urls.append(full_url)

        # Loại bỏ các URL trùng (giữ thứ tự ban đầu)
        image_urls = list(dict.fromkeys(image_urls))

        # Xoá tin nhắn thông báo "Đang tải trang: {url}" khi tải trang thành công
        await ctx.delete_original_response()

        # Nếu không tìm thấy URL ảnh nào
        if not image_urls:
            await send_and_delete(ctx, f"Không tìm thấy URL ảnh nào từ trang {url}", delay=60)
            return

        # Đánh số các URL ảnh và chia thành các nhóm (chunk) nếu quá 2000 ký tự mỗi tin nhắn
        numbered = [f"{i+1}. <{img_url}>" for i, img_url in enumerate(image_urls)]
        current_chunk = ""
        for line in numbered:
            if len(current_chunk) + len(line) + 1 > 2000:
                await send_and_delete(ctx, current_chunk, delay=60)
                current_chunk = line + "\n"
            else:
                current_chunk += line + "\n"
        if current_chunk:
            await send_and_delete(ctx, current_chunk, delay=60)