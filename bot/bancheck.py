import discord
import requests
from discord import app_commands

# Hàm gọi API kiểm tra UID có bị ban hay không
def check_banned(player_id: str):
    url = f"https://ff.garena.com/api/antihack/check_banned?lang=en&uid={player_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "referer": "https://ff.garena.com/en/support/",
        "x-requested-with": "B6FksShzIgjfrYImLpTsadjS86sddhFH"
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json().get("data", {})
            is_banned = data.get("is_banned", 0)
            period = data.get("period", 0)
            return {
                "status": "BANNED" if is_banned else "NOT BANNED",
                "ban_period": period if is_banned else 0,
                "uid": player_id,
                "is_banned": bool(is_banned)
            }
        else:
            return {"error": "Không thể lấy dữ liệu từ máy chủ", "status_code": 500}
    except Exception as e:
        return {"error": str(e), "status_code": 500}

def register_bancheck(bot):
    @bot.tree.command(name="bancheck", description="Kiểm tra UID Free Fire có bị cấm không")
    @app_commands.describe(uid="UID người chơi Free Fire")
    async def bancheck_command(interaction: discord.Interaction, uid: str):
        await interaction.response.defer()
        result = check_banned(uid)

        if "error" in result:
            await interaction.followup.send(f"❌ Lỗi: {result['error']}", ephemeral=True)
            return

        is_banned = result["is_banned"]
        status_text = "🔴 BỊ CẤM" if is_banned else "🟢 KHÔNG BỊ CẤM"

        # Mô tả chi tiết
        description = f"**UID:** {result['uid']}\n**Trạng thái:** {status_text}"
        if is_banned:
            description += f"\n**Thời gian cấm:** {result['ban_period']} ngày"

        # Gửi embed
        embed = discord.Embed(
            title="🛡️ Kiểm Tra Trạng Thái Tài Khoản Free Fire",
            description=description,
            color=discord.Color.red() if is_banned else discord.Color.green()
        )

        await interaction.followup.send(embed=embed)
        await interaction.followup.send(embed=embed)