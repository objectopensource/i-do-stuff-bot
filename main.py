import discord
import os
import dotenv
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext
dotenv.load_dotenv()

client = commands.Bot(
    command_prefix=commands.when_mentioned_or("_"), case_insensitive=True)
slash = SlashCommand(client, sync_commands=True,
                     delete_from_unused_guilds=True)


@client.event
async def on_ready():
    print("Main script is running")


@client.event
async def on_command_error(ctx, error):  # Error handlers
    if isinstance(error, commands.BotMissingPermissions):
        await ctx.send("Command failed - I don't have enough permissions to run this command!")
    elif isinstance(error, commands.MissingPermissions):

        await ctx.send("You don't have enough permissions to use this command.")
    elif isinstance(error, commands.NotOwner):
        await ctx.send("Only the owner of the bot can use this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("You've missed one or more required arguments. Check the command's help for what arguments you should provide.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Bad Argument error - make sure you've typed your arguments correctly.")
    elif isinstance(error, commands.ChannelNotFound):
        await ctx.send("I don't think that channel exists!")
    else:
        print(error)


@client.command(help="Tests the bot's latency and displays it in milliseconds", brief="Tests the bot's latency")
async def ping(ctx):
    await ctx.send(f"Pong! The bot's latency is `{round(client.latency * 1000)}ms`")


@client.command(help="View the bot's information", brief="View information", aliases=["information"])
async def info(ctx):
    info_embed = discord.Embed(
        title="`I Do Stuff` information", color=0xFF6600)
    info_embed.add_field(
        name="Source code",
        value="View the bot's source code on [GitHub](https://github.com/opensourze/i-do-stuff)",
        inline=False)
    info_embed.add_field(
        name="Creator",
        value="[OpenSourze#0414](https://github.com/opensourze)",
        inline=False
    )
    info_embed.add_field(
        name="Version",
        value="`0.5` :_)",
        inline=False
    )
    info_embed.add_field(
        name="Invite link",
        value="[dsc.gg/i-do-stuff](https://dsc.gg/i-do-stuff)",
        inline=False
    )
    info_embed.set_thumbnail(
        url="https://cdn.discordapp.com/avatars/848936530617434142/548866771e35e12361e4822b3807e717.png?size=512")
    await ctx.send(embed=info_embed)


@client.command(hidden=True)
@commands.is_owner()
async def load(ctx, extension):
    client.load_extension(f"cogs.{extension}")
    await ctx.send(f"Loaded {extension}")


@client.command(hidden=True)
@commands.is_owner()
async def unload(ctx, extension):
    client.unload_extension(f"cogs.{extension}")
    await ctx.send(f"Unloaded {extension}")


# Slash commands


@slash.slash(name="ping", description="Test the bot's latency")
async def ping_slash(ctx: SlashContext):
    await ping(ctx)


@slash.slash(name="info", description="View the bot's information", guild_ids=[841226150789120000])
async def info_slash(ctx: SlashContext):
    await info(ctx)


# Loop through all files in cogs directory and load them
for file in os.listdir("./cogs"):
    if file.endswith(".py"):
        client.load_extension(f"cogs.{file[:-3]}")

client.run(os.environ["TOKEN"])
