import logging
import os
import threading
import time

import discord
import firebase_admin
from discord.ext import commands
from discord_slash import SlashCommand
from firebase_admin import firestore

import streamer
import util
from cogs import events, subreddit, subscribe, user

bot = commands.AutoShardedBot(command_prefix="/", help_command=None)
slash = SlashCommand(bot)

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


@bot.command(name="list")
async def list_subs(ctx):
    if ctx.author.id == 408355239108935681:
        db = firebase_admin.firestore.client()
        subs = []
        for i in db.collection("webhooks").get():
            if i.to_dict()["subreddit"] in subs:
                continue
            await ctx.channel.send(i.to_dict()["subreddit"])
            subs.append(i.to_dict()["subreddit"])
    else:
        mes = await ctx.channel.send("You found a secret!")
        time.sleep(2)
        await mes.delete()

cogs = [
    subreddit.Subreddit(bot),
    user.User(bot),
    subscribe.Subscribe(bot),
    events.Events(bot),
]

for cog in cogs:
    bot.add_cog(cog)

if __name__ == '__main__':
    if int(os.environ["PRODUCTION"]) == 1:
        logging.info("Logging in as production")

        streamer_instance = streamer.Streamer(
            437439562386505730,
            os.environ["REDDITBOT_TOKEN"],
            os.environ["REDDIT_ID"],
            os.environ["REDDIT_SECRET"],
        )

        streamer_listener = threading.Thread(
            target=streamer_instance.listen,
            args=()
        )
        streamer_listener.start()

        bot.run(os.environ["REDDITBOT_TOKEN"])
    else:
        logging.info("Logging in as dev")

        bot.run(os.environ["DEV_TOKEN"])
