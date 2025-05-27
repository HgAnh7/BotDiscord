# bot/scl.py
import io
import os
import re
import json
import random
import requests
from discord import Embed, File, ui, ButtonStyle, Interaction
from discord.ext import commands

# Giữ state tạm cho mỗi user (user_id -> track list)
scl_data = {}

PLATFORM    = "soundcloud"
API_BASE    = "https://api-v2.soundcloud.com"
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
            return config.get('client_id', '')
        return ''

def get_music_info(question, limit=10):
    try:
        client_id = get_client_id()
        response = requests.get(
            f"{API_BASE}/search/tracks",
            params={
                "q": question,
                "client_id": client_id,
                "limit": limit,
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
            (t['url'] for t in data.get('media', {}).get('transcodings', [])
             if t['format']['protocol'] == 'progressive'),
            None
        )
        if not progressive_url:
            raise ValueError("No progressive URL")
        stream_resp = requests.get(
            f"{progressive_url}?client_id={client_id}&track_authorization={data.get('track_authorization','')}",
            headers=get_headers()
        )
        stream_resp.raise_for_status()
        return stream_resp.json().get('url')
    except Exception as e:
        print(f"Error getting stream URL: {e}")
        return None

class SCLView(ui.View):
    def __init__(self, user_id: int, tracks: list, timeout=60):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.tracks = tracks
        # Tạo nút cho mỗi track
        for idx, track in enumerate(tracks):
            self.add_item(ui.Button(label=str(idx+1), style=ButtonStyle.primary, custom_id=f"scl_{user_id}_{idx}"))

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Bạn không được phép bấm nút này.", ephemeral=True)
            return False
        return True

    @ui.button(label="Hủy", style=ButtonStyle.danger, custom_id="scl_cancel")
    async def cancel(self, button: ui.Button, interaction: Interaction):
        await interaction.message.edit(content="❌ Đã huỷ chọn.", view=None)
        self.stop()

    async def on_timeout(self):
        # Khi timeout, xoá view
        for child in self.children:
            child.disabled = True

def register_scl(bot: commands.Bot):
    @bot.command(name="scl", help="Tìm và tải nhạc từ SoundCloud: !scl <tên bài>")
    async def soundcloud(ctx: commands.Context, *, *, query: str = None):
        if not query:
            return await ctx.send("🚫 Vui lòng nhập tên bài hát. Ví dụ: `!scl Blinding Lights`")
        await ctx.trigger_typing()

        data = get_music_info(query)
        if not data or not data.get('collection'):
            return await ctx.send("🚫 Không tìm thấy kết quả.")

        # Lọc track có artwork
        tracks = [t for t in data['collection'] if t.get('artwork_url')]
        if not tracks:
            return await ctx.send("🚫 Không có kết quả nào có hình ảnh.")

        # Lưu tracks tạm
        scl_data[ctx.author.id] = tracks

        # Tạo nội dung message
        desc = "<b>🎵 Kết quả tìm kiếm:</b>\n\n"
        for i, t in enumerate(tracks, start=1):
            desc += (f"<b>{i}. {t['title']}</b>\n"
                     f"👤 {t['user']['username']} | ▶️ {t['playback_count']:,} plays | ❤️ {t['likes_count']:,}\n\n")
        desc += "<b>Chọn số để tải (hoặc bấm Hủy):</b>"

        # Gửi embed kèm Buttons
        embed = Embed(description=desc, color=0x1DB954)
        view = SCLView(ctx.author.id, tracks)
        await ctx.send(embed=embed, view=view)

    @bot.event
    async def on_interaction(interaction: Interaction):
        # Bắt custom_id scl_{user}_{idx}
        cid = interaction.data.get("custom_id", "")
        if not cid.startswith("scl_"):
            return  # không quan tâm
        parts = cid.split("_")
        if parts[1] == "cancel":
            return  # nút cancel đã xử lý trong view
        user_id = int(parts[1])
        idx     = int(parts[2])
        if interaction.user.id != user_id:
            return

        tracks = scl_data.get(user_id)
        if not tracks or idx >= len(tracks):
            return await interaction.response.send_message("❌ Lựa chọn không hợp lệ hoặc đã hết dữ liệu.", ephemeral=True)

        track = tracks[idx]
        await interaction.response.defer()  # acknowledge

        # Cập nhật message loading
        await interaction.message.edit(content=f"⏳ Đang lấy file cho: **{track['title']}**", view=None)

        # Lấy URL stream và thumbnail
        stream_url = get_music_stream_url(track)
        thumb_url  = track.get('artwork_url', '').replace("-large", "-t500x500")
        if not stream_url:
            return await interaction.followup.send("🚫 Không tải được audio.")

        # Gửi ảnh + audio
        embed = Embed(title=track['title'], url=track['permalink_url'], color=0x1DB954)
        embed.set_thumbnail(url=thumb_url)
        embed.add_field(name="Artist", value=track['user']['username'], inline=True)
        embed.add_field(name="Plays", value=f"{track['playback_count']:,}", inline=True)
        embed.add_field(name="Likes", value=f"{track['likes_count']:,}", inline=True)
        await interaction.followup.send(embed=embed)

        # Download và gửi audio
        resp = requests.get(stream_url, stream=True)
        audio_bytes = resp.content
        buf = io.BytesIO(audio_bytes)
        buf.name = f"{track['title']}.mp3"
        await interaction.followup.send(file=File(buf))

        # Dọn dẹp dữ liệu
        scl_data.pop(user_id, None)