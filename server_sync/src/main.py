import os
import sys
import asyncio
import logging.config
import yaml
from pathlib import Path
from typing import Optional
import signal
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Додаємо директорію проекту до PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.bot import SyncBot
from src.database.db_manager import DatabaseManager

class BotRunner:
    """Клас для управління життєвим циклом бота."""
    
    def __init__(self):
        self.bot: Optional[SyncBot] = None
        self.db: Optional[DatabaseManager] = None
        self._setup_logging()
        self.logger = logging.getLogger('BotRunner')
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        
    def _setup_logging(self) -> None:
        """Налаштовує систему логування з конфігураційного файлу."""
        try:
            log_config_path = project_root / 'config' / 'logging.yaml'
            
            if log_config_path.exists():
                with open(log_config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    
                if not config:  # Перевірка на порожній файл
                    raise ValueError("Файл конфігурації логування порожній")
                
                # Створюємо директорію для логів якщо її немає
                log_dir = project_root / 'logs'
                log_dir.mkdir(exist_ok=True)
                
                # Встановлюємо повні шляхи до файлів логів
                for handler in config.get('handlers', {}).values():
                    if 'filename' in handler:
                        handler['filename'] = str(log_dir / handler['filename'])
                
                logging.config.dictConfig(config)
                
                # Перевіряємо, що логування налаштовано
                test_logger = logging.getLogger('BotRunner')
                test_logger.debug("Logging system initialized")
                
            else:
                # Базове налаштування якщо файл конфігурації відсутній
                logging.basicConfig(
                    level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.StreamHandler(),
                        logging.FileHandler(
                            str(project_root / 'logs' / 'bot.log'),
                            encoding='utf-8'
                        )
                    ]
                )
                logging.warning("Використовується базова конфігурація логування")
                
        except Exception as e:
            # Якщо виникла помилка при налаштуванні логування, встановлюємо базову конфігурацію
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[logging.StreamHandler()]
            )
            logging.error(f"Помилка при налаштуванні логування: {e}")
    
    async def _setup_database(self) -> None:
        """Ініціалізує підключення до бази даних."""
        try:
            log_config_path = project_root / 'config' / 'config.yaml'
            with open(log_config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            self.db = DatabaseManager(config)
            await self.db.initialize()
            self.logger.info("База даних успішно ініціалізована")
        except Exception as e:
            self.logger.error(f"Помилка при ініціалізації бази даних: {e}")
            raise
    
    async def _setup_bot(self) -> None:
        """Створює та налаштовує екземпляр бота."""
        try:
            self.bot = SyncBot()
            self.bot.db = self.db
            self.logger.info("Бот успішно створений та налаштований")
        except Exception as e:
            self.logger.error(f"Помилка при створенні бота: {e}")
            raise
    
    def _setup_signal_handlers(self) -> None:
        """Налаштовує обробники системних сигналів."""
        def signal_handler(sig, frame):
            self.logger.info(f"Отримано сигнал {sig}, починаємо завершення роботи...")
            if self.loop and self.loop.is_running():
                self.loop.create_task(self.shutdown())
        
        try:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        except Exception as e:
            self.logger.error(f"Помилка при налаштуванні обробників сигналів: {e}")
    
    async def shutdown(self) -> None:
        """Коректно завершує роботу всіх компонентів."""
        try:
            self.logger.info("Початок процедури завершення роботи...")
            
            # Спочатку закриваємо бота, щоб припинити створення нових задач
            if self.bot and not self.bot.is_closed():
                self.logger.info("Відключення бота...")
                await self.bot.close()
            
            # Закриваємо підключення до БД
            if self.db:
                self.logger.info("Закриття підключення до бази даних...")
                await self.db.close()
            
            # Отримуємо всі задачі крім поточної
            current_task = asyncio.current_task()
            pending = [task for task in asyncio.all_tasks(self.loop) 
                    if task is not current_task and not task.done()]
            
            if pending:
                self.logger.info(f"Закриття {len(pending)} pending tasks...")
                
                # Додайте цей код перед циклом закриття задач для діагностики
                for task in pending:
                    self.logger.info(f"Pending task: {task.get_name()}, done: {task.done()}, cancelled: {task.cancelled()}")

                # Скасовуємо всі задачі
                for task in pending:
                    task.cancel()
                
                # Чекаємо завершення всіх задач з таймаутом
                try:
                    await asyncio.wait(pending, timeout=5.0)
                    self.logger.info("Всі задачі успішно завершені")
                except asyncio.TimeoutError:
                    self.logger.warning("Деякі задачі не вдалося завершити вчасно")
                
                # Перевіряємо статус задач
                for task in pending:
                    if not task.done():
                        self.logger.warning(f"Задача {task.get_name()} не завершилась")
                    elif task.cancelled():
                        self.logger.info(f"Задача {task.get_name()} була скасована")
                    elif task.exception():
                        self.logger.error(f"Задача {task.get_name()} завершилась з помилкою: {task.exception()}")
            
            self.logger.info("Завершення роботи виконано успішно")
            
        except Exception as e:
            self.logger.error(f"Помилка при завершенні роботи: {e}")
            raise
        finally:
            # Зупиняємо event loop якщо він все ще працює
            try:
                if self.loop and self.loop.is_running():
                    self.loop.stop()
            except Exception as e:
                self.logger.error(f"Помилка при зупинці event loop: {e}")
    
    async def start(self) -> None:
        """Запускає бота та всі необхідні компоненти."""
        try:
            # Завантажуємо змінні середовища
            load_dotenv()
            token = os.getenv('DISCORD_BOT_TOKEN')
            
            if not token:
                raise ValueError("Не знайдено токен бота в змінних середовища")
            
            # Зберігаємо поточний event loop
            self.loop = asyncio.get_running_loop()
            
            # Налаштовуємо обробники сигналів
            self._setup_signal_handlers()
            
            # Ініціалізуємо компоненти
            await self._setup_database()
            await self._setup_bot()
            
            # Запускаємо бота
            self.logger.info("Запуск бота...")
            await self.bot.start(token)
            
        except Exception as e:
            self.logger.error(f"Критична помилка при запуску: {e}")
            await self.shutdown()
            raise

def main():
    """Головна функція для запуску бота."""
    # Налаштовуємо Windows для роботи з asyncio
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Створюємо та запускаємо бота
    runner = BotRunner()
    
    try:
        asyncio.run(runner.start())
    except KeyboardInterrupt:
        print("\nОтримано сигнал завершення роботи")
    except Exception as e:
        print(f"Критична помилка: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()