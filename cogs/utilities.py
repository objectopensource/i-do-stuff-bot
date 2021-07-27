import asyncio
import base64
import contextlib
import io
import os
import textwrap
from traceback import format_exception

import discord
import requests
from discord.ext import buttons, commands
from discord_slash import SlashContext, cog_ext
from discord_slash.utils.manage_commands import create_option
from temperature_converter_py import fahrenheit_to_celsius


class Utility(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.__class__.__name__} cog is ready")

    # Search repositories
    @commands.command(
        help="Search for GitHub repositories",
        aliases=["searchrepo", "githubsearch"],
    )
    async def github(self, ctx, *, query):
        json = requests.get(
            f"https://api.github.com/search/repositories?q={query}"
        ).json()

        if json["total_count"] == 0:
            await ctx.send("No matching repositories found")
        else:
            await ctx.send(
                f"First result for '{query}':\n{json['items'][0]['html_url']}"
            )

    @cog_ext.cog_slash(
        name="search_github", description="Search for repositories on GitHub"
    )
    async def github_slash(self, ctx: SlashContext, *, query):
        await self.githubsearch(ctx, query=query)

    # PyPI command
    @commands.command(help="Get info for a PyPI module")
    async def pypi(self, ctx, *, package):
        request = requests.get(f"https://pypi.org/pypi/{package}/json")
        if request.status_code == 404:
            await ctx.send(":x: That module doesn't exist!")
            return

        json = request.json()

        embed = discord.Embed(
            title=json["info"]["name"],
            color=0xFF6600,
            url=json["info"]["package_url"],
        )

        if json["info"]["summary"] != "UNKNOWN":
            embed.description = json["info"]["summary"]

        if len(json["info"]["description"]) <= 1024:
            embed.add_field(
                name="Description", value=json["info"]["description"], inline=False
            )
        else:
            # Slice description to 1021 characters and add ellipsis
            embed.add_field(
                name="Description",
                value=json["info"]["description"][:1021] + "...",
                inline=False,
            )

        if json["info"]["home_page"]:
            embed.add_field(name="Homepage", value=json["info"]["home_page"])

        embed.add_field(name="Version", value=json["info"]["version"])
        embed.add_field(name="Author", value=json["info"]["author"])
        embed.add_field(name="License", value=json["info"]["license"])

        await ctx.send(embed=embed)

    @cog_ext.cog_slash(name="pypi", description="Get info for a PyPI module")
    async def pypi_slash(self, ctx: SlashContext, *, package):
        await self.pypi(ctx, package=package)

    # NPM command
    @commands.command(help="Get info for an NPM module")
    async def npm(self, ctx, *, package):
        json = requests.get(f"https://registry.npmjs.org/{package}").json()

        try:
            if json["error"]:
                await ctx.send(":x: " + json["error"])
        except KeyError:
            embed = discord.Embed(
                title=json["name"],
                description=json["description"],
                color=0xD50000,
                url="https://www.npmjs.com/package/" + package,
            )

            if json["homepage"]:
                embed.add_field(name="Homepage", value=json["homepage"], inline=False)

            embed.add_field(name="Author", value=json["author"]["name"])
            embed.add_field(
                name="GitHub repository",
                value=json["repository"]["url"][4:-4],
                inline=False,
            )
            embed.add_field(
                name="Repository maintainers",
                value=", ".join(
                    maintainer["name"] for maintainer in json["maintainers"]
                ),
                inline=False,
            )
            embed.add_field(name="License", value=json["license"], inline=False)

            await ctx.send(embed=embed)

    @cog_ext.cog_slash(name="npm", description="Get info for an NPM module")
    async def npm_slash(self, ctx: SlashContext, *, package):
        await self.npm(ctx, package=package)

    # Base64
    @commands.group(
        invoke_without_command=True, help="Encode/decode base64", aliases=["b64"]
    )
    async def base64(self, ctx):
        embed = discord.Embed(
            title="Base64 commands",
            description="Run `1 base64 e {text}` to convert the text into base64.\n"
            + "Run `1 base64 d {base64}` to decode base64 code.\n",
            color=0xFF6600,
        ).set_footer(text="Don't include the brackets while running commands!")

        await ctx.send(embed=embed)

    @base64.command(help="Encode text into base64", aliases=["e"])
    async def encode(self, ctx, *, text):
        await ctx.send(base64.b64encode(text.encode()).decode())

    @base64.command(help="Decode base64 into text", aliases=["d"])
    async def decode(self, ctx, *, code):
        await ctx.send(base64.b64decode(code.encode()).decode())

    @cog_ext.cog_subcommand(
        base="base64", name="encode", description="Encode text into base64"
    )
    async def encode_slash(self, ctx: SlashContext, *, text):
        await self.encode(ctx, text=text)

    @cog_ext.cog_subcommand(
        base="base64", name="decode", description="Decode base64 into text"
    )
    async def decode_slash(self, ctx: SlashContext, *, code):
        await self.decode(ctx, code=code)

    # Weather command
    @commands.command(
        help="Get weather info for a city. The city name is required. Optionally add state and country codes separated by commas. Example: `1 weather washington,wa,us`, or `1 weather washington`",
        brief="Get weather info for a city",
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def weather(self, ctx, *, query):
        json = requests.get(
            f"https://api.openweathermap.org/data/2.5/weather?q={query}&appid={os.environ['OWM_KEY']}&units=imperial"
        ).json()

        # If code is 404 (not found), send an error message
        if int(json["cod"]) == 404:
            await ctx.send(
                ":x: City not found. Provide only the city name, **or:**\n"
                + "The city name with the state code and country code separated by commas.\n"
                + "E.g.: `washington,wa,us` or just `washington`."
            )
        else:
            weather_description = json["weather"][0]["description"].capitalize()
            icon_url = (  # icons URL + icon code + @2x.png (for higher resolution icon)
                "https://openweathermap.org/img/wn/"
                + json["weather"][0]["icon"]
                + "@2x.png"
            )
            celsius_temp = fahrenheit_to_celsius(json["main"]["temp"])

            weather_embed = discord.Embed(
                title=f"Weather in {json['name']}",  # "Weather in <city name>"
                description=weather_description,
                color=0xFF6600,
            )
            weather_embed.set_thumbnail(url=icon_url)

            weather_embed.add_field(
                name="Temperature",
                # "<temp. in fahrenheit>° F / <temp. in celsius>° C"
                value=f"{json['main']['temp']}° F / {round(celsius_temp, 2)}° C",
            )
            weather_embed.add_field(
                name="Cloudiness", value=f"{json['clouds']['all']}%"
            )
            weather_embed.add_field(
                name="Humidity", value=f"{json['main']['humidity']}%"
            )
            weather_embed.add_field(
                name="Wind speed", value=f"{json['wind']['speed']} m/s"
            )
            weather_embed.add_field(
                name="Wind direction", value=f"{json['wind']['deg']}°"
            )

            await ctx.send(embed=weather_embed)

    @cog_ext.cog_slash(
        name="weather",
        description="Get weather info for a city",
        options=[
            create_option(
                name="city",
                description="City name. Optionally add state code and country code separated by commas",
                required=True,
                option_type=3,
            )
        ],
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def weather_slash(self, ctx: SlashContext, city):
        await self.weather(ctx, query=city)

    # Embed creator
    @commands.command(aliases=["makeembed", "createembed"], help="Create an embed")
    @commands.has_permissions(manage_messages=True)
    async def embed(self, ctx):
        await ctx.channel.send(
            "Embed creation process started.\n"
            + "Please send the **title you want to use for the embed** within 60 seconds."
        )

        try:
            title = await self.client.wait_for(
                "message",
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                timeout=60,
            )
            await ctx.channel.send(
                f"Title of the embed will be set to '{title.content}'.\n"
                + "Please send the text to use for the **content of the embed** within 60 seconds."
            )
            desc = await self.client.wait_for(
                "message",
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                timeout=60,
            )
            await ctx.channel.send(
                "Please send the text to use as a **footer**.\n"
                + "The footer text will be small and light and will be at the bottom of the embed.\n"
                + "**If you don't want a footer, say 'empty'.**"
            )
            footer = await self.client.wait_for(
                "message",
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                timeout=60,
            )
            await ctx.channel.send(
                "Do you want me to display you as the author of the embed?\n"
                + "Please answer with **yes** or **no** within 60 seconds.\n"
                + "__Send anything *other than* yes or no to cancel the embed creation.__"
            )
            author = await self.client.wait_for(
                "message",
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                timeout=60,
            )

            await ctx.channel.purge(limit=9)

            embed = discord.Embed(
                title=title.content, color=0xFF6600, description=desc.content
            )

            if author.content.lower() == "yes":
                embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
            elif author.content.lower() != "no":
                await ctx.send(":exclamation: Exiting embed creator.")
                return

            if footer.content.lower() != "empty":
                embed.set_footer(text=footer.content)

            await ctx.channel.send(embed=embed)

        except asyncio.TimeoutError:
            await ctx.channel.send(":x: Command has timed out. Exiting embed creator.")

    @cog_ext.cog_slash(name="embed", description="Create an embed")
    async def embed_slash(self, ctx: SlashContext):
        await ctx.defer()
        await self.embed(ctx)

    # Poll command
    @commands.command(help="Create a poll")
    @commands.guild_only()
    async def poll(self, ctx, question, *, options):
        numbers = ("1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟")

        option_list = options.split("/")

        if len(option_list) > 10:
            await ctx.send(":x: You cannot have more than 10 choices!")
            return
        elif len(option_list) < 2:
            await ctx.send(":x: You need to provide multiple options!")
            return

        embed = discord.Embed(
            title=question,
            colour=0xFF6600,
            description="\n\n".join(
                [
                    f"{numbers[i]} {option_list[i]}"  # number emoji + option
                    for i in range(len(option_list))
                ]
            ),
        )
        embed.set_footer(text=f"Poll created by {str(ctx.author.name)}")

        poll_msg = await ctx.send(embed=embed)

        # loop through emojis until the end of the option list is reached
        for emoji in numbers[: len(option_list)]:
            await poll_msg.add_reaction(emoji)  # react with the number emoji

    @cog_ext.cog_slash(
        name="poll",
        description="Create a poll",
        options=[
            create_option(
                name="question",
                description="The title of the poll",
                required=True,
                option_type=3,
            ),
            create_option(
                name="options",
                description="The choices you want for the poll separated by slashes",
                required=True,
                option_type=3,
            ),
        ],
    )
    async def poll_slash(self, ctx, question, options):
        await self.poll(ctx, question, options=options)

    # Eval command
    @commands.command(name="eval", aliases=["exec"], hidden=True)
    @commands.is_owner()
    async def _eval(self, ctx, *, code):
        if code.startswith("```") and code.endswith("```"):
            code = "\n".join(code.split("\n")[1:])[:-3]

        local_variables = {
            "discord": discord,
            "commands": commands,
            "client": self.client,
            "ctx": ctx,
            "message": ctx.message,
            "asyncio": asyncio,
        }

        stdout = io.StringIO()

        try:
            with contextlib.redirect_stdout(stdout):
                exec(
                    f"async def func():\n{textwrap.indent(code, '    ')}",
                    local_variables,
                )

                obj = await local_variables["func"]()
                result = f"{stdout.getvalue()}\nReturned: {obj}\n"
        except Exception as e:
            result = "".join(format_exception(e, e, e.__traceback__))

        pager = buttons.Paginator(
            timeout=None,
            color=0xFF6600,
            entries=[result[i : i + 2000] for i in range(0, len(result), 2000)],
            length=1,
            prefix="```\n",
            suffix="```",
        )

        await pager.start(ctx)


# Add cog
def setup(client):
    client.add_cog(Utility(client))
