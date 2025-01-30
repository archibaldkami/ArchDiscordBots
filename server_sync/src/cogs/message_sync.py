import discord
from discord.ext import commands
import asyncio
from typing import Optional, Dict, List, Union
import logging
from datetime import datetime
import json

class MessageSync(commands.Cog):
    """Ког для синхронізації повідомлень між серверами."""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('MessageSync')
        self.webhook_cache: Dict[int, discord.Webhook] = {}
        self.sync_tasks = {}
        self.thread_map: Dict[int, int] = {}

        self.logger.setLevel(logging.DEBUG)
    
    @commands.group(name='sync', invoke_without_command=True)
    @commands.has_role('SyncAdmin')
    async def sync(self, ctx):
        """Група команд для синхронізації повідомлень."""
        await ctx.send("Доступні підкоманди: start, status, stop")
    
    @sync.command(name='start')
    async def sync_start(self, ctx, limit: Optional[int] = None):
        """
        Починає синхронізацію повідомлень.
        
        Parameters:
            limit (Optional[int]): Кількість повідомлень для синхронізації
        """
        if not await self._check_permissions(ctx):
            return
        
        # Отримання налаштувань з конфігурації
        source_guild_id = int(self.bot.config['servers']['primary']['id'])
        target_guild_id = int(self.bot.config['servers']['secondary']['id'])
        
        source_guild = self.bot.get_guild(source_guild_id)
        target_guild = self.bot.get_guild(target_guild_id)
        
        if not source_guild or not target_guild:
            await ctx.send("❌ Не вдалося отримати доступ до серверів")
            return
        
        # Створення завдання синхронізації
        task = asyncio.create_task(
            self._sync_messages(ctx, source_guild, target_guild, limit)
        )
        self.sync_tasks[target_guild_id] = task
        
        await ctx.send("✅ Розпочато процес синхронізації повідомлень")
    
    async def _sync_messages(self, ctx, source_guild: discord.Guild, 
                           target_guild: discord.Guild, limit: Optional[int] = None):
        """Виконує синхронізацію повідомлень між серверами."""
        try:
            await self.bot.update_sync_progress(target_guild.id, "sync_start", 0.0)
            
            # Створення словника відповідності каналів
            channels_map = self._create_channels_map(source_guild, target_guild)
            
            # Підрахунок загальної кількості повідомлень
            total_messages = 0
            processed_messages = 0
            
            # First pass: count messages
            for source_channel in source_guild.text_channels:
                target_channel = channels_map.get(source_channel.id)
                if not target_channel:
                    continue
                
                message_limit = limit or self.bot.config['sync']['message_history_limit']
                async for _ in source_channel.history(limit=message_limit):
                    total_messages += 1
            
            # Second pass: sync messages
            for source_channel in source_guild.text_channels:
                target_channel = channels_map.get(source_channel.id)
                if not target_channel:
                    continue
                
                webhook = await self._get_webhook(target_channel)
                if not webhook:
                    continue
                
                # Store messages in a list to maintain order
                channel_messages = []
                async for message in source_channel.history(limit=message_limit):
                    channel_messages.append(message)
                
                # Process messages in reverse order
                for message in reversed(channel_messages):
                    try:
                        await self._sync_message(message, webhook)
                        processed_messages += 1
                        
                        # Оновлення прогресу
                        progress = processed_messages / total_messages
                        await self.bot.update_sync_progress(
                            target_guild.id,
                            "syncing_messages",
                            progress
                        )
                        
                    except Exception as e:
                        self.logger.error(f"Помилка синхронізації повідомлення {message.id}: {str(e)}")
            
            await self.bot.update_sync_progress(target_guild.id, "sync_completed", 1.0)
            await ctx.send("✅ Синхронізацію повідомлень завершено")
            
        except Exception as e:
            self.logger.exception("Помилка при синхронізації повідомлень")
            await ctx.send(f"❌ Помилка при синхронізації повідомлень: {str(e)}")
            
        finally:
            await self.bot.clear_sync_progress(target_guild.id)
    
    async def _sync_message(self, message: discord.Message, webhook: discord.Webhook, target_channel: discord.TextChannel):
        """Синхронізує окреме повідомлення через webhook."""

        # Перевіряємо, чи повідомлення в гілці
        if isinstance(message.channel, discord.Thread):
            target_thread_id = self.threads_map.get(message.channel.id)
            if not target_thread_id:
                return
        
        # Підготовка вкладень
        files = []
        for attachment in message.attachments:
            try:
                file = await attachment.to_file()
                files.append(file)
            except discord.HTTPException:
                self.logger.warning(f"Не вдалося завантажити вкладення {attachment.filename}")
        
        # Підготовка embeds
        embeds = message.embeds
        
        # Створення часової мітки
        timestamp = int(message.created_at.timestamp())
        content = message.content
        
        if message.type == discord.MessageType.reply and (message.reference and message.reference.channel_id):
            channel_id = message.reference.channel_id
            message_id = message.reference.message_id
            channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
            message_replied = await channel.fetch_message(message_id)
            
            if content:
                content = f"> -# {message_replied.author} - <t:{int(message.created_at.timestamp())}:t> [message]({message.jump_url})\n> {message_replied.content}\n\n{content}"
            else:
                content = f"> -# {message_replied.author} - <t:{int(message.created_at.timestamp())}:t> [message]({message.jump_url})\n> {message_replied.content}"
                
        elif content:
            content = f"{content}"
        else:
            content = f"<t:{timestamp}:t>"

        # Відправка повідомлення через webhook
        try:
            if webhook:
                await webhook.send(
                    content=content,
                    username=message.author.name,
                    avatar_url=message.author.display_avatar.url,
                    embeds=embeds,
                    files=files
                )
            else:
                await target_channel.send(f"-# {message.author.name}\n{content}", embeds=embeds, files=files)

        except discord.HTTPException as e:
            self.logger.error(f"Помилка відправки через webhook: {str(e)}")
            raise

    async def _get_webhook(self, channel: discord.TextChannel) -> Optional[discord.Webhook]:
        """Отримує або створює webhook для каналу."""
        if channel.id in self.webhook_cache:
            return self.webhook_cache[channel.id]
        
        # Пошук існуючого webhook
        webhooks = await channel.webhooks()
        webhook = discord.utils.get(
            webhooks,
            name=self.bot.config['sync']['webhook_name']
        )
        
        # Створення нового webhook якщо не знайдено
        if not webhook:
            try:
                webhook = await channel.create_webhook(
                    name=self.bot.config['sync']['webhook_name']
                )
            except discord.HTTPException:
                self.logger.error(f"Не вдалося створити webhook для каналу {channel.name}")
                return None
        
        self.webhook_cache[channel.id] = webhook
        return webhook
    
    @staticmethod
    def _create_channels_map(source_guild: discord.Guild, target_guild: discord.Guild) -> Dict[int, discord.TextChannel]:
        """
        Створює мапу відповідності каналів між серверами.
        
        Returns:
            Dict[int, discord.TextChannel]: Словник {source_channel_id: target_channel}
        """
        channels_map = {}
        
        for source_channel in source_guild.text_channels:
            # Шукаємо канал з таким самим ім'ям та категорією
            target_channel = discord.utils.get(
                target_guild.text_channels,
                name=source_channel.name,
                category__name=source_channel.category.name if source_channel.category else None
            )
            
            if target_channel:
                channels_map[source_channel.id] = target_channel
        
        return channels_map

    @staticmethod
    async def _create_threads_map(source_guild: discord.Guild, target_guild: discord.Guild,
                                category_name: str = None, thread_name: str = None) -> dict:
        """
        Повертає словник зі співвідношенням гілок між вихідним та цільовим серверами Discord.
        
        Параметри:
        source_guild (discord.Guild): Вихідний сервер Discord
        target_guild (discord.Guild): Цільовий сервер Discord
        category_name (str, optional): Назва категорії для фільтрації
        thread_name (str, optional): Назва гілки для фільтрації
        
        Повертає:
        dict: Словник у форматі {source_thread: target_thread}
        """
        threads_mapping = {}
        
        # Отримуємо всі активні гілки з серверів
        source_threads = await source_guild.active_threads()
        target_threads = await target_guild.active_threads()
        
        # Фільтруємо гілки за категорією, якщо вказано
        if category_name:
            source_threads = [thread for thread in source_threads 
                            if (thread.parent and thread.parent.category and 
                                thread.parent.category.name.lower() == category_name.lower())]
            target_threads = [thread for thread in target_threads 
                            if (thread.parent and thread.parent.category and 
                                thread.parent.category.name.lower() == category_name.lower())]
        
        # Фільтруємо гілки за назвою, якщо вказано
        if thread_name:
            source_threads = [thread for thread in source_threads 
                            if thread.name.lower() == thread_name.lower()]
            target_threads = [thread for thread in target_threads 
                            if thread.name.lower() == thread_name.lower()]
        
        # Створюємо мапінг гілок
        for source_thread in source_threads:
            # Шукаємо відповідну гілку на цільовому сервері
            target_thread = next(
                (thread for thread in target_threads 
                if thread.name.lower() == source_thread.name.lower() and
                (not category_name or 
                (thread.parent and thread.parent.category and 
                thread.parent.category.name.lower() == category_name.lower()))),
                None
            )
            
            if target_thread:
                threads_mapping[source_thread.id] = target_thread
        
        return threads_mapping

    @sync.command(name='status')
    async def sync_status(self, ctx):
        """Показує статус процесу синхронізації повідомлень."""
        guild_id = ctx.guild.id
        progress = await self.bot.get_sync_progress(guild_id)
        
        if not progress:
            await ctx.send("❌ Активного процесу синхронізації не знайдено")
            return
        
        # Створюємо embed зі статусом
        embed = discord.Embed(
            title="Статус синхронізації повідомлень",
            color=discord.Color.blue(),
            timestamp=datetime.fromtimestamp(progress['last_update'])
        )
        
        # Додаємо поля з інформацією
        operation_name = progress['operation'].replace('_', ' ').title()
        embed.add_field(
            name="Операція",
            value=operation_name,
            inline=False
        )
        
        # Створюємо прогрес-бар
        progress_value = progress['progress']
        progress_bar = self._create_progress_bar(progress_value)
        embed.add_field(
            name="Прогрес",
            value=f"{progress_bar} ({progress_value:.1%})",
            inline=False
        )
        
        # Додаємо час останнього оновлення
        embed.set_footer(text="Останнє оновлення")
        
        await ctx.send(embed=embed)
    
    @sync.command(name='stop')
    async def sync_stop(self, ctx):
        """Зупиняє процес синхронізації повідомлень."""
        guild_id = ctx.guild.id
        
        if guild_id in self.sync_tasks:
            task = self.sync_tasks[guild_id]
            task.cancel()
            await self.bot.clear_sync_progress(guild_id)
            del self.sync_tasks[guild_id]
            await ctx.send("✅ Процес синхронізації зупинено")
        else:
            await ctx.send("❌ Активного процесу синхронізації не знайдено")
    
    @staticmethod
    def _create_progress_bar(progress: float, length: int = 20) -> str:
        """
        Створює текстовий прогрес-бар.
        
        Args:
            progress (float): Значення прогресу від 0 до 1
            length (int): Довжина прогрес-бару
            
        Returns:
            str: Текстовий прогрес-бар
        """
        filled = int(length * progress)
        bar = '█' * filled + '░' * (length - filled)
        return f"`{bar}`"
    
    async def _check_permissions(self, ctx) -> bool:
        """
        Перевіряє права користувача на виконання команд синхронізації.
        
        Returns:
            bool: True якщо користувач має необхідні права
        """
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ Необхідні права адміністратора для виконання цієї команди")
            return False
        return True
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Обробник нових повідомлень для синхронізації в реальному часі.
        """
        # Ігноруємо повідомлення від ботів та webhook'ів
        if message.author.bot or message.webhook_id:
            return
        
        # Перевіряємо, чи це повідомлення з основного серверу
        source_guild_id = int(self.bot.config['servers']['primary']['id'])
        if message.guild.id != source_guild_id:
            return
        
        try:
            # Отримуємо цільовий сервер
            target_guild_id = int(self.bot.config['servers']['secondary']['id'])
            target_guild = self.bot.get_guild(target_guild_id)
            if not target_guild:
                return
            
            # Знаходимо відповідний канал
            channels_map = self._create_channels_map(message.guild, target_guild)
            self.threads_map = await self._create_threads_map(message.guild, target_guild)

            if message.channel.type == discord.ChannelType.public_thread:
                # Знаходимо цільову гілку
                target_channel = id=self.threads_map.get(message.channel.id)

            else:
                target_channel = channels_map.get(message.channel.id)
            if not target_channel:
                return


            # Отримуємо webhook
            if message.channel.type == discord.ChannelType.public_thread:
                await self._sync_message(message, False, target_channel)

            else:
                webhook = await self._get_webhook(target_channel)
                await self._sync_message(message, webhook, target_channel)
            # if not webhook:
            #     return
            
            # # Синхронізуємо повідомлення
            # await self._sync_message(message, webhook, target_channel)
            
        except Exception as e:
            self.logger.error(f"Помилка синхронізації повідомлення в реальному часі: {str(e)}")

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """Обробник видалення повідомлень."""
        if message.author.bot or message.webhook_id:
            return
            
        if message.guild.id != int(self.bot.config['servers']['primary']['id']):
            return
            
        try:
            # Отримуємо цільовий сервер та канал
            target_guild = self.bot.get_guild(int(self.bot.config['servers']['secondary']['id']))
            if not target_guild:
                return
            
            if message.channel.type == discord.ChannelType.public_thread:
                threads_map = await self._create_threads_map(message.guild, target_guild)
                target_channel = threads_map.get(message.channel.id)
            else:
                channels_map = self._create_channels_map(message.guild, target_guild)
                target_channel = channels_map.get(message.channel.id)
            
            if not target_channel:
                return
                
            # Створюємо embed для видаленого повідомлення
            embed = discord.Embed(
                title="Повідомлення видалено",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="Автор",
                value=f"{message.author.name} ({message.author.id})",
                inline=False
            )
            
            if message.content:
                embed.add_field(
                    name="Вміст повідомлення",
                    value=message.content[:1024],  # Discord має ліміт на 1024 символи
                    inline=False
                )
                
            embed.add_field(
                name="Канал",
                value=f"#{message.channel.name}",
                inline=False
            )
            
            embed.set_footer(text=f"ID повідомлення: {message.id}")
            
            log_channel = discord.utils.get(target_guild.channels, id=self.bot.config["channels"]["message_log"])
            log_webhook = await self._get_webhook(log_channel)

            if log_webhook:
                await log_webhook.send(embed=embed)

            # Отримуємо webhook і надсилаємо embed
            if message.channel.type != discord.ChannelType.public_thread:
                webhook = await self._get_webhook(target_channel)
                
                if webhook:
                    await webhook.send(embed=embed)

            
                
        except Exception as e:
            self.logger.error(f"Помилка при обробці видалення повідомлення: {str(e)}")

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """Обробник редагування повідомлень."""
        if before.author.bot or before.webhook_id:
            return
            
        if before.guild.id != int(self.bot.config['servers']['primary']['id']):
            return
            
        # Ігноруємо якщо вміст не змінився
        if before.content == after.content:
            return
            
        try:
            # Отримуємо цільовий сервер та канал
            target_guild = self.bot.get_guild(int(self.bot.config['servers']['secondary']['id']))
            if not target_guild:
                return

            if after.channel.type == discord.ChannelType.public_thread:
                threads_map = await self._create_threads_map(before.guild, target_guild)
                target_channel = threads_map.get(before.channel.id)
            else:
                channels_map = self._create_channels_map(before.guild, target_guild)
                target_channel = channels_map.get(before.channel.id)

            if not target_channel:
                return
                
            # Створюємо embed для редагованого повідомлення
            embed = discord.Embed(
                title="Повідомлення відредаговано",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="Автор",
                value=f"{before.author.name} ({before.author.id})",
                inline=False
            )
            
            embed.add_field(
                name="До редагування",
                value=before.content[:1024] if before.content else "*пусто*",
                inline=False
            )
            
            embed.add_field(
                name="Після редагування",
                value=after.content[:1024] if after.content else "*пусто*",
                inline=False
            )
            
            embed.add_field(
                name="Канал",
                value=f"#{before.channel.name}",
                inline=False
            )
            
            embed.set_footer(text=f"ID повідомлення: {before.id}")

            log_channel = discord.utils.get(target_guild.channels, id=self.bot.config["channels"]["message_log"])
            log_webhook = await self._get_webhook(log_channel)

            if log_webhook:
                await log_webhook.send(embed=embed)

            # Отримуємо webhook і надсилаємо embed
            if message.channel.type == discord.ChannelType.public_thread:
                webhook = await self._get_webhook(target_channel)
                if webhook:
                    await webhook.send(embed=embed)
                
        except Exception as e:
            self.logger.error(f"Помилка при обробці редагування повідомлення: {str(e)}")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        """Обробник додавання реакцій."""
        if user.bot or reaction.message.webhook_id:
            return
            
        if reaction.message.guild.id != int(self.bot.config['servers']['primary']['id']):
            return
            
        try:
            # Отримуємо цільовий сервер та канал
            target_guild = self.bot.get_guild(int(self.bot.config['servers']['secondary']['id']))
            if not target_guild:
                return
                
            channels_map = self._create_channels_map(reaction.message.guild, target_guild)
            target_channel = channels_map.get(reaction.message.channel.id)
            if not target_channel:
                return
                
            # Створюємо embed для реакції
            embed = discord.Embed(
                title="Додано реакцію",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="Користувач",
                value=f"{user.name} ({user.id})",
                inline=False
            )
            
            if isinstance(reaction.emoji, discord.PartialEmoji):
                emoji_info = f"{reaction.emoji.name} - (`{reaction.emoji.id}`)"
            else:
                emoji_info = f"{reaction.emoji}"

                
            embed.add_field(
                name="Реакція",
                value=emoji_info,
                inline=False
            )
            
            embed.add_field(
                name="Повідомлення",
                value=reaction.message.content[:1024] if reaction.message.content else "*пусто*",
                inline=False
            )
            
            embed.add_field(
                name="Канал",
                value=f"#{reaction.message.channel.name}",
                inline=False
            )
            
            embed.set_footer(text=f"ID повідомлення: {reaction.message.id}")
            
            # Отримуємо webhook і надсилаємо embed
            webhook = await self._get_webhook(target_channel)
            if webhook:
                await webhook.send(embed=embed)
                
        except Exception as e:
            self.logger.error(f"Помилка при обробці додавання реакції: {str(e)}")

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        """Обробник створення нових гілок."""
        if thread.guild.id != int(self.bot.config['servers']['primary']['id']):
            return


        # target_guild = self.bot.get_guild(int(self.bot.config['servers']['secondary']['id']))
        # if not target_guild:
        #     return

        # channels_map = self._create_channels_map(thread.guild, target_guild)
        # target_channel = channels_map.get(thread.parent_id)
        try:
            pass
            # Отримуємо цільовий сервер та канал
            target_guild = self.bot.get_guild(int(self.bot.config['servers']['secondary']['id']))
            if not target_guild:
                return

            channels_map = self._create_channels_map(thread.guild, target_guild)
            target_channel = channels_map.get(thread.parent_id)
            if not target_channel:
                return

            # Створюємо нову гілку на цільовому сервері
            target_thread = await target_channel.create_thread(
                name=thread.name,
                type=thread.type,
                auto_archive_duration=thread.auto_archive_duration
            )

            # Зберігаємо відповідність гілок
            self.thread_map[thread.id] = target_thread.id
            self.threads_map = _create_threads_map(message.guild, target_guild)

            # Отримуємо всі повідомлення з вихідної гілки
            async for message in thread.history(oldest_first=True):
                if not message.author.bot:
                    await self._sync_message(message, False, target_thread)

        except Exception as e:
            self.logger.error(f"Помилка при створенні гілки: {str(e)}")

    @commands.Cog.listener()
    async def on_thread_update(self, before: discord.Thread, after: discord.Thread):
        """Обробник оновлення гілок."""
        if before.guild.id != int(self.bot.config['servers']['primary']['id']):
            return

        try:
            target_thread_id = self.thread_map.get(before.id)
            if not target_thread_id:
                return

            target_guild = self.bot.get_guild(int(self.bot.config['servers']['secondary']['id']))
            if not target_guild:
                return

            # Знаходимо цільову гілку
            target_thread = discord.utils.get(target_guild.threads, id=target_thread_id)
            if not target_thread:
                return

            # Оновлюємо властивості гілки
            await target_thread.edit(
                name=after.name,
                archived=after.archived,
                locked=after.locked,
                slowmode_delay=after.slowmode_delay,
                auto_archive_duration=after.auto_archive_duration
            )

        except Exception as e:
            self.logger.error(f"Помилка при оновленні гілки: {str(e)}")

    @commands.Cog.listener()
    async def on_thread_delete(self, thread: discord.Thread):
        """Обробник видалення гілок."""
        if thread.guild.id != int(self.bot.config['servers']['primary']['id']):
            return

        try:
            target_thread_id = self.thread_map.get(thread.id)
            if not target_thread_id:
                return

            target_guild = self.bot.get_guild(int(self.bot.config['servers']['secondary']['id']))
            if not target_guild:
                return

            # Знаходимо цільову гілку
            target_thread = discord.utils.get(target_guild.threads, id=target_thread_id)
            if target_thread:
                await target_thread.delete()

            # Видаляємо запис з мапи
            del self.thread_map[thread.id]

        except Exception as e:
            self.logger.error(f"Помилка при видаленні гілки: {str(e)}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Обробник змін стану голосового каналу."""
        if member.bot:
            return
            
        if member.guild.id != int(self.bot.config['servers']['primary']['id']):
            return
            
        try:
            # Отримуємо цільовий сервер
            target_guild = self.bot.get_guild(int(self.bot.config['servers']['secondary']['id']))
            if not target_guild:
                return

            # Визначаємо тип дії з голосовим каналом
            if before.channel is None and after.channel is not None:
                action = f"Приєднався до каналу: {after.channel.name}"
                embed = discord.Embed(
                    title="Приєднався до каналу",
                    color=discord.Color.red(),
                    timestamp=datetime.utcnow()
                )
            elif before.channel is not None and after.channel is None:
                action = f"Покинув канал: {before.channel.name}"
                embed = discord.Embed(
                    title="Покинув канал",
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
            elif before.channel != after.channel:
                action = f"Перейшов з каналу {before.channel.name} до {after.channel.name}"
                embed = discord.Embed(
                    title="Перейшов з каналу",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
            else:
                embed = discord.Embed(
                    title="Зміна голосового статусу",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
            
            embed.add_field(
                name="Користувач",
                value=f"{member.name} ({member.id})",
                inline=False
            )
                
            embed.add_field(name="Дія", value=action, inline=False)
            embed.set_footer(text=f"ID користувача: {member.id}")

            if member.avatar:
                embed.set_thumbnail(url=member.avatar.url)
            
            # Надсилаємо лог
            log_channel = discord.utils.get(target_guild.channels, id=self.bot.config["channels"]["voice_log"])
            log_webhook = await self._get_webhook(log_channel)
            
            if log_webhook:
                await log_webhook.send(embed=embed)
                
        except Exception as e:
            self.logger.error(f"Помилка при обробці зміни голосового статусу: {str(e)}")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Обробник приєднання користувача до серверу."""
        if member.bot:
            return
            
        if member.guild.id != int(self.bot.config['servers']['primary']['id']):
            return
            
        try:
            target_guild = self.bot.get_guild(int(self.bot.config['servers']['secondary']['id']))
            if not target_guild:
                return
                
            embed = discord.Embed(
                title="Новий користувач",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="Користувач",
                value=f"{member.name} ({member.id})",
                inline=False
            )
            
            embed.add_field(
                name="Акаунт створено",
                value=member.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
                inline=False
            )
            
            embed.set_footer(text=f"ID користувача: {member.id}")
            
            if member.avatar:
                embed.set_thumbnail(url=member.avatar.url)
                
            log_channel = discord.utils.get(target_guild.channels, id=self.bot.config["channels"]["member_log"])
            log_webhook = await self._get_webhook(log_channel)
            
            if log_webhook:
                await log_webhook.send(embed=embed)
                
        except Exception as e:
            self.logger.error(f"Помилка при обробці приєднання користувача: {str(e)}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Обробник виходу користувача з серверу."""
        if member.bot:
            return
            
        if member.guild.id != int(self.bot.config['servers']['primary']['id']):
            return
            
        try:
            target_guild = self.bot.get_guild(int(self.bot.config['servers']['secondary']['id']))
            if not target_guild:
                return
                
            embed = discord.Embed(
                title="Користувач покинув сервер",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="Користувач",
                value=f"{member.name} ({member.id})",
                inline=False
            )
            
            embed.add_field(
                name="Приєднався",
                value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
                inline=False
            )
            
            roles = [role.name for role in member.roles if role.name != "@everyone"]
            if roles:
                embed.add_field(
                    name="Ролі",
                    value=", ".join(roles),
                    inline=False
                )
                
            embed.set_footer(text=f"ID користувача: {member.id}")
            
            if member.avatar:
                embed.set_thumbnail(url=member.avatar.url)
                
            log_channel = discord.utils.get(target_guild.channels, id=self.bot.config["channels"]["member_log"])
            log_webhook = await self._get_webhook(log_channel)
            
            if log_webhook:
                await log_webhook.send(embed=embed)
                
        except Exception as e:
            self.logger.error(f"Помилка при обробці виходу користувача: {str(e)}")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Обробник оновлення даних користувача."""
        if before.bot:
            return
            
        if before.guild.id != int(self.bot.config['servers']['primary']['id']):
            return
            
        try:
            # Перевіряємо чи змінився нікнейм
            if before.nick == after.nick:
                return
                
            target_guild = self.bot.get_guild(int(self.bot.config['servers']['secondary']['id']))
            if not target_guild:
                return
                
            embed = discord.Embed(
                title="Зміна нікнейму",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="Користувач",
                value=f"{after.name} ({after.id})",
                inline=False
            )
            
            embed.add_field(
                name="Старий нікнейм",
                value=before.nick or "Не встановлено",
                inline=False
            )
            
            embed.add_field(
                name="Новий нікнейм",
                value=after.nick or "Не встановлено",
                inline=False
            )
            
            embed.set_footer(text=f"ID користувача: {after.id}")
            
            log_channel = discord.utils.get(target_guild.channels, id=self.bot.config["channels"]["member_update_log"])
            log_webhook = await self._get_webhook(log_channel)
            
            if log_webhook:
                await log_webhook.send(embed=embed)
                
        except Exception as e:
            self.logger.error(f"Помилка при обробці зміни нікнейму: {str(e)}")

async def setup(bot):
    """Налаштовує ког для бота."""
    await bot.add_cog(MessageSync(bot))