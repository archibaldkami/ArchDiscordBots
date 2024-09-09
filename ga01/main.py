import sys, discord, os
sys.path.insert(0, '../../.data')
import data

if __name__ == "__main__":

    class MyClient(discord.Client):
        async def on_ready(self):
            print(f'We have logged in as {client.user}')

        async def on_message(self, message):
            if message.content.strip().startswith("$"):
                if message.content.split("$")[1].split(" ")[0] == "cchannel":
                    categoty = await message.guild.create_category(str(message.content.split("$")[1].split(" ")[1]))
                    # await message.guild.create_category_channel(str(message.content.split("$")[1].split(" ")[1]*2))

                    role = await message.guild.create_role(name=str(message.content.split("$")[1].split(" ")[1]))
                    overwrites = {
                        message.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                        message.guild.me: discord.PermissionOverwrite(view_channel=True),
                        role: discord.PermissionOverwrite(view_channel=True)
                        # message.guild.get_role: discord.PermissionOverwrite(view_channel=False)
                    }

                    await message.guild.create_text_channel('secret', overwrites=overwrites, category=categoty)

    intents = discord.Intents.all()
    intents.message_content = True
    client = MyClient(intents=intents)

    try:
        client.run(data.a2e_token)
    except Exception as ex:
        print(ex)
        with open(f"{os.getcwd()}/error_log.log", "a", encoding="utf-8") as file:
            file.write(f"{ex}\n")