import re
import discord
import requests
from bs4 import BeautifulSoup
from discord.ext import commands

def register_images(bot: commands.Bot):
    @bot.tree.command(name="images", description="Lấy tất cả URL ảnh từ một trang web")
    async def images(ctx: discord.Interaction, url: str):
        # Kiểm tra xem URL có hợp lệ không
        if not re.match(r'^https?://', url):
            await ctx.response.send_message(
                "URL không hợp lệ. Hãy bắt đầu bằng http:// hoặc https://",
                ephemeral=True
            )
            return

        # Thông báo đang tải trang (ephemeral -> chỉ hiển thị với người dùng nên không cần xoá)
        await ctx.response.send_message(f"Đang tải trang: {url}", ephemeral=True)

        headers = {
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36")
        }
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            # Dùng followup với delete_after để tự xoá tin nhắn lỗi sau 60 giây
            await ctx.followup.send(f"Không thể tải trang: {e}", delete_after=60)
            return

        # Phân tích nội dung trang với BeautifulSoup và thu thập các URL ảnh
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

        # Loại bỏ các URL trùng (order preserved)
        image_urls = list(dict.fromkeys(image_urls))

        # Nếu không có ảnh, thông báo qua followup với delete_after
        if not image_urls:
            await ctx.followup.send(
                f"Không tìm thấy URL ảnh nào từ trang {url}",
                delete_after=60
            )
            return

        # Đánh số các URL ảnh, chia thành các khối (chunk) nếu vượt quá 2000 ký tự mỗi tin nhắn
        numbered = [f"{i+1}. <{img_url}>" for i, img_url in enumerate(image_urls)]
        current_chunk = ""
        for line in numbered:
            if len(current_chunk) + len(line) + 1 > 2000:
                await ctx.followup.send(current_chunk, delete_after=60)
                current_chunk = line + "\n"
            else:
                current_chunk += line + "\n"
        if current_chunk:
            await ctx.followup.send(current_chunk, delete_after=60)