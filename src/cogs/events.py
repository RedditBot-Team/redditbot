import logging
import os
import random

import discord
import firebase_admin
from discord.ext import commands
from firebase_admin import firestore

logging.basicConfig(level=logging.INFO)


class Events(commands.Cog, name="Events"):
    def __init__(self, bot):
        self.bot = bot

    async def refresh_status(self):
        db = firebase_admin.firestore.client()
        config_ref = db.document(f"meta/config")
        config = config_ref.get().to_dict()

        try:
            await self.bot.change_presence(
                status=discord.Status.online,
                activity=discord.Game(config["status_override"]),
            )
        except KeyError:
            await self.bot.change_presence(
                status=discord.Status.online,
                activity=discord.Game(
                    f"/help | Active in {len(self.bot.guilds)} servers"
                ),
            )

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info("We have logged in as {0.user}".format(self.bot))
        logging.info(f"With {len(self.bot.guilds)} guilds")
        await self.refresh_status()

    @commands.Cog.listener()
    async def on_resumed(self):
        await self.refresh_status()

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.refresh_status()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        await self.refresh_status()

    @commands.Cog.listener()
    async def on_slash_command(self, ctx):
        if random.randint(0, 5) == 0:
            await ctx.channel.send(
                embed=discord.Embed(
                    title="Enjoying redditbot? Vote please!",
                    description="If you voted for me, my creator would really appreciate it",
                    url="https://redditbot.bwac.dev/vote",
                )
            )

    @commands.Cog.listener()
    async def on_slash_command_error(self, ctx, ex: Exception):
        await ctx.channel.send(
            embed=discord.Embed(
                title="An error happened. Oh dear",
                #url="https://discord.com/invite/JAzBJZp",
            ),
        )


def setup(bot):
    bot.add_cog(Events(bot))
