import random
import discord
from discord.ext import commands

emoji_list = [
    '👍', '👎', '❤️', '🔥', '🥰', '👏', '😁', '🤔', '🤯', '😱',
    '🤬', '😢', '🎉', '🤩', '🤮', '💩', '🙏', '👌', '🕊️', '🤡',
    '🥱', '🥴', '😍', '🐳', '❤️‍🔥', '🌚', '🌭', '💯', '🤣', '⚡',
    '🍌', '🏆', '💔', '🤨', '😐', '🍓', '🍾', '💋', '🖕', '😈',
    '😴', '😭', '🤓', '👻', '👨‍💻', '👀', '🎃', '🙈', '😇', '😨',
    '🤝', '✍️', '🤗', '🫡', '🎅', '🎄', '☃️', '💅', '🤪', '🗿',
    '🆒', '💘', '🙉', '🦄', '😘', '💊', '🙊', '😎', '👾', '🤷‍♂️',
    '🤷', '🤷‍♀️', '😡'
]

def register_emoji(bot: commands.Bot):
    @bot.event
    async def on_message(message: discord.Message):
        # Bỏ qua tin nhắn của bot để tránh feedback vòng lặp
        if message.author.bot:
            return

        try:
            random_emoji = random.choice(emoji_list)
            await message.add_reaction(random_emoji)
        except Exception:
            # Nếu có lỗi xảy ra, không làm gì cả
            pass

        # Đảm bảo rằng các command khác vẫn được xử lý
        await bot.process_commands(message)
