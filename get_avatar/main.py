import discord, os, sys
sys.path.insert(0, "/home/archibald/Documents/GIT/.data")
import data # type: ignore


test = 0

class MyClient(discord.Client):
    
    async def on_ready(self):
        print(f'We have logged in as {client.user}')

    async def on_message(self, message):
        if message.author == client.user:
            return
        if message.content.startswith("%"):
            if "test" in message.content.split(" ")[0][1:]:
                await message.channel.send(message.author.avatar)
            elif message.content.split(" ")[0][1:] == "status":
                if sys.platform == "linux": await message.channel.send(f'"avatar": active')
                else: await message.channel.send("\"speechbubble\": poshel nahui")

        if message.content.startswith("%avatar"):
            if message.content.split(" ")[1].startswith("<@") and message.content.split(" ")[1][-1] == ">":
                await discord.utils.get(message.guild.members, id=int(message.content.split(" ")[1][2:-1])).avatar.save(f"{os.getcwd()}/temp/temp.png")
                await message.reply(file=discord.File(f"{os.getcwd()}/temp/temp.png", filename="temp.png"))
                os.remove(f"{os.getcwd()}/temp/temp.png")
if __name__ == "__main__":
    if sys.platform == "linux":
        path = os.getcwd()
    elif sys.platform == "win32":
        path = os.getcwd() + "/py/ArchTests"
    else: raise Exception("OS is not supported")

    
    try:
        with open(f"{os.getcwd()}/error_log.log", "r", encoding="utf-8") as file:
            pass
    except:
        with open(f"{os.getcwd()}/error_log.log", "w", encoding="utf-8") as file:
            file.write("# This is bot internal errors log\n\n")

    intents = discord.Intents.all()
    intents.message_content = True
    client = MyClient(intents=intents)

    try:
        if test:
            client.run(data.archtests_token)
        else: 
            client.run(data.viscord_token)
    except Exception as ex:
        print(ex)
        with open(f"{os.getcwd()}/error_log.log", "a", encoding="utf-8") as file:
            file.write(f"{ex}\n")
