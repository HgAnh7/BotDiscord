# bot/emoji.py
import random
import discord
from discord.ext import commands

# Emoji mặc định (unicode)
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

# Emoji server (custom emoji) — ID phải là int
server_emoji = [
    1375694110979260488,
    1375694113344852028,
    1375694117220257802,
    1375694120634421351,
    1375694124442718350,
    1375694127987032184,
    1375694133045493871,
    1375694136497279037
]

def register_emoji(bot: commands.Bot):
    @bot.event
    async def on_message(message: discord.Message):
        if message.author.bot:
            return

        try:
            # 50% khả năng dùng emoji server, 50% emoji thường
            if random.random() < 0.5:
                emoji_id = random.choice(server_emoji)
                emoji = bot.get_emoji(emoji_id)
                if emoji:
                    await message.add_reaction(emoji)
                else:
                    # Fallback nếu không lấy được emoji server
                    await message.add_reaction(random.choice(emoji_list))
            else:
                await message.add_reaction(random.choice(emoji_list))

        except Exception:
            pass

        await bot.process_commands(message)
