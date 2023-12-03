import discord 
from config import Token
from discord import Activity, ActivityType, Status, Embed, PermissionOverwrite
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_commands import create_option, create_choice
from discord_slash.model import SlashMessage
import asyncio
from datetime import datetime, timedelta
import pytz

intents = discord.Intents(guilds=True)
client = commands.Bot(command_prefix='!', intents=intents)
slash = SlashCommand(client, sync_commands=True)
client.load_extension('key_cog')
client.load_extension('nuke_cog')

last_pings = {}

@client.event
async def on_ready():
    print('Bot is ready!')
    activity = Activity(name='Slot Helper', type=ActivityType.listening)


@client.check
async def is_admin(ctx):
    return ctx.author.guild_permissions.administrator

async def is_registered(ctx: SlashContext) -> bool:
    with open('users.txt', 'r') as f:
        lines = f.readlines()
    user_ids = [line.split()[0] for line in lines]
    if str(ctx.author.id) not in user_ids:
        await ctx.send('You are not registered to use this command')
        return False
    return True

@slash.slash(name='slot', description='Create a slot channel with specified user access, duration, role, and category',
             options=[
                 create_option(
                     name='user',
                     description='The user to grant access',
                     option_type=6, # USER type
                     required=True
                 ),
                 create_option(
                     name='duration',
                     description='The duration of access (1 minute, 7 days, 30 days, or lifetime)',
                     option_type=3, # STRING type
                     required=True,
                     choices=[
                         create_choice(
                             name='1 minute',
                             value='1 minute'
                         ),
                         create_choice(
                             name='7 days',
                             value='7 days'
                         ),
                         create_choice(
                             name='30 days',
                             value='30 days'
                         ),
                         create_choice(
                             name='Lifetime',
                             value='lifetime'
                         )
                     ]
                 ),
                 create_option(
                     name='role',
                     description='The role to assign for access',
                     option_type=8, # ROLE type
                     required=True
                 ),
                 create_option(
                     name='category',
                     description='The category to create the channel in',
                     option_type=7, # CHANNEL type
                     required=True
                 ),
                 create_option(
                     name='channel_name',
                     description='The name of the channel to create (optional)',
                     option_type=3, # STRING type
                     required=False
                 )
             ])
@commands.check(is_admin)
@commands.check(is_registered)
async def slot(ctx: SlashContext, user: discord.Member, duration: str, role: discord.Role, category: discord.CategoryChannel, channel_name: str = None):
    guild = ctx.guild
    verified_role = discord.utils.get(guild.roles, name='Member')
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(view_channel=True),
        user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        verified_role: discord.PermissionOverwrite(view_channel=True, send_messages=False)
    }
    if channel_name is None:
        channel_name = f'{user.name}-slot'
    try:
        channel = await category.create_text_channel(channel_name, overwrites=overwrites, reason=f'Slot channel created ({duration})')
        if channel is None:
            await ctx.send('An error occurred while creating the channel')
            return
    except Exception as e:
        await ctx.send(f"An error occurred while creating the channel: {e}")
        return
    
    # Create and send the embed
    if duration == 'lifetime':
        duration_str = 'Lifetime'
    else:
        duration_seconds = get_duration_in_seconds(duration)
        duration_str = f'{duration} ({datetime.utcnow() + timedelta(seconds=duration_seconds)})'
    embed = Embed(title="Slot Channel Created", description=f"Duration: {duration_str}", color=0x00ff00)
    embed.add_field(name="User", value=user.mention)
    embed.add_field(name="Channel", value=channel.mention)
    try:
        await channel.send(embed=embed)
        await ctx.send(f"Slot channel {channel.mention} has been created for {user.mention} with duration {duration}")
        second_embed = Embed(title="RULES", description="➥ Use /ping for pinging. \n➥ No refund on private slot.\n➥ You can't sell your slot.\n➥ You can't share your slot.\n➥ Scam=Revoke.\n➥ Refuse to use mm=Revoke.\n➥ Overping=Revoke \n\n<:support:1167095286125052004> **Revoke= Removing Slot without Refund** \n\n<:support:1167095286125052004> **Once you purchase a Slot in KM Service you agree to our Slot Rules**", color=0xF20808)
        await channel.send(embed=second_embed)
    except Exception as e:
        await ctx.send(f"An error occurred while sending the embed: {e}")
        return

    # Assign the specified role to the user
    try:
        await user.add_roles(role)
    except Exception as e:
        await ctx.send(f"An error occurred while assigning the role: {e}")
        return

    if duration != 'lifetime':
        await asyncio.sleep(get_duration_in_seconds(duration))
        try:
            await channel.set_permissions(user, send_messages=False, reason='Slot channel access revoked')
            staff_role = discord.utils.get(guild.roles, name='Owner')
            await channel.send(f'{user.mention} has lost access to the slot channel: {channel.mention}. Please contact {staff_role.mention} if you have any questions.')
            await user.remove_roles(role)
        except Exception as e:
            await ctx.send(f"An error occurred while revoking access: {e}")
            return
    else:
        await channel.send(f'{user.mention} does not have a valid license to access this channel.')

