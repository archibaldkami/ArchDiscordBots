import discord, os, sys, subprocess, time, json, datetime
sys.path.insert(0, '/home/ubuntu/.arch/bots/.data')
import data

test = 0

def check_perm_level(interaction=0, message=0):
    inner_roles = [str(role) for role in _config_['roles']]
    if interaction:
        member = interaction.user
    elif message:
        member = message.author
    else: return 5
    if member.id in data.supreme_administrator_list:
        return 0
    elif member.id in _config_['roles'][inner_roles[0]]:
        return 1
    elif member.id in _config_['roles'][inner_roles[1]]:
        return 2
    elif data.moderator_role in [int(role.id) for role in member.roles]:
        return 3
    elif data.verified_role in [int(role.id) for role in member.roles]:
        return 4
    else: return 5


class MyClient(discord.Client):
# Делает Мэджик
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tree = discord.app_commands.CommandTree(self)

    async def on_ready(self):
        global logger_channel, date, date_now
        await self.tree.sync()
        date_now = datetime.datetime.now()
        date = date_now.strftime("%Y") + "." + date_now.strftime("%m") + "." + date_now.strftime("%d") + "  " + date_now.strftime("%H") + ":" + date_now.strftime("%M") + ":" + date_now.strftime("%S")
        logger_channel = discord.utils.get(discord.utils.get(client.guilds, id=_config_["settings"]["logs"][0]).channels, id=_config_["settings"]["logs"][1])
        print(f'We have logged in as {client.user}')
        os.chdir(path)

