import discord
from .base_module import BaseModule

# modules/admin_module.py
class Module(BaseModule):
    def setup(self):
        @self.bot.tree.command(name="clear", description="Очистити повідомлення")
        async def clear(interaction: discord.Interaction, amount: int):
            if not interaction.user.guild_permissions.manage_messages:
                await interaction.response.send_message("У вас немає прав для цієї команди", ephemeral=True)
                return
                
            channel = interaction.channel
            deleted = await channel.purge(limit=amount)
            await interaction.response.send_message(
                f"Видалено {len(deleted)} повідомлень", 
                ephemeral=True
            )