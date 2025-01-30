import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Dict, List
import logging
from datetime import datetime, timedelta
import asyncio
from discord.ui import View, Button, Select

class ConfirmationView(View):
    """Інтерактивне вікно підтвердження дії."""
    
    def __init__(self, timeout: float = 180.0):
        super().__init__(timeout=timeout)
        self.value = None
    
    @discord.ui.button(label="Підтвердити", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        self.value = True
        self.stop()
        await interaction.response.defer()
    
    @discord.ui.button(label="Скасувати", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        self.value = False
        self.stop()
        await interaction.response.defer()

class ServerSelectorView(View):
    """Меню вибору сервера для операцій."""
    
    def __init__(self, servers: List[discord.Guild]):
        super().__init__()
        
        # Створюємо селект-меню з серверами
        select = Select(
            placeholder="Виберіть сервер",
            options=[
                discord.SelectOption(
                    label=server.name,
                    value=str(server.id),
                    description=f"ID: {server.id}"
                ) for server in servers
            ]
        )
        
        select.callback = self.select_callback
        self.add_item(select)
        self.value = None
    
    async def select_callback(self, interaction: discord.Interaction):
        """Обробник вибору сервера."""
        self.value = interaction.data["values"][0]
        self.stop()
        await interaction.response.defer()

class AdminInterface(commands.Cog):
    """Ког для адміністративного інтерфейсу керування ботом."""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('AdminInterface')
        self.active_tasks: Dict[int, asyncio.Task] = {}
        
    @commands.hybrid_command(name="admin")
    @commands.has_role('SyncAdmin')
    async def admin_panel(self, ctx: commands.Context):
        """Відкриває панель адміністратора."""
        embed = discord.Embed(
            title="Панель адміністратора",
            description="Оберіть дію для керування синхронізацією серверів",
            color=discord.Color.blue()
        )
        
        # Створюємо кнопки для різних дій
        view = discord.ui.View(timeout=300)
        
        # Кнопка статусу
        status_button = Button(
            style=discord.ButtonStyle.primary,
            label="Статус синхронізації",
            custom_id="status"
        )
        status_button.callback = self.show_status
        view.add_item(status_button)
        
        # Кнопка налаштувань
        settings_button = Button(
            style=discord.ButtonStyle.secondary,
            label="Налаштування",
            custom_id="settings"
        )
        settings_button.callback = self.show_settings
        view.add_item(settings_button)
        
        # Кнопка керування задачами
        tasks_button = Button(
            style=discord.ButtonStyle.success,
            label="Активні задачі",
            custom_id="tasks"
        )
        tasks_button.callback = self.show_tasks
        view.add_item(tasks_button)
        
        await ctx.send(embed=embed, view=view)
    
    async def show_status(self, interaction: discord.Interaction):
        """Показує поточний статус синхронізації."""
        await interaction.response.defer()
        
        embed = discord.Embed(
            title="Статус синхронізації",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Отримуємо статус для всіх серверів
        for guild in self.bot.guilds:
            progress = await self.bot.get_sync_progress(guild.id)
            if progress:
                # Форматуємо прогрес
                operation = progress['operation'].replace('_', ' ').title()
                progress_bar = self._create_progress_bar(progress['progress'])
                status_text = (
                    f"Операція: {operation}\n"
                    f"Прогрес: {progress_bar} ({progress['progress']:.1%})\n"
                    f"Оновлено: <t:{int(progress['last_update'])}:R>"
                )
            else:
                status_text = "Неактивний"
            
            embed.add_field(
                name=guild.name,
                value=status_text,
                inline=False
            )
        
        await interaction.followup.send(embed=embed)
    
    async def show_settings(self, interaction: discord.Interaction):
        """Показує та дозволяє змінювати налаштування бота."""
        embed = discord.Embed(
            title="Налаштування синхронізації",
            color=discord.Color.blue()
        )
        
        # Додаємо поточні налаштування
        config = self.bot.config
        settings_text = (
            f"**Інтервал синхронізації:** {config['sync']['sync_interval']} сек\n"
            f"**Ліміт історії:** {config['sync']['message_history_limit']} повідомлень\n"
            f"**Інтервал бекапів:** {config['security']['backup_interval'] // 3600} годин\n"
            f"**Рівень логування:** {config['logging']['level']}"
        )
        
        embed.description = settings_text
        
        # Створюємо кнопки для зміни налаштувань
        view = discord.ui.View(timeout=300)
        
        # Селект для вибору параметра
        select = Select(
            placeholder="Виберіть параметр для зміни",
            options=[
                discord.SelectOption(
                    label="Інтервал синхронізації",
                    value="sync_interval",
                    description="Частота синхронізації в секундах"
                ),
                discord.SelectOption(
                    label="Ліміт історії",
                    value="message_history_limit",
                    description="Кількість повідомлень для синхронізації"
                ),
                discord.SelectOption(
                    label="Інтервал бекапів",
                    value="backup_interval",
                    description="Частота створення резервних копій"
                )
            ]
        )
        
        select.callback = self.setting_selected
        view.add_item(select)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def setting_selected(self, interaction: discord.Interaction):
        """Обробник вибору налаштування для зміни."""
        setting = interaction.data["values"][0]
        
        # Створюємо модальне вікно для введення нового значення
        modal = discord.ui.Modal(title=f"Зміна налаштування")
        
        # Додаємо поле введення
        input_field = discord.ui.TextInput(
            label="Нове значення",
            placeholder="Введіть нове значення...",
            required=True
        )
        modal.add_item(input_field)
        
        async def modal_submit(interaction: discord.Interaction):
            try:
                # Конвертуємо та валідуємо значення
                value = int(input_field.value)
                if value <= 0:
                    raise ValueError("Значення має бути більше 0")
                
                # Оновлюємо конфігурацію
                if setting == "sync_interval":
                    self.bot.config['sync']['sync_interval'] = value
                elif setting == "message_history_limit":
                    self.bot.config['sync']['message_history_limit'] = value
                elif setting == "backup_interval":
                    self.bot.config['security']['backup_interval'] = value * 3600
                
                await interaction.response.send_message(
                    f"✅ Налаштування успішно оновлено!",
                    ephemeral=True
                )
                
            except ValueError as e:
                await interaction.response.send_message(
                    f"❌ Помилка: {str(e)}",
                    ephemeral=True
                )
        
        modal.on_submit = modal_submit
        await interaction.response.send_modal(modal)
    
    async def show_tasks(self, interaction: discord.Interaction):
        """Показує активні задачі синхронізації."""
        embed = discord.Embed(
            title="Активні задачі синхронізації",
            color=discord.Color.blue()
        )
        
        if not self.active_tasks:
            embed.description = "Немає активних задач"
        else:
            for guild_id, task in self.active_tasks.items():
                guild = self.bot.get_guild(guild_id)
                if guild:
                    # Отримуємо інформацію про задачу
                    task_info = (
                        f"Статус: {'Виконується' if not task.done() else 'Завершено'}\n"
                        f"Запущено: <t:{int(task.get_coro().cr_frame.f_locals.get('start_time', 0))}:R>"
                    )
                    embed.add_field(
                        name=guild.name,
                        value=task_info,
                        inline=False
                    )
        
        # Додаємо кнопку для зупинки задач
        view = discord.ui.View(timeout=300)
        
        stop_button = Button(
            style=discord.ButtonStyle.danger,
            label="Зупинити всі задачі",
            custom_id="stop_all",
            disabled=not self.active_tasks
        )
        stop_button.callback = self.stop_all_tasks
        view.add_item(stop_button)
        
        await interaction.response.send_message(embed=embed, view=view)
    
    async def stop_all_tasks(self, interaction: discord.Interaction):
        """Зупиняє всі активні задачі синхронізації."""
        # Запитуємо підтвердження
        confirm_view = ConfirmationView()
        await interaction.response.send_message(
            "⚠️ Ви впевнені, що хочете зупинити всі активні задачі?",
            view=confirm_view,
            ephemeral=True
        )
        
        # Очікуємо відповідь
        await confirm_view.wait()
        
        if confirm_view.value:
            # Зупиняємо всі задачі
            for task in self.active_tasks.values():
                task.cancel()
            
            self.active_tasks.clear()
            
            await interaction.followup.send(
                "✅ Всі задачі успішно зупинено",
                ephemeral=True
            )
    
    @staticmethod
    def _create_progress_bar(progress: float, length: int = 20) -> str:
        """Створює текстовий прогрес-бар."""
        filled = int(length * progress)
        bar = '█' * filled + '░' * (length - filled)
        return f"`{bar}`"
    
    @commands.Cog.listener()
    async def on_task_complete(self, guild_id: int):
        """Обробник завершення задачі синхронізації."""
        if guild_id in self.active_tasks:
            del self.active_tasks[guild_id]

async def setup(bot):
    """Налаштовує ког для бота."""
    await bot.add_cog(AdminInterface(bot))