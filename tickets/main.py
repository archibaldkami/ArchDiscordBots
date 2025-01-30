import discord
from discord.ext import commands
from discord.ui import Button, View
import asyncio
import os
import sys

sys.path.insert(0, '/home/ubuntu/.arch/bots/.data')
# sys.path.insert(0, '/home/kami/Documents/Backups/BOTS BACKUP/bots/.data')
import data 

TOKEN = data.viscord_token
# TOKEN = data.a2e_token
GUILD_ID = 1227656291384557648
CATEGORY_ID = 1294015235253862420
ARCHIVE_CATEGORY_ID = 1290779648124522588
TICKET_CHANNEL_ID = 1294017045805142081
# GUILD_ID = 689454398463672323
# CATEGORY_ID = 1327718964935135293
# ARCHIVE_CATEGORY_ID = 1327719001824170147
# TICKET_CHANNEL_ID = 1327718161709006949

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

class TicketCloseView(View):
    def __init__(self, member: discord.Member, ticket_channel: discord.TextChannel):
        super().__init__(timeout=None)
        self.member = member
        self.ticket_channel = ticket_channel
        self.disabled = True

    @discord.ui.button(label="Отменить закрытие", style=discord.ButtonStyle.red)
    async def cancel_close(self, interaction: discord.Interaction, button: Button):
        self.disabled = False
        print("[DEBUG] -> Запрос на отмену закрытия тикета от пользователя:", interaction.user)
        await interaction.channel.send(
            embed=discord.Embed(description="Закрытие тикета отменено!", color=discord.Color.red())
        )
        await interaction.message.delete()
        print("[DEBUG] -> Закрытие тикета отменено и сообщение о закрытии удалено")

class TicketView(View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=None)
        self.member = member

    @discord.ui.button(label="Закрыть тикет", style=discord.ButtonStyle.red)
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        print("[DEBUG] -> Запрос на закрытие тикета от пользователя:", interaction.user)
        await interaction.response.send_message("Тикет будет закрыт через 1 минуту. Нажмите 'Отменить закрытие', чтобы отменить.", ephemeral=True)
        
        self.view=TicketCloseView(self.member, interaction.channel)
        close_msg = await interaction.channel.send(
            embed=discord.Embed(description="Тикет будет закрыт через 1 минуту.", color=discord.Color.red()),
            view=self.view
        )

        await asyncio.sleep(60)

        if self.view.disabled:
            print("[DEBUG] -> Тикет не был отменен, начинаем процесс закрытия")
            await interaction.channel.set_permissions(self.member, overwrite=None)
            await interaction.channel.edit(category=bot.get_channel(ARCHIVE_CATEGORY_ID))
            await interaction.channel.send("Тикет закрыт и перемещен в архив.")
            print("[DEBUG] -> Тикет закрыт и перенесен в архив")

@bot.event
async def on_ready():
    print(f'Бот {bot.user} успешно запущен.')
    
    ticket_channel = bot.get_channel(TICKET_CHANNEL_ID)

    if ticket_channel is not None:
        embed = discord.Embed(title="Создать тикет", description="Нажмите на кнопку ниже, чтобы создать тикет.", color=discord.Color.green())
        button = Button(label="Создать тикет", style=discord.ButtonStyle.green)

        async def button_callback(interaction: discord.Interaction):
            guild = bot.get_guild(GUILD_ID)
            category = bot.get_channel(CATEGORY_ID)

            print("[DEBUG] -> Получен запрос на открытие тикета от пользователя:", interaction.user)

            new_ticket_channel = await guild.create_text_channel(f"🎫-{interaction.user.name}", category=category)
            await new_ticket_channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
            print("[DEBUG] -> Канал тикета создан. Права пользователя настроены.")

            await new_ticket_channel.send(
                embed=discord.Embed(description="Опишите вашу проблему.", color=discord.Color.blue()),
                view=TicketView(interaction.user)
            )
            
            await interaction.response.send_message(f"Тикет создан: {new_ticket_channel.mention}", ephemeral=True)
            await interaction.user.send(f"Ваш тикет создан: {new_ticket_channel.mention}")
            print("[DEBUG] -> Тикет успешно создан и сообщение отправлено пользователю")

        button.callback = button_callback

        view = View(timeout=None)
        view.add_item(button)

        await ticket_channel.send(embed=embed, view=view)
        print("[DEBUG] -> Сообщение для создания тикетов отправлено в канал")

    # await bot.tree.sync()
    print("[DEBUG] -> Синхронизация команд завершена")

bot.run(TOKEN)
