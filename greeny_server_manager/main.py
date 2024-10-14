import discord, os, json, sys, time
sys.path.insert(0, "/home/archibald/Documents/GIT/.data")
import data#type: ignore

class MyClient(discord.Client):
    async def on_ready(self):
        if linux: print("Working on Linux")
        else: print("Working on Windows")
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
                await message.channel.send("Restarting...")
                if linux: 
                    os.system("bash restart.sh")
                    sys.exit()
                # if linux: await message.channel.send("Poshel nahui")
                else: os.system("start /min cmd.exe /c restart.bat")

            elif message.content.split(" ")[0][1:] == 'stop':
                await message.channel.send("Stopping...")
                if linux: os.system(f'screen -XS "{screen}" quit')
                else: os.system(f"taskkill /PID {out}")

            elif message.content.split("\n")[0][1:] == 'delete_groups':
                for group in message.content.split("\n")[1:]:
                    cat = discord.utils.get(message.guild.categories, name=group)
                    for i in cat.channels:  
                        # await message.channel.send(i.name + f" {group}")
                        await i.delete()
                        print(f"'{i.name}' channel deleted")
                    await cat.delete()
                    print(f"'{cat.name}' category deleted")

                    roles = [role for role in message.guild.roles]
                    base = discord.utils.get(message.guild.roles, name=group)
                    try:
                        for role in roles:
                            if group == role.name:
                                for invite in _config_[message.guild.name]:
                                    if base.id == _config_[message.guild.name][invite][0]:
                                        del _config_[message.guild.name][invite]
                                        with open("config.json", "w") as file: file.write(json.dumps(_config_))
                                        print(f"{invite} invite deleted")
                                        print("\nconfig updated\n")
                                        break
                    except Exception as ex: print(ex)

                    for role in roles:
                        if group == role.name.split(" ")[0]:
                            await role.delete()
                            print(f"'{role.name}' role deleted")

                    
            
            elif message.content.startswith('$create_groups'):
                temp_config = {}
                for_groups = ""
                for group in message.content.split("\n")[1:]:
                    
                    teacher = discord.utils.get(message.guild.roles, id=1221843659868213399)
                    base = await message.guild.create_role(name=f"{group}")
                    print(f"'{group}' role created")
                    subsubcurator = await message.guild.create_role(name=f"{group} Зам старости")
                    print(f"'{group} Зам старости' role created")
                    subcurator = await message.guild.create_role(name=f"{group} Староста")
                    print(f"'{group} Староста' role created")
                    curator = await message.guild.create_role(name=f"{group} Куратор")
                    print(f"'{group} Куратор' role created")

                    category_overwrites = {
                        base: discord.PermissionOverwrite(view_channel=True, connect=True),
                        subsubcurator: discord.PermissionOverwrite(view_channel=True, connect=True, manage_messages=True, priority_speaker=True),
                        subcurator: discord.PermissionOverwrite(view_channel=True, connect=True, manage_messages=True, manage_channels=True, mute_members=True, deafen_members=True, move_members=True, priority_speaker=True),
                        curator: discord.PermissionOverwrite(view_channel=True, connect=True, manage_messages=True, manage_threads=True, manage_channels=True, mute_members=True, deafen_members=True, move_members=True, priority_speaker=True),
                        message.guild.default_role: discord.PermissionOverwrite(view_channel=False, connect=False)
                        }
                    without_curator_overwrites = {
                        base: discord.PermissionOverwrite(view_channel=True, connect=True),
                        subsubcurator: discord.PermissionOverwrite(view_channel=True, connect=True, manage_messages=True, priority_speaker=True),
                        subcurator: discord.PermissionOverwrite(view_channel=True, connect=True, manage_messages=True, manage_channels=True, mute_members=True, deafen_members=True, move_members=True, priority_speaker=True),
                        curator: discord.PermissionOverwrite(view_channel=False),
                        message.guild.default_role: discord.PermissionOverwrite(view_channel=False, connect=False)
                        }
                    with_teacher_overwrites = {
                        base: discord.PermissionOverwrite(view_channel=True, connect=True),
                        subsubcurator: discord.PermissionOverwrite(view_channel=True, connect=True, manage_messages=True, priority_speaker=True),
                        subcurator: discord.PermissionOverwrite(view_channel=True, connect=True, manage_messages=True, manage_channels=True, mute_members=True, deafen_members=True, move_members=True, priority_speaker=True),
                        curator: discord.PermissionOverwrite(view_channel=True, connect=True, manage_messages=True, manage_threads=True, manage_channels=True, mute_members=True, deafen_members=True, move_members=True, priority_speaker=True),
                        message.guild.default_role: discord.PermissionOverwrite(view_channel=False, connect=False),
                        teacher: discord.PermissionOverwrite(view_channel=False, connect=False)
                        }
                    
                    category = await message.guild.create_category_channel(group, overwrites=category_overwrites)
                    print(f"'{group}' category created")

                    main_chat = await category.create_text_channel("основний", overwrites=category_overwrites)
                    print("'основний' channel created")
                    await category.create_text_channel("без-куратора", overwrites=without_curator_overwrites)
                    print("'без-куратора' channel created")
                    await category.create_text_channel("викладачі", overwrites=with_teacher_overwrites)
                    print("'викладачі' channel created")
                    await category.create_voice_channel("голосовий", overwrites=category_overwrites)
                    print("'голосовий' channel created")

                    invite = await main_chat.create_invite(max_uses=50)
                    print(f"'{invite.code}' invite created")
                    temp_config[invite.code] = [base.id, student]
                    await message.channel.send(f"{group} - {invite.url}\n")
                
                _config_[message.guild.name].update(temp_config)
                with open("config.json", "w") as file: file.write(json.dumps(_config_))
                print("\nconfig updated\n")

                print(json.dumps(temp_config, indent=4))

            # elif message.content.split(" ")[0][1:] == "status":
            #     if linux: await message.channel.send(f'"greeny_invite_detector": active')
            #     else: await message.channel.send(f"Current bot session id is `{out}`")

            # elif message.content.split(" ")[0][1:] == "linux":
            #     if linux: await message.channel.send("Yep, Mreow")
            #     else: await message.channel.send("Ahh, no")

if __name__ == "__main__":
    global allowed_guilds_name
    global out
    global _config_
    global linux


    os.chdir("/home/archibald/Documents/GIT/DiscordBots/greeny_server_manager")
    test = 0

    student = 1221849035808178237
    screen = "greeny_server_manager"

    allowed_guilds_id = [data.notes, data.greeny]
    allowed_guilds_name = {"Kami Notes": {}, "Greeny": {}}

    # os.system('screen -XS "RGM" quit')

    if sys.platform == "linux": linux = 1
    elif sys.platform == "win32": linux = 0
    else: raise Exception(f"OS \"{sys.platform}\" is not supported")

    if linux:
        if not os.path.isfile(f"{os.getcwd()}/restart.sh"):
            with open(f"{os.getcwd()}/restart.sh", "w") as file:
                file.write(f'#!/bin/bash\nsleep 2\nscreen -d -m -S "{screen}" bin/python main.py')
        if not os.path.isfile(f"{os.getcwd()}/start.sh"):
            with open(f"{os.getcwd()}/start.sh", "w") as file:
                file.write(f'#!/bin/bash\nscreen -d -m -S "{screen}" bin/python main.py')
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
            client.run(data.greeny_token)
    except Exception as ex:
        print(ex)
