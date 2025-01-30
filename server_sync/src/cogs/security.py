import discord
from discord.ext import commands
import asyncio
import json
import shutil
from datetime import datetime, timedelta
import logging
from pathlib import Path
from typing import Optional, List, Dict
import aiofiles
import yaml

class Security(commands.Cog):
    """
    Ког для забезпечення безпеки та керування правами доступу.
    Включає систему бекапів, керування правами та відкат змін.
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('Security')
        self.backup_path = Path('data/backups')
        self.backup_path.mkdir(parents=True, exist_ok=True)
        self.backup_task = None
        self._load_security_config()
        self._start_backup_scheduler()
    
    def _load_security_config(self):
        """Завантажує конфігурацію безпеки."""
        self.security_config = self.bot.config['security']
        self.allowed_roles = set(self.security_config['allowed_roles'])
        self.backup_interval = self.security_config['backup_interval']
        self.max_backups = self.security_config['max_backups']
    
    def _start_backup_scheduler(self):
        """Запускає планувальник автоматичних бекапів."""
        async def backup_scheduler():
            while True:
                try:
                    await self.create_backup()
                    await asyncio.sleep(self.backup_interval)
                except Exception as e:
                    self.logger.error(f"Помилка в планувальнику бекапів: {str(e)}")
                    await asyncio.sleep(300)  # Очікування 5 хвилин перед повторною спробою
        
        self.backup_task = asyncio.create_task(backup_scheduler())
    
    @commands.group(name='security', invoke_without_command=True)
    @commands.has_role('SyncAdmin')
    async def security(self, ctx):
        """Група команд для керування безпекою."""
        await ctx.send("Доступні підкоманди: backup, restore, permissions, audit")
    
    @security.command(name='backup')
    async def backup(self, ctx, description: Optional[str] = None):
        """Створює резервну копію даних серверу."""
        try:
            backup_path = await self.create_backup(description)
            await ctx.send(f"✅ Резервну копію створено успішно: `{backup_path.name}`")
        except Exception as e:
            await ctx.send(f"❌ Помилка створення резервної копії: {str(e)}")
    
    async def create_backup(self, description: Optional[str] = None) -> Path:
        """
        Створює резервну копію даних серверу.
        
        Args:
            description: Опис бекапу
            
        Returns:
            Path: Шлях до створеного бекапу
        """
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_name = f"backup_{timestamp}"
        if description:
            backup_name += f"_{description}"
        
        backup_dir = self.backup_path / backup_name
        backup_dir.mkdir(exist_ok=True)
        
        try:
            # Бекап конфігурації
            await self._backup_config(backup_dir)
            
            # Бекап даних серверів
            await self._backup_guilds_data(backup_dir)
            
            # Бекап бази даних
            await self._backup_database(backup_dir)
            
            # Створення метаданих бекапу
            await self._create_backup_metadata(backup_dir, description)
            
            # Видалення старих бекапів
            await self._cleanup_old_backups()
            
            return backup_dir
            
        except Exception as e:
            shutil.rmtree(backup_dir, ignore_errors=True)
            self.logger.error(f"Помилка створення бекапу: {str(e)}")
            raise
    
    async def _backup_config(self, backup_dir: Path):
        """Створює копію конфігураційних файлів."""
        config_dir = backup_dir / 'config'
        config_dir.mkdir(exist_ok=True)
        
        # Копіювання конфігураційних файлів
        config_files = Path('config').glob('*.yaml')
        for file in config_files:
            shutil.copy2(file, config_dir / file.name)
    
    async def _backup_guilds_data(self, backup_dir: Path):
        """Зберігає дані про структуру серверів."""
        for guild_id in [self.bot.config['servers']['primary']['id'],
                        self.bot.config['servers']['secondary']['id']]:
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                continue
            
            guild_data = {
                'id': guild.id,
                'name': guild.name,
                'categories': [],
                'roles': [],
                'channels': []
            }
            
            # Збереження категорій
            for category in guild.categories:
                guild_data['categories'].append({
                    'name': category.name,
                    'position': category.position,
                    'overwrites': self._serialize_overwrites(category.overwrites)
                })
            
            # Збереження ролей
            for role in guild.roles:
                guild_data['roles'].append({
                    'name': role.name,
                    'permissions': role.permissions.value,
                    'color': role.color.value,
                    'hoist': role.hoist,
                    'mentionable': role.mentionable,
                    'position': role.position
                })
            
            # Збереження каналів
            for channel in guild.channels:
                if isinstance(channel, (discord.TextChannel, discord.VoiceChannel)):
                    channel_data = {
                        'name': channel.name,
                        'type': str(channel.type),
                        'position': channel.position,
                        'category': channel.category.name if channel.category else None,
                        'overwrites': self._serialize_overwrites(channel.overwrites)
                    }
                    
                    if isinstance(channel, discord.TextChannel):
                        channel_data.update({
                            'topic': channel.topic,
                            'slowmode_delay': channel.slowmode_delay,
                            'nsfw': channel.nsfw
                        })
                    elif isinstance(channel, discord.VoiceChannel):
                        channel_data.update({
                            'bitrate': channel.bitrate,
                            'user_limit': channel.user_limit
                        })
                    
                    guild_data['channels'].append(channel_data)
            
            # Збереження даних серверу
            guild_file = backup_dir / f'guild_{guild.id}.json'
            async with aiofiles.open(guild_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(guild_data, indent=2))
    
    @staticmethod
    def _serialize_overwrites(overwrites):
        """Серіалізує налаштування прав доступу."""
        serialized = {}
        for target, overwrite in overwrites.items():
            allow, deny = overwrite.pair()
            serialized[target.name] = {
                'allow': allow.value,
                'deny': deny.value
            }
        return serialized
    
    async def _backup_database(self, backup_dir: Path):
        """Створює копію бази даних."""
        db_path = Path(self.bot.config['database']['url'].replace('sqlite:///', ''))
        if db_path.exists():
            shutil.copy2(db_path, backup_dir / 'database.sqlite')
    
    async def _create_backup_metadata(self, backup_dir: Path, description: Optional[str]):
        """Створює файл метаданих бекапу."""
        metadata = {
            'timestamp': datetime.utcnow().isoformat(),
            'description': description,
            'version': '1.0',
            'bot_version': getattr(self.bot, 'version', 'unknown')
        }
        
        metadata_file = backup_dir / 'metadata.json'
        async with aiofiles.open(metadata_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(metadata, indent=2))
    
    async def _cleanup_old_backups(self):
        """Видаляє старі бекапи, залишаючи тільки останні n штук."""
        backups = sorted(self.backup_path.glob('backup_*'))
        while len(backups) > self.max_backups:
            oldest = backups.pop(0)
            shutil.rmtree(oldest)
    
    @security.command(name='restore')
    async def restore(self, ctx, backup_name: str):
        """Відновлює дані з резервної копії."""
        backup_dir = self.backup_path / backup_name
        if not backup_dir.exists():
            await ctx.send("❌ Вказану резервну копію не знайдено")
            return
        
        confirm_msg = await ctx.send(
            "⚠️ Відновлення з резервної копії призведе до перезапису поточних даних. "
            "Ви впевнені? Реагуйте ✅ для підтвердження або ❌ для скасування."
        )
        
        await confirm_msg.add_reaction('✅')
        await confirm_msg.add_reaction('❌')
        
        try:
            reaction, user = await self.bot.wait_for(
                'reaction_add',
                timeout=30.0,
                check=lambda r, u: u == ctx.author and str(r.emoji) in ['✅', '❌']
            )
            
            if str(reaction.emoji) == '✅':
                await ctx.send("🔄 Починаємо відновлення з резервної копії...")
                await self._restore_from_backup(backup_dir)
                await ctx.send("✅ Відновлення завершено успішно!")
            else:
                await ctx.send("❌ Відновлення скасовано")
                
        except asyncio.TimeoutError:
            await ctx.send("❌ Час очікування минув. Відновлення скасовано")
    
    async def _restore_from_backup(self, backup_dir: Path):
        """Відновлює дані з резервної копії."""
        # Відновлення конфігурації
        config_dir = backup_dir / 'config'
        if config_dir.exists():
            for config_file in config_dir.glob('*.yaml'):
                shutil.copy2(config_file, Path('config') / config_file.name)
        
        # Відновлення бази даних
        db_backup = backup_dir / 'database.sqlite'
        if db_backup.exists():
            db_path = Path(self.bot.config['database']['url'].replace('sqlite:///', ''))
            shutil.copy2(db_backup, db_path)
        
        # Перезавантаження конфігурації бота
        self._load_security_config()

    @security.command(name='permissions')
    async def permissions(self, ctx, role: discord.Role = None):
        """Показує або змінює налаштування прав доступу."""
        if not role:
            # Показуємо поточні налаштування
            embed = discord.Embed(
                title="Налаштування прав доступу",
                color=discord.Color.blue()
            )
            
            allowed_roles = "\n".join(self.allowed_roles) or "Не налаштовано"
            embed.add_field(
                name="Дозволені ролі",
                value=f"```\n{allowed_roles}\n```",
                inline=False
            )
            
            await ctx.send(embed=embed)
        else:
            # Перевіряємо права адміністратора
            if not ctx.author.guild_permissions.administrator:
                await ctx.send("❌ Необхідні права адміністратора для зміни налаштувань")
                return
            
            if role.name in self.allowed_roles:
                self.allowed_roles.remove(role.name)
                await ctx.send(f"✅ Роль {role.name} видалено з дозволених")
            else:
                self.allowed_roles.add(role.name)
                await ctx.send(f"✅ Роль {role.name} додано до дозволених")
            
            # Оновлюємо конфігурацію
            self.security_config['allowed_roles'] = list(self.allowed_roles)
            await self._save_security_config()
    
    async def _save_security_config(self):
        """Зберігає зміни в конфігурації безпеки."""
        config_path = Path('config/config.yaml')
        
        async with aiofiles.open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(await f.read())
        
        config['security'] = self.security_config
        
        async with aiofiles.open(config_path, 'w', encoding='utf-8') as f:
            await f.write(yaml.dump(config, default_flow_style=False))

async def setup(bot):
    """Налаштовує ког для бота."""
    await bot.add_cog(Security(bot))