import discord
from discord.ext import commands
import asyncio
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime
import io

class ServerClone(commands.Cog):
    """Ког для клонування та синхронізації структури серверів."""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('ServerClone')
        self.clone_tasks = {}
        self.cache = {}

    async def _handle_rate_limit(self, exception: discord.HTTPException):
        """Обробляє помилки rate limit"""
        if exception.code == 429:  # Rate limit error
            retry_after = exception.retry_after
            self.logger.warning(f"Rate limit hit, waiting {retry_after} seconds")
            await asyncio.sleep(retry_after)
            return True
        return False

    async def _get_channel_history(self, channel, limit=None):
        """Кешує історію повідомлень каналу"""
        cache_key = f"channel_history_{channel.id}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
            
        messages = []
        async for msg in channel.history(limit=limit, oldest_first=True):
            messages.append(msg)
            
        self.cache[cache_key] = messages
        return messages

    async def _update_progress(self, ctx, current, total, message):
        """Оновлює прогрес-бар"""
        progress = current / total
        bar = self._create_progress_bar(progress)
        await ctx.send(f"{message}: {bar} {progress:.1%}")

    def _convert_overwrites(self, channel, target_guild, roles_map):
        """Конвертує налаштування дозволів"""
        overwrites = {}
        for role, overwrite in channel.overwrites.items():
            if role.name == '@everyone':
                target_role = target_guild.default_role
            else:
                target_role = roles_map.get(role)
                if not target_role:
                    target_role = discord.utils.get(target_guild.roles, name=role.name)
            
            if target_role:
                overwrites[target_role] = overwrite
        return overwrites
        
    @commands.group(name='clone', invoke_without_command=True)
    @commands.has_role('SyncAdmin')
    async def clone(self, ctx):
        """Група команд для клонування серверу."""
        await ctx.send("""Доступні підкоманди: 
- start - повне клонування серверу
- emojis - керування емодзі
- roles - керування ролями
- channels - керування каналами
- categories - керування категоріями
- status - статус клонування
- stop - зупинка клонування""")

    # Група команд для емодзі
    @clone.group(name='emojis')
    async def clone_emojis_group(self, ctx):
        """Керування емодзі серверу."""
        if ctx.invoked_subcommand is None:
            await ctx.send("""Доступні підкоманди для емодзі:
- clone - клонувати емодзі
- delete - видалити всі емодзі""")
    
    @clone.command(name='start')
    async def clone_start(self, ctx):
        """Починає процес клонування серверу."""
        # Перевірка прав доступу
        if not await self._check_permissions(ctx):
            return
            
        # Отримання серверів з конфігурації
        source_guild_id = int(self.bot.config['servers']['primary']['id'])
        target_guild_id = int(self.bot.config['servers']['secondary']['id'])
        
        source_guild = self.bot.get_guild(source_guild_id)
        target_guild = self.bot.get_guild(target_guild_id)
        
        if not source_guild or not target_guild:
            await ctx.send("❌ Не вдалося отримати доступ до серверів")
            return
            
        # Створення завдання клонування
        task = asyncio.create_task(self._clone_guild(ctx, source_guild, target_guild))
        self.clone_tasks[target_guild_id] = task
        
        await ctx.send("✅ Розпочато процес клонування серверу")
        
    async def _clone_guild(self, ctx, source_guild: discord.Guild, target_guild: discord.Guild):
        """Виконує клонування серверу."""
        try:
            # Оновлення прогресу
            await self.bot.update_sync_progress(target_guild.id, "clone_start", 0.0)
            
            # Клонування категорій
            await self._clone_categories(source_guild, target_guild)
            await self.bot.update_sync_progress(target_guild.id, "categories_cloned", 0.25)
            await ctx.send(f"✅ Категорії клоновано")
            
            # Клонування ролей і збереження мапінгу ролей
            roles_map = await self._clone_roles(source_guild, target_guild)
            await self.bot.update_sync_progress(target_guild.id, "roles_cloned", 0.5)
            await ctx.send(f"✅ Ролі клоновано")
            
            # Клонування каналів з передачею мапінгу ролей
            await self._clone_channels(source_guild, target_guild, roles_map)
            await self.bot.update_sync_progress(target_guild.id, "channels_cloned", 0.75)
            await ctx.send(f"✅ Канали клоновано")
            
            # Клонування емодзі
            # await self._clone_emojis(source_guild, target_guild)
            # await self.bot.update_sync_progress(target_guild.id, "clone_completed", 1.0)
            # await ctx.send(f"✅ Емодзі клоновано")
            
            await ctx.send("✅ Клонування серверу успішно завершено")
            
        except Exception as e:
            self.logger.exception("Помилка при клонуванні серверу")
            await ctx.send(f"❌ Помилка при клонуванні серверу: {str(e)}")
            
        finally:
            await self.bot.clear_sync_progress(target_guild.id)

    async def _clone_channels(self, source: discord.Guild, target: discord.Guild, roles_map: Dict):
        """Клонує канали з вихідного серверу."""
        try:
            channels_map = {}
            categories_map = {cat.name: cat for cat in target.categories}
            
            # Групуємо канали за типом
            text_channels = []
            voice_channels = []
            
            for channel in source.channels:
                if isinstance(channel, discord.TextChannel) and channel.category:
                    text_channels.append(channel)
                elif isinstance(channel, discord.VoiceChannel) and channel.category:
                    voice_channels.append(channel)
            
            # Створюємо текстові канали чанками
            total_channels = len(text_channels)
            for i, chunk in enumerate([text_channels[i:i+5] for i in range(0, len(text_channels), 5)]):
                try:
                    new_channels = await asyncio.gather(*(
                        target.create_text_channel(
                            name=channel.name,
                            category=categories_map.get(channel.category.name),
                            topic=channel.topic,
                            position=channel.position,
                            slowmode_delay=channel.slowmode_delay,
                            nsfw=channel.nsfw,
                            overwrites=self._convert_overwrites(channel, target, roles_map)
                        ) for channel in chunk if categories_map.get(channel.category.name)
                    ))
                    channels_map.update(dict(zip([c.id for c in chunk], new_channels)))
                    
                    await asyncio.sleep(1)
                    
                except discord.HTTPException as e:
                    if await self._handle_rate_limit(e):
                        continue
                    raise
            
            # Створюємо голосові канали чанками
            for chunk in [voice_channels[i:i+5] for i in range(0, len(voice_channels), 5)]:
                try:
                    new_channels = await asyncio.gather(*(
                        target.create_voice_channel(
                            name=channel.name,
                            category=categories_map.get(channel.category.name),
                            bitrate=channel.bitrate,
                            user_limit=channel.user_limit,
                            position=channel.position,
                            overwrites=self._convert_overwrites(channel, target, roles_map)
                        ) for channel in chunk if categories_map.get(channel.category.name)
                    ))
                    channels_map.update(dict(zip([c.id for c in chunk], new_channels)))
                    
                    await asyncio.sleep(1)
                    
                except discord.HTTPException as e:
                    if await self._handle_rate_limit(e):
                        continue
                    raise
            
            return channels_map
            
        except Exception as e:
            self.logger.error(f"Error in _clone_channels: {str(e)}")
            raise

    async def _clone_messages_and_threads(self, source_channel: discord.TextChannel, 
                                        target_channel: discord.TextChannel, 
                                        roles_map: Dict):
        """Клонує повідомлення та гілки з вихідного каналу."""
        try:
            # Отримуємо історію повідомлень (обмежену кількість)
            messages = await self._get_channel_history(source_channel, limit=100)
            
            thread_messages = {}
            threads_map = {}

            # Збираємо повідомлення з гілок
            for thread in source_channel.threads:
                thread_messages[thread.id] = await self._get_channel_history(thread, limit=100)

            # Клонуємо повідомлення чанками
            for chunk in [messages[i:i+5] for i in range(0, len(messages), 5)]:
                try:
                    for msg in chunk:
                        # Клонуємо основне повідомлення
                        new_msg = await self._clone_single_message(msg, target_channel)

                        # Якщо це стартове повідомлення гілки, створюємо нову гілку
                        if msg.id in thread_messages:
                            # Створюємо нову гілку
                            thread_name = next((thread.name for thread in source_channel.threads 
                                            if thread.id in thread_messages), "Thread")
                            new_thread = await new_msg.create_thread(name=thread_name)
                            threads_map[msg.id] = new_thread

                            # Клонуємо повідомлення гілки чанками
                            thread_msgs = thread_messages[msg.id]
                            for thread_chunk in [thread_msgs[i:i+5] for i in range(0, len(thread_msgs), 5)]:
                                try:
                                    await asyncio.gather(*(
                                        self._clone_single_message(thread_msg, new_thread)
                                        for thread_msg in thread_chunk
                                    ))
                                    await asyncio.sleep(1)
                                except discord.HTTPException as e:
                                    if await self._handle_rate_limit(e):
                                        continue
                                    raise
                    
                    await asyncio.sleep(1)
                    
                except discord.HTTPException as e:
                    if await self._handle_rate_limit(e):
                        continue
                    raise

        except Exception as e:
            self.logger.error(f"Error in _clone_messages_and_threads: {str(e)}")
            raise

    async def _clone_single_message(self, msg, target_channel):
        """Клонує одне повідомлення."""
        try:
            # Підготовка вкладень
            files = []
            for attachment in msg.attachments:
                try:
                    file_data = await attachment.read()
                    files.append(discord.File(
                        io.BytesIO(file_data),
                        filename=attachment.filename
                    ))
                except Exception as e:
                    self.logger.error(f"Помилка при завантаженні вкладення: {str(e)}")

            # Створення ембедів
            embeds = [embed.to_dict() for embed in msg.embeds]
            
            # Клонування повідомлення
            return await target_channel.send(
                content=msg.content,
                embeds=[discord.Embed.from_dict(embed) for embed in embeds],
                files=files
            )
        except Exception as e:
            self.logger.error(f"Error in _clone_single_message: {str(e)}")
            raise

    async def _clone_categories(self, source: discord.Guild, target: discord.Guild):
        """Клонує категорії з вихідного серверу."""
        # Видалення існуючих категорій
        for category in target.categories:
            await category.delete()
        
        # Видалення існуючих каналів
        for channel in target.channels:
            if channel.id != 1326259863080276102:
                await channel.delete()
        
        # Створення нових категорій
        for category in source.categories:
            await target.create_category(
                name=category.name,
                position=category.position,
                overwrites=category.overwrites
            )
        
    async def _clone_roles(self, source: discord.Guild, target: discord.Guild):
        """Клонує ролі з вихідного серверу."""
        try:
            # Масово видаляємо ролі
            roles_to_delete = [role for role in target.roles[1:] if role.position < target.me.top_role.position]
            for chunk in [roles_to_delete[i:i+5] for i in range(0, len(roles_to_delete), 5)]:
                try:
                    await asyncio.gather(*(
                        role.delete() 
                        for role in chunk 
                        if not role.managed and role.position < target.me.top_role.position
                    ))
                except discord.HTTPException as e:
                    self.logger.warning(f"Не вдалося видалити деякі ролі: {str(e)}")
                await asyncio.sleep(1)
            
            # Створюємо ролі чанками
            roles_data = []
            roles_to_create = [
                (role.name, role.permissions, role.colour, role.hoist, role.mentionable) 
                for role in reversed(source.roles[1:])  # Пропускаємо @everyone
                if not role.managed  # Пропускаємо інтеграційні ролі
            ]
            
            total_roles = len(roles_to_create)
            
            for i, chunk in enumerate([roles_to_create[i:i+5] for i in range(0, len(roles_to_create), 5)]):
                try:
                    new_roles = await asyncio.gather(*(
                        target.create_role(
                            name=role_data[0],
                            permissions=role_data[1],
                            colour=role_data[2],
                            hoist=role_data[3],
                            mentionable=role_data[4]
                        ) for role_data in chunk
                    ))
                    roles_data.extend(zip([role for role, _, _, _, _ in chunk], new_roles))
                    
                    # Оновлюємо прогрес
                    current_progress = (i + 1) * 5
                    if current_progress > total_roles:
                        current_progress = total_roles
                        
                    await asyncio.sleep(1)
                    
                except discord.HTTPException as e:
                    if await self._handle_rate_limit(e):
                        continue
                    self.logger.error(f"Помилка при створенні ролей: {str(e)}")
                        
            return dict(roles_data)
                
        except Exception as e:
            self.logger.error(f"Error in _clone_roles: {str(e)}")
            raise

    async def _clone_emojis(self, source: discord.Guild, target: discord.Guild):
        """Клонує емодзі з вихідного серверу."""
        # Видалення існуючих емодзі
        for emoji in target.emojis:
            try:
                await emoji.delete()
            except discord.HTTPException:
                self.logger.warning(f"Не вдалося видалити емодзі {emoji.name}")
        
        # Створення нових емодзі
        for emoji in source.emojis:
            try:
                # Завантажуємо зображення емодзі
                asset = await emoji.read()
                await target.create_custom_emoji(
                    name=emoji.name,
                    image=asset
                )
            except discord.HTTPException as e:
                self.logger.error(f"Помилка при створенні емодзі {emoji.name}: {str(e)}")

    @clone.command(name='status')
    async def clone_status(self, ctx):
        """Показує статус процесу клонування."""
        guild_id = ctx.guild.id
        progress = await self.bot.get_sync_progress(guild_id)
        
        if not progress:
            await ctx.send("❌ Активного процесу клонування не знайдено")
            return
        
        # Створюємо embed зі статусом
        embed = discord.Embed(
            title="Статус клонування серверу",
            color=discord.Color.blue()
        )
        
        # Додаємо інформацію про прогрес
        embed.add_field(
            name="Поточна операція",
            value=progress['operation'].replace('_', ' ').title(),
            inline=False
        )
        
        # Додаємо прогрес-бар
        progress_bar = self._create_progress_bar(progress['progress'])
        embed.add_field(
            name="Прогрес",
            value=f"`{progress_bar}` {progress['progress']:.1%}",
            inline=False
        )
        
        # Додаємо час останнього оновлення
        last_update = discord.utils.format_dt(
            datetime.fromtimestamp(progress['last_update']),
            style='R'
        )
        embed.add_field(
            name="Останнє оновлення",
            value=last_update,
            inline=False
        )
        
        await ctx.send(embed=embed)

    @staticmethod
    def _create_progress_bar(progress: float, length: int = 20) -> str:
        """Створює текстовий прогрес-бар."""
        filled = int(length * progress)
        bar = '█' * filled + '░' * (length - filled)
        return bar

    @clone.command(name='stop')
    async def clone_stop(self, ctx):
        """Зупиняє процес клонування."""
        guild_id = ctx.guild.id
        
        if guild_id in self.clone_tasks:
            task = self.clone_tasks[guild_id]
            task.cancel()
            await self.bot.clear_sync_progress(guild_id)
            del self.clone_tasks[guild_id]
            await ctx.send("✅ Процес клонування зупинено")
        else:
            await ctx.send("❌ Активного процесу клонування не знайдено")

    async def _check_permissions(self, ctx) -> bool:
        """Перевіряє права користувача на виконання команд клонування."""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ Необхідні права адміністратора для виконання цієї команди")
            return False
        return True

    @clone_emojis_group.command(name='clone')
    async def clone_emojis_cmd(self, ctx):
        """Клонує емодзі з основного серверу."""
        if not await self._check_permissions(ctx):
            return

        source_guild = await self._get_source_guild()
        target_guild = ctx.guild
        
        if not source_guild:
            await ctx.send("❌ Не вдалося отримати доступ до серверів")
            return

        await ctx.send("🔄 Починаю клонування емодзі...")
        try:
            await self._clone_emojis(source_guild, target_guild)
            await ctx.send("✅ Емодзі успішно клоновано")
        except Exception as e:
            await ctx.send(f"❌ Помилка при клонуванні емодзі: {str(e)}")

    @clone_emojis_group.command(name='delete')
    async def delete_emojis_cmd(self, ctx):
        """Видаляє всі емодзі з серверу."""
        if not await self._check_permissions(ctx):
            return
        if not await self._confirm_action(ctx, "видалити всі емодзі"):
            return

        await self._delete_all_emojis(ctx, ctx.guild)

    # Група команд для ролей
    @clone.group(name='roles')
    async def clone_roles_group(self, ctx):
        """Керування ролями серверу."""
        if ctx.invoked_subcommand is None:
            await ctx.send("""Доступні підкоманди для ролей:
- clone - клонувати ролі
- delete - видалити всі ролі""")

    @clone_roles_group.command(name='clone')
    async def clone_roles_cmd(self, ctx):
        """Клонує ролі з основного серверу."""
        if not await self._check_permissions(ctx):
            return

        source_guild = await self._get_source_guild()
        if not source_guild:
            await ctx.send("❌ Не вдалося отримати доступ до серверів")
            return

        await ctx.send("🔄 Починаю клонування ролей...")
        try:
            roles_map = await self._clone_roles(source_guild, ctx.guild)
            await ctx.send(f"✅ Успішно клоновано {len(roles_map)} ролей")
        except Exception as e:
            await ctx.send(f"❌ Помилка при клонуванні ролей: {str(e)}")

    @clone_roles_group.command(name='delete')
    async def delete_roles_cmd(self, ctx):
        """Видаляє всі ролі з серверу."""
        if not await self._check_permissions(ctx):
            return
        if not await self._confirm_action(ctx, "видалити всі ролі"):
            return

        await self._delete_all_roles(ctx, ctx.guild)

    # Група команд для каналів
    @clone.group(name='channels')
    async def clone_channels_group(self, ctx):
        """Керування каналами серверу."""
        if ctx.invoked_subcommand is None:
            await ctx.send("""Доступні підкоманди для каналів:
- clone - клонувати канали
- delete - видалити всі канали""")

    @clone_channels_group.command(name='clone')
    async def clone_channels_cmd(self, ctx):
        """Клонує канали з основного серверу."""
        if not await self._check_permissions(ctx):
            return

        source_guild = await self._get_source_guild()
        if not source_guild:
            await ctx.send("❌ Не вдалося отримати доступ до серверів")
            return

        await ctx.send("🔄 Починаю клонування каналів...")
        try:
            roles_map = await self._clone_roles(source_guild, ctx.guild)  # Потрібно для прав доступу
            channels_map = await self._clone_channels(source_guild, ctx.guild, roles_map)
            await ctx.send(f"✅ Успішно клоновано {len(channels_map)} каналів")
        except Exception as e:
            await ctx.send(f"❌ Помилка при клонуванні каналів: {str(e)}")

    @clone_channels_group.command(name='delete')
    async def delete_channels_cmd(self, ctx):
        """Видаляє всі канали з серверу."""
        if not await self._check_permissions(ctx):
            return
        if not await self._confirm_action(ctx, "видалити всі канали"):
            return

        await self._delete_all_channels(ctx, ctx.guild)

    # Група команд для категорій
    @clone.group(name='categories')
    async def clone_categories_group(self, ctx):
        """Керування категоріями серверу."""
        if ctx.invoked_subcommand is None:
            await ctx.send("""Доступні підкоманди для категорій:
- clone - клонувати категорії
- delete - видалити всі категорії""")

    @clone_categories_group.command(name='clone')
    async def clone_categories_cmd(self, ctx):
        """Клонує категорії з основного серверу."""
        if not await self._check_permissions(ctx):
            return

        source_guild = await self._get_source_guild()
        if not source_guild:
            await ctx.send("❌ Не вдалося отримати доступ до серверів")
            return

        await ctx.send("🔄 Починаю клонування категорій...")
        try:
            await self._clone_categories(source_guild, ctx.guild)
            await ctx.send("✅ Категорії успішно клоновано")
        except Exception as e:
            await ctx.send(f"❌ Помилка при клонуванні категорій: {str(e)}")

    @clone_categories_group.command(name='delete')
    async def delete_categories_cmd(self, ctx):
        """Видаляє всі категорії з серверу."""
        if not await self._check_permissions(ctx):
            return
        if not await self._confirm_action(ctx, "видалити всі категорії"):
            return

        await self._delete_all_categories(ctx, ctx.guild)

    # Допоміжні методи
    async def _get_source_guild(self) -> Optional[discord.Guild]:
        """Отримує вихідний сервер з конфігурації."""
        source_guild_id = int(self.bot.config['servers']['primary']['id'])
        return self.bot.get_guild(source_guild_id)

    async def _confirm_action(self, ctx, action: str) -> bool:
        """Запитує підтвердження дії у користувача."""
        await ctx.send(f"⚠️ Ви впевнені, що хочете {action}? Напишіть `confirm` для підтвердження.")
        
        try:
            msg = await self.bot.wait_for(
                'message',
                timeout=30.0,
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel
            )
        except asyncio.TimeoutError:
            await ctx.send("❌ Час очікування минув. Операцію скасовано.")
            return False

        return msg.content.lower() == 'confirm'

    async def _delete_all_emojis(self, ctx, guild: discord.Guild):
        """Видаляє всі емодзі з серверу."""
        deleted_count = 0
        failed_count = 0

        for emoji in guild.emojis:
            try:
                await emoji.delete()
                deleted_count += 1
                await asyncio.sleep(1.5)
            except Exception as e:
                failed_count += 1
                self.logger.error(f"Не вдалося видалити емодзі {emoji.name}: {str(e)}")

        await ctx.send(f"✅ Видалено емодзі: {deleted_count}\n❌ Не вдалося видалити: {failed_count}")

    async def _delete_all_roles(self, ctx, guild: discord.Guild):
        """Видаляє всі ролі з серверу."""
        deleted_count = 0
        failed_count = 0

        roles = [r for r in guild.roles[1:] if r.position < guild.me.top_role.position]
        for role in roles:
            try:
                if not role.managed:
                    await role.delete()
                    deleted_count += 1
                    await asyncio.sleep(1.5)
            except Exception as e:
                failed_count += 1
                self.logger.error(f"Не вдалося видалити роль {role.name}: {str(e)}")

        await ctx.send(f"✅ Видалено ролей: {deleted_count}\n❌ Не вдалося видалити: {failed_count}")

    async def _delete_all_channels(self, ctx, guild: discord.Guild):
        """Видаляє всі канали з серверу."""
        deleted_count = 0
        failed_count = 0

        for channel in guild.channels:
            try:
                if channel.id != 1326259863080276102:  # Зберігаємо системний канал
                    await channel.delete()
                    deleted_count += 1
                    await asyncio.sleep(1.5)
            except Exception as e:
                failed_count += 1
                self.logger.error(f"Не вдалося видалити канал {channel.name}: {str(e)}")

        await ctx.send(f"✅ Видалено каналів: {deleted_count}\n❌ Не вдалося видалити: {failed_count}")

    async def _delete_all_categories(self, ctx, guild: discord.Guild):
        """Видаляє всі категорії з серверу."""
        deleted_count = 0
        failed_count = 0

        for category in guild.categories:
            try:
                await category.delete()
                deleted_count += 1
                await asyncio.sleep(1.5)
            except Exception as e:
                failed_count += 1
                self.logger.error(f"Не вдалося видалити категорію {category.name}: {str(e)}")

        await ctx.send(f"✅ Видалено категорій: {deleted_count}\n❌ Не вдалося видалити: {failed_count}")

async def setup(bot):
    """Налаштовує ког для бота."""
    await bot.add_cog(ServerClone(bot))