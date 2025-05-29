import re
import discord
import requests
from bs4 import BeautifulSoup
from discord.ext import commands

def register_images(bot: commands.Bot):
    @bot.tree.command(name="images", description="Lấy tất cả URL ảnh từ một trang web")
    async def images(ctx: discord.Interaction, url: str):
        # Tự động thêm https:// nếu thiếu
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
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
            # Nếu có lỗi, gửi tin nhắn lỗi
            await ctx.followup.send(f"Không thể tải trang: {e}")
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
            matches = re.findall(r'url\(["\']?(.*?)["\']?\)', style)
            for match in matches:
                full_url = requests.compat.urljoin(resp.url, match)
                image_urls.append(full_url)
        
        # Loại bỏ các URL trùng lặp, giữ nguyên thứ tự xuất hiện
        image_urls = list(dict.fromkeys(image_urls))
        
        # Nếu không có URL nào được thu thập
        if not image_urls:
            await ctx.followup.send(f"Không tìm thấy URL ảnh nào từ trang {url}")
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
        
        # Gửi tất cả các tin nhắn chứa URL ngay lập tức
        for chunk in chunks:
            await ctx.followup.send(chunk)
