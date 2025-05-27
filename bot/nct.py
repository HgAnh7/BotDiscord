# bot/nct.py
import os
import re
import random
import discord
from discord.ext import commands
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

# --- CẤU HÌNH ---
BASE_URL = 'https://www.nhaccuatui.com'
API_SEARCH = BASE_URL + '/tim-kiem/bai-hat'

# Lưu tạm dữ liệu cho mỗi lần tìm kiếm theo user_id
nct_data = {}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]
ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "fr-FR,fr;q=0.9",
    "es-ES,es;q=0.9",
    "de-DE,de;q=0.9",
    "zh-CN,zh;q=0.9",
]

def get_headers():
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept-Language': random.choice(ACCEPT_LANGUAGES),
        'Referer': BASE_URL,
    }

def search_nhaccuatui(keyword, limit=10):
    params = {'q': keyword, 'b': 'keyword', 'l': 'tat-ca', 's': 'default'}
    try:
        resp = requests.get(API_SEARCH, params=params, headers=get_headers())
        resp.raise_for_status()
        html = resp.text
    except requests.exceptions.RequestException:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    items = soup.select('ul.sn_search_returns_list_song li.sn_search_single_song')[:limit]
    tracks = []
    for item in items:
        title_elem = item.select_one('h3.title_song a')
        artist_elem = item.select_one('h4.singer_song')
        detail_href = title_elem.get('href') if title_elem else None
        if title_elem and detail_href:
            # Phần ID vẫn lưu trong dict (nếu cần cho xử lý nội bộ) nhưng không hiển thị.
            track_id = detail_href.split('.')[-2]
            title = title_elem.get_text(separator=' ', strip=True)
            artist = 'Unknown'
            if artist_elem:
                artist_links = artist_elem.select('a')
                if artist_links:
                    artists = [a.get_text(separator=' ', strip=True) for a in artist_links]
                    artist = ', '.join(artists)
                else:
                    artist = artist_elem.get_text(separator=' ', strip=True)
            tracks.append({
                'title': title,
                'artist': artist,
                'id': track_id,
                'detail_url': urljoin(BASE_URL, detail_href)
            })
    return tracks

def get_download_url(track):
    detail_url = track.get('detail_url')
    if not detail_url:
        return None
    # Khởi tạo thumbnail mặc định là None
    track['thumbnail'] = None
    try:
        resp = requests.get(detail_url, headers=get_headers())
        resp.raise_for_status()
        html = resp.text
    except requests.exceptions.RequestException:
        return None
    try:
        soup = BeautifulSoup(html, 'html.parser')
        og_image = soup.select_one('meta[property="og:image"]')
        if og_image and og_image.has_attr('content'):
            thumb_url = og_image['content'].strip()
            if thumb_url.startswith('//'):
                thumb_url = 'https:' + thumb_url
            track['thumbnail'] = thumb_url
    except Exception:
        track['thumbnail'] = None

    xml_match = re.search(
        r"peConfig\.xmlURL\s*=\s*['\"](https://www\.nhaccuatui\.com/flash/xml\?html5=true&key1=[^'\"]+)['\"]",
        html
    )
    if not xml_match:
        return None
    xml_url = xml_match.group(1)
    try:
        xml_resp = requests.get(xml_url, headers={**get_headers(), 'Referer': detail_url})
        xml_resp.raise_for_status()
        xml_content = xml_resp.text
    except requests.exceptions.RequestException:
        return None
    try:
        root = ET.fromstring(xml_content)
        loc = root.find('.//location')
        if loc is not None and loc.text:
            audio_url = loc.text.strip()
            if audio_url.startswith('//'):
                audio_url = 'https:' + audio_url
            elif audio_url.startswith('http://'):
                audio_url = 'https://' + audio_url[len('http://'):]
            return audio_url
    except ET.ParseError:
        return None
    return None

