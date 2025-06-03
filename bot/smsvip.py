import os
import json
import asyncio
import discord
from datetime import datetime
from discord.ext import commands
from discord import app_commands

spam_processes = {}
last_spam_time = {}
VIP_FILE = "bot/spam/vip.json"
ADMIN_ID = 849989363387596840

def load_vip_data():
    try:
        os.makedirs(os.path.dirname(VIP_FILE), exist_ok=True)
        with open(VIP_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_vip_data(data):
    os.makedirs(os.path.dirname(VIP_FILE), exist_ok=True)
    with open(VIP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def is_vip(user_id):
    return str(user_id) in load_vip_data()

def validate_phone(phone):
    return len(phone) == 10 and phone.startswith("0") and phone.isdigit()

async def check_cooldown(user_id, cooldown=60):
    if user_id in last_spam_time:
        elapsed = (datetime.now() - last_spam_time[user_id]).total_seconds()
        if elapsed < cooldown:
            return int(cooldown - elapsed)
    return 0

def register_smsvip(bot):
    @bot.tree.command(name="add", description="Thêm người dùng vào VIP spam (Chỉ Admin)")
    async def add_vip(interaction: discord.Interaction, user: discord.Member):
        if interaction.user.id != ADMIN_ID:
            return await interaction.response.send_message("❌ Không có quyền!", ephemeral=True)
        
        vip_data = load_vip_data()
        if str(user.id) in vip_data:
            return await interaction.response.send_message(f"✅ {user.mention} đã là VIP!", ephemeral=True)
        
        vip_data[str(user.id)] = user.name
        save_vip_data(vip_data)
        await interaction.response.send_message(f"✅ Đã thêm {user.mention} vào VIP!")

    @bot.tree.command(name="smsvip", description="Gửi tin nhắn SMS (Chỉ VIP)")
    @app_commands.describe(phone="Số điện thoại (10 số, bắt đầu bằng 0)", loops="Số lần gửi (1-50)")
    async def spam_sms(interaction: discord.Interaction, phone: str, loops: int):
        global last_spam_time, spam_processes
        
        user = interaction.user

        # Kiểm tra quyền VIP
        if not is_vip(user.id):
            return await interaction.response.send_message("❌ Chỉ VIP mới được sử dụng!", ephemeral=True)

        # Kiểm tra thời gian chờ
        remaining = await check_cooldown(user.id)
        if remaining:
            return await interaction.response.send_message(f"❌ Vui lòng chờ {remaining} giây nữa!", ephemeral=True)

        # Kiểm tra định dạng số điện thoại
        if not validate_phone(phone):
            return await interaction.response.send_message("❌ Số điện thoại phải có 10 chữ số và bắt đầu bằng 0!", ephemeral=True)

        # Kiểm tra số lượng vòng lặp
        if not (1 <= loops <= 50):
            return await interaction.response.send_message("❌ Số vòng lặp phải từ 1 đến 50!", ephemeral=True)

        # Kiểm tra file script có tồn tại
        if not os.path.exists("bot/spam/smsvip.py"):
            return await interaction.response.send_message("❌ Không tìm thấy file thực thi!", ephemeral=True)

        last_spam_time[user.id] = datetime.now()

        # Tạo embed thông báo
        embed = discord.Embed(
            title="🚀 SMS VIP",
            description=(
                f"**📱 Số điện thoại:** {phone}\n"
                f"**🔄 Số lần gửi:** {loops:,}\n"
                f"**⏳ Trạng thái:** Đang thực hiện..."
            ),
            color=discord.Color.green()
        )

        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()

        try:
            # Dừng tiến trình cũ nếu có
            if user.id in spam_processes:
                old_process = spam_processes[user.id]
                if old_process.returncode is None:
                    old_process.terminate()
                    try:
                        await asyncio.wait_for(old_process.wait(), timeout=3)
                    except asyncio.TimeoutError:
                        old_process.kill()

            # Tạo tiến trình mới
            process = await asyncio.create_subprocess_exec(
                "python3", "bot/spam/smsvip.py", phone, str(loops),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            spam_processes[user.id] = process

            # Chờ hoàn thành (không giới hạn thời gian)
            await process.wait()

            # Cập nhật trạng thái hoàn thành
            done_embed = discord.Embed(
                title="✅ SMS VIP",
                description=(
                    f"**📱 Số điện thoại:** {phone}\n"
                    f"**🔄 Số lần gửi:** {loops:,}\n"
                    f"**✅ Trạng thái:** Hoàn thành!"
                ),
                color=discord.Color.blue()
            )
            await message.edit(embed=done_embed)

        except Exception as e:
            await interaction.followup.send(f"❌ Có lỗi xảy ra: {str(e)}", ephemeral=True)

        finally:
            # Dọn dẹp
            if user.id in spam_processes:
                del spam_processes[user.id]

    @bot.tree.command(name="stop", description="Dừng việc gửi SMS đang thực hiện")
    async def stop_spam(interaction: discord.Interaction):
        user = interaction.user
        
        if user.id not in spam_processes:
            return await interaction.response.send_message("❌ Bạn không có tiến trình nào đang chạy!", ephemeral=True)
        
        try:
            process = spam_processes[user.id]
            if process.returncode is None:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=3)
            
            del spam_processes[user.id]
            await interaction.response.send_message("✅ Đã dừng việc gửi SMS!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Lỗi khi dừng: {str(e)}", ephemeral=True)