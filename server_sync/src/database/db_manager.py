from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any, TypeVar, Generic, AsyncGenerator
import logging
from datetime import datetime, timedelta

from .models import Base, Guild, Channel, Role, Message, SyncOperation

T = TypeVar('T')

class DatabaseManager:
    """
    Менеджер бази даних для асинхронної роботи з SQLAlchemy.
    Забезпечує ефективну роботу з БД через пул з'єднань та кешування.
    """
    
    def __init__(self, config: dict):
        """
        Ініціалізує менеджер бази даних.
        
        Args:
            config (dict): Конфігурація з налаштуваннями БД
        """
        self.logger = logging.getLogger('DatabaseManager')
        self.config = config['database']
        self.is_closed = False
        
        # Створюємо асинхронний двигун SQLAlchemy
        self.engine = create_async_engine(
            self.config['url'],
            # pool_size=self.config.get('pool_size', 5),
            # max_overflow=self.config.get('max_overflow', 10),
            echo=self.config.get('echo', False)
        )
        
        # Створюємо фабрику сесій
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Кеш для зберігання часто використовуваних даних
        self._cache: Dict[str, Dict[str, Any]] = {
            'guilds': {},
            'channels': {},
            'roles': {}
        }
        
        # Налаштування кешування
        self.cache_ttl = timedelta(minutes=15)
        self.last_cache_update = {
            'guilds': datetime.min,
            'channels': datetime.min,
            'roles': datetime.min
        }

    async def close(self):
        """
        Закриває з'єднання з базою даних та очищує ресурси.
        Цей метод повинен викликатися при завершенні роботи програми.
        """
        if self.is_closed:
            return
            
        try:
            # Очищуємо кеш
            await self.clear_cache()
            
            # Закриваємо пул з'єднань
            await self.engine.dispose()
            
            self.is_closed = True
            self.logger.info("З'єднання з базою даних закрито")
            
        except Exception as e:
            self.logger.error(f"Помилка при закритті з'єднання з базою даних: {str(e)}")
            raise
    
    async def __aenter__(self):
        """Підтримка асинхронного контекстного менеджера."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закриває з'єднання при виході з контекстного менеджера."""
        await self.close()
        
    async def initialize(self):
        """Ініціалізує базу даних, створюючи всі необхідні таблиці."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.logger.info("База даних ініціалізована")
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Контекстний менеджер для роботи з сесією бази даних.
        
        Yields:
            AsyncSession: Асинхронна сесія SQLAlchemy
        """
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Помилка транзакції: {str(e)}")
                raise
    
    async def get_guild(self, discord_id: str) -> Optional[Guild]:
        """
        Отримує інформацію про сервер з кешу або бази даних.
        
        Args:
            discord_id (str): Discord ID серверу
            
        Returns:
            Optional[Guild]: Об'єкт серверу або None
        """
        # Перевіряємо кеш
        if self._is_cache_valid('guilds'):
            if discord_id in self._cache['guilds']:
                return self._cache['guilds'][discord_id]
        
        # Отримуємо з бази даних
        async with self.session() as session:
            guild = await session.get(Guild, discord_id)
            if guild:
                self._cache['guilds'][discord_id] = guild
                self.last_cache_update['guilds'] = datetime.now()
            return guild
    
    async def create_guild(self, discord_id: str, name: str, is_primary: bool) -> Guild:
        """
        Створює новий запис серверу в базі даних.
        
        Args:
            discord_id (str): Discord ID серверу
            name (str): Назва серверу
            is_primary (bool): Чи є сервер основним
            
        Returns:
            Guild: Створений об'єкт серверу
        """
        guild = Guild(discord_id=discord_id, name=name, is_primary=is_primary)
        
        async with self.session() as session:
            session.add(guild)
            await session.flush()
            await session.refresh(guild)
            
            # Оновлюємо кеш
            self._cache['guilds'][discord_id] = guild
            self.last_cache_update['guilds'] = datetime.now()
            
            return guild
    
    async def create_channel(self, guild_id: int, discord_id: str, 
                           name: str, channel_type: str, **kwargs) -> Channel:
        """
        Створює новий запис каналу в базі даних.
        
        Args:
            guild_id (int): ID серверу в базі даних
            discord_id (str): Discord ID каналу
            name (str): Назва каналу
            channel_type (str): Тип каналу
            **kwargs: Додаткові параметри каналу
            
        Returns:
            Channel: Створений об'єкт каналу
        """
        channel = Channel(
            guild_id=guild_id,
            discord_id=discord_id,
            name=name,
            type=channel_type,
            **kwargs
        )
        
        async with self.session() as session:
            session.add(channel)
            await session.flush()
            await session.refresh(channel)
            
            # Оновлюємо кеш
            self._cache['channels'][discord_id] = channel
            self.last_cache_update['channels'] = datetime.now()
            
            return channel
    
    async def create_sync_operation(self, operation_type: str,
                                  source_guild_id: str,
                                  target_guild_id: str) -> SyncOperation:
        """
        Створює новий запис операції синхронізації.
        
        Args:
            operation_type (str): Тип операції
            source_guild_id (str): ID вихідного серверу
            target_guild_id (str): ID цільового серверу
            
        Returns:
            SyncOperation: Створений об'єкт операції
        """
        operation = SyncOperation(
            operation_type=operation_type,
            source_guild_id=source_guild_id,
            target_guild_id=target_guild_id,
            status='in_progress'
        )
        
        async with self.session() as session:
            session.add(operation)
            await session.flush()
            await session.refresh(operation)
            return operation
    
    async def update_sync_operation(self, operation_id: int,
                                  status: str,
                                  items_processed: int,
                                  error_log: Optional[str] = None) -> None:
        """
        Оновлює статус операції синхронізації.
        
        Args:
            operation_id (int): ID операції
            status (str): Новий статус
            items_processed (int): Кількість оброблених елементів
            error_log (Optional[str]): Лог помилок
        """
        async with self.session() as session:
            operation = await session.get(SyncOperation, operation_id)
            if operation:
                operation.status = status
                operation.items_processed = items_processed
                if error_log:
                    operation.error_log = error_log
                if status in ['completed', 'failed']:
                    operation.completed_at = datetime.utcnow()
    
    async def create_message(self, channel_id: int, discord_id: str,
                           author_id: str, content: Optional[str],
                           **kwargs) -> Message:
        """
        Створює новий запис повідомлення в базі даних.
        
        Args:
            channel_id (int): ID каналу в базі даних
            discord_id (str): Discord ID повідомлення
            author_id (str): Discord ID автора
            content (Optional[str]): Текст повідомлення
            **kwargs: Додаткові параметри повідомлення
            
        Returns:
            Message: Створений об'єкт повідомлення
        """
        message = Message(
            channel_id=channel_id,
            discord_id=discord_id,
            author_id=author_id,
            content=content,
            **kwargs
        )
        
        async with self.session() as session:
            session.add(message)
            await session.flush()
            await session.refresh(message)
            return message
    
    def _is_cache_valid(self, cache_type: str) -> bool:
        """
        Перевіряє актуальність кешу.
        
        Args:
            cache_type (str): Тип кешу
            
        Returns:
            bool: True якщо кеш актуальний
        """
        last_update = self.last_cache_update[cache_type]
        return (datetime.now() - last_update) < self.cache_ttl
    
    async def clear_cache(self, cache_type: Optional[str] = None) -> None:
        """
        Очищає кеш.
        
        Args:
            cache_type (Optional[str]): Тип кешу для очищення. Якщо None - очищає весь кеш
        """
        if cache_type:
            if cache_type in self._cache:
                self._cache[cache_type].clear()
                self.last_cache_update[cache_type] = datetime.min
        else:
            for cache in self._cache.values():
                cache.clear()
            for key in self.last_cache_update:
                self.last_cache_update[key] = datetime.min
    
    async def get_sync_statistics(self) -> Dict[str, Any]:
        """
        Отримує статистику синхронізації.
        
        Returns:
            Dict[str, Any]: Словник зі статистикою
        """
        async with self.session() as session:
            # Загальна кількість синхронізованих повідомлень
            total_messages = await session.scalar(
                """
                SELECT COUNT(*) 
                FROM messages 
                WHERE sync_status = 'synced'
                """
            )
            
            # Кількість повідомлень за останні 24 години
            recent_messages = await session.scalar(
                """
                SELECT COUNT(*) 
                FROM messages 
                WHERE sync_status = 'synced' 
                AND created_at > :time_limit
                """,
                {'time_limit': datetime.utcnow() - timedelta(days=1)}
            )
            
            # Статистика по операціях
            operations_stats = await session.execute(
                """
                SELECT operation_type, status, COUNT(*) 
                FROM sync_operations 
                GROUP BY operation_type, status
                """
            )
            
            return {
                'total_synced_messages': total_messages,
                'recent_synced_messages': recent_messages,
                'operations': {
                    op_type: {status: count for status, count in stats}
                    for op_type, stats in operations_stats.fetchall()
                }
            }

async def setup_database(config: dict) -> DatabaseManager:
    """
    Налаштовує та ініціалізує менеджер бази даних.
    
    Args:
        config (dict): Конфігурація з налаштуваннями
        
    Returns:
        DatabaseManager: Налаштований менеджер бази даних
    """
    db = DatabaseManager(config)
    await db.initialize()
    return db