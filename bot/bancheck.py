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

        embed = discord.Embed(
            title="Kiểm Tra Trạng Thái Tài Khoản Free Fire",
            color=discord.Color.red() if result["is_banned"] else discord.Color.green()
        )
        embed.add_field(name="UID", value=result["uid"], inline=False)
        embed.add_field(
            name="Trạng Thái",
            value="🔴 BỊ CẤM" if result["is_banned"] else "🟢 KHÔNG BỊ CẤM",
            inline=False
        )
        if result["is_banned"]:
            embed.add_field(name="Thời Gian Cấm", value=f"{result['ban_period']} ngày", inline=False)

        await interaction.followup.send(embed=embed)