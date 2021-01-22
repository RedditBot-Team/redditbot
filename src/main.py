import os
import discord
import logging
from cogs import subreddit, user, subscribe, topgg, events
from discord.ext import commands
import firebase_admin
from discord_slash import SlashCommand
import util

bot = commands.AutoShardedBot(command_prefix="/", help_command=None)
slash = SlashCommand(bot, auto_register=True, auto_delete=True)

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
    await ctx.send("If slash commands aren't working, re-add again with the correct permissions here: https://redditbot.bwac.dev/invite")


cogs = [
    subreddit.Subreddit(bot),
    user.User(bot),
    subscribe.Subscribe(bot),
    events.Events(bot),
]

for cog in cogs:
    bot.add_cog(cog)


if int(os.environ["PRODUCTION"]) == 1:
    bot.add_cog(topgg.TopGG(bot))

    logging.info("Logging in as production")

    bot.run(os.environ["REDDITBOT_TOKEN"])
else:
    logging.info("Logging in as dev")

    bot.run(os.environ["DEV_TOKEN"])
