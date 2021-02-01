from os import path
import json
import asyncio
import time
import re
import traceback
from typing import Optional
import sys
import random

from discord.ext import commands, tasks
import discord
from termcolor import cprint

# hex colours
GREEN = 0x0e8710


def get_prefix(bot, msg):
    with open("prefixes.json", "r") as f:
        prefixes = json.load(f)
    guild_id = str(msg.guild.id)
    if guild_id in prefixes:
        return commands.when_mentioned_or(prefixes[guild_id])(bot, msg)
    return commands.when_mentioned_or(bot.config["prefix"])(bot, msg)


class DerpBot(commands.Bot):
    def __init__(self, **options):
        if not path.isfile("config.json"):
            with open("config.json", "w+") as f:
                json.dump({
                    "token": 'hidden',
                    "prefix": "!"
                }, f, indent=2)
            print("Created a template config.json\nYou can open it as if its a .txt")
            time.sleep(10)
            exit()
        if not path.isfile("prefixes.json"):
            with open("prefixes.json", "w") as f:
                json.dump({}, f)

        self.index = {}
        self.last_updated = None

        super().__init__(command_prefix=get_prefix, **options)


    @property
    def config(self):
        with open("config.json", "r") as f:
            return json.load(f)


    async def on_ready(self):
        cprint("------------------", "green")
        cprint(f"Logged in as\n{bot.user}\n{bot.user.id}", "green")
        cprint(f"{len(bot.guilds)} servers and {len(bot.users)} users", "green")
        cprint("------------------", "green")


    async def on_command_error(self, context, exception):
        ignored = (commands.CommandNotFound)
        if isinstance(exception, ignored):
            return
        await context.send(embed=discord.Embed(description=str(exception)))
        silent = (
            commands.MissingRequiredArgument,
            commands.CommandOnCooldown,
            commands.BadArgument,
            commands.CheckFailure,
            commands.NotOwner,
            commands.NoPrivateMessage,
            commands.DisabledCommand
        )
        if not isinstance(exception, silent):
            traceback.print_exception(type(exception), exception, exception.__traceback__, file=sys.stderr)


    async def wait(self, message):
        cprint(message, "yellow", end="\r")
        index = 0
        chars = r"-/-\-"
        while True:
            cprint(f"{message} {chars[index]}", "yellow", end="\r")
            index += 1
            if index + 1 == len(chars):
                index = 0
            await asyncio.sleep(0.21)

    
    async def get_choice(self, ctx, options, user, timeout=30) -> Optional[object]:
        """ Reaction based menu for users to choose between things """

        async def add_reactions(message) -> None:
            for emoji in emojis:
                if not message:
                    return
                try:
                    await message.add_reaction(emoji)
                except discord.errors.NotFound:
                    return
                if len(options) > 5:
                    await asyncio.sleep(1)
                elif len(options) > 2:
                    await asyncio.sleep(0.5)

        def predicate(r, u) -> bool:
            return u.id == user.id and str(r.emoji) in emojis

        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️"][:len(options)]
        if not user:
            user = ctx.author

        e = discord.Embed()
        e.set_author(name="Select which option", icon_url=ctx.author.avatar_url)
        e.description = "\n".join(f"{emojis[i]} {option}" for i, option in enumerate(options))
        e.set_footer(text=f"You have 30 seconds")
        message = await ctx.send(embed=e)
        self.loop.create_task(add_reactions(message))

        try:
            reaction, _user = await self.wait_for("reaction_add", check=predicate, timeout=timeout)
        except asyncio.TimeoutError:
            await message.delete()
            return None
        else:
            await message.delete()
            return options[emojis.index(str(reaction.emoji))]


    async def display(self, options: dict, context):
        """ Reaction based configuration """

        async def wait_for_reaction():
            def pred(r, u):
                return u.id == context.author.id and r.message.id == message.id

            try:
                reaction, user = await self.wait_for('reaction_add', check=pred, timeout=60)
            except asyncio.TimeoutError:
                await message.edit(content="Menu Inactive")
                return None
            else:
                return reaction, user

        async def clear_user_reactions(message) -> None:
            message = await context.channel.fetch_message(message.id)
            for reaction in message.reactions:
                if reaction.count > 1:
                    async for user in reaction.users():
                        if user.id == context.author.id:
                            await message.remove_reaction(reaction.emoji, user)
                            break

        async def init_reactions_task() -> None:
            if len(options) > 9:
                other = ["🏡", "◀", "▶"]
                for i, emoji in enumerate(other):
                    if i > 0:
                        await asyncio.sleep(1)
                    await message.add_reaction(emoji)

        pages = []
        tmp_page = {}
        index = 1
        for i, (key, value) in enumerate(options.items()):
            value = options[key]
            if index > 20:
                index = 1
                pages.append(tmp_page)
                tmp_page = {}
                continue
            tmp_page[key] = value
            index += 1
        pages.append(tmp_page)
        page = 0

        def overview():
            e = discord.Embed(color=GREEN) #0x6C3483
            e.description = ""
            for i, (key, value) in enumerate(pages[page].items()):
                if value:
                    e.description += f"\n• [{key}]({value})"
                else:
                    e.description += f"\n• {key}"
            e.set_footer(text=f"Page {page + 1}/{len(pages)}")
            return e

        message = await context.send(embed=overview())
        self.loop.create_task(init_reactions_task())
        while True:
            await clear_user_reactions(message)
            payload = await wait_for_reaction()
            if not payload:
                return None
            reaction, user = payload
            emoji = str(reaction.emoji)
            if emoji == "🏡":
                await message.edit(embed=overview())
                continue
            elif emoji == "▶":
                page += 1
                await message.edit(embed=overview())
                continue
            elif emoji == "◀":
                page -= 1
                await message.edit(embed=overview())
                continue


    def run(self):
        cprint("Starting bot..", "yellow")
        super().run(self.config["token"])


