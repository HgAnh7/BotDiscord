# bot/scl.py
import io
import os
import re
import json
import discord
import requests

API_BASE = "https://api-v2.soundcloud.com"
CONFIG_PATH = "config.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

def get_client_id():
    # Đọc config sẵn
    config = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
        if config.get('client_id'):
            return config['client_id']

    # Nếu chưa có trong config, fetch script để lấy
    try:
        resp = requests.get("https://soundcloud.com/", headers=HEADERS)
        resp.raise_for_status()
        urls = re.findall(r'<script crossorigin src="(https[^"]+)"', resp.text)
        script = requests.get(urls[-1], headers=HEADERS).text
        cid = re.search(r',client_id:"([^"]+)"', script).group(1)
        with open(CONFIG_PATH, 'w') as f:
            json.dump({"client_id": cid}, f, indent=2)
        return cid
    except:
        return "vjvE4M9RytEg9W09NH1ge2VyrZPUSKo5"

def get_music_info(question, limit=10):
    try:
        client_id = get_client_id()
        response = requests.get(
            f"{API_BASE}/search/tracks",
            params={
                "q": question,
                "client_id": client_id,
                "limit": limit,
            },
            headers=HEADERS
        )
        response.raise_for_status()
        return response.json()
    except:
        return None

def get_music_stream_url(track):
    try:
        client_id = get_client_id()
        api_url = f"{API_BASE}/resolve?url={track['permalink_url']}&client_id={client_id}"
        response = requests.get(api_url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        progressive_url = next(
            (t['url'] for t in data.get('media', {}).get('transcodings', []) if t['format']['protocol'] == 'progressive'),
            None
        )
        if not progressive_url:
            raise ValueError("No progressive transcoding URL found")
        stream_response = requests.get(
            f"{progressive_url}?client_id={client_id}",
            headers=HEADERS
        )
        stream_response.raise_for_status()
        return stream_response.json()['url']
    except:
        return None

# Discord View cho buttons
class SoundCloudView(discord.ui.View):
    def __init__(self, tracks, user_id, interaction: discord.Interaction):
        super().__init__(timeout=180)  # 3 minutes timeout
        self.tracks = tracks
        self.user_id = user_id
        self.interaction = interaction
        self.chosen = False
        
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
            await interaction.response.defer()
            if interaction.user.id != self.user_id:
                await interaction.followup.send(
                    "❌ Bạn không có quyền sử dụng nút này!",
                    ephemeral=True
                )
                return
                
            self.chosen = True
            
            # Parse button index
            track_index = int(interaction.data['custom_id'].split('_')[1])
            
            # Kiểm tra index hợp lệ
            if track_index >= len(self.tracks):
                await interaction.followup.send(
                    "❌ Lựa chọn không hợp lệ!",
                    ephemeral=True
                )
                return
            
            track = self.tracks[track_index]
            artist = track['user']['username']
            
            await interaction.edit_original_response(
                content=f"🧭 Đang tải: **{track['title']}**\n👤 Nghệ sĩ: {artist}\n\n⏳ Vui lòng chờ...",
                embed=None,
                view=None,
                attachments=[]
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
                description=f"**» Nghệ sĩ:** {artist}\n**» Lượt nghe:** {track['playback_count']:,}\n**» Lượt thích:** {track['likes_count']:,}\n**» Nguồn:** SoundCloud 🎶",
                color=0xff7700  # SoundCloud orange color
            )
            embed.set_thumbnail(url=thumbnail_url)
            
            # Tải audio về buffer
            try:
                resp = requests.get(audio_url, stream=True)
                resp.raise_for_status()

                content_length = int(resp.headers.get('Content-Length', 0))
                if content_length > 8 * 1024 * 1024:  # Giới hạn 8MB
                    await interaction.edit_original_response(
                        content=f"🚫 File nhạc quá lớn (>8MB) nên không thể gửi qua Discord.\n🎧 **[Nhấn vào đây để tải nhạc]({audio_url})**"
                    )
                    return

                audio_bytes = resp.content
                audio_buffer = io.BytesIO(audio_bytes)
                audio_buffer.name = f"{track['title']}.mp3"
                
                # Gửi embed và file audio
                await interaction.edit_original_response(
                    content=None,
                    embed=embed,
                    attachments=[discord.File(audio_buffer, filename=audio_buffer.name)],
                )
                    
            except Exception as e:
                await interaction.edit_original_response(
                    content=f"🚫 Lỗi khi tải nhạc: {str(e)}"
                )
                
        except Exception as e:
            await interaction.followup.send(
                f"❌ Có lỗi xảy ra: {str(e)}",
                ephemeral=True
            )
    
    async def on_timeout(self):
        try:
            if not self.chosen:
                await self.interaction.delete_original_response()
        except Exception:
            pass  # Có thể message đã bị xóa tay hoặc lỗi quyền, nên bỏ qua

def register_scl(bot):
    @bot.tree.command(name="scl", description="Tải nhạc từ SoundCloud")
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

        embed = discord.Embed(color=0xff7700)
        
        lines = ["🎵 Kết quả tìm kiếm trên SoundCloud\n"]
        for i, track in enumerate(tracks):
            lines.append(
                f"{i + 1}. **{track['title']}\n**"
                f" **» Nghệ sĩ:** {track['user']['username']}\n"
                f" **» Lượt nghe:** {track['playback_count']:,} | **Thích:** {track['likes_count']:,}\n"
            )
        lines.append("**💡 Chọn số bài hát bạn muốn tải!**")
        embed.description = "\n".join(lines)

        view = SoundCloudView(tracks, interaction.user.id, interaction)
        await interaction.response.send_message(embed=embed, view=view)