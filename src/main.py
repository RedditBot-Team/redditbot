import logging
import os

import discord
import firebase_admin
from discord.ext import commands
from discord_slash import SlashCommand

import util
from cogs import events, subreddit, subscribe, user
from jishaku.cog import Jishaku

bot = commands.AutoShardedBot(command_prefix="/", help_command=None)
slash = SlashCommand(bot, auto_register=True)

intents = discord.Intents(messages=True, guilds=True)

logging.basicConfig(level=logging.INFO)

firebase_admin.initialize_app(util.make_credentials())


async def help(ctx):
    await ctx.channel.send(
        embed=discord.Embed(
            title=f"Read everything about me here",
            url="https://bwac.gitbook.io/redditbot/",
        ).set_author(
            name="RedditBot",
            icon_url=bot.user.avatar_url,
            url="https://top.gg/bot/437439562386505730",
        )
    )


@slash.slash(name="help", description="I need help!")
async def _help(ctx):
    await help(ctx)


@bot.command(name="help")
async def __help(ctx):
    await help(ctx)
    await ctx.send(
        "Also, if slash commands aren't working, re-add again with the correct permissions here: "
        "https://redditbot.bwac.dev/invite\nIf it keeps happening try again later "
    )


cogs = [
    subreddit.Subreddit(bot),
    user.User(bot),
    subscribe.Subscribe(bot),
    events.Events(bot),
]

for cog in cogs:
    bot.add_cog(cog)


if int(os.environ["PRODUCTION"]) == 1:
    logging.info("Logging in as production")

    bot.run(os.environ["REDDITBOT_TOKEN"])
else:
    logging.info("Logging in as dev")

    bot.load_extension('jishaku')

    bot.run(os.environ["DEV_TOKEN"])