# Discord View cho buttons
class NhacCuaTuiView(discord.ui.View):
    def __init__(self, songs, user_id):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.songs = songs
        self.user_id = user_id
        
        # Tạo buttons (maximum 25 buttons per view)
        for i in range(min(len(songs), 25)):
            button = discord.ui.Button(
                label=str(i + 1),
                style=discord.ButtonStyle.primary,
                custom_id=f"nct_{i}"
            )
            button.callback = self.button_callback
            self.add_item(button)
    
    async def button_callback(self, interaction: discord.Interaction):
        try:
            # Kiểm tra quyền truy cập
            if interaction.user.id != self.user_id:
                await interaction.response.send_message(
                    "❌ Bạn không có quyền sử dụng nút này!",
                    ephemeral=True
                )
                return
            
            # Parse button index
            song_index = int(interaction.data['custom_id'].split('_')[1])
            
            # Kiểm tra index hợp lệ
            if song_index < 0 or song_index >= len(self.songs):
                await interaction.response.send_message(
                    "❌ Lựa chọn không hợp lệ!",
                    ephemeral=True
                )
                return
            
            song = self.songs[song_index]
            
            # Response với loading message
            await interaction.response.edit_message(
                content=f"🧭 Đang tải: **{song['title']}**\n👤 Nghệ sĩ: {song['artist']}\n\n⏳ Vui lòng chờ...",
                view=None
            )
            
            # Lấy audio URL
            audio_url = get_download_url(song)
            
            if not audio_url:
                await interaction.edit_original_response(
                    content="🚫 Không thể tải bài hát này."
                )
                return
            
            thumbnail_url = song.get('thumbnail')
            
            # Tạo embed cho thông tin bài hát
            embed = discord.Embed(
                title=song['title'],
                description=f"**Nghệ sĩ:** {song['artist']}\n**Nguồn:** NhacCuaTui",
                color=0x00ff00  # Green color for NhacCuaTui
            )
            
            if thumbnail_url:
                embed.set_thumbnail(url=thumbnail_url)
            
            try:
                # Gửi embed với thông tin bài hát
                await interaction.followup.send(embed=embed)
                
                # Gửi audio bằng URL trực tiếp
                await interaction.followup.send(audio_url)
                
                # Xóa tin nhắn kết quả tìm kiếm
                try:
                    await interaction.delete_original_response()
                except Exception:
                    pass
                    
            except Exception as e:
                await interaction.edit_original_response(
                    content=f"🚫 Không thể gửi audio: {str(e)}"
                )
                
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Có lỗi xảy ra: {str(e)}",
                ephemeral=True
            )
            print(f"Error in button callback: {e}")
    
    async def on_timeout(self):
        # Disable all buttons when timeout
        for item in self.children:
            item.disabled = True

def register_nct(bot):
    """
    Đăng ký lệnh /nct cho Discord bot
    """
    
    @bot.command(name='nct')
    async def nhaccuatui(ctx, *, keyword: str = None):
        if not keyword:
            await ctx.reply(
                '🚫 Vui lòng nhập tên bài hát muốn tìm kiếm.\nVí dụ: `/nct Tên bài hát`'
            )
            return

        keyword = keyword.strip()
        results = search_nhaccuatui(keyword)
        
        if not results:
            await ctx.reply(f'🚫 Không tìm thấy bài hát nào với từ khóa: {keyword}')
            return

        songs = results[:10]
        
        # Tạo embed cho kết quả tìm kiếm
        embed = discord.Embed(
            title="🎵 Kết quả tìm kiếm trên Nhaccuatui",
            color=0x00ff00
        )
        
        # Thêm thông tin các bài hát
        description = ""
        for i, song in enumerate(songs, 1):
            description += f"**{i}. {song['title']}**\n"
            description += f"👤 Nghệ sĩ: {song['artist']}\n\n"
        
        description += "**💡 Chọn bài hát bạn muốn tải:**"
        embed.description = description

        # Tạo view với buttons
        view = NhacCuaTuiView(songs, ctx.author.id)
        
        # Gửi message với embed và view
        await ctx.reply(embed=embed, view=view)

# Sử dụng:
# intents = discord.Intents.default()
# intents.message_content = True
# bot = commands.Bot(command_prefix='/', intents=intents)
# register_nct(bot)
# bot.run('YOUR_BOT_TOKEN')