import re
import requests
from bs4 import BeautifulSoup
import discord
from discord.ext import commands

def register_images(bot: commands.Bot):
    @bot.command(name="images")
    async def images(ctx, url: str = None):
        # Nếu không có URL được truyền vào, thông báo cho người dùng.
        if url is None:
            await ctx.send('Vui lòng cung cấp URL. Ví dụ: /images https://example.com')
            return

        # Kiểm tra URL có bắt đầu bằng http:// hoặc https:// không
        if not re.match(r'^https?://', url):
            await ctx.send('URL không hợp lệ. Hãy bắt đầu bằng http:// hoặc https://')
            return

        # Gửi tin nhắn thông báo đang tải và lưu lại đối tượng tin nhắn
        loading_msg = await ctx.send(f'Đang tải trang: {url} ...')
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()  # Kiểm tra lỗi HTTP nếu có.
        except Exception as e:
            await ctx.send(f'Không thể tải trang: {e}')
            return

        # Sau khi tải xong, xoá tin nhắn "Đang tải trang..."
        await loading_msg.delete()

        soup = BeautifulSoup(resp.text, 'html.parser')
        image_urls = []

        # Lấy các URL từ thẻ <img>
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src')
            if src:
                full_url = requests.compat.urljoin(resp.url, src)
                image_urls.append(full_url)

        # Lấy URL từ thuộc tính style (ví dụ: background-image)
        for tag in soup.find_all(style=True):
            style = tag['style']
            matches = re.findall(r'url["\']?(.*?)["\']?', style)
            for match in matches:
                full_url = requests.compat.urljoin(resp.url, match)
                image_urls.append(full_url)

        if not image_urls:
            await ctx.send('Không tìm thấy ảnh nào trên trang.')
            return

        # Đánh số các URL, chia theo nhóm (mỗi tin nhắn tối đa 30 dòng)
        # Dùng dấu < > quanh URL để tắt preview link của Discord
        numbered = [f"{i+1}. <{img_url}>" for i, img_url in enumerate(image_urls)]
        batch_size = 30
        for i in range(0, len(numbered), batch_size):
            chunk = "\n".join(numbered[i:i+batch_size])
            await ctx.send(chunk)
