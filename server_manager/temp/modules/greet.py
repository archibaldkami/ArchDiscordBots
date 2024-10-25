# modules/greeting_module.py
from discord import Interaction, app_commands
from .base_module import BaseModule

class Module(BaseModule):
    def setup(self):
        @self.bot.tree.command(
            name="hello",
            description="Привітатися з ботом"
        )
        async def hello(interaction: Interaction):
            user_name = interaction.user.name
            responses = [
                f"Привіт, {user_name}! Радий тебе бачити! 👋",
                f"Вітаю тебе, {user_name}! Як твої справи? 😊",
                f"Доброго дня, {user_name}! Чудово виглядаєш сьогодні! ✨"
            ]
            import random
            response = random.choice(responses)
            
            await interaction.response.send_message(
                response,
                ephemeral=True  # Повідомлення буде видно тільки користувачу
            )