def get_duration_in_seconds(duration: str) -> int:
    if duration == '1 minute':
        return 10
    elif duration == '7 days':
        return 7 * 24 * 60 * 60
    elif duration == '30 days':
        return 30 * 24 * 60 * 60
    else:
        return 0

@slash.slash(name='remove', description='Delete a specified channel',
             options=[
                 create_option(
                     name='channel',
                     description='The channel to delete',
                     option_type=7, # CHANNEL type
                     required=True
                 )
             ])
@commands.check(is_admin)
async def remove(ctx: SlashContext, channel: discord.TextChannel):
    try:
        await channel.delete()
        embed = discord.Embed(title='Channel Deleted', description=f'The channel {channel.mention} has been deleted.', color=discord.Color.red())
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"An error occurred while deleting the channel: {e}")

@slash.slash(name='ping', description='Ping @here or @everyone',
             options=[
                 create_option(
                     name='ping_type',
                     description='The type of ping to send',
                     option_type=3,
                     required=True,
                     choices=[
                         create_choice(name='@here', value='@here'),
                         create_choice(name='@everyone', value='@everyone')
                     ]
                 )
             ])
async def ping(ctx: SlashContext, ping_type: str):
    user_roles = [role.name for role in ctx.author.roles]
    if 'Lifetime' in user_roles:
        max_pings_allowed = max_pings['Lifetime'][ping_type]
        max_here_pings_allowed = max_here_pings['Lifetime']
    elif 'Month' in user_roles:
        max_pings_allowed = max_pings['Month'][ping_type]
        max_here_pings_allowed = max_here_pings['Month']
    elif 'Week' in user_roles:
        max_pings_allowed = max_pings['Week'][ping_type]
        max_here_pings_allowed = max_here_pings['Week']
    else:
        embed = discord.Embed(title='Ping Error', description='You do not have permission to use this command', color=0xff0000)
        await ctx.send(embed=embed)
        return

    user_id = str(ctx.author.id)
    if user_id not in last_pings:
        last_pings[user_id] = {'@here': 0, '@everyone': 0}

    total_pings = max_here_pings_allowed if ping_type == '@here' else max_pings_allowed
    remaining_pings = max(total_pings - last_pings[user_id][ping_type], 0)
    if remaining_pings <= 0:
        embed = discord.Embed(title='Ping Error', description=f'You have exceeded the maximum number of {ping_type} pings', color=0xff0000)
        await ctx.send(embed=embed)
        return
    await ctx.channel.send(f'{ping_type}')
    last_pings[user_id][ping_type] += 1

    now = datetime.now(pytz.timezone('CET'))
    reset_time = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=pytz.timezone('CET')) + timedelta(days=1)
    time_until_reset = reset_time - now
    time_until_reset_seconds = int(time_until_reset.total_seconds())
    time_until_reset_formatted = f'<t:{time_until_reset_seconds}:t>'
    time_until_reset_hours = time_until_reset_seconds // 3600
    time_until_reset_minutes = (time_until_reset_seconds % 3600) // 60
    embed = discord.Embed(title='Remaining Pings', description=f'You have {last_pings[user_id][ping_type]}/{total_pings} {ping_type} pings┃**Use MM**\nTime until reset: `{time_until_reset_hours}h {time_until_reset_minutes}m`', color=0x00ff00)
    await ctx.send(embed=embed)

@slash.slash(name='reset', description='Reset ping limits for a user',
             options=[
                 create_option(
                     name='ping_type',
                     description='The type of ping to reset',
                     option_type=3,
                     required=True,
                     choices=[
                         create_choice(name='@here', value='@here'),
                         create_choice(name='@everyone', value='@everyone')
                     ]
                 ),
                 create_option(
                     name='user',
                     description='The user to reset ping limits for',
                     option_type=6, # USER type
                     required=True
                 )
             ])
@commands.has_permissions(administrator=True)
async def reset(ctx: SlashContext, ping_type: str, user: discord.User):
    global last_pings
    user_id = str(user.id)
    if user_id in last_pings:
        last_pings[user_id][ping_type] = 0
        embed = discord.Embed(title='Ping Limits Reset', description=f'{ping_type} ping limits have been reset for {user.mention}', color=0x00ff00)
        await ctx.send(embed=embed)
    else:
        last_pings[user_id] = {'@here': 0, '@everyone': 0}
        embed = discord.Embed(title='Ping Limits Reset', description=f'{ping_type} ping limits have been reset for {user.mention}', color=0x00ff00)
        await ctx.send(embed=embed)

