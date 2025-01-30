import discord
from discord.ext import commands, tasks
from typing import Dict, List, Optional
import logging
from datetime import datetime, timedelta
import json
import asyncio
from pathlib import Path
import matplotlib.pyplot as plt
import io

class Monitoring(commands.Cog):
    """Ког для моніторингу подій та збору статистики."""
    
    def __init__(self, bot: commands.Bot):
        """Initialize the monitoring cog with a bot instance."""
        if not isinstance(bot, (commands.Bot, commands.AutoShardedBot)):
            raise TypeError("Expected commands.Bot or commands.AutoShardedBot instance")
            
        self.bot = bot
        self.logger = logging.getLogger('Monitoring')
        
        # Ініціалізація лічильників статистики
        self.stats = {
            'messages': 0,
            'edits': 0,
            'deletions': 0,
            'files': 0,
            'reactions': 0,
            'commands': 0,
            'errors': 0
        }
        
        # Кеш для агрегації даних
        self.hourly_stats = {}
        self.daily_stats = {}
        
        # Don't start tasks in __init__, wait for cog_load
        
    async def cog_load(self):
        """Start background tasks when the cog is loaded."""
        self.stats_update.start()
        self.daily_report.start()
    
    def cog_unload(self):
        """Очищення при вивантаженні кога."""
        self.stats_update.cancel()
        self.daily_report.cancel()
    
    @tasks.loop(minutes=5.0)
    async def stats_update(self):
        """Фонове завдання для оновлення статистики."""
        try:
            # Wait for bot to be ready before updating status
            await self.bot.wait_until_ready()
            
            current_hour = datetime.utcnow().strftime('%Y-%m-%d-%H')
            
            # Зберігаємо поточні значення лічильників
            self.hourly_stats[current_hour] = self.stats.copy()
            
            # Зберігаємо статистику в базу даних
            await self._save_stats_to_db()
            
            # Оновлюємо статус бота
            if self.bot is not None and self.bot.is_ready():
                status_text = f"Monitoring {len(self.bot.guilds)} servers | {self.stats['messages']} msgs"
                await self.bot.change_presence(
                    status=discord.Status.online, 
                    activity=discord.CustomActivity(
                        name=status_text
                    )
                )
            
        except Exception as e:
            self.logger.error(f"Помилка оновлення статистики: {str(e)}")
    
    @tasks.loop(hours=24.0)
    async def daily_report(self):
        """Генерує та надсилає щоденний звіт."""
        try:
            # Отримуємо канал для звітів
            alert_channel_id = self.bot.config['monitoring']['alert_channel']
            for guild in self.bot.guilds:
                channel = discord.utils.get(guild.channels, name=alert_channel_id)
                if channel:
                    report = await self._generate_daily_report()
                    await channel.send(embed=report)
        
        except Exception as e:
            self.logger.error(f"Помилка генерації щоденного звіту: {str(e)}")
    
    async def _generate_daily_report(self) -> discord.Embed:
        """Генерує щоденний звіт у форматі embed."""
        embed = discord.Embed(
            title="📊 Щоденний звіт про активність",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Додаємо статистику повідомлень
        embed.add_field(
            name="📝 Повідомлення",
            value=f"Нові: {self.stats['messages']}\n"
                  f"Редаговані: {self.stats['edits']}\n"
                  f"Видалені: {self.stats['deletions']}",
            inline=True
        )
        
        # Додаємо статистику файлів та реакцій
        embed.add_field(
            name="📎 Вкладення та реакції",
            value=f"Файли: {self.stats['files']}\n"
                  f"Реакції: {self.stats['reactions']}",
            inline=True
        )
        
        # Додаємо статистику команд та помилок
        embed.add_field(
            name="⚙️ Системна інформація",
            value=f"Команди: {self.stats['commands']}\n"
                  f"Помилки: {self.stats['errors']}",
            inline=True
        )
        
        # Додаємо графік активності
        chart = await self._generate_activity_chart()
        if chart:
            file = discord.File(chart, filename="activity.png")
            embed.set_image(url="attachment://activity.png")
        
        return embed, file if chart else None
    
    async def _generate_activity_chart(self) -> Optional[io.BytesIO]:
        """Генерує графік активності за останні 24 години."""
        try:
            # Підготовка даних
            hours = []
            message_counts = []
            
            now = datetime.utcnow()
            for i in range(24):
                hour = now - timedelta(hours=i)
                hour_key = hour.strftime('%Y-%m-%d-%H')
                
                hours.insert(0, hour.strftime('%H:00'))
                message_counts.insert(0, self.hourly_stats.get(hour_key, {}).get('messages', 0))
            
            # Створення графіку
            plt.figure(figsize=(10, 5))
            plt.plot(hours, message_counts, marker='o')
            plt.title('Активність повідомлень за 24 години')
            plt.xlabel('Година')
            plt.ylabel('Кількість повідомлень')
            plt.xticks(rotation=45)
            plt.grid(True)
            
            # Зберігаємо графік у байтовий потік
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight')
            buffer.seek(0)
            plt.close()
            
            return buffer
            
        except Exception as e:
            self.logger.error(f"Помилка генерації графіку: {str(e)}")
            return None
    
    async def _update_bot_status(self):
        """Оновлює статус бота з поточною статистикою."""
        try:
            status_text = f"Monitoring {len(self.bot.guilds)} servers | {self.stats['messages']} msgs"
            await self.bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name=status_text
                )
            )
        except Exception as e:
            self.logger.error(f"Помилка оновлення статусу бота: {str(e)}")
    
    async def _save_stats_to_db(self):
        """Зберігає статистику в базу даних."""
        # TODO: Реалізувати після створення db_manager
        pass
    
    @commands.group(name='monitor', invoke_without_command=True)
    @commands.has_role('SyncAdmin')
    async def monitor(self, ctx):
        """Група команд для моніторингу."""
        await ctx.send("Доступні підкоманди: stats, report, reset")
    
    @monitor.command(name='stats')
    async def show_stats(self, ctx):
        """Показує поточну статистику."""
        embed = discord.Embed(
            title="📊 Поточна статистика",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        for key, value in self.stats.items():
            embed.add_field(
                name=key.title(),
                value=str(value),
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    @monitor.command(name='reset')
    async def reset_stats(self, ctx):
        """Скидає лічильники статистики."""
        self.stats = {key: 0 for key in self.stats}
        await ctx.send("✅ Статистику скинуто")
    
    @monitor.command(name='report')
    async def generate_report(self, ctx):
        """Генерує та надсилає звіт за запитом."""
        report, file = await self._generate_daily_report()
        if file:
            await ctx.send(embed=report, file=file)
        else:
            await ctx.send(embed=report)
    
    # Event listeners для збору статистики
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Відстежує нові повідомлення."""
        if not message.author.bot:
            self.stats['messages'] += 1
            if message.attachments:
                self.stats['files'] += len(message.attachments)
    
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Відстежує редагування повідомлень."""
        if not after.author.bot and before.content != after.content:
            self.stats['edits'] += 1
    
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Відстежує видалення повідомлень."""
        if not message.author.bot:
            self.stats['deletions'] += 1
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Відстежує додавання реакцій."""
        if not user.bot:
            self.stats['reactions'] += 1
    
    @commands.Cog.listener()
    async def on_command(self, ctx):
        """Відстежує використання команд."""
        self.stats['commands'] += 1
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Відстежує помилки команд."""
        self.stats['errors'] += 1
        self.logger.error(f"Помилка команди {ctx.command}: {str(error)}")

async def setup(bot):
    """Налаштовує ког для бота."""
    await bot.add_cog(Monitoring(bot))