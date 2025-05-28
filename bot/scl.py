# bot/scl.py
import io
import os
import re
import json
import random
import discord
import requests

# Biến toàn cục và cấu hình
API_BASE = "https://api-v2.soundcloud.com"
CONFIG_PATH = "config.json"
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

def get_random_element(array):
    return random.choice(array)

def get_headers():
    return {
        "User-Agent": get_random_element(USER_AGENTS),
        "Accept-Language": get_random_element(ACCEPT_LANGUAGES),
        "Referer": "https://soundcloud.com/",
        "Upgrade-Insecure-Requests": "1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }

def get_client_id():
    try:
        config = {}
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            if config.get('client_id'):
                return config['client_id']

        response = requests.get("https://soundcloud.com/", headers=get_headers())
        response.raise_for_status()
        script_tags = re.findall(r'<script crossorigin src="([^"]+)"', response.text)
        script_urls = [url for url in script_tags if url.startswith("https")]

        if not script_urls:
            raise ValueError("No script URLs found")

        script_response = requests.get(script_urls[-1], headers=get_headers())
        script_response.raise_for_status()
        client_id_match = re.search(r',client_id:"([^"]+)"', script_response.text)
        if not client_id_match:
            raise ValueError("Client ID not found in script")

        client_id = client_id_match.group(1)
        config['client_id'] = client_id
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        return client_id
    except Exception as e:
        print(f"Error fetching client ID: {e}")
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            return config.get('client_id', 'W00nmY7TLer3uyoEo1sWK3Hhke5Ahdl9')
        return 'W00nmY7TLer3uyoEo1sWK3Hhke5Ahdl9'

def get_music_info(question, limit=10):
    try:
        client_id = get_client_id()
        response = requests.get(
            f"{API_BASE}/search/tracks",
            params={
                "q": question,
                "variant_ids": "",
                "facet": "genre",
                "client_id": client_id,
                "limit": limit,
                "offset": 0,
                "linked_partitioning": 1,
                "app_locale": "en",
            },
            headers=get_headers()
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching music info: {e}")
        return None

def get_music_stream_url(track):
    try:
        client_id = get_client_id()
        api_url = f"{API_BASE}/resolve?url={track['permalink_url']}&client_id={client_id}"
        response = requests.get(api_url, headers=get_headers())
        response.raise_for_status()
        data = response.json()
        progressive_url = next(
            (t['url'] for t in data.get('media', {}).get('transcodings', []) if t['format']['protocol'] == 'progressive'),
            None
        )
        if not progressive_url:
            raise ValueError("No progressive transcoding URL found")
        stream_response = requests.get(
            f"{progressive_url}?client_id={client_id}&track_authorization={data.get('track_authorization', '')}",
            headers=get_headers()
        )
        stream_response.raise_for_status()
        return stream_response.json()['url']
    except Exception as e:
        print(f"Error getting music stream URL: {e}")
        return None

# Discord View cho buttons
class SoundCloudView(discord.ui.View):
    def __init__(self, tracks, user_id):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.tracks = tracks
        self.user_id = user_id
        
        # Tạo buttons (maximum 25 buttons per view)
        for i in range(min(len(tracks), 25)):
            button = discord.ui.Button(
                label=str(i + 1),
                style=discord.ButtonStyle.primary,
                custom_id=f"scl_{i}"
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
            track_index = int(interaction.data['custom_id'].split('_')[1])
            
            # Kiểm tra index hợp lệ
            if track_index >= len(self.tracks):
                await interaction.response.send_message(
                    "❌ Lựa chọn không hợp lệ!",
                    ephemeral=True
                )
                return
            
            track = self.tracks[track_index]
            
            # Response với loading message
            await interaction.response.edit_message(
                content=f"🧭 Đang tải: **{track['title']}**\n👤 Nghệ sĩ: {track['user']['username']}\n\n⏳ Vui lòng chờ...",
                view=None
            )
            
            # Lấy audio URL và thumbnail
            audio_url = get_music_stream_url(track)
            thumbnail_url = track.get('artwork_url', '').replace("-large", "-t500x500")
            
            if not audio_url or not thumbnail_url:
                await interaction.edit_original_response(
                    content="🚫 Không tìm thấy nguồn audio hoặc thumbnail."
                )
                return
            
            # Tạo embed cho thông tin bài hát
            embed = discord.Embed(
                title=track['title'],
                description=f"**Nghệ sĩ:** {track['user']['username']}\n**Lượt nghe:** {track['playback_count']:,} | **Lượt thích:** {track['likes_count']:,}\n**Nguồn:** SoundCloud 🎶",
                color=0xff7700  # SoundCloud orange color
            )
            embed.set_thumbnail(url=thumbnail_url)
            
            # Tải audio về buffer
            try:
                resp = requests.get(audio_url, stream=True)
                resp.raise_for_status()
                audio_bytes = resp.content
                audio_buffer = io.BytesIO(audio_bytes)
                
                # Tạo file Discord
                audio_file = discord.File(
                    audio_buffer, 
                    filename=f"{track['title']}.mp3"
                )
                
                # Gửi embed và file audio
                await interaction.followup.send(
                    embed=embed,
                    file=audio_file
                )
                
                # Xóa tin nhắn kết quả tìm kiếm
                try:
                    await interaction.delete_original_response()
                except Exception:
                    pass
                    
            except Exception as e:
                await interaction.edit_original_response(
                    content=f"🚫 Lỗi khi tải nhạc: {str(e)}"
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

def register_scl(bot):
    @bot.tree.command(name="scl", description="Tìm kiếm và tải nhạc từ SoundCloud")
    async def scl(interaction: discord.Interaction, keyword: str):

        keyword = keyword.strip()
        music_info = get_music_info(keyword)
        
        if not music_info or not music_info.get('collection') or len(music_info['collection']) == 0:
            await interaction.response.send_message("🚫 Không tìm thấy bài hát nào khớp với từ khóa.")
            return

        tracks = [track for track in music_info['collection'] if track.get('artwork_url')]
        if not tracks:
            await interaction.response.send_message("🚫 Không tìm thấy bài hát nào có hình ảnh.")
            return

        embed = discord.Embed(
            title="🎵 Kết quả tìm kiếm trên SoundCloud",
            color=0xff7700
        )
        
        description = ""
        for i, track in enumerate(tracks):
            description += f"**{i + 1}. {track['title']}**\n"
            description += f"👤 Nghệ sĩ: {track['user']['username']}\n"
            description += f"📊 Lượt nghe: {track['playback_count']:,} | Thích: {track['likes_count']:,}\n\n"
        
        description += "**💡 Chọn số bài hát bạn muốn tải!**"
        embed.description = description

        view = SoundCloudView(tracks, interaction.user.id)

        await interaction.response.send_message(embed=embed, view=view)
