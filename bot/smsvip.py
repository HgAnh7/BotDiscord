import json
import asyncio
import discord
import subprocess
from datetime import datetime
from discord.ext import commands
from discord import app_commands

spam_processes = {}
last_spam_time = {}

VIP_FILE = "bot/spam/vip.json"
ADMIN_ID = 849989363387596840

def load_vip_data():
    """Load VIP data from JSON file"""
    try:
        with open(VIP_FILE, "r") as f:
            data = json.load(f)
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_vip_data(data):
    """Save VIP data to JSON file"""
    with open(VIP_FILE, "w") as f:
        json.dump(data, f, indent=2)

def is_vip(user_id):
    vip_data = load_vip_data()
    return str(user_id) in vip_data

def validate_phone(phone):
    """Validate phone number format"""
    return len(phone) == 10 and phone.startswith("0") and phone.isdigit()

async def check_cooldown(user_id, cooldown=60):
    """Check if user is in cooldown period"""
    if user_id in last_spam_time:
        elapsed = (datetime.now() - last_spam_time[user_id]).total_seconds()
        if elapsed < cooldown:
            return int(cooldown - elapsed)
    return 0

def register_smsvip(bot):
    """Register spam commands for Discord bot"""

    @bot.tree.command(name="add", description="Thêm người dùng vào VIP spam (Admin only)")
    async def add_vip(interaction: discord.Interaction, user: discord.Member):
        # Kiểm tra Admin hoặc chủ bot
        app_owner = (await bot.application_info()).owner
        if interaction.user.id != ADMIN_ID and interaction.user.id != app_owner.id:
            return await interaction.response.send_message("❌ Không có quyền!", ephemeral=True)

        vip_data = load_vip_data()
        if str(user.id) in vip_data:
            return await interaction.response.send_message(f"✅ {user.mention} đã là VIP!", ephemeral=True)

        vip_data[str(user.id)] = user.name
        save_vip_data(vip_data)
        await interaction.response.send_message(f"✅ Đã thêm {user.mention} vào VIP!")

    @bot.tree.command(name="smsvip", description="Spam SMS (VIP only)")
    @app_commands.describe(phone="Số điện thoại", loops="Số lần gửi (1–1000)")
    async def spam_sms(interaction: discord.Interaction, phone: str, loops: int):
        user = interaction.user

        if not is_vip(user.id):
            return await interaction.response.send_message("❌ Chỉ VIP mới dùng được!", ephemeral=True)

        remaining = await check_cooldown(user.id)
        if remaining:
            return await interaction.response.send_message(f"⏳ Vui lòng chờ {remaining}s trước khi spam tiếp!", ephemeral=True)

        if not validate_phone(phone):
            return await interaction.response.send_message("❌ SĐT phải 10 số, bắt đầu bằng 0!", ephemeral=True)

        if not (1 <= loops <= 1000):
            return await interaction.response.send_message("❌ Số lần gửi phải từ 1–1000!", ephemeral=True)

        embed = discord.Embed(
            title="🚀 Spam SMS VIP",
            description=f"**📱 Mục tiêu:** {phone}\n**🍃 Vòng lặp:** {loops:,}\n**⏳ Trạng thái:** Đang khởi chạy...",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

        # Dừng process cũ nếu còn chạy
        if user.id in spam_processes:
            old_proc = spam_processes[user.id]
            if old_proc and old_proc.poll() is None:
                old_proc.terminate()

        try:
            # Dùng subprocess chạy async (dạng background)
            proc = subprocess.Popen(["python3", "bot/spam/smsvip.py", phone, str(loops)])
            spam_processes[user.id] = proc
            last_spam_time[user.id] = datetime.now()

            # Đợi kết thúc và cleanup
            asyncio.create_task(wait_and_cleanup(user.id, proc))

        except Exception as e:
            await interaction.followup.send(f"❌ Lỗi khi chạy script: {e}", ephemeral=True)

async def wait_and_cleanup(user_id, proc):
    """Chờ process kết thúc và xóa khỏi bộ nhớ"""
    proc.wait()
    if user_id in spam_processes and spam_processes[user_id] == proc:
        del spam_processes[user_id]