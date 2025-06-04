# File: bot/ngl.py
import asyncio
import aiohttp
import discord
from discord.ext import commands

# Cấu hình các hằng số cần thiết (không dùng các tên ZPROJECT)
LIMIT = 10         # Số lần gửi thất bại liên tiếp tối đa cho phép trước khi tạm dừng.
TIMEOUT = 10      # Thời gian timeout cho mỗi request (đơn vị giây).
DELAY = 0         # Delay giữa các lần gửi request (đơn vị giây).
API_URL = 'https://ngl.link/api/submit'

async def send_ngl_message(username: str, tinhan: str) -> bool:
    """
    Gửi một tin nhắn đến API của ngl.link với các header và dữ liệu cần thiết.
    Nếu nhận được HTTP status 200 thì trả về True, ngược lại trả về False.
    """
    headers = {
        'Host': 'ngl.link',
        'Accept': '*/*',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Origin': 'https://ngl.link',
        'Referer': f'https://ngl.link/{username}'
    }
    data = {
        'username': username,
        'question': tinhan,
        'deviceId': '0',
        'gameSlug': '',
        'referrer': ''
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, data=data, headers=headers, timeout=TIMEOUT) as response:
                return response.status == 200
    except Exception as e:
        print(f"Error sending message to ngl.link: {e}")
    return False

def register_nglattack(bot: commands.Bot):
    """
    Đăng ký lệnh slash /ngl cho bot.
    Tham số:
     • username: Tên người dùng trên ngl.link.
     • tinhan: Nội dung tin nhắn.
     • solan: Số lần gửi tin nhắn.
    """
    @bot.slash_command(name="ngl", description="Spam tin nhắn NGL")
    async def ngl(
        ctx: discord.ApplicationContext,
        username: str,
        tinhan: str,
        solan: int
    ):
        username = username.strip()
        tinhan = tinhan.strip()

        if not username or not tinhan:
            await ctx.respond("Username và tin nhắn không được để trống.", ephemeral=True)
            return

        if solan <= 0:
            await ctx.respond("Số lượng tin nhắn phải lớn hơn 0.", ephemeral=True)
            return

        success_count = 0
        failure_count = 0

        await ctx.respond(f"Bắt đầu gửi {solan} tin nhắn đến **{username}** với nội dung: **{tinhan}**")

        for i in range(solan):
            result = await send_ngl_message(username, tinhan)
            if result:
                success_count += 1
                failure_count = 0  # reset bước đếm thất bại nếu gửi thành công
            else:
                failure_count += 1
                # Nếu gửi thất bại liên tiếp đạt giới hạn, tạm dừng 60 giây trước khi tiếp tục
                if failure_count >= LIMIT:
                    await ctx.send("Đã gặp quá nhiều lỗi, tạm dừng 60 giây...", ephemeral=True)
                    await asyncio.sleep(60)
                    failure_count = 0
            await asyncio.sleep(DELAY)

        reply = (
            f"**Attack Thành Công trên ngl.link**\n"
            f"Tổng tin nhắn gửi thành công: {success_count}\n"
            f"Tổng số yêu cầu: {solan}\n"
            f"Tổng tin nhắn thất bại: {solan - success_count}"
        )
        await ctx.send(reply)