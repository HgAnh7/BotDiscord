# bot/ngl.py
import threading
import random
import time
import requests
import discord
from discord import app_commands
from discord.ext import commands

EMOJIS = [
    "😂", "😍", "🥺", "😎", "🤔", "😏", "😢", "😳", "🙄", "😇",
    "🤪", "😬", "😈", "🥵", "🤡", "💀", "👻", "🎃", "💩", "👽",
]

def get_random_emoji():
    return random.choice(EMOJIS)

def send_message(username, question, use_emoji):
    try:
        url = f"https://ngl.link/api/submit"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "NGL-Android/1.2.7",
        }

        payload = {
            "username": username,
            "question": question + (" " + get_random_emoji() if use_emoji else ""),
            "deviceId": ''.join(random.choices('abcdef0123456789', k=16))
        }

        response = requests.post(url, headers=headers, data=payload)
        return response.status_code == 200

    except Exception:
        return False

def spam_ngl(username, threads, question, use_emoji):
    success_count = 0
    lock = threading.Lock()

    def worker():
        nonlocal success_count
        if send_message(username, question, use_emoji):
            with lock:
                success_count += 1

    thread_list = []

    for _ in range(threads):
        t = threading.Thread(target=worker)
        t.start()
        thread_list.append(t)

    for t in thread_list:
        t.join()

    return success_count

def register_ngl(bot: commands.Bot):
    @bot.tree.command(name="ngl", description="Spam tin ẩn danh tới NGL profile")
    @app_commands.describe(
        username="Tên NGL (ngl.link/username)",
        threads="Số luồng gửi (khuyên dùng < 50)",
        message="Nội dung tin nhắn ẩn danh",
        emoji="Bật emoji ngẫu nhiên? (yes/no)"
    )
    async def ngl_command(
        interaction: discord.Interaction,
        username: str,
        threads: int,
        message: str = "",
        emoji: str = "no"
    ):
        await interaction.response.defer(thinking=True)

        use_emoji = emoji.lower() in ["yes", "true", "on", "1"]
        if threads > 100:
            await interaction.followup.send("⚠️ Số luồng quá lớn! Vui lòng nhập giá trị ≤ 100.")
            return

        try:
            success = spam_ngl(username, threads, message, use_emoji)
            await interaction.followup.send(
                f"✅ Đã gửi thành công `{success}` tin nhắn tới `{username}`!"
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Lỗi xảy ra: `{e}`")
