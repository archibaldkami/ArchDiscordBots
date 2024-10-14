# WIP: This is a work in progress. The code is not yet complete and may not work as intended.

import json
import os
from typing import Dict, List
import sys
import asyncio
from datetime import datetime, timedelta
sys.path.insert(0, "/home/archibald/Documents/GIT/.data")
import data #type: ignore

import aiohttp
import discord
from bs4 import BeautifulSoup
from discord.ext import commands, tasks

CONFIG_FILE = 'config.json'
DISCORD_TOKEN = data.viscord_token
DEFAULT_PREFIX = '&'

test = 1

if test:
    DISCORD_TOKEN = data.archtests_token

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=DEFAULT_PREFIX, intents=intents)

config: Dict = {}
news_channel_id: int = 1253435782593642728

YOUTUBE_CHECK_INTERVAL = 5 * 60  # 5 minutes in seconds
TWITCH_CHECK_INTERVAL = 15  # 15 seconds
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

async def load_config():
    global config
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
    else:
        config = {"content": [{"yt": [], "twitch": []}]}
    
    for channel in config['content'][0]['yt']:
        if 'video_count' not in channel[list(channel.keys())[0]]:
            channel[list(channel.keys())[0]]['video_count'] = 0
    
    for channel in config['content'][0]['twitch']:
        if 'stream' not in channel[list(channel.keys())[0]]:
            channel[list(channel.keys())[0]]['stream'] = 'offline'

async def save_config():
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

async def fetch_with_retry(session, url, max_retries=MAX_RETRIES):
    for attempt in range(max_retries):
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
        except aiohttp.ClientError:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(RETRY_DELAY)
    return None

async def fetch_youtube_video_count(session, channel_url: str) -> int:
    html = await fetch_with_retry(session, f"{channel_url}/videos")
    if html:
        soup = BeautifulSoup(html, 'html.parser')
        videos = soup.find_all('a', {'id': 'video-title'})
        return len(videos)
    return 0

async def check_twitch_status(session, channel_url: str) -> bool:
    html = await fetch_with_retry(session, channel_url)
    if html:
        soup = BeautifulSoup(html, 'html.parser')
        return 'isLiveBroadcast' in str(soup)
    return False

async def check_youtube_updates():
    if news_channel_id is None:
        return

    channel = bot.get_channel(news_channel_id)
    if channel is None:
        return

    async with aiohttp.ClientSession() as session:
        for yt_channel in config['content'][0]['yt']:
            username = list(yt_channel.keys())[0]
            channel_data = yt_channel[username]
            url = channel_data['url']
            new_video_count = await fetch_youtube_video_count(session, url)
            
            if new_video_count == channel_data['video_count'] + 1:
                await channel.send(f"New video from {username}: {url}/videos")
                channel_data['video_count'] = new_video_count
            elif new_video_count != channel_data['video_count']:
                channel_data['video_count'] = new_video_count

    await save_config()

async def check_twitch_updates():
    if news_channel_id is None:
        return

    channel = bot.get_channel(news_channel_id)
    if channel is None:
        return

    async with aiohttp.ClientSession() as session:
        for twitch_channel in config['content'][0]['twitch']:
            username = list(twitch_channel.keys())[0]
            channel_data = twitch_channel[username]
            url = channel_data['url']
            is_live = await check_twitch_status(session, url)
            
            if is_live and channel_data['stream'] == 'offline':
                await channel.send(f"{username} is now live on Twitch! {url}")
                channel_data['stream'] = 'online'
            elif not is_live and channel_data['stream'] == 'online':
                await channel.send(f"{username} has ended their Twitch stream.")
                channel_data['stream'] = 'offline'

    await save_config()

@tasks.loop(seconds=YOUTUBE_CHECK_INTERVAL)
async def youtube_check_loop():
    await check_youtube_updates()

@tasks.loop(seconds=TWITCH_CHECK_INTERVAL)
async def twitch_check_loop():
    await check_twitch_updates()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await load_config()
    youtube_check_loop.start()
    twitch_check_loop.start()

@bot.command(name='add')
async def add_channel(ctx, channel_type: str, channel_name: str, channel_url: str):
    if channel_type not in ['yt', 'twitch']:
        await ctx.send("Invalid channel type. Use 'yt' for YouTube or 'twitch' for Twitch.")
        return

    channels = config['content'][0][channel_type]
    for channel in channels:
        if channel_name in channel:
            await ctx.send(f"{channel_type.capitalize()} channel {channel_name} already exists.")
            return

    if channel_type == 'yt':
        new_channel = {channel_name: {"url": channel_url, "video_count": 0}}
    else:
        new_channel = {channel_name: {"url": channel_url, "stream": "offline"}}

    channels.append(new_channel)
    await save_config()
    await ctx.send(f"{channel_type.capitalize()} channel {channel_name} added successfully.")

@bot.command(name='remove')
async def remove_channel(ctx, channel_type: str, channel_name: str):
    if channel_type not in ['yt', 'twitch']:
        await ctx.send("Invalid channel type. Use 'yt' for YouTube or 'twitch' for Twitch.")
        return

    channels = config['content'][0][channel_type]
    for i, channel in enumerate(channels):
        if channel_name in channel:
            del channels[i]
            await save_config()
            await ctx.send(f"{channel_type.capitalize()} channel {channel_name} removed successfully.")
            return

    await ctx.send(f"{channel_type.capitalize()} channel {channel_name} not found.")

@bot.command(name='news_channel')
async def set_news_channel(ctx, channel_id: int):
    global news_channel_id
    news_channel_id = channel_id
    await ctx.send(f"News channel set to {channel_id}")

@bot.command(name='get_config')
async def get_config(ctx):
    yt_channels = "\n".join([f"{list(channel.keys())[0]}: {channel[list(channel.keys())[0]]['url']}, Video Count: {channel[list(channel.keys())[0]]['video_count']}" for channel in config['content'][0]['yt']])
    twitch_channels = "\n".join([f"{list(channel.keys())[0]}: {channel[list(channel.keys())[0]]['url']}, Stream: {channel[list(channel.keys())[0]]['stream']}" for channel in config['content'][0]['twitch']])
    
    response = f"YouTube Channels:\n{yt_channels}\n\nTwitch Channels:\n{twitch_channels}"
    await ctx.send(response)

bot.run(DISCORD_TOKEN)