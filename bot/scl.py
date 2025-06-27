import io
import os
import re
import json
import requests
import discord
from discord.ext import commands
from discord import ui

# --- Cấu hình chung ---
API_BASE = "https://api-v2.soundcloud.com"
CONFIG_PATH = "config.json"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

# --- Hàm hỗ trợ SoundCloud ---

def get_client_id():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            cfg = json.load(f)
            if cfg.get('client_id'):
                return cfg['client_id']
    try:
        resp = requests.get("https://soundcloud.com/", headers=HEADERS)
        resp.raise_for_status()
        urls = re.findall(r'<script crossorigin src="(https[^"]+)"]', resp.text)
        script = requests.get(urls[-1], headers=HEADERS).text
        cid = re.search(r',client_id:"([^"]+)"', script).group(1)
        with open(CONFIG_PATH, 'w') as f:
            json.dump({"client_id": cid}, f, indent=2)
        return cid
    except:
        return "vjvE4M9RytEg9W09NH1ge2VyrZPUSKo5"


def get_music_info(query, limit=10):
    try:
        cid = get_client_id()
        r = requests.get(
            f"{API_BASE}/search/tracks",
            params={"q": query, "client_id": cid, "limit": limit},
            headers=HEADERS,
        )
        r.raise_for_status()
        return r.json()
    except:
        return None


def get_music_stream_url(track):
    try:
        cid = get_client_id()
        r = requests.get(
            f"{API_BASE}/resolve",
            params={"url": track['permalink_url'], "client_id": cid},
            headers=HEADERS,
        )
        r.raise_for_status()
        data = r.json()
        prog = next(
            (t['url'] for t in data['media']['transcodings'] if t['format']['protocol'] == 'progressive'),
            None
        )
        if not prog:
            return None
        r2 = requests.get(f"{prog}?client_id={cid}", headers=HEADERS)
        r2.raise_for_status()
        return r2.json().get('url')
    except:
        return None

# --- Định nghĩa register_scl ---

def register_scl(bot: commands.Bot):
    """
    Đăng ký lệnh /scl và xử lý nút tương tác cho bot Discord.
    """
    class SclView(ui.View):
        def __init__(self, user_id: int, tracks: list, message: discord.Message):
            super().__init__(timeout=120)
            self.user_id = user_id
            self.tracks = tracks
            self.message = message
            for idx, _ in enumerate(tracks):
                btn = ui.Button(
                    label=str(idx+1),
                    style=discord.ButtonStyle.primary,
                    custom_id=f"scl_{user_id}_{idx}"
                )
                self.add_item(btn)
        
        @ui.button(label="Cancel", style=discord.ButtonStyle.danger, custom_id="scl_cancel")
        async def cancel(self, interaction: discord.Interaction, button: ui.Button):
            if interaction.user.id != self.user_id:
                return await interaction.response.send_message(
                    "❌ Bạn không có quyền hủy!", ephemeral=True
                )
            await interaction.response.edit_message(content="🚫 Đã hủy tìm kiếm.", view=None)

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            cid = interaction.data.get('custom_id', '')
            if cid == 'scl_cancel':
                return True
            if not cid.startswith(f"scl_{self.user_id}_"):
                return False
            if interaction.user.id != self.user_id:
                await interaction.response.send_message(
                    "❌ Bạn không có quyền sử dụng nút này!", ephemeral=True
                )
                return False

            # Xử lý lựa chọn bài
            parts = cid.split('_')
            idx = int(parts[-1])
            track = self.tracks[idx]
            await interaction.response.defer(thinking=True)

            # Hiển thị loading
            await self.message.edit(
                content=f"🧭 Đang tải **{track['title']}**...⏳",
                view=None
            )

            audio_url = get_music_stream_url(track)
            thumb = track.get('artwork_url','').replace('-large','-t500x500')
            if not audio_url:
                return await self.message.edit(content="🚫 Không tìm thấy nguồn audio.")

            resp = requests.get(audio_url, stream=True)
            if int(resp.headers.get('Content-Length', 0)) > 50*1024*1024:
                return await self.message.edit(content="🚫 File quá lớn (>50MB).")

            data = resp.content
            file = discord.File(io.BytesIO(data), filename=f"{track['title']}.mp3")
            embed = discord.Embed(
                title=track['title'],
                description=(
                    f"👤 {track['user']['username']}  | ▶️ {track['playback_count']:,} | ❤️ {track['likes_count']:,}"
                )
            )
            if thumb:
                embed.set_thumbnail(url=thumb)
            await interaction.followup.send(embed=embed, file=file)
            await self.message.delete()
            return True

    @bot.command(name="scl")
    async def scl(ctx: commands.Context, *, keyword: str = None):
        if not keyword:
            return await ctx.send(
                "🚫 Vui lòng nhập tên bài hát. Ví dụ: `/scl Bad Guy`"
            )
        info = get_music_info(keyword)
        if not info or not info.get('collection'):
            return await ctx.send("🚫 Không tìm thấy bài nào khớp từ khóa.")
        tracks = [t for t in info['collection'] if t.get('artwork_url')]
        if not tracks:
            return await ctx.send("🚫 Không tìm thấy bài nào có hình ảnh.")

        lines = ["**🎵 Kết quả tìm kiếm trên SoundCloud**\n"]
        for i, t in enumerate(tracks, 1):
            lines.append(f"**{i}. {t['title']}**")
            lines.append(f"👤 {t['user']['username']} | ▶️ {t['playback_count']:,} | ❤️ {t['likes_count']:,}\n")
        lines.append("**💡 Bấm nút số bên dưới để tải bài bạn muốn!**")
        # Gửi message với view chứa nút
        placeholder = await ctx.send("\n".join(lines), view=None)
        view = SclView(ctx.author.id, tracks, placeholder)
        await placeholder.edit(view=view)
