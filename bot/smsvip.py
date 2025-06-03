import json
import asyncio
import discord
import subprocess
from datetime import datetime
from discord.ext import commands
from discord import app_commands

spam_processes = {}
last_spam_time = {}
spam_process = None
VIP_FILE = "bot/spam/vip.json"
ADMIN_ID = 849989363387596840

def load_vip_data():
    """Load VIP data from JSON file"""
    try:
        with open(VIP_FILE, "r") as f:
            return json.load(f)
    except:
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
        if interaction.user.id != ADMIN_ID:
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
        global last_spam_time, spam_processes
        
        user = interaction.user
        
        # Check VIP status
        if not is_vip(user.id):
            return await interaction.response.send_message("❌ Chỉ VIP mới dùng được!", ephemeral=True)
        
        # Check cooldown
        remaining = await check_cooldown(user.id)
        if remaining:
            return await interaction.response.send_message(f"❌ Chờ {remaining}s nữa!", ephemeral=True)
        
        # Validate inputs
        if not validate_phone(phone):
            return await interaction.response.send_message("❌ SĐT phải 10 số, bắt đầu bằng 0!", ephemeral=True)
        
        if not (1 <= loops <= 1000):
            return await interaction.response.send_message("❌ Vòng lặp: 1-1000!", ephemeral=True)
        
        # Update last use time
        last_spam_time[user.id] = datetime.now()
        
        # Send response in description format
        description = (
            f"**📱 Mục tiêu:** {phone}\n"
            f"**🍃 Vòng lặp:** {loops:,}\n"
            f"**⏳ Trạng thái:** Đang khởi chạy...\n"
        )
        
        embed = discord.Embed(
            title="🚀 Spam SMS VIP",
            description=description,
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)
        
        # Stop old process and start new one
        if user.id in spam_processes and spam_processes[user.id].poll() is None:
            spam_processes[user.id].terminate()
        
        try:
            spam_processes[user.id] = subprocess.Popen(["python3", "bot/spam/smsvip.py", phone, str(loops)])
            
        except Exception as e:
            await interaction.followup.send(f"❌ Lỗi: {e}", ephemeral=True)