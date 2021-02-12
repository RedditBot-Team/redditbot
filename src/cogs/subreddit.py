from discord.ext import commands
from discord_slash import SlashCommand, SlashContext, cog_ext
from discord_slash.utils import manage_commands

import util



class Subreddit(commands.Cog):
    def __init__(self, bot):
        if not hasattr(bot, "slash"):
            # Creates new SlashCommand instance to bot if bot doesn't have.
            bot.slash = SlashCommand(bot, override_type=True, auto_register=True)
        self.bot = bot
        self.bot.slash.get_cog_commands(self)

    def cog_unload(self):
        self.bot.slash.remove_cog_commands(self)

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
        await ctx.send(5)

        # make a loading screen
        message = await ctx.channel.send(embed=util.create_loading_embed(self.bot))

        # Make sure our subreddit name is formatted nicely
        # AKA remove 'r/'
        subreddit_name = util.get_formatted_subreddit_name(subreddit)

        # Create our reddit instance
        reddit = util.create_reddit_instance()

        # Grab our reddit details
        subreddit = reddit.subreddit(subreddit_name)

        # Test to see if the subreddit even exits
        try:
            # Check that we are safe for nsfw content
            if subreddit.over18 and not ctx.channel.is_nsfw():
                await message.edit(embed=util.create_nsfw_content_embed())
                return
        except:
            await message.edit(
                embed=util.create_cant_find_embed(self.bot, subreddit_name)
            )
            return

        # Make subreddit display embed
        embed = util.create_subreddit_embed(self.bot, subreddit, subreddit_name)

        await message.edit(embed=embed)


def setup(bot):
    bot.add_cog(Subreddit(bot))
