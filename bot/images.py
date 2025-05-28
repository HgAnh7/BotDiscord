import re
import time
import requests
import discord
from bs4 import BeautifulSoup
from discord.ext import commands

def register_images(bot: commands.Bot):
    @bot.command(name="images")
    async def images(ctx, url: str = None):
        if url is None:
            await ctx.send("Vui lòng cung cấp URL. Ví dụ: !images https://example.com")
            return

        if not re.match(r'^https?://', url):
            await ctx.send("URL không hợp lệ. Hãy bắt đầu bằng http:// hoặc https://")
            return

        loading_msg = await ctx.send(f"Đang tải trang: {url} ...")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:112.0) Gecko/20100101 Firefox/112.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        }
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            await ctx.send(f"Không thể tải trang: {e}")
            return

        await loading_msg.delete()

        # Phân tích nội dung trang với BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        image_urls = []

        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src")
            if src:
                full_url = requests.compat.urljoin(resp.url, src)
                image_urls.append(full_url)

        for tag in soup.find_all(style=True):
            style = tag["style"]
            matches = re.findall(r'url["\']?(.*?)["\']?', style)
            for match in matches:
                full_url = requests.compat.urljoin(resp.url, match)
                image_urls.append(full_url)

        image_urls = list(dict.fromkeys(image_urls))
        # Nếu không có ảnh, có thể xem xét dùng Selenium để xử lý trang động
        if not image_urls:
            # [Xử lý với Selenium nếu cần...]
            await ctx.send("Không tìm thấy ảnh nào từ trang tĩnh và Selenium chưa được thiết lập thêm.")
            return

        numbered = [f"{i+1}. <{img_url}>" for i, img_url in enumerate(image_urls)]
        current_chunk = ""
        for line in numbered:
            if len(current_chunk) + len(line) + 1 > 2000:
                await ctx.send(current_chunk)
                current_chunk = line + "\n"
            else:
                current_chunk += line + "\n"
        if current_chunk:
            await ctx.send(current_chunk)