bot = DerpBot(case_insensitive=True)
bot.remove_command("help")
bot.allowed_mentions = discord.AllowedMentions(everyone=False, roles=False, users=False)


@bot.command(name="test")
async def test(ctx):
    await ctx.send("I'm up and running")


@bot.command(name="newprefix", aliases=["np"])
@commands.has_permissions(manage_messages=True)
async def newprefix(ctx, *, new_prefix):
    guild_id = str(ctx.guild.id)
    with open("prefixes.json", "r") as f:
        prefixes = json.load(f)  # type: dict
    if new_prefix == bot.config["prefix"]:
        if guild_id in prefixes:
            del prefixes[guild_id]
            await ctx.send(f"Set the prefix back to {new_prefix}")
        else:
            return await ctx.send("There's no custom prefix being used in this server!")
    else:
        prefixes[guild_id] = new_prefix
        await ctx.send(f"Set the prefix to {new_prefix}")
    with open("prefixes.json", "w") as f:
        json.dump(prefixes, f)


@bot.command(name="help")
async def choose_link_category(ctx):
    e = discord.Embed(color=GREEN)
    e.set_author(name="Available Commands", icon_url=ctx.author.avatar_url)
    e.set_thumbnail(url=bot.user.avatar_url)
    e.description = "These are the commands you can use:"
    guild_id = str(ctx.guild.id)
    with open("prefixes.json", "r") as f:
        prefixes = json.load(f)
    try:
        prefix = prefixes[guild_id]
    except KeyError:
        prefix = '!'
    potential_prefix = '*'
    if prefix == '*':
        potential_prefix = '!'

    e.add_field(
        name="⍟ Commands ⍟",
        value=f"**{prefix}help**"
              f"\n • Show available commands"
              f"\n**{prefix}newprefix ({prefix}np)**"
              f"\n • eg. type '{prefix}newprefix {potential_prefix}' to change prefix from '{prefix}' to '{potential_prefix}'"
              f"\n**{prefix}links**"
              f"\n • Show list of online literature website categories"
              f"\n**{prefix}wordpress ({prefix}wp)**"
              f"\n • Show list of recommended WordPress links"
              f"\n**{prefix}substack ({prefix}ss)**"
              f"\n • Show list of recommended SubStack links"
              f"\n**{prefix}blogspot ({prefix}bs)**"
              f"\n • Show list of recommended BlogSpot links"
              f"\n**{prefix}medium ({prefix}md)**"
              f"\n • Show list of recommended Medium links"
              f"\n**{prefix}add_link ({prefix}al)**"
              f"\n • Add a link to the database (Admin only).\n   eg. {prefix}al <category> <title> <link>"
              f"\n**{prefix}remove_link ({prefix}rl)**"
              f"\n • Remove a link from the database (Admin only).\n   eg. {prefix}rl <category> <title>"
              f"\n**{prefix}coinflip ({prefix}cf)**"
              f"\n • COINFLIP!!!!",
        inline=False
    )
    
    await ctx.send(embed=e)


@bot.command(name="Coinflip", aliases=["cf"])
async def coinflip(ctx):
    e = discord.Embed(color=0x6C3483)
    e.set_author(name="Coinflip", icon_url=ctx.author.avatar_url)
    choice = ["Heads", "Tails"]
    e.description = f"{random.choice(choice)}"
    await ctx.send(embed=e)


