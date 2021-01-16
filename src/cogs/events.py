from discord.ext import commands
import firebase_admin
from firebase_admin import firestore

import util


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def cog_unload(self):
        self.bot.slash.remove_cog_commands(self)

    async def refresh_status(self):
        db = firebase_admin.firestore.client()
        config_ref = db.document(f"meta/config")
        config = config_ref.get().to_dict()

        if config["status_override"] is not None:
            await self.bot.change_presence(status=discord.Status.online, activity=discord.Game(config["status_override"]))
            return

        await self.bot.change_presence(status=discord.Status.online,
                                  activity=discord.Game(f"/help | Active in {len(self.bot.guilds)} servers"))

    @commands.Cog.listener
    async def on_ready(self):
        print("We have logged in as {0.user}".format(self.bot))
        print(f"With {len(self.bot.guilds)} guilds")
        await self.refresh_status()

    @commands.Cog.listener
    async def on_resumed(self):
        await self.refresh_status()

    @commands.Cog.listener
    async def on_guild_join(self):
        await self.refresh_status()

    @commands.Cog.listener
    async def on_guild_remove(self):
        await self.refresh_status()


def setup(bot):
    bot.add_cog(Events(bot))
