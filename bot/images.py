import re
import discord
import requests
from bs4 import BeautifulSoup
from discord.ext import commands

# Hàm đăng ký lệnh /images với tham số limit
def register_images(bot: commands.Bot):
    @bot.tree.command(
        name="images",
        description="Lấy một số lượng URL ảnh nhất định từ một trang web"
    )
    async def images(
        ctx: discord.Interaction,
        url: str,
        limit: int  # Số lượng URL ảnh cần lấy
    ):
        # Kiểm tra limit có hợp lệ không
        if limit <= 0:
            await ctx.response.send_message(
                "Vui lòng nhập `limit` là một số nguyên dương.", ephemeral=True
            )
            return

        # Tự động thêm https:// nếu thiếu
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        # Thông báo đang tải trang (chỉ người dùng hiện tại nhìn thấy)
        await ctx.response.send_message(
            f"Đang tải trang: {url} (giới hạn {limit} ảnh)", 
            ephemeral=True
        )

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"
            )
        }

        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            await ctx.followup.send(f"Không thể tải trang: {e}")
            return

        # Phân tích HTML và thu thập URL ảnh
        soup = BeautifulSoup(resp.text, "html.parser")
        image_urls = []

        # Lấy từ thẻ <img>
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src")
            if src:
                full_url = requests.compat.urljoin(resp.url, src)
                image_urls.append(full_url)

        # Lấy từ thuộc tính style có url(...)
        for tag in soup.find_all(style=True):
            style = tag.get("style", "")
            matches = re.findall(r'url\(["\']?(.*?)["\']?\)', style)
            for match in matches:
                full_url = requests.compat.urljoin(resp.url, match)
                image_urls.append(full_url)

        # Loại bỏ trùng lặp, giữ nguyên thứ tự
        image_urls = list(dict.fromkeys(image_urls))

        if not image_urls:
            await ctx.followup.send(f"Không tìm thấy URL ảnh nào từ trang {url}")
            return

        total_found = len(image_urls)
        # Cắt danh sách theo limit nếu cần
        if limit < total_found:
            image_urls = image_urls[:limit]
        else:
            limit = total_found

        # Đánh số và chia thành chunk (mỗi tin nhắn tối đa 2000 ký tự)
        numbered = [f"{i+1}. {img_url}" for i, img_url in enumerate(image_urls)]
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

        # Thông báo tổng số ảnh và số ảnh thực tế đang hiển thị
        await ctx.followup.send(
            f"Đã tìm thấy tổng cộng {total_found} URL ảnh. "
            f"Hiển thị {limit} ảnh đầu tiên:"
        )

        # Gửi tất cả các chunk
        for chunk in chunks:
            await ctx.followup.send(chunk)