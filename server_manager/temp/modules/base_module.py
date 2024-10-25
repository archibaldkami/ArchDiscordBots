import discord

# modules/base_module.py
class BaseModule:
    """Базовий клас для всіх модулів"""
    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.setup()
    
    def setup(self):
        """Налаштування модуля"""
        pass

