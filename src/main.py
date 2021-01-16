import os
import discord
import logging
from cogs import subreddit, user, subscribe, topgg
from discord.ext import commands
import firebase_admin
from discord_slash import SlashCommand
import util

bot = commands.AutoShardedBot(command_prefix="")
slash = SlashCommand(bot, auto_register=True)
intents = discord.Intents(messages=True, guilds=True)

logging.basicConfig(level=logging.INFO)

firebase_admin.initialize_app(util.make_credentials())


@slash.slash(name="help", description="I need help!")
async def _help(ctx):  # Defines a new "context" (ctx) command called "ping."
    await ctx.send(5)
    await ctx.channel.send(embed=discord.Embed(
        title=f"Read everything about me here",
        url="https://bwac.gitbook.io/redditbot/"
    ).set_author(
        name="RedditBot",
        icon_url=bot.user.avatar_url,
        url="https://top.gg/bot/437439562386505730",
    ))


async def refresh_status():
    db = firebase_admin.firestore.client()
    config_ref = db.document(f"meta/config")
    config = config_ref.get().to_dict()

    if config["status_override"] is not None:
        await bot.change_presence(status=discord.Status.online, activity=discord.Game(config["status_override"]))
        return

    await bot.change_presence(status=discord.Status.online, activity=discord.Game(f"/help | Active in {len(bot.guilds)} servers"))


@bot.event
async def on_ready():
    print("We have logged in as {0.user}".format(bot))
    await refresh_status()


@bot.event
async def on_resumed():
    await refresh_status()


@bot.event
async def on_guild_join():
    await refresh_status()


@bot.event
async def on_guild_remove():
    await refresh_status()


bot.add_cog(subreddit.Subreddit(bot))
bot.add_cog(user.User(bot))
bot.add_cog(subscribe.Subscribe(bot))

if int(os.environ['PRODUCTION']) == 1:
    bot.add_cog(topgg.TopGG(bot))

    bot.run(os.environ['REDDITBOT_TOKEN'])
else:
    bot.run(os.environ['DEV_TOKEN'])
