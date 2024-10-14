import discord, os, sys
from PIL import Image, ImageDraw
sys.path.insert(0, '/home/ubuntu/.arch/bots/.data')
import data


test = 0

class MyClient(discord.Client):
    
#    # Makes Magic
#    def __init__(self, *args, **kwargs):
#        super().__init__(*args, **kwargs)
#        self.tree = discord.app_commands.CommandTree(self)
    
    async def on_ready(self):
        print(f'We have logged in as {client.user}')
        os.chdir(path)

    async def on_message(self, message):
        if message.author == client.user:
            return
        if message.content.startswith("$") and message.author.id in data.supreme_administrator_list:
            if "test" in message.content.split(" ")[0][1:]:
                await message.channel.send(message.author.avatar)
            elif message.content.split(" ")[0][1:] == "status":
                if sys.platform == "linux": await message.channel.send(f'"speech_bubble": active')
                else: await message.channel.send("\"speechbubble\": poshel nahui")

        if message.content.startswith("$sb"):
            if message.content.lower().strip() == "$sb" and message.attachments:
                if message.attachments[0].filename.split(".")[-1] in ["jpg", "png", "webp", "jpeg"]:
                    try:
                        await message.attachments[0].save(f"{os.getcwd()}/temp/{message.attachments[0].filename}")
                        with Image.open(f"{os.getcwd()}/temp/{message.attachments[0].filename}").convert("RGBA") as img:
                            draw = ImageDraw.Draw(img)
                            x, y = img.size[0]//100, img.size[1]//100
                            draw.ellipse((-x*5, -y*10, img.size[0]+x*5, y*10), fill=(0, 0, 0, 0))
                            draw.polygon([(img.size[0], y*4), (img.size[0]*3//4, img.size[1]//4), (img.size[0]-x*15, y*3)], fill=(0, 0, 0, 0))
                            img.save(f"{os.getcwd()}/temp/out.gif", "PNG")
                        
                        await message.reply(file=discord.File(f"{os.getcwd()}/temp/out.gif", filename="out.gif"))
                        os.remove(f"{os.getcwd()}/temp/{message.attachments[0].filename}")
                        os.remove(f"{os.getcwd()}/temp/out.gif")
                    except:
                        try:
                            print("<bly", end="")
                            os.remove(f"{os.getcwd()}/temp/{message.attachments[0].filename}")
                            os.remove(f"{os.getcwd()}/temp/out.gif")
                            print("at>")
                        except: pass
            elif message.content.split(" ")[1].startswith("<@") and message.content.split(" ")[1][-1] == ">":
                await discord.utils.get(message.guild.members, id=int(message.content.split(" ")[1][2:-1])).avatar.save(f"{os.getcwd()}/temp/temp.png")
                with Image.open(f"{os.getcwd()}/temp/temp.png").convert("RGBA") as img:
                    draw = ImageDraw.Draw(img)
                    x, y = img.size[0]//100, img.size[1]//100
                    draw.ellipse((-x*5, -y*10, img.size[0]+x*5, y*10), fill=(0, 0, 0, 0))
                    draw.polygon([(img.size[0], y*4), (img.size[0]*3//4, img.size[1]//4), (img.size[0]-x*15, y*3)], fill=(0, 0, 0, 0))
                    img.save(f"{os.getcwd()}/temp/out.gif", "PNG")
                    
                await message.reply(file=discord.File(f"{os.getcwd()}/temp/out.gif", filename="out.gif"))
                os.remove(f"{os.getcwd()}/temp/temp.png")
                os.remove(f"{os.getcwd()}/temp/out.gif")
        if message.content.startswith("$convert"):
            if message.content.lower().strip() == "$convert" and message.attachments:
                if message.attachments[0].filename.split(".")[-1] in ["jpg", "png", "webp", "jpeg"]:
                    try:
                        await message.attachments[0].save(f"{os.getcwd()}/temp/{message.attachments[0].filename}")
                        with Image.open(f"{os.getcwd()}/temp/{message.attachments[0].filename}") as img:
                            img.save(f"{os.getcwd()}/temp/out.gif", "PNG")
                        await message.reply(file=discord.File(f"{os.getcwd()}/temp/out.gif", filename="out.gif"))
                        os.remove(f"{os.getcwd()}/temp/{message.attachments[0].filename}")
                        os.remove(f"{os.getcwd()}/temp/out.gif")
                    except:
                        try:
                            print("<bly", end="")
                            os.remove(f"{os.getcwd()}/temp/{message.attachments[0].filename}")
                            os.remove(f"{os.getcwd()}/temp/out.gif")
                            print("at>")
                        except: pass


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

#    @client.tree.command(name="git_pull", description="Just git pull")
#    async def git_pull(interaction: discord.Interaction):
#        if interaction.user.id in data.git_command_permitted_users:
#            os.system("sudo runuser -l hellpizza -c 'cd /home/hellpizza/PFUServer/ve-labs; git pull'")
#            await interaction.response.send_message(f'> Access permitted\n> Success', ephemeral=True)
#        else:
#            await interaction.response.send_message(f'Access denied', ephemeral=True)

#    @client.tree.command(name="sbu", description="Creates speech bubble from user avatar")
#    async def sbu(interaction: discord.Interaction, username: str):
#        if interaction.guild:
#            await discord.utils.get(interaction.guild.members, id=int(username[2:-1])).avatar.save(f"{os.getcwd()}/temp/temp.png")
#            with Image.open(f"{os.getcwd()}/temp/temp.png").convert("RGBA") as img:
#                draw = ImageDraw.Draw(img)
#                x, y = img.size[0]//100, img.size[1]//100
#                draw.ellipse((-x*5, -y*10, img.size[0]+x*5, y*10), fill=(0, 0, 0, 0))
#                draw.polygon([(img.size[0], y*4), (img.size[0]*3//4, img.size[1]//4), (img.size[0]-x*15, y*3)], fill=(0, 0, 0, 0))
#                img.save(f"{os.getcwd()}/temp/out.gif", "PNG")
#            
#            await interaction.response.send_message(file=discord.File(f"{os.getcwd()}/temp/out.gif", filename="out.gif"))
#            os.remove(f"{os.getcwd()}/temp/temp.png")
#            os.remove(f"{os.getcwd()}/temp/out.gif")
#        else: await interaction.response.send_message(f'This only can be used in guilds', ephemeral=True)


    try:
        if test:
            client.run(data.archtests_token)
        else: 
            client.run(data.viscord_token)
    except Exception as ex:
        print(ex)
        with open(f"{os.getcwd()}/error_log.log", "a", encoding="utf-8") as file:
            file.write(f"{ex}\n")
