import os
import json
import asyncio
import discord
import logging
from datetime import datetime
from discord.ext import commands
from discord import app_commands

# Cấu hình hệ thống
CONFIG = {
    "vip_file": "bot/spam/vip.json",           # File lưu danh sách VIP
    "admin_ids": [849989363387596840],         # Danh sách ID admin (có thể thêm nhiều)
    "error_channel_id": 1377693583741812867,   # Kênh gửi thông báo lỗi
    "cooldown": 60,                            # Thời gian chờ giữa các lần spam (giây)
    "max_loops": 50,                           # Số loop tối đa cho mỗi lần spam
    "max_concurrent": 3,                       # Số tiến trình đồng thời tối đa
    "timeout_per_loop": 60                     # Thời gian timeout cho mỗi loop (giây)
}

# Biến toàn cục để quản lý trạng thái
spam_processes = {}    # Lưu các tiến trình SMS đang chạy
last_spam_time = {}    # Lưu thời gian spam cuối của từng user

# Tắt logging console, chỉ dùng để gửi lỗi qua Discord
logging.getLogger().setLevel(logging.CRITICAL)  # Tắt hầu hết log console

def load_vip_data():
    """Đọc dữ liệu VIP từ file JSON"""
    try:
        os.makedirs(os.path.dirname(CONFIG["vip_file"]), exist_ok=True)
        with open(CONFIG["vip_file"], "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_vip_data(data):
    """Lưu dữ liệu VIP vào file JSON"""
    os.makedirs(os.path.dirname(CONFIG["vip_file"]), exist_ok=True)
    with open(CONFIG["vip_file"], "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def is_admin(user_id):
    """Kiểm tra user có phải admin không"""
    return user_id in CONFIG["admin_ids"]

def is_vip(user_id):
    """Kiểm tra user có phải VIP không"""
    return str(user_id) in load_vip_data()

def validate_phone(phone):
    """Kiểm tra định dạng số điện thoại (10 số, bắt đầu bằng 0)"""
    return len(phone) == 10 and phone.startswith("0") and phone.isdigit()

async def check_cooldown(user_id):
    """Kiểm tra thời gian chờ của user"""
    if user_id in last_spam_time:
        elapsed = (datetime.now() - last_spam_time[user_id]).total_seconds()
        if elapsed < CONFIG["cooldown"]:
            return int(CONFIG["cooldown"] - elapsed)
    return 0

async def cleanup_process(user_id):
    """Dọn dẹp tiến trình của user"""
    if user_id in spam_processes:
        process = spam_processes.pop(user_id)
        if process.returncode is None:
            try:
                process.terminate()  # Dừng tiến trình nhẹ nhàng
                await asyncio.wait_for(process.wait(), timeout=3)
            except asyncio.TimeoutError:
                process.kill()  # Buộc dừng nếu không tự dừng
            except Exception:
                pass  # Bỏ qua lỗi cleanup

def create_embed(title, phone, loops, status, color):
    """Tạo embed message thống nhất"""
    return discord.Embed(
        title=title,
        description=f"**📱 SĐT:** {phone}\n**🍃 Loops:** {loops:,}\n**📊 Trạng thái:** {status}",
        color=color
    )

async def send_error_to_channel(bot, error_msg, user_id=None):
    """Gửi thông báo lỗi về kênh Discord thay vì console"""
    try:
        channel = bot.get_channel(CONFIG["error_channel_id"])
        if channel:
            error_embed = discord.Embed(
                title="🚨 Lỗi hệ thống",
                description=f"**Lỗi:** {error_msg}\n**User ID:** {user_id if user_id else 'Không xác định'}\n**Thời gian:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
                color=discord.Color.red()
            )
            await channel.send(embed=error_embed)
    except Exception:
        pass  # Tránh lỗi kép nếu không gửi được

def register_smsvip(bot):
    @bot.tree.command(name="add", description="Thêm VIP (Chỉ Admin)")
    async def add_vip(interaction: discord.Interaction, user: discord.Member):
        # Kiểm tra quyền admin
        if not is_admin(interaction.user.id):
            return await interaction.response.send_message("❌ Không có quyền!", ephemeral=True)
        
        vip_data = load_vip_data()
        if str(user.id) in vip_data:
            return await interaction.response.send_message(f"✅ {user.mention} đã là VIP!", ephemeral=True)
        
        # Thêm VIP và lưu file
        vip_data[str(user.id)] = user.name
        save_vip_data(vip_data)
        await interaction.response.send_message(f"✅ Đã thêm {user.mention} vào VIP!")

    @bot.tree.command(name="smsvip", description="SMS spam (Chỉ VIP)")
    @app_commands.describe(phone="SĐT (10 số, bắt đầu 0)", loops="Số lần (1-50)")
    async def spam_sms(interaction: discord.Interaction, phone: str, loops: int):
        user_id = interaction.user.id
        
        # Kiểm tra quyền VIP
        if not is_vip(user_id):
            return await interaction.response.send_message("❌ Chỉ VIP!", ephemeral=True)
        
        # Kiểm tra thời gian chờ
        remaining = await check_cooldown(user_id)
        if remaining:
            return await interaction.response.send_message(f"❌ Chờ {remaining}s!", ephemeral=True)
        
        # Kiểm tra định dạng số điện thoại
        if not validate_phone(phone):
            return await interaction.response.send_message("❌ SĐT không hợp lệ!", ephemeral=True)
        
        # Kiểm tra số lần spam
        if not (1 <= loops <= CONFIG["max_loops"]):
            return await interaction.response.send_message(f"❌ Loops: 1-{CONFIG['max_loops']}!", ephemeral=True)
        
        # Kiểm tra số tiến trình đồng thời
        if len(spam_processes) >= CONFIG["max_concurrent"]:
            return await interaction.response.send_message("❌ Hệ thống đang bận!", ephemeral=True)
        
        # Kiểm tra file script có tồn tại
        if not os.path.exists("bot/spam/smsvip.py"):
            return await interaction.response.send_message("❌ Script không tồn tại!", ephemeral=True)

        # Bắt đầu quá trình spam
        last_spam_time[user_id] = datetime.now()
        embed = create_embed("🚀 SMS VIP", phone, loops, "⏳ Đang xử lý...", discord.Color.green())
        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()

        try:
            # Dọn dẹp tiến trình cũ nếu có
            await cleanup_process(user_id)
            
            # Tạo tiến trình mới để chạy script SMS
            process = await asyncio.create_subprocess_exec(
                "python3", "bot/spam/smsvip.py", phone, str(loops),
                stdout=asyncio.subprocess.DEVNULL,  # Tắt output
                stderr=asyncio.subprocess.PIPE      # Lấy lỗi để gửi Discord
            )
            spam_processes[user_id] = process

            # Chờ tiến trình hoàn thành với timeout
            timeout = loops * CONFIG["timeout_per_loop"]
            try:
                returncode = await asyncio.wait_for(process.wait(), timeout=timeout)
                # Kiểm tra kết quả
                if returncode == 0:
                    status = "✅ Thành công!"
                    color = discord.Color.blue()
                else:
                    status = f"❌ Lỗi ({returncode})"
                    color = discord.Color.red()
                    # Gửi lỗi về kênh Discord
                    stderr_output = await process.stderr.read()
                    if stderr_output:
                        await send_error_to_channel(bot, f"SMS process error: {stderr_output.decode()}", user_id)
            except asyncio.TimeoutError:
                # Timeout = coi như thành công (đã chạy đủ thời gian)
                process.terminate()
                status = "✅ Hoàn thành!"
                color = discord.Color.blue()

            # Cập nhật trạng thái cuối
            final_embed = create_embed("🚀 SMS VIP", phone, loops, status, color)
            await message.edit(embed=final_embed)

        except Exception as e:
            # Gửi lỗi về kênh Discord thay vì console
            await send_error_to_channel(bot, f"SMS command error: {str(e)}", user_id)
            error_embed = create_embed("❌ SMS VIP", phone, loops, f"❌ Lỗi: {str(e)}", discord.Color.red())
            try:
                await message.edit(embed=error_embed)
            except:
                await interaction.followup.send(f"❌ Lỗi: {str(e)}", ephemeral=True)
        finally:
            # Luôn dọn dẹp tiến trình khi kết thúc
            await cleanup_process(user_id)

    @bot.tree.command(name="stop", description="Dừng SMS")
    async def stop_spam(interaction: discord.Interaction):
        user_id = interaction.user.id
        
        # Kiểm tra có tiến trình đang chạy không
        if user_id not in spam_processes:
            return await interaction.response.send_message("❌ Không có tiến trình nào!", ephemeral=True)
        
        try:
            await cleanup_process(user_id)
            await interaction.response.send_message("✅ Đã dừng!", ephemeral=True)
        except Exception as e:
            # Gửi lỗi về Discord
            await send_error_to_channel(bot, f"Stop command error: {str(e)}", user_id)
            await interaction.response.send_message(f"❌ Lỗi: {str(e)}", ephemeral=True)

    @bot.tree.command(name="status", description="Kiểm tra trạng thái hệ thống (Admin)")
    async def system_status(interaction: discord.Interaction):
        # Chỉ admin mới xem được
        if not is_admin(interaction.user.id):
            return await interaction.response.send_message("❌ Không có quyền!", ephemeral=True)
        
        # Thống kê hệ thống
        vip_count = len(load_vip_data())
        active_processes = len(spam_processes)
        
        status_embed = discord.Embed(
            title="📊 Trạng thái hệ thống",
            description=(
                f"**👥 Số VIP:** {vip_count}\n"
                f"**⚡ Tiến trình đang chạy:** {active_processes}/{CONFIG['max_concurrent']}\n"
                f"**⚙️ Max Loops:** {CONFIG['max_loops']}\n"
                f"**⏰ Thời gian chờ:** {CONFIG['cooldown']}s\n"
                f"**🔧 Timeout/loop:** {CONFIG['timeout_per_loop']}s"
            ),
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=status_embed, ephemeral=True)

    @bot.tree.command(name="viplist", description="Xem danh sách VIP (Admin)")
    async def vip_list(interaction: discord.Interaction):
        # Chỉ admin mới xem được
        if not is_admin(interaction.user.id):
            return await interaction.response.send_message("❌ Không có quyền!", ephemeral=True)
        
        vip_data = load_vip_data()
        if not vip_data:
            return await interaction.response.send_message("📝 Chưa có VIP nào!", ephemeral=True)
        
        # Tạo danh sách VIP
        vip_list_text = ""
        for user_id, username in vip_data.items():
            vip_list_text += f"• <@{user_id}> ({username})\n"
        
        # Chia nhỏ nếu quá dài (Discord limit 4096 chars)
        if len(vip_list_text) > 3900:
            vip_list_text = vip_list_text[:3900] + "\n... (và nhiều hơn)"
        
        vip_embed = discord.Embed(
            title="👥 Danh sách VIP",
            description=vip_list_text,
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=vip_embed, ephemeral=True)
