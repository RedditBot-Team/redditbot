from discord.ext import commands
import firebase_admin
from firebase_admin import firestore

import util


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def cog_unload(self):
        self.bot.slash.remove_cog_commands(self)


def setup(bot):
    bot.add_cog(Events(bot))
