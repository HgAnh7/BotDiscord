import aiohttp
import asyncio
import random
import json
from discord import app_commands
from discord.ext import commands

HEADERS = {
    'User-Agent': 'NGL/6.7.8 (iPhone; iOS 16.0; Scale/2.00)',
    'Accept': '*/*',
    'Accept-Language': 'en-US',
    'Content-Type': 'application/x-www-form-urlencoded',
}

MESSAGES = [
    "Bạn thật quyến rũ 😍", "Tôi thích phong cách của bạn!", "Bạn rất thông minh 🤓",
    "Nụ cười của bạn làm ngày tôi tốt hơn 😊", "Bạn thật dễ thương 🥺",
    "Ai mà không thích bạn chứ? 😘", "Bạn là người bạn tuyệt vời 🫶",
]

async def send_ngl_message(session, username, message):
    try:
        payload = {
            "username": username,
            "question": message,
            "deviceId": "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=16)),
        }

        async with session.post("https://ngl.link/api/submit", data=payload, headers=HEADERS) as resp:
            if resp.status == 200:
                return True
            else:
                text = await resp.text()
                print(f"Lỗi gửi: {resp.status} - {text}")
                return False
    except Exception as e:
        print(f"Lỗi khi gửi tin nhắn: {e}")
        return False

async def spam_ngl(ctx, username, count):
    success = 0
    failed = 0

    await ctx.response.send_message(f"⏳ Bắt đầu spam {count} tin nhắn đến `{username}`...")

    async with aiohttp.ClientSession() as session:
        for _ in range(count):
            message = random.choice(MESSAGES)
            result = await send_ngl_message(session, username, message)
            if result:
                success += 1
            else:
                failed += 1
            await asyncio.sleep(random.uniform(0.8, 1.5))  # tránh spam quá nhanh

    result_msg = f"✅ Đã gửi `{success}` tin nhắn thành công, `{failed}` thất bại tới `{username}`!"
    await ctx.followup.send(result_msg)

def register_ngl(bot: commands.Bot):
    @bot.tree.command(name="ngl", description="Spam tin nhắn ẩn danh đến NGL link")
    @app_commands.describe(username="Tên người dùng NGL (không kèm ngl.link)", count="Số lượng tin nhắn muốn gửi (mặc định: 5)")
    async def ngl_command(interaction, username: str, count: int = 5):
        if count > 100:
            await interaction.response.send_message("⚠️ Số lượng quá lớn. Vui lòng gửi tối đa 100 tin nhắn.", ephemeral=True)
            return
        await spam_ngl(interaction, username, count)