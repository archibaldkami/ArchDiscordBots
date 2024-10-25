import discord
from .base_module import BaseModule

# modules/music_module.py
class Module(BaseModule):
    def setup(self):
        self.voice_clients = {}
        
        @self.bot.tree.command(name="join", description="Приєднатися до голосового каналу")
        async def join(interaction: discord.Interaction):
            if not interaction.user.voice:
                await interaction.response.send_message(
                    "Ви повинні бути в голосовому каналі",
                    ephemeral=True
                )
                return
                
            voice_channel = interaction.user.voice.channel
            voice_client = await voice_channel.connect()
            self.voice_clients[interaction.guild_id] = voice_client
            
            await interaction.response.send_message(
                f"Приєднано до {voice_channel.name}",
                ephemeral=True
            )

        @self.bot.tree.command(name="leave", description="Покинути голосовий канал")
        async def leave(interaction: discord.Interaction):
            if interaction.guild_id not in self.voice_clients:
                await interaction.response.send_message(
                    "Бот не знаходиться в голосовому каналі",
                    ephemeral=True
                )
                return
                
            await self.voice_clients[interaction.guild_id].disconnect()
            del self.voice_clients[interaction.guild_id]
            await interaction.response.send_message(
                "Канал покинуто",
                ephemeral=True
            )
