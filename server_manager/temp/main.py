# main.py
import discord
import asyncio
import os
from typing import Optional

class DiscordBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)
        self.modules = {}
        
    async def setup_hook(self) -> None:
        await self.load_modules()
        await self.tree.sync()
        
    async def load_modules(self) -> None:
        """Завантаження всіх модулів"""
        # Список модулів, які потрібно пропустити
        skip_modules = ['__init__', 'base_module']
        
        for filename in os.listdir('./modules'):
            if filename.endswith('.py'):
                module_name = filename[:-3]
                # Пропускаємо базові модулі
                if module_name in skip_modules:
                    continue
                    
                try:
                    module = await self.load_module(module_name)
                    self.modules[module_name] = module
                    print(f"Модуль {module_name} успішно завантажено")
                except Exception as e:
                    print(f"Помилка завантаження модуля {filename}: {str(e)}")

    async def load_module(self, module_name: str):
        """Завантаження окремого модуля"""
        module = __import__(f'modules.{module_name}', fromlist=['Module'])
        return module.Module(self)