@bot.command(name="add_link", aliases=["al"])
@commands.has_permissions(manage_messages=True)
async def add_link(ctx, category, title, link):
    if category not in ['wordpress', 'blogspot', 'substack', 'medium']:
        return await ctx.send(f"'{category}' is not a valid category. Link not added.")
    with open("links.txt", "a") as f:
        f.write(f'\n{category},{title},{link}')
    await ctx.send(f"Your link has been added to the category {category}!")


@bot.command(name="remove_link", aliases=["rl"])
@commands.has_permissions(manage_messages=True)
async def remove_link(ctx, category, title):
    if category not in ['wordpress', 'blogspot', 'substack', 'medium']:
        return await ctx.send(f"'{category}' is not a valid category. Check your spelling and try again!")
    original_line_count = 0
    updated_line_count = 0
    with open("links.txt", "r") as file_input:
        lines = file_input.readlines()
    with open("links.txt", "w") as output: 
        for line in lines:
            line = line.strip("\n")
            original_line_count += 1
            split_line = line.split(',')
            if not ((split_line[0].lower() == category.lower()) and (split_line[1].lower() == title.lower())):
                output.write(line+'\n')
                updated_line_count += 1
    if updated_line_count == original_line_count:
        return await ctx.send(f"'{title}' was not found. Check your spelling and try again!")

    await ctx.send(f"Link titled '{title}' has been removed from the category '{category}'!")


@bot.command(name="links")
async def choose_link_category(ctx):
    e = discord.Embed(color=GREEN) #0x6C3483
    e.set_author(name="Choose Link Category", icon_url=ctx.author.avatar_url)
    e.set_thumbnail(url=bot.user.avatar_url)
    guild_id = str(ctx.guild.id)
    with open("prefixes.json", "r") as f:
        prefixes = json.load(f)
    try:
        prefix = prefixes[guild_id]
    except KeyError:
        prefix = '!'
    e.description = f"Choose a category to get links from and \ntype it as a command. eg. ({prefix}wordpress)"

    e.add_field(
        name="⍟ Categories ⍟",
        value=f"wordpress"
              f"\nsubstack"
              f"\nblogspot"
              f"\nmedium",
        inline=False
    )
    
    await ctx.send(embed=e)


@bot.command(name="Wordpress", aliases=["wp"])
async def wordpress_links(ctx):
    e = discord.Embed(color=GREEN) #0x6C3483
    e.set_author(name="Wordpress Links", icon_url=ctx.author.avatar_url) #can replace with whatever avatar icon you want
    with open("links.txt") as f:
        links = f.readlines()
        text = ''
        for link in links:
            link = ''.join(link).split(',')
            if link[0].lower() == 'wordpress':
                text += f'Title: **{link[1]}**\n'
                text += link[2]
        e.description = text
    await ctx.send(embed=e)


@bot.command(name="Substack", aliases=["ss"])
async def substack_links(ctx):
    e = discord.Embed(color=GREEN) #0x6C3483
    e.set_author(name="Substack Links", icon_url=ctx.author.avatar_url) #can replace with whatever avatar icon you want
    with open("links.txt") as f:
        links = f.readlines()
        text = ''
        for link in links:
            link = ''.join(link).split(',')
            if link[0].lower() == 'substack':
                text += f'Title: **{link[1]}**\n'
                text += link[2]
        e.description = text
    await ctx.send(embed=e)


@bot.command(name="Blogspot", aliases=["bs"])
async def blogspot_links(ctx):
    e = discord.Embed(color=GREEN) #0x6C3483
    e.set_author(name="Blogspot Links", icon_url=ctx.author.avatar_url) #can replace with whatever avatar icon you want
    with open("links.txt") as f:
        links = f.readlines()
        text = ''
        for link in links:
            link = ''.join(link).split(',')
            if link[0].lower() == 'blogspot':
                text += f'Title: **{link[1]}**\n'
                text += link[2]
        e.description = text
    await ctx.send(embed=e)


@bot.command(name="Medium", aliases=["md"])
async def medium_links(ctx):
    e = discord.Embed(color=GREEN) #0x6C3483
    e.set_author(name="Medium Links", icon_url=ctx.author.avatar_url) #can replace with whatever avatar icon you want
    with open("links.txt") as f:
        links = f.readlines()
        text = ''
        for link in links:
            link = ''.join(link).split(',')
            if link[0].lower() == 'medium':
                text += f'Title: **{link[1]}**\n'
                text += link[2]
        e.description = text
    await ctx.send(embed=e)


bot.run()