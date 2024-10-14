import discord, os, json, sys

sys.path.insert(0, '/home/ubuntu/.arch/bots/.data')
import data

global allowed_guilds_name
global out
global _config_
global linux

test = 0

allowed_guilds_id = [data.notes, data.viscord]
allowed_guilds_name = {"Kami Notes": {}, "Viscord Empire": {}}
previous_role = "@everyone"

class MyClient(discord.Client):
    async def on_ready(self):
        print(f'We have logged in as {client.user}')
        for temp_guild in allowed_guilds_id:
            guild = client.get_guild(temp_guild)
            invites = await guild.invites()
            invite_list_json = f'{"{"}' + ", ".join(f'"{invite.code}": {invite.uses}' for invite in invites) + "}"
            allowed_guilds_name[f"{guild.name}"] = json.loads(invite_list_json)
    
    async def on_member_join(self, member):
        invites = await member.guild.invites()
        current_invite_list = json.loads(f'{"{"}' + ", ".join(f'"{invite.code}": "{invite.uses}"' for invite in invites) + "}")
        for invite in allowed_guilds_name[member.guild.name]:
            try:
                if int(allowed_guilds_name[member.guild.name][invite]) != int(current_invite_list[invite]):
                    roles = [discord.utils.get(member.guild.roles, id=int(role_)) for role_ in _config_[member.guild.name][invite]]
                    allowed_guilds_name[member.guild.name] = current_invite_list
                    await member.add_roles(*roles)
            except Exception as ex: 
                with open(f"{os.getcwd()}/error_log.log", "a", encoding="utf-8") as file:
                    file.write(f"{ex}\n")

    async def on_message(self, message):
        if message.author == client.user:
            return
        if message.content.startswith("$") and message.author.id in data.supreme_administrator_list:
            if message.content.split(" ")[0][1:] == "invites":
                await message.channel.send(f"```{allowed_guilds_name}```")

            elif message.content.split(" ")[0][1:] == "restart":
                # await message.channel.send("Restarting...")
                if linux: os.system("bash restart.sh")
                if linux: await message.channel.send("Poshel nahui")
                else: os.system("start /min cmd.exe /c restart.bat")

            elif message.content.split(" ")[0][1:] == 'stop':
                await message.channel.send("Stopping...")
                if linux: os.system('screen -XS "invite_detector" quit')
                else: os.system(f"taskkill /PID {out}")

            elif message.content.split(" ")[0][1:] == "status":
                if not linux: await message.channel.send(f"Current bot session id is `{out}`")
                else: await message.channel.send(f'"invite_detector": active')

            elif message.content.split(" ")[0][1:] == "linux":
                if linux: await message.channel.send("Yep, Mreow")
                else: await message.channel.send("Ahh, no")

if __name__ == "__main__":

    if sys.platform == "linux": linux = 1
    elif sys.platform == "win32": linux = 0
    else: raise Exception(f"OS \"{sys.platform}\" is not supported")

    if linux:
        if not os.path.isfile(f"{os.getcwd()}/restart.sh"):
            with open(f"{os.getcwd()}/restart.sh", "w") as file:
                file.write('screen -XS "invite_detector" quit\nscreen -d -m -S "invite_detector" python3 main.py')
    else:
        session_id_file = "temporary_sessionid"
        os.system(f"wmic process where \"name='cmd.exe'\" get ProcessId > {session_id_file}.log")
        with open(f"{session_id_file}.log", "r") as file:
            out = str(file.read())
            out = "".join(list(out.split("\n")[-5].split()[0])[1::2])
        with open(f"restart.bat", "w") as file:
            file.write(f"@echo off\ntaskkill /PID {out}\npython {__file__}")

    try:
        with open(f"{os.getcwd()}/error_log.log", "r", encoding="utf-8") as file:
            pass
    except:
        with open(f"{os.getcwd()}/error_log.log", "w", encoding="utf-8") as file:
            file.write("# This is bot internal errors log\n\n")

    try:
        with open(f"{os.getcwd()}/config.json", "r", encoding="utf-8") as file:
            _config_ = json.loads(file.read())
    except:
        with open(f"{os.getcwd()}/error_log.log", "a", encoding="utf-8") as file:
            file.write("Config file is not exists\n")
            raise Exception("Config file is not exists")

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
