import discord
from .base_module import BaseModule

# modules/events_module.py
class Module(BaseModule):
    def setup(self):
        @self.bot.event
        async def on_member_join(member: discord.Member):
            channel = member.guild.system_channel
            if channel:
                await channel.send(f"Вітаємо {member.mention} на сервері!")
                
        @self.bot.event
        async def on_message(message: discord.Message):
            if message.author == self.bot.user:
                return
                
            # Приклад реакції на повідомлення
            if "привіт" in message.content.lower():
                await message.add_reaction("👋")