@slash.slash(name='purge', description='Delete a specified number of messages from the current channel',
             options=[
                 create_option(
                     name='amount',
                     description='The number of messages to delete',
                     option_type=4, # INTEGER type
                     required=True
                 )
             ])
@commands.has_permissions(administrator=True)
async def purge(ctx: SlashContext, amount: int):
    channel = ctx.channel
    messages = await channel.history(limit=amount + 1).flatten()
    try:
        await channel.delete_messages(messages)
        await asyncio.sleep(3) # Wait for 3 seconds before sending the embed
        embed = discord.Embed(title='Purge', description=f'{amount} messages deleted by {ctx.author.mention}', color=0xff0000)
        await ctx.channel.send(embed=embed)
    except Exception as e:
        await ctx.send(f"An error occurred while purging messages: {e}")

async def reset_ping_limits():
    global last_pings
    while True:
        now = datetime.now()
        if now.hour == 0 and now.minute == 0:
            last_pings = {}
        await asyncio.sleep(60) # Check every minute

@slash.slash(name='limits', description='Set the maximum ping limits for each role',
             options=[
                 create_option(
                     name='lifetime_everyone_limit',
                     description='The maximum number of @everyone pings allowed for Lifetime role',
                     option_type=4, # INTEGER type
                     required=True
                 ),
                 create_option(
                     name='lifetime_here_limit',
                     description='The maximum number of @here pings allowed for Lifetime role',
                     option_type=4, # INTEGER type
                     required=True
                 ),
                 create_option(
                     name='month_everyone_limit',
                     description='The maximum number of @everyone pings allowed for Month role',
                     option_type=4, # INTEGER type
                     required=True
                 ),
                 create_option(
                     name='month_here_limit',
                     description='The maximum number of @here pings allowed for Month role',
                     option_type=4, # INTEGER type
                     required=True
                 ),
                 create_option(
                     name='week_everyone_limit',
                     description='The maximum number of @everyone pings allowed for Week role',
                     option_type=4, # INTEGER type
                     required=True
                 ),
                 create_option(
                     name='week_here_limit',
                     description='The maximum number of @here pings allowed for Week role',
                     option_type=4, # INTEGER type
                     required=True
                 )
             ])
@commands.has_permissions(administrator=True)
async def limits(ctx: SlashContext, lifetime_everyone_limit: int, lifetime_here_limit: int, month_everyone_limit: int, month_here_limit: int, week_everyone_limit: int, week_here_limit: int):
    global max_pings, max_here_pings
    max_pings = {'Lifetime': {'@everyone': lifetime_everyone_limit, '@here': lifetime_here_limit}, 'Month': {'@everyone': month_everyone_limit, '@here': month_here_limit}, 'Week': {'@everyone': week_everyone_limit, '@here': week_here_limit}}
    max_here_pings = {'Lifetime': lifetime_here_limit, 'Month': month_here_limit, 'Week': week_here_limit}
    embed = discord.Embed(title='Ping Limits Set', description=f'Maximum ping limits have been set:\nLifetime: @everyone: {lifetime_everyone_limit}, @here: {lifetime_here_limit}\nMonth: @everyone: {month_everyone_limit}, @here: {month_here_limit}\nWeek: @everyone: {week_everyone_limit}, @here: {week_here_limit}', color=0x00ff00)
    await ctx.send(embed=embed)

@slash.slash(name='help', description='List all available commands')
async def help(ctx: SlashContext):
    embed = discord.Embed(title='Available Commands', color=0x9F07F6)
    for command in client.commands:
        embed.add_field(name=f"Slot Creation and Pings", value="**/slot**<a:1071436133084438550:1153969326869721158>`This command will create a channel for you and add role to the desired user.`\n **/ping**<a:1071436133084438550:1153969326869721158>`This command will ping @here or @everyone and check limits depending on the role.` \n **/reset**<a:1071436133084438550:1153969326869721158>`This command will reset ping limits for ceratain user.` \n **/limits**<a:1071436133084438550:1153969326869721158>`This command will set ping limits for Week, Month, LifeTime role.` ", inline=True)
        embed.add_field(name="Licence System", value="**/genkey**<a:1071436133084438550:1153969326869721158>`This command will generate keys for Week, Month, LifeTime role.` \n **/redeem**<a:1071436133084438550:1153969326869721158>`This command will redeem keys for Week, Month, LifeTime role.` ", inline=True)
        embed.add_field(name="Miscellaneous", value="**/remove**<a:1071436133084438550:1153969326869721158>`This command will delete a desired channel.` \n **/purge**<a:1071436133084438550:1153969326869721158>`This command will delete certain ammount of messages.` \n **/help**<a:1071436133084438550:1153969326869721158>`This command will show all available commands.` ", inline=True)
    await ctx.send(embed=embed)

client.loop.create_task(reset_ping_limits())
client.run(Token)
