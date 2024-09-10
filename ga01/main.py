import sys, discord, os, json
sys.path.insert(0, '../../.data')
import data

if __name__ == "__main__":

    class MyClient(discord.Client):
        async def on_ready(self):
            print(f'We have logged in as {client.user}')

        async def on_message(self, message):
            if message.content.strip().startswith("$"):
                if message.content.split("$")[1].startswith("cchannel"):
                    for_config, for_members = {}, {}
                    for group_name in message.content.split("\n")[1:]:
                        if True not in [group_name in role.name for role in message.guild.roles]:
                            base_role = await message.guild.create_role(name=f"{group_name}")
                            subsubcur_role = await message.guild.create_role(name=f"{group_name} Зам старости")
                            subcur_role = await message.guild.create_role(name=f"{group_name} Староста")
                            curator_role = await message.guild.create_role(name=f"Куратор {group_name}")

                            teacher = discord.utils.get(message.guild.roles, id=1273993607178879016)
                            rules = discord.utils.get(message.guild.channels, id=1253435782593642728)

                            category_overwrites = {
                                message.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                                message.guild.me: discord.PermissionOverwrite(view_channel=True),
                                base_role: discord.PermissionOverwrite(view_channel=True, connect=True),
                                subsubcur_role: discord.PermissionOverwrite(view_channel=True, connect=True, manage_messages=True, priority_speaker=True),
                                subcur_role: discord.PermissionOverwrite(view_channel=True, connect=True, manage_messages=True, priority_speaker=True, manage_channels=True, deafen_members=True, move_members=True, mute_members=True),
                                curator_role: discord.PermissionOverwrite(view_channel=True, connect=True, manage_messages=True, priority_speaker=True, manage_channels=True, deafen_members=True, move_members=True, mute_members=True, manage_threads=True)
                            }
                            no_cur_overwrites = {
                                message.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                                message.guild.me: discord.PermissionOverwrite(view_channel=True),
                                base_role: discord.PermissionOverwrite(view_channel=True, connect=True),
                                subsubcur_role: discord.PermissionOverwrite(view_channel=True, connect=True, manage_messages=True, priority_speaker=True),
                                subcur_role: discord.PermissionOverwrite(view_channel=True, connect=True, manage_messages=True, priority_speaker=True, manage_channels=True, deafen_members=True, move_members=True, mute_members=True),
                                curator_role: discord.PermissionOverwrite(view_channel=True, connect=True, manage_messages=True, priority_speaker=True, manage_channels=True, deafen_members=True, move_members=True, mute_members=True, manage_threads=True)
                            }
                            teacher_overwrites = {
                                message.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                                message.guild.me: discord.PermissionOverwrite(view_channel=True),
                                base_role: discord.PermissionOverwrite(view_channel=True, connect=True),
                                subsubcur_role: discord.PermissionOverwrite(view_channel=True, connect=True, manage_messages=True, priority_speaker=True),
                                subcur_role: discord.PermissionOverwrite(view_channel=True, connect=True, manage_messages=True, priority_speaker=True, manage_channels=True, deafen_members=True, move_members=True, mute_members=True),
                                curator_role: discord.PermissionOverwrite(view_channel=False, connect=True, manage_messages=True, priority_speaker=True, manage_channels=True, deafen_members=True, move_members=True, mute_members=True, manage_threads=True),
                                teacher: discord.PermissionOverwrite(view_channel=True, connect=True, manage_messages=True, priority_speaker=True, manage_channels=True, deafen_members=True, move_members=True, mute_members=True)
                            
                            }
                            
                            categoty = await message.guild.create_category(group_name, overwrites=category_overwrites)
                            # teacher = discord.utils.get(message.guild.roles, id=1221843659868213399)
                            # rules = discord.utils.get(message.guild.channels, id=1147849067565686934)

                            await message.guild.create_text_channel('загальний', category=categoty, overwrites=category_overwrites)
                            await message.guild.create_text_channel('без-куратора', category=categoty, overwrites=no_cur_overwrites)
                            await message.guild.create_text_channel(f'{group_name}-викладачі', category=categoty, overwrites=teacher_overwrites)
                            await message.guild.create_voice_channel('Голосовий канал', category=categoty, overwrites=category_overwrites)
                            invite = await rules.create_invite(max_uses=50)
                            for_config[str(invite.code)] = [base_role.id, 1221849035808178237]
                            for_members[str(group_name)] = str(invite.url)
                        else: await message.channel.send("Error > channel already exists.")
                    await message.channel.send(f"```{json.dumps(for_config, indent=4, sort_keys=True)}```")
                    res = ""
                    for i in for_members:
                        res += f"{i}: {for_members[i]}\n"
                    await message.channel.send(res)

    intents = discord.Intents.all()
    intents.message_content = True
    client = MyClient(intents=intents)

    try:
        # client.run(data.greeny_token)
        client.run(data.a2e_token)
    except Exception as ex:
        print(ex)
        with open(f"{os.getcwd()}/error_log.log", "a", encoding="utf-8") as file:
            file.write(f"{ex}\n")