import json
import asyncio
import discord
import subprocess
from datetime import datetime
from discord.ext import commands
from discord import app_commands

# Global variables
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

def is_vip(user_id, username):
    """Check if user is VIP"""
    vip_data = load_vip_data()
    return username in vip_data or user_id in vip_data.values()

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

def register_spam(bot):
    """Register spam commands for Discord bot"""
    
    @bot.tree.command(name="add", description="Thêm người dùng vào VIP spam (Admin only)")
    async def add_vip(interaction: discord.Interaction, user: discord.Member):
        if interaction.user.id != ADMIN_ID:
            return await interaction.response.send_message("❌ Không có quyền!", ephemeral=True)
        
        vip_data = load_vip_data()
        if user.name in vip_data:
            return await interaction.response.send_message(f"✅ {user.mention} đã là VIP!", ephemeral=True)
        
        vip_data[user.name] = user.id
        save_vip_data(vip_data)
        await interaction.response.send_message(f"✅ Đã thêm {user.mention} vào VIP!")

    @bot.tree.command(name="smsvip", description="Spam SMS (VIP only)")
    async def spam_sms(interaction: discord.Interaction, phone: str, loops: int):
        global last_spam_time, spam_process
        
        user = interaction.user
        
        # Check VIP status
        if not is_vip(user.id, user.name):
            return await interaction.response.send_message("❌ Chỉ VIP mới dùng được!", ephemeral=True)
        
        # Check cooldown
        remaining = await check_cooldown(user.id)
        if remaining:
            return await interaction.response.send_message(f"❌ Chờ {remaining}s nữa!", ephemeral=True)
        
        # Validate inputs
        if not validate_phone(phone):
            return await interaction.response.send_message("❌ SĐT phải 10 số, bắt đầu bằng 0!", ephemeral=True)
        
        if not (1 <= loops <= 100):
            return await interaction.response.send_message("❌ Vòng lặp: 1-100!", ephemeral=True)
        
        # Update last use time
        last_spam_time[user.id] = datetime.now()
        
        # Send response
        embed = discord.Embed(title="🚀 Spam VIP", color=0x00ff00)
        embed.add_field(name="📱 Mục tiêu", value=phone, inline=True)
        embed.add_field(name="🍃 Vòng lặp", value=loops, inline=True)
        embed.set_footer(text="Auto-stop after 500s")
        
        await interaction.response.send_message(embed=embed)
        
        # Stop old process and start new one
        if spam_process and spam_process.poll() is None:
            spam_process.terminate()
        
        try:
            spam_process = subprocess.Popen(["python3", "bot/spam/smsvip.py", phone, "200"])
            
            # Auto-stop after 500s
            async def auto_stop():
                global spam_process
                await asyncio.sleep(500)
                if spam_process and spam_process.poll() is None:
                    spam_process.terminate()
                    spam_process = None
            
            asyncio.create_task(auto_stop())
            
        except Exception as e:
            await interaction.followup.send(f"❌ Lỗi: {e}", ephemeral=True)
