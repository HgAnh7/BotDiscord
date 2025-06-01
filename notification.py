import discord
from discord.ext import commands

WELCOME_CHANNEL_ID = 1375698214564528128
GOODBYE_CHANNEL_ID = 1378583823041957899

def register_notification(bot: commands.Bot):
    @bot.event
    async def on_member_join(member):
        channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            await channel.send(f'👋 Chào mừng {member.mention} đến với server **{member.guild.name}**!')

    @bot.event
    async def on_member_remove(member):
        channel = member.guild.get_channel(GOODBYE_CHANNEL_ID)
        if channel:
            await channel.send(f'😢 {member.name} đã rời khỏi server.')
