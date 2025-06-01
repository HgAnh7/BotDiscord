import discord
from discord.ext import commands

def register_notification(bot: commands.Bot):
  @bot.event
  async def on_member_join(member):
      channel = discord.utils.get(member.guild.text_channels, name='Save all file')  # đổi tên kênh nếu khác
      if channel:
          await channel.send(f'👋 Chào mừng {member.mention} đến với server **{member.guild.name}**!')
  
  # Khi có thành viên rời server
  @bot.event
  async def on_member_remove(member):
      channel = discord.utils.get(member.guild.text_channels, name='general')
      if channel:
          await channel.send(f'😢 {member.name} đã rời khỏi server.')