if __name__ == "__main__":
    global _config_
    if sys.platform == "linux":
        path = os.getcwd()
    elif sys.platform == "win32":
        path = os.getcwd() + "/py/ArchTests"
    else: raise Exception("OS is not supported")

    try:
        with open(f"{os.getcwd()}/config.json", "r") as file:
            _config_ = json.loads(file.read())
    except:
        with open(f"{os.getcwd()}/config.json", "w") as file:
            file.write(json.dumps({'servers': [], 'repos' : [], 'roles': {"system-administrator": [], "server-administrator": []}}))
        with open(f"{os.getcwd()}/config.json", "r") as file:
            _config_ = json.loads(file.read())
    # try:
    #     with open(f"{os.getcwd()}/git_repos.json", "r") as file:
    #         _git_repos_ = json.loads(file.read())
    # except:
    #     with open(f"{os.getcwd()}/git_repos.json", "w") as file:
    #         file.write(json.dumps({'repos': ['tech', 've-labs']}))
    #     with open(f"{os.getcwd()}/git_repos.json", "r") as file:
    #         _git_repos_ = json.loads(file.read())
    try:
        with open(f"{os.getcwd()}/error_log.log", "r", encoding="utf-8") as file:
            pass
    except:
        with open(f"{os.getcwd()}/error_log.log", "w", encoding="utf-8") as file:
            file.write("# This is bot internal errors log\n\n")

    intents = discord.Intents.all()
    intents.message_content = True
    client = MyClient(intents=intents)

    @client.tree.command(name="git_pull", description="Just git pull")
    async def git_pull(interaction: discord.Interaction, server: str):
        date_now = datetime.datetime.now()
        date = date_now.strftime("%Y") + "." + date_now.strftime("%m") + "." + date_now.strftime("%d") + "  " + date_now.strftime("%H") + ":" + date_now.strftime("%M") + ":" + date_now.strftime("%S")
        if server in _config_['repos']:
            if check_perm_level(interaction) <= 1:
                if f"{server}" in subprocess.check_output("sudo runuser -l hellpizza -c 'cd; ls /home/hellpizza/PFUServer'", shell=True, text=True):
                    os.system(f"sudo runuser -l hellpizza -c 'cd /home/hellpizza/PFUServer/{server}; git pull'")
                    await interaction.response.send_message(f"Operation permitted: `Success`", ephemeral=True)
                else: await interaction.response.send_message(f"Operation denied: `Error > Incorrect server name`", ephemeral=True)
            else: await interaction.response.send_message(f'Operation denied: `Permission denied`', ephemeral=True)
        else: await interaction.response.send_message(f"Operation denied: `Error > Incorrect server name`\nCurrent config:```{_config_['repos']}```", ephemeral=True)
        await logger_channel.send(f"```{date}\nuser.name: '{interaction.user.name}'\nuser.id: '{interaction.user.id}'\nperm: {check_perm_level(interaction)}\ninteraction: 'git_pull'\nrepo: '{server}'```")
    
    @client.tree.command(name="server_stop", description="Stop some server")
    async def server_stop(interaction: discord.Interaction, server: str):
        date_now = datetime.datetime.now()
        date = date_now.strftime("%Y") + "." + date_now.strftime("%m") + "." + date_now.strftime("%d") + "  " + date_now.strftime("%H") + ":" + date_now.strftime("%M") + ":" + date_now.strftime("%S")
        if check_perm_level(interaction) <= 2:
            if server in _config_['servers']:
                if f".{server}" in subprocess.check_output("sudo runuser -l hellpizza -c 'screen -ls'", shell=True, text=True):
                    try:
                        os.system(f"sudo runuser -l hellpizza -c \"screen -S {server} -X stuff 'stop\015'\"")
                        await interaction.response.send_message(f"Operation permitted: `Success`", ephemeral=True)
                    except Exception as ex:
                        with open(f"{os.getcwd()}/error_log.log", "a", encoding="utf-8") as file:
                            file.write(f"{ex}\n")
                        await interaction.response.send_message(f"Operation denied: `Error > {ex}`", ephemeral=True)
                else: await interaction.response.send_message(f"Operation denied: `Error > Incorrect server name`", ephemeral=True)
            else: await interaction.response.send_message(f"Operation denied: `Error > '{server}' not found in config.", ephemeral=True)
        else: await interaction.response.send_message(f'Operation denied: `Permission denied`', ephemeral=True)
        await logger_channel.send(f"```{date}\nuser.name: '{interaction.user.name}'\nuser.id: '{interaction.user.id}'\nperm: {check_perm_level(interaction)}\ninteraction: 'server_stop'\nserver: '{server}'```")

    @client.tree.command(name="server_kill", description="kill some server")
    async def server_kill(interaction: discord.Interaction, server: str):
        date_now = datetime.datetime.now()
        date = date_now.strftime("%Y") + "." + date_now.strftime("%m") + "." + date_now.strftime("%d") + "  " + date_now.strftime("%H") + ":" + date_now.strftime("%M") + ":" + date_now.strftime("%S")
        if check_perm_level(interaction) <= 2:
            if server in _config_['servers']:
                if f".{server}" in subprocess.check_output("sudo runuser -l hellpizza -c 'screen -ls'", shell=True, text=True):
                    try:
                        os.system(f'sudo runuser -l hellpizza -c "screen -XS {server} quit"')
                        await interaction.response.send_message(f"Operation permitted: `Success`", ephemeral=True)
                    except Exception as ex:
                        with open(f"{os.getcwd()}/error_log.log", "a", encoding="utf-8") as file:
                            file.write(f"{ex}\n")
                        await interaction.response.send_message(f"Operation denied: `Error > {ex}`", ephemeral=True)
                else: await interaction.response.send_message(f"Operation denied: `Error > Incorrect server name`", ephemeral=True)
            else: await interaction.response.send_message(f"Operation denied: `Error > '{server}' not found in config.", ephemeral=True)
        else: await interaction.response.send_message(f'Operation denied: `Permission denied`', ephemeral=True)
        await logger_channel.send(f"```{date}\nuser.name: '{interaction.user.name}'\nuser.id: '{interaction.user.id}'\nperm: {check_perm_level(interaction)}\ninteraction: 'server_stop'\nserver: '{server}'```")

    @client.tree.command(name="server_restart", description="Restart some server")
    async def server_restart(interaction: discord.Interaction, server:str):
        date_now = datetime.datetime.now()
        date = date_now.strftime("%Y") + "." + date_now.strftime("%m") + "." + date_now.strftime("%d") + "  " + date_now.strftime("%H") + ":" + date_now.strftime("%M") + ":" + date_now.strftime("%S")
        if check_perm_level(interaction) <= 2:
            if server in _config_['servers']:
                if f".{server}" in subprocess.check_output("sudo runuser -l hellpizza -c 'screen -ls'", shell=True, text=True):
                    try:
                        os.system(f"sudo runuser -l hellpizza -c \"screen -S {server} -X stuff 'stop\015'\"")
                        time.sleep(2)
                        if os.path.isfile(f"/home/hellpizza/PFUServer/{server}/start.sh"):
                            os.system(f"sudo runuser -l hellpizza -c 'cd ~/PFUServer/{server}; bash start.sh'")
                            await interaction.response.send_message(f"Operation permitted: `Success`", ephemeral=True)
                        else: await interaction.response.send_message(f"Operation permitted: Server '{server}' stopped & `Error > file '/home/hellpizza/PFUServer/{server}/start.sh' not found`", ephemeral=True)
                    except Exception as ex:
                        with open(f"{os.getcwd()}/error_log.log", "a", encoding="utf-8") as file:
                            file.write(f"{ex}\n")
                        await interaction.response.send_message(f"Operation denied: `Error > {ex}`", ephemeral=True)
                else: await interaction.response.send_message(f"Operation denied: `Error > Incorrect server name or server is not running`", ephemeral=True)
            else: await interaction.response.send_message(f"Operation denied: `Error > '{server}' not found in config.", ephemeral=True)
        else: await interaction.response.send_message(f'Operation denied: `Permission denied`', ephemeral=True)
        await logger_channel.send(f"```{date}\nuser.name: '{interaction.user.name}'\nuser.id: '{interaction.user.id}'\nperm: {check_perm_level(interaction)}\ninteraction: 'server_restart'\nserver: '{server}'```")

    @client.tree.command(name="server_start", description="Start some server")
    async def server_start(interaction: discord.Interaction, server:str):
        date_now = datetime.datetime.now()
        date = date_now.strftime("%Y") + "." + date_now.strftime("%m") + "." + date_now.strftime("%d") + "  " + date_now.strftime("%H") + ":" + date_now.strftime("%M") + ":" + date_now.strftime("%S")
        if check_perm_level(interaction) <= 2:
            if server in _config_['servers']:
                if f".{server}" not in subprocess.check_output("sudo runuser -l hellpizza -c 'screen -ls'", shell=True, text=True):
                    if os.path.isfile(f"/home/hellpizza/PFUServer/{server}/start.sh"):
                        try:
                            os.system(f"sudo runuser -l hellpizza -c 'cd ~/PFUServer/{server}; bash start.sh'")
                            await interaction.response.send_message(f"Operation permitted: `Success`", ephemeral=True)
                        except Exception as ex:
                            with open(f"{os.getcwd()}/error_log.log", "a", encoding="utf-8") as file:
                                file.write(f"{ex}\n")
                            await interaction.response.send_message(f"Operation denied: `Error > {ex}`", ephemeral=True)
                    else: await interaction.response.send_message(f"Operation denied: `Error > file '/home/hellpizza/PFUServer/{server}/start.sh' not found`", ephemeral=True)
                else: await interaction.response.send_message(f"Operation denied: `Error > Incorrect server name or server already running`", ephemeral=True)
            else: await interaction.response.send_message(f"Operation denied: `Error > '{server}' not found in config.", ephemeral=True)
        else: await interaction.response.send_message(f'Operation denied: `Permission denied`', ephemeral=True)
        await logger_channel.send(f"```{date}\nuser.name: '{interaction.user.name}'\nuser.id: '{interaction.user.id}'\nperm: {check_perm_level(interaction)}\ninteraction: 'server_start'\nserver: '{server}'```")
        

    @client.tree.command(name="server_command", description="Send command to some server")
    async def server_command(interaction: discord.Interaction, server:str, command: str):
        date_now = datetime.datetime.now()
        date = date_now.strftime("%Y") + "." + date_now.strftime("%m") + "." + date_now.strftime("%d") + "  " + date_now.strftime("%H") + ":" + date_now.strftime("%M") + ":" + date_now.strftime("%S")
        if check_perm_level(interaction) <= 3:
            if server in _config_['servers']:
                if f".{server}" in subprocess.check_output("sudo runuser -l hellpizza -c 'screen -ls'", shell=True, text=True):
                    try:
                        if command.split(' ')[0] in _config_["not_allowed_commands"] and check_perm_level(interaction) > 2:
                            await interaction.response.send_message(f"Operation denied: `Error > Permission denied.`\n> You are not allowed to use this command!", ephemeral=True)
                        else:
                            os.system(f"sudo runuser -l hellpizza -c \"screen -S {server} -X stuff '{command}\015'\"")
                            await interaction.response.send_message(f"Operation permitted: `Success`", ephemeral=True)
                    except Exception as ex:
                        with open(f"{os.getcwd()}/error_log.log", "a", encoding="utf-8") as file:
                            file.write(f"{ex}\n")
                        await interaction.response.send_message(f"Operation denied: `Error > {ex}`", ephemeral=True)
                else: await interaction.response.send_message(f"Operation denied: `Error > Incorrect server name or server is not running`", ephemeral=True)
            else: await interaction.response.send_message(f"Operation denied: `Error > '{server}' not found in config.", ephemeral=True)
        else: await interaction.response.send_message(f'Operation denied: `Permission denied`', ephemeral=True)
        await logger_channel.send(f"```{date}\nuser.name: '{interaction.user.name}'\nuser.id: '{interaction.user.id}'\nperm: {check_perm_level(interaction)}\ninteraction: 'server_command'\ncommand: '{command}'```")

    @client.tree.command(name="servers_status", description="See server online statistics")
    async def server_status(interaction: discord.Interaction):
        date_now = datetime.datetime.now()
        date = date_now.strftime("%Y") + "." + date_now.strftime("%m") + "." + date_now.strftime("%d") + "  " + date_now.strftime("%H") + ":" + date_now.strftime("%M") + ":" + date_now.strftime("%S")
        if check_perm_level(interaction) <= 4:
            if _config_['servers']:
                try:
                    temp_str = ''
                    for server in _config_['servers']:
                        if f".{server}" in subprocess.check_output("sudo runuser -l hellpizza -c 'screen -ls'", shell=True, text=True):
                            temp_str += f"{server}: online\n"
                        else: temp_str += f"{server}: offline\n"
                    await interaction.response.send_message(f"Operation permitted: `Success`\n```{temp_str}```", ephemeral=True)
                except Exception as ex:
                    with open(f"{os.getcwd()}/error_log.log", "a", encoding="utf-8") as file:
                        file.write(f"{ex}\n")
                    await interaction.response.send_message(f"Operation denied: `Error > {ex}`", ephemeral=True)
            else: await interaction.response.send_message(f"Operation denied: `Error > config is empty`", ephemeral=True)
        else: await interaction.response.send_message(f'Operation denied: `Permission denied`', ephemeral=True)
        await logger_channel.send(f"```{date}\nuser.name: '{interaction.user.name}'\nuser.id: '{interaction.user.id}'\nperm: {check_perm_level(interaction)}\ninteraction: 'servers_status'```")

    @client.tree.command(name="add_server_to_config", description="Add server to authentificated")
    async def add_server_to_config(interaction: discord.Interaction, server:str):
        date_now = datetime.datetime.now()
        date = date_now.strftime("%Y") + "." + date_now.strftime("%m") + "." + date_now.strftime("%d") + "  " + date_now.strftime("%H") + ":" + date_now.strftime("%M") + ":" + date_now.strftime("%S")
        if check_perm_level(interaction) <= 1:
            if server not in _config_['servers']:
                try:
                    _config_['servers'].append(server)
                    with open("config.json", "w") as file:
                        file.write(json.dumps(_config_))
                    await interaction.response.send_message(f"Operation permitted: `Success`\nCurrent config:\n```{_config_['servers']}```", ephemeral=True)
                except Exception as ex:
                    with open(f"{os.getcwd()}/error_log.log", "a", encoding="utf-8") as file:
                        file.write(f"{ex}\n")
                    await interaction.response.send_message(f"Operation denied: `Error > {ex}`", ephemeral=True)
            else: await interaction.response.send_message(f"Operation denied: `Error > server '{server}' already exists in config`", ephemeral=True)
        else: await interaction.response.send_message(f'Operation denied: `Permission denied`', ephemeral=True)
        await logger_channel.send(f"```{date}\nuser.name: '{interaction.user.name}'\nuser.id: '{interaction.user.id}'\nperm: {check_perm_level(interaction)}\ninteraction: 'add_server_to_config'\nserver: '{server}'```")

    @client.tree.command(name="remove_server_from_config", description="Removes server from authentificated")
    async def remove_server_from_config(interaction: discord.Interaction, server:str):
        date_now = datetime.datetime.now()
        date = date_now.strftime("%Y") + "." + date_now.strftime("%m") + "." + date_now.strftime("%d") + "  " + date_now.strftime("%H") + ":" + date_now.strftime("%M") + ":" + date_now.strftime("%S")
        if check_perm_level(interaction) <= 1:
            if server in _config_['servers']:
                try:
                    _config_['servers'].remove(server)
                    with open("config.json", "w") as file:
                        file.write(json.dumps(_config_))
                    await interaction.response.send_message(f"Operation permitted: `Success`\nCurrent config:\n```{_config_['servers']}```", ephemeral=True)
                except Exception as ex:
                    with open(f"{os.getcwd()}/error_log.log", "a", encoding="utf-8") as file:
                        file.write(f"{ex}\n")
                    await interaction.response.send_message(f"Operation denied: `Error > {ex}`", ephemeral=True)
            else: await interaction.response.send_message(f"Operation denied: `Error > server '{server}' does not exist in config`", ephemeral=True)
        else: await interaction.response.send_message(f'Operation denied: `Permission denied`', ephemeral=True)
        await logger_channel.send(f"```{date}\nuser.name: '{interaction.user.name}'\nuser.id: '{interaction.user.id}'\nperm: {check_perm_level(interaction)}\ninteraction: 'remove_server_from_config'\nserver: '{server}'```")

    @client.tree.command(name="add_role", description="Add inner role to some member")
    async def add_role_to_config(interaction: discord.Interaction, role:str, member:str):
        date_now = datetime.datetime.now()
        date = date_now.strftime("%Y") + "." + date_now.strftime("%m") + "." + date_now.strftime("%d") + "  " + date_now.strftime("%H") + ":" + date_now.strftime("%M") + ":" + date_now.strftime("%S")
        if check_perm_level(interaction) <= 1:
            if role in _config_['roles']:
                if int(member[2:-1]) not in _config_['roles'][role]:
                    try:
                        _config_['roles'][role].append(int(member[2:-1]))
                        with open("config.json", "w") as file:
                            file.write(json.dumps(_config_))
                        await interaction.response.send_message(f"Operation permitted: `Success`", ephemeral=True)
                    except Exception as ex:
                        with open(f"{os.getcwd()}/error_log.log", "a", encoding="utf-8") as file:
                            file.write(f"{ex}\n")
                        await interaction.response.send_message(f"Operation denied: `Error > {ex}`", ephemeral=True)
                else: await interaction.response.send_message(f"Operation denied: `Error > member '{member}' already exists in config`", ephemeral=True)
            else: await interaction.response.send_message(f"Operation denied: `Error > role '{role}' does not exist in config. Did you mean one of '{' or '.join([mreow for mreow in _config_['roles']])}'?`", ephemeral=True)
        else: await interaction.response.send_message(f'Operation denied: `Permission denied`', ephemeral=True)
        await logger_channel.send(f"```{date}\nuser.name: '{interaction.user.name}'\nuser.id: '{interaction.user.id}'\nperm: {check_perm_level(interaction)}\ninteraction: 'add_role'\nrole: '{role}'\nmember: '{member}'```")

    @client.tree.command(name="remove_role", description="Remove inner role from some member")
    async def remove_role_from_config(interaction: discord.Interaction, role:str, member:str):
        date_now = datetime.datetime.now()
        date = date_now.strftime("%Y") + "." + date_now.strftime("%m") + "." + date_now.strftime("%d") + "  " + date_now.strftime("%H") + ":" + date_now.strftime("%M") + ":" + date_now.strftime("%S")
        if check_perm_level(interaction) <= 1:
            if role in _config_['roles']:
                if int(member[2:-1]) in _config_['roles'][role]:
                    if check_perm_level(interaction) > 0 and interaction.user.id == int(member[2:-1]):
                        await interaction.response.send_message(f"Operation denied: `Idiot Protection Error > you cannot remove yourself from config`", ephemeral=True)
                    else:
                        try:
                            _config_['roles'][role].remove(int(member[2:-1]))
                            with open("config.json", "w") as file:
                                file.write(json.dumps(_config_))
                            await interaction.response.send_message(f"Operation permitted: `Success`", ephemeral=True)
                        except Exception as ex:
                            with open(f"{os.getcwd()}/error_log.log", "a", encoding="utf-8") as file:
                                file.write(f"{ex}\n")
                            await interaction.response.send_message(f"Operation denied: `Error > {ex}`", ephemeral=True)
                else: await interaction.response.send_message(f"Operation denied: `Error > member '{member}' does not exists in config`", ephemeral=True)
            else: await interaction.response.send_message(f"Operation denied: `Error > role '{role}' does not exist in config. Did you mean one of '{' or '.join([mreow for mreow in _config_['roles']])}'?`", ephemeral=True)
        else: await interaction.response.send_message(f'Operation denied: `Permission denied`', ephemeral=True)
        await logger_channel.send(f"```{date}\nuser.name: '{interaction.user.name}'\nuser.id: '{interaction.user.id}'\nperm: {check_perm_level(interaction)}\ninteraction: 'remove_role'\nrole: '{role}'\nmember: '{member}'```")

    @client.tree.command(name="roles_list", description="See list roles")
    async def see_roles_list(interaction: discord.Interaction):
        date_now = datetime.datetime.now()
        date = date_now.strftime("%Y") + "." + date_now.strftime("%m") + "." + date_now.strftime("%d") + "  " + date_now.strftime("%H") + ":" + date_now.strftime("%M") + ":" + date_now.strftime("%S")
        if check_perm_level(interaction) <= 2:
            try:
                temp_str = ''.join(map(str, [(f'```{role}:\n' + str("\n".join(map(str, [discord.utils.get(interaction.guild.members, id=int(temp_id)).name for temp_id in _config_['roles'][role]]))) + '```') for role in _config_['roles']]))
                await interaction.response.send_message(temp_str, ephemeral=True)
            except Exception as ex:
                with open(f"{os.getcwd()}/error_log.log", "a", encoding="utf-8") as file:
                    file.write(f"{ex}\n")
                await interaction.response.send_message(f"Operation denied: `Error > {ex}`", ephemeral=True)
        else: await interaction.response.send_message(f'Operation denied: `Permission denied`', ephemeral=True)
        await logger_channel.send(f"```{date}\nuser.name: '{interaction.user.name}'\nuser.id: '{interaction.user.id}'\nperm: {check_perm_level(interaction)}\ninteraction: 'roles_list'```")

    @client.tree.command(name="add_not_allowed_command", description="Add not allowed 'server_command' for moderators")
    async def add_not_allowed_command(interaction: discord.Interaction, command:str):
        date_now = datetime.datetime.now()
        date = date_now.strftime("%Y") + "." + date_now.strftime("%m") + "." + date_now.strftime("%d") + "  " + date_now.strftime("%H") + ":" + date_now.strftime("%M") + ":" + date_now.strftime("%S")
        if check_perm_level(interaction) <= 2:
            if command not in _config_["not_allowed_commands"]:
                try:
                    _config_["not_allowed_commands"].append(command)
                    with open("config.json", "w") as file:
                        file.write(json.dumps(_config_))
                    await interaction.response.send_message('Operation permitted: `Success`\nCurrent config:\n```' + str(_config_["not_allowed_commands"]) + '```', ephemeral=True)
                except Exception as ex:
                    with open(f"{os.getcwd()}/error_log.log", "a", encoding="utf-8") as file:
                        file.write(f"{ex}\n")
                    await interaction.response.send_message(f"Operation denied: `Error > {ex}`", ephemeral=True)
            else: await interaction.response.send_message(f"Operation denied: `Error > command '{command}' already exists in config`", ephemeral=True)
        else: await interaction.response.send_message(f'Operation denied: `Permission denied`', ephemeral=True)
        await logger_channel.send(f"```{date}\nuser.name: '{interaction.user.name}'\nuser.id: '{interaction.user.id}'\nperm: {check_perm_level(interaction)}\ninteraction: 'add_not_allowed_command'\ncommand: '{command}'```")

    @client.tree.command(name="remove_not_allowed_command", description="Remove not allowed 'server_command' for moderators")
    async def remove_not_allowed_command(interaction: discord.Interaction, command:str):
        date_now = datetime.datetime.now()
        date = date_now.strftime("%Y") + "." + date_now.strftime("%m") + "." + date_now.strftime("%d") + "  " + date_now.strftime("%H") + ":" + date_now.strftime("%M") + ":" + date_now.strftime("%S")
        if check_perm_level(interaction) <= 2:
            if command in _config_["not_allowed_commands"]:
                try:
                    _config_["not_allowed_commands"].remove(command)
                    with open("config.json", "w") as file:
                        file.write(json.dumps(_config_))
                    await interaction.response.send_message('Operation permitted: `Success`\nCurrent config:\n```' + str(_config_["not_allowed_commands"]) + '```', ephemeral=True)
                except Exception as ex:
                    with open(f"{os.getcwd()}/error_log.log", "a", encoding="utf-8") as file:
                        file.write(f"{ex}\n")
                    await interaction.response.send_message(f"Operation denied: `Error > {ex}`", ephemeral=True)
            else: await interaction.response.send_message(f"Operation denied: `Error > command '{command}' does not exist in config`", ephemeral=True)
        else: await interaction.response.send_message(f'Operation denied: `Permission denied`', ephemeral=True)
        await logger_channel.send(f"```{date}\nuser.name: '{interaction.user.name}'\nuser.id: '{interaction.user.id}'\nperm: {check_perm_level(interaction)}\ninteraction: 'remove_not_allowed_command'\ncommand: '{command}'```")

    @client.tree.command(name="not_allowed_commands_list", description="See list not allowed commands")
    async def see_not_allowed_commands_list(interaction: discord.Interaction):
        date_now = datetime.datetime.now()
        date = date_now.strftime("%Y") + "." + date_now.strftime("%m") + "." + date_now.strftime("%d") + "  " + date_now.strftime("%H") + ":" + date_now.strftime("%M") + ":" + date_now.strftime("%S")
        if check_perm_level(interaction) <= 3:
            try:
                await interaction.response.send_message(''.join(map(str, ('```Current config:\n' + str("\n".join(map(str, _config_["not_allowed_commands"]))) + '```'))), ephemeral=True)
            except Exception as ex:
                with open(f"{os.getcwd()}/error_log.log", "a", encoding="utf-8") as file:
                    file.write(f"{ex}\n")
                await interaction.response.send_message(f"Operation denied: `Error > {ex}`", ephemeral=True)
        else: await interaction.response.send_message(f'Operation denied: `Permission denied`', ephemeral=True)
        await logger_channel.send(f"```{date}\nuser.name: '{interaction.user.name}'\nuser.id: '{interaction.user.id}'\nperm: {check_perm_level(interaction)}\ninteraction: 'not_allowed_commands_list'```")

    try:
        if test:
            client.run(data.archtests_token)
        else: 
            client.run(data.viscord_token)
    except Exception as ex:
        print(ex)
        with open(f"{os.getcwd()}/error_log.log", "a", encoding="utf-8") as file:
            file.write(f"{ex}\n")