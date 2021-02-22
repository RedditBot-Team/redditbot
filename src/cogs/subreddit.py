from discord.ext import commands
from discord_slash import SlashCommand, SlashContext, cog_ext
from discord_slash.utils import manage_commands

import util


class Subreddit(commands.Cog, name="Subreddit"):
    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_slash(
        name="subreddit",
        description="See some info on a subreddit",
        options=[
            manage_commands.create_option(
                name="subreddit",
                description="The name of a subreddit.",
                option_type=3,
                required=True,
            )
        ],
    )
    async def _subreddit(self, ctx: SlashContext, subreddit: str):
        # Make sure our token doesnt disappear
        await ctx.respond()

        # make a loading screen
        message = await ctx.send(embed=util.create_loading_embed(self.bot))

        # Make sure our subreddit name is formatted nicely
        # AKA remove 'r/'
        subreddit_name = util.get_formatted_subreddit_name(subreddit)

        # Create our reddit instance
        reddit = util.create_reddit_instance()

        # Grab our reddit details
        try:
            subreddit = await reddit.subreddit(subreddit_name, fetch=True)
        except:
            # Sub doesnt exist
            await message.edit(
                embed=util.create_cant_find_embed(self.bot, subreddit_name)
            )
            return

        # Check that we are safe for nsfw content
        if subreddit.over18 and not ctx.channel.is_nsfw():
            await message.edit(embed=util.create_nsfw_content_embed())
            return

        # Make subreddit display embed
        embed = util.create_subreddit_embed(self.bot, subreddit, subreddit_name)

        await message.edit(embed=embed)


def setup(bot):
    bot.add_cog(Subreddit(bot))
