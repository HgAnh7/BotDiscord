import os
import re
import zipfile
import requests
import tempfile
import urllib.parse
from bs4 import BeautifulSoup
import discord

def download_website(base_url: str, output_dir: str, max_files: int = 1000):
    """Tải xuống toàn bộ website và lưu vào thư mục đầu ra."""
    processed_urls = set()
    downloaded_files = []
    url_queue = [base_url]
    base_domain = urllib.parse.urlparse(base_url).netloc
    file_count = 0
    
    # Giới hạn kích thước file tối đa (50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # Sử dụng requests.Session() để connection pooling
    session = requests.Session()
    session.headers.update(headers)

    while url_queue and file_count < max_files:
        current_url = url_queue.pop(0)

        if current_url in processed_urls:
            continue

        processed_urls.add(current_url)
        parsed_url = urllib.parse.urlparse(current_url)
        if parsed_url.netloc and parsed_url.netloc != base_domain:
            continue

        try:
            response = session.get(current_url, timeout=30)
            if response.status_code != 200:
                continue

            # Kiểm tra kích thước file trước khi tải
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > MAX_FILE_SIZE:
                continue

            content_type = response.headers.get('Content-Type', '').lower()
            url_path = parsed_url.path
            if not url_path or url_path.endswith('/'):
                url_path += 'index.html'
            safe_path = re.sub(r'[?#].*$', '', url_path)

            file_path = os.path.join(output_dir, base_domain, safe_path.lstrip('/'))
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Kiểm tra kích thước nội dung thực tế
            content = response.content
            if len(content) > MAX_FILE_SIZE:
                continue

            with open(file_path, 'wb') as f:
                f.write(content)

            downloaded_files.append(file_path)
            file_count += 1

            if 'text/html' in content_type:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Tìm các link CSS
                for css_link in soup.find_all('link', rel='stylesheet'):
                    href = css_link.get('href')
                    if href:
                        css_url = urllib.parse.urljoin(current_url, href)
                        url_queue.append(css_url)

                # Tìm các script JS
                for script in soup.find_all('script', src=True):
                    script_url = urllib.parse.urljoin(current_url, script.get('src'))
                    url_queue.append(script_url)

                # Tìm các hình ảnh
                for img in soup.find_all('img', src=True):
                    img_url = urllib.parse.urljoin(current_url, img.get('src'))
                    url_queue.append(img_url)

                # Tìm các link khác cùng trang web
                for a_tag in soup.find_all('a', href=True):
                    link_url = urllib.parse.urljoin(current_url, a_tag.get('href'))
                    if urllib.parse.urlparse(link_url).netloc == base_domain:
                        url_queue.append(link_url)
        except Exception as e:
            print(f"Lỗi khi tải {current_url}: {e}")
            continue

    
    session.close()
    return downloaded_files

async def source_web_command(interaction: discord.Interaction, url: str) -> None:
    """Slash command để tải xuống source code của website và gửi file zip."""
    
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    await interaction.response.defer()

    try:
        domain = urllib.parse.urlparse(url).netloc
        zip_filename = f"{domain}_source.zip"

        with tempfile.TemporaryDirectory() as temp_dir:
            downloaded_files = download_website(url, temp_dir)

            if not downloaded_files:
                await interaction.followup.send("Không thể tải xuống nội dung từ trang web này.")
                return

            zip_path = os.path.join(temp_dir, zip_filename)
            added_files = set()

            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for file_path in downloaded_files:
                    relative_path = os.path.relpath(file_path, temp_dir)
                    if relative_path not in added_files:
                        zipf.write(file_path, relative_path)
                        added_files.add(relative_path)

            # Kiểm tra kích thước file ZIP
            zip_size = os.path.getsize(zip_path)
            max_discord_file_size = 8 * 1024 * 1024  # 8MB
            
            if zip_size > max_discord_file_size:
                await interaction.followup.send(f"File ZIP quá lớn ({zip_size / (1024*1024):.1f}MB). Giới hạn Discord là 8MB.")
                return

            # Gửi file zip
            with open(zip_path, 'rb') as file_obj:
                discord_file = discord.File(file_obj, filename=zip_filename)
                await interaction.followup.send(
                    content=f"Source code của {url} ({len(added_files)} files)",
                    file=discord_file
                )

    except Exception as e:
        await interaction.followup.send(f"Lỗi: {str(e)}")

def register_sourceweb(bot: discord.ext.commands.Bot):
    @bot.tree.command(name="sourceweb", description="Tải xuống source code của website")
    async def _sourceweb(interaction: discord.Interaction, url: str):
        await source_web_command(interaction, url)
