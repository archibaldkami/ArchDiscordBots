import sys, os, discord, time, asyncio
from datetime import date
sys.path.insert(0, '../.data')
import data
today = date.today().strftime("%d-%m-%y")
img = f"cd temp; wget https://energy.volyn.ua/spozhyvacham/perervy-u-elektropostachanni/hrafik-vidkliuchen/\!img/{today}.jpg; cd .."
path = os.getcwd()

test = 0
blcc_channel = 1280960338937909300
test_channel = 1253435782593642728
channel = test_channel

async def bruh():
    while True:
        # if int(time.strftime("%S", time.localtime())) % 60 == 0 and int(time.strftime("%M", time.localtime())) % 60 == 0 and int(time.strftime("%H", time.localtime())) % 24 == 6:
        if int(time.strftime("%S", time.localtime())) % 60 == 0 and int(time.strftime("%M", time.localtime())) % 60 == 30 and int(time.strftime("%H", time.localtime())) % 24 == 6:
            # await message.reply("bruh...")
            os.system(img)
            await blcc.send(file=discord.File(f"temp/{today}.jpg", filename=f"{today}.jpg"))
            os.remove(f"temp/{today}.jpg")
            print("bruh...")
        await asyncio.sleep(1)

class MyClient(discord.Client):
    async def on_ready(self):
        global blcc
        blcc = discord.utils.get(discord.utils.get(client.guilds, id=689454398463672323).channels, id=channel)
        os.chdir(path)
        await bruh()
        print(f'We have logged in as {client.user}')

    async def on_message(self, message):
        if message.content.strip().startswith("$get_bcl"):
            try:
                os.system(img)
                await message.reply(file=discord.File(f"temp/{today}.jpg", filename=f"{today}.jpg"))
                os.remove(f"temp/{today}.jpg")
            except Exception as ex: print(ex, img, sep="\n")
if __name__ == "__main__":
    intents = discord.Intents.all()
    intents.message_content = True
    client = MyClient(intents=intents)

    try:
        if test:
            client.run(data.archtests_token)
        else:
            client.run(data.a2e_token)
    except Exception as ex:
        print(ex)
        with open(f"{os.getcwd()}/error_log.log", "a", encoding="utf-8") as file:
            file.write(f"{ex}\n")

