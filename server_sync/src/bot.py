import os
import yaml
import logging
from pathlib import Path
from discord.ext import commands
import discord
from typing import Optional, Dict

class SyncBot(commands.Bot):
    """
    Основний клас бота для синхронізації серверів Discord.
    Включає базову конфігурацію та управління когами.
    """
    
    def __init__(self):
        # Завантаження конфігурації
        self.config = self._load_config()
        
        # Налаштування базових параметрів бота
        intents = discord.Intents.all()
        super().__init__(
            command_prefix=self.config['bot']['command_prefix'],
            description=self.config['bot']['description'],
            intents=intents
        )
        
        # Ініціалізація логера
        self._setup_logging()
        
        # Кеш для швидкого доступу до даних синхронізації
        self.sync_cache: Dict[str, dict] = {}
        
        # Словник для зберігання активних операцій синхронізації
        self.active_syncs: Dict[int, dict] = {}
    
    @staticmethod
    def _load_config() -> dict:
        """Завантажує конфігурацію з YAML файлу."""
        config_path = Path("config/config.yaml")
        if not config_path.exists():
            raise FileNotFoundError("Конфігураційний файл не знайдено")
            
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        # Підстановка змінних середовища
        if '${DISCORD_BOT_TOKEN}' in config['bot']['token']:
            config['bot']['token'] = os.getenv('DISCORD_BOT_TOKEN')
            
        return config
    
    def _setup_logging(self) -> None:
        """Налаштовує систему логування."""
        log_config = self.config['logging']
        logging.basicConfig(
            level=log_config['level'],
            format=log_config['format'],
            filename=log_config['file']
        )
        self.logger = logging.getLogger('SyncBot')
    
    async def setup_hook(self) -> None:
        """Хук, що викликається при ініціалізації бота."""
        # Завантаження когів
        await self.load_extension('src.cogs.server_clone')
        await self.load_extension('src.cogs.message_sync')
        await self.load_extension('src.cogs.security')
        await self.load_extension('src.cogs.monitoring')
        await self.load_extension('src.cogs.admin_interface')
        
        self.logger.info("Всі коги успішно завантажено")
    
    async def on_ready(self):
        """Обробник події готовності бота."""
        self.logger.info(f'Бот {self.user} успішно підключився до Discord')
        
        # Перевірка доступу до основного та дочірнього серверів
        primary_guild = self.get_guild(int(self.config['servers']['primary']['id']))
        secondary_guild = self.get_guild(int(self.config['servers']['secondary']['id']))
        
        if not primary_guild or not secondary_guild:
            self.logger.error("Не вдалося отримати доступ до одного з серверів")
            return
            
        self.logger.info("Підключення до серверів встановлено успішно")
    
    async def on_error(self, event: str, *args, **kwargs):
        """Глобальний обробник помилок."""
        self.logger.exception(f"Помилка в події {event}")
    
    async def get_sync_progress(self, guild_id: int) -> Optional[dict]:
        """Повертає прогрес активної синхронізації для вказаного серверу."""
        return self.active_syncs.get(guild_id)
    
    async def update_sync_progress(self, guild_id: int, operation: str, progress: float):
        """Оновлює прогрес синхронізації для вказаного серверу."""
        if guild_id in self.active_syncs:
            self.active_syncs[guild_id].update({
                'operation': operation,
                'progress': progress,
                'last_update': discord.utils.utcnow().timestamp()
            })
    
    async def clear_sync_progress(self, guild_id: int):
        """Очищає інформацію про прогрес синхронізації після завершення."""
        self.active_syncs.pop(guild_id, None)