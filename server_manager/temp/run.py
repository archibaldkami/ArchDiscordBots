# run.py
from data import TOKEN
from main import *

if __name__ == "__main__":
    try:
        bot = DiscordBot()
        bot.run(TOKEN)
    except Exception as e:
        print(f"Помилка запуску бота: {str(e)}")