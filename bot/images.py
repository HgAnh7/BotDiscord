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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Referer": "https://meoden.net/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Connection": "keep-alive"
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

        def get_possible_img_src(img_tag):
            attrs_to_check = ["src", "data-src", "data-lazy", "data-original", "data-srcset"]
            for attr in attrs_to_check:
                src = img_tag.get(attr)
                if src:
                    return src
            return None

        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']

        for img in soup.find_all("img"):
            raw_src = get_possible_img_src(img)
            if raw_src:
                full_url = requests.compat.urljoin(resp.url, raw_src)
                if any(full_url.lower().split("?")[0].endswith(ext) for ext in valid_extensions):
                    image_urls.append(full_url)

        # Lấy ảnh từ CSS style="background-image: url(...)"
        for tag in soup.find_all(style=True):
            style = tag["style"]
            matches = re.findall(r'url\(["\']?(.*?)["\']?\)', style)
            for match in matches:
                full_url = requests.compat.urljoin(resp.url, match)
                if any(full_url.lower().split("?")[0].endswith(ext) for ext in valid_extensions):
                    image_urls.append(full_url)

        # Loại bỏ trùng lặp
        image_urls = list(dict.fromkeys(image_urls))

        if not image_urls:
            await ctx.send("Không tìm thấy ảnh hợp lệ từ trang tĩnh và Selenium chưa được thiết lập thêm.")
            return

        # Gửi các ảnh dạng danh sách số thứ tự
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