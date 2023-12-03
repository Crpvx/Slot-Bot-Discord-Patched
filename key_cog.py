import discord
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option, create_choice
import random
import asyncio

# Define the types of keys
KEY_TYPES = ['Week', 'Month', 'Lifetime']

class KeyCog(commands.Cog):
    AUTHORIZED_USER_ID = 805801275265908756  # Replace with the authorized user ID

    def __init__(self, bot):
        self.bot = bot

        # Initialize the list of keys
        self.keys = []

        # Load the keys from the keys.txt file
        with open('keys.txt', 'r') as f:
            self.keys = f.read().splitlines()

    # Define the /genkey command
    @cog_ext.cog_slash(name='genkey', description='Generate a new key',
                options=[
                    create_option(
                        name='key_type',
                        description='The type of key to generate',
                        option_type=3,
                        required=True,
                        choices=[
                            create_choice(name='Week', value='Week'),
                            create_choice(name='Month', value='Month'),
                            create_choice(name='Lifetime', value='Lifetime')
                        ]
                    ),
                    create_option(
                        name='count',
                        description='The number of keys to generate',
                        option_type=4,
                        required=True
                    )
                ])
    @commands.has_permissions(administrator=True)
    async def genkey(self, ctx: SlashContext, key_type: str, count: int):
        if ctx.author.id != self.AUTHORIZED_USER_ID:
            await ctx.send('You are not authorized to use this command')
            return
        keys = [f'{key_type}-{random.randint(100000, 999999)}' for _ in range(count)]
        self.keys.extend(keys)
        with open('keys.txt', 'a') as f:
            f.write('\n'.join(keys) + '\n')
        embed = discord.Embed(title='New Keys', description=f'{count} new {key_type} keys have been generated: `{", ".join(keys)}`', color=0x00ff00)
        await ctx.send(embed=embed)

    # Define the /redeem command
    @cog_ext.cog_slash(name='redeem', description='Redeem a key',
                    options=[
                        create_option(
                            name='key',
                            description='The key to redeem',
                            option_type=3,
                            required=True
                        )
                    ])
    async def redeem(self, ctx: SlashContext, key: str):
        if key not in self.keys:
            embed = discord.Embed(title='Invalid Key', description='The key you entered is invalid', color=0xff0000)
            await ctx.send(embed=embed)
            return
        key_type = key.split('-')[0]
        if key_type == 'Week':
            expiry_time = 604800  # 1 week in seconds
        elif key_type == 'Month':
            expiry_time = 2592000  # 1 month in seconds
        else:
            expiry_time = -1  # Lifetime key
        self.keys.remove(key)
        with open('keys.txt', 'w') as f:
            f.write('\n'.join(self.keys))
        if expiry_time != 0:
            with open('users.txt', 'a') as f:
                if expiry_time == -1:
                    f.write(f'{ctx.author.id} redeemed lifetime key {key}\n')
                else:
                    f.write(f'{ctx.author.id} redeemed key {key} (expires in {expiry_time} seconds)\n')
            if expiry_time > 0:
                expiry_message = f'Your subscription for {key_type} key {key} has expired.'
                await asyncio.sleep(expiry_time)
                with open('users.txt', 'r') as f:
                    lines = f.readlines()
                with open('users.txt', 'w') as f:
                    for line in lines:
                        if f'{ctx.author.id} redeemed key {key}' not in line:
                            f.write(line)
                    user = await self.bot.fetch_user(ctx.author.id)
                    await user.send(expiry_message)
                    embed = discord.Embed(title='Key Redeemed', description='Your key has been redeemed', color=0x00ff00)
                    await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title='Key Redeemed', description='Your lifetime key has been redeemed', color=0x00ff00)
            await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(KeyCog(bot))
