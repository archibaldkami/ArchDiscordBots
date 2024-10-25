# modules/farewell_module.py
from discord import Interaction, app_commands
from .base_module import BaseModule

class Module(BaseModule):
    def setup(self):
        @self.bot.tree.command(
            name="goodbye",
            description="Попрощатися з ботом"
        )
        async def goodbye(interaction: Interaction):
            user_name = interaction.user.name
            responses = [
                f"До побачення, {user_name}! Повертайся скоріше! 👋",
                f"Бувай, {user_name}! Гарного дня! 🌟",
                f"На все добре, {user_name}! Буду чекати на твоє повернення! 😊"
            ]
            import random
            response = random.choice(responses)
            
            await interaction.response.send_message(
                response,
                ephemeral=True
            )