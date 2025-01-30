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
from message_sync import _create_channels_map

class ServerSync(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('ServerSync')
    
    async def on_guild_channel_create(channel):
        source_guild_id = int(self.bot.config['servers']['primary']['id'])
        if message.guild.id != source_guild_id:
            return
        try:
            target_guild_id = int(self.bot.config['servers']['secondary']['id'])
            target_guild = self.bot.get_guild(target_guild_id)
            if not target_guild:
                return
            
            channels_map = self._create_channels_map(channel.guild, target_guild)
            target_channel = channels_map.get(channel.id)
            if not target_channel:
                return
                
        except Exception as e:
            self.logger.error(f"Помилка синхронізації повідомлення в реальному часі: {str(e)}")

async def setup(bot):
    """Налаштовує ког для бота."""
    await bot.add_cog(ServerSync(bot))