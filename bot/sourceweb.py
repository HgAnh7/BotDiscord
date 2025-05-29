import os
import re
import requests
import zipfile
import tempfile
import logging
import urllib.parse
import warnings
from bs4 import BeautifulSoup
import discord

logging.basicConfig(level=logging.CRITICAL)
warnings.filterwarnings("ignore")


def download_website(base_url: str, output_dir: str, max_files: int = 1000):
    """Tải toàn bộ website và lưu vào thư mục output_dir."""
    processed, files = set(), []
    queue = [base_url]
    base_domain = urllib.parse.urlparse(base_url).netloc
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/91.0.4472.124 Safari/537.36"
    }

    while queue and len(files) < max_files:
        url = queue.pop(0)
        if url in processed:
            continue
        processed.add(url)

        parsed = urllib.parse.urlparse(url)
        if parsed.netloc and parsed.netloc != base_domain:
            continue

        try:
            resp = requests.get(url, headers=headers)
            if resp.status_code != 200:
                continue

            content_type = resp.headers.get("Content-Type", "").lower()
            path = parsed.path or "/"
            if path.endswith("/"):
                path += "index.html"
            safe_path = re.sub(r"[?#].*$", "", path)
            file_path = os.path.join(output_dir, base_domain, safe_path.lstrip("/"))
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, "wb") as f:
                f.write(resp.content)
            files.append(file_path)

            if "text/html" in content_type:
                soup = BeautifulSoup(resp.text, "html.parser")
                for tag, attr in [("link", "href"), ("script", "src"), ("img", "src"), ("a", "href")]:
                    for el in soup.find_all(tag, **{attr: True}):
                        link = el.get(attr)
                        if not link:
                            continue
                        abs_url = urllib.parse.urljoin(url, link)
                        if tag == "a" and urllib.parse.urlparse(abs_url).netloc != base_domain:
                            continue
                        queue.append(abs_url)
        except Exception:
            continue

    return files


async def source_web_command(interaction: discord.Interaction, url: str) -> None:
    """
    Slash command để tải source code của website và gửi file zip.
    Ví dụ: /sourceweb https://example.com
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    await interaction.response.defer()

    try:
        domain = urllib.parse.urlparse(url).netloc
        zip_filename = f"{domain}_source.zip"
        with tempfile.TemporaryDirectory() as temp_dir:
            downloaded = download_website(url, temp_dir)
            if not downloaded:
                await interaction.followup.send(
                    "Không thể tải xuống nội dung từ trang web. Kiểm tra URL và thử lại."
                )
                return

            zip_path = os.path.join(temp_dir, zip_filename)
            unique_files = {}
            for f in downloaded:
                rel = os.path.relpath(f, temp_dir)
                unique_files.setdefault(rel, f)
            with zipfile.ZipFile(zip_path, "w") as zipf:
                for rel, f in unique_files.items():
                    zipf.write(f, rel)

            with open(zip_path, "rb") as file_obj:
                discord_file = discord.File(file_obj, filename=zip_filename)
                await interaction.followup.send(
                    content=f"Source code của {url} ({len(unique_files)} files)",
                    file=discord_file
                )
            print(f"Đã tải source web: {url} ({len(unique_files)} files)")
    except Exception as e:
        await interaction.followup.send(f"Lỗi khi tải xuống: {str(e)}")


def register_sourceweb(bot: discord.ext.commands.Bot):
    @bot.tree.command(
        name="sourceweb",
        description="Tải xuống source code của website dưới dạng file zip"
    )
    async def _sourceweb(interaction: discord.Interaction, url: str):
        await source_web_command(interaction, url)