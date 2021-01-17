from datetime import datetime

import discord
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash import SlashCommand
from discord_slash import SlashContext
from discord_slash.utils import manage_commands
import util
import firebase_admin
from firebase_admin import firestore


class Subscribe(commands.Cog):
    def __init__(self, bot):
        if not hasattr(bot, "slash"):
            # Creates new SlashCommand instance to bot if bot doesn't have.
            bot.slash = SlashCommand(
                bot, override_type=True, auto_register=True, auto_delete=True
            )
        self.bot = bot
        self.bot.slash.get_cog_commands(self)

    def cog_unload(self):
        self.bot.slash.remove_cog_commands(self)

    @cog_ext.cog_slash(
        name="subscriptions",
        description="live updating posts to channels"
    )
    async def _parent_command(self, ctx: SlashContext):
        pass

    @cog_ext.cog_subcommand(
        base="subscriptions",
        name="unsubscribe",
        description="Unsubscribe a channel from a subreddit",
    )
    async def _unsubscribe(self, ctx: SlashContext):
        await ctx.send(5),
        await ctx.channel.send(embed=util.create_delete_integration_embed(self.bot))

    @cog_ext.cog_subcommand(
        base="subscriptions",
        name="subscribe",
        description="Subscribe a channel to a subreddit, for live updating posts",
        options=[
            manage_commands.create_option(
                name="text_channel",
                description="The channel to subscribe the subreddit to.",
                option_type=7,
                required=True,
            ),
            manage_commands.create_option(
                name="subreddit",
                description="The name of the subreddit.",
                option_type=3,
                required=True,
            ),
        ],
    )
    async def _subscribe(self, ctx: SlashContext, text_channel, subreddit):
        # Make sure our token doesnt disappear
        await ctx.send(5)
        await ctx.channel.send("Currently disabled")
        return

        # USER PERMISSION CHECK

        if not isinstance(text_channel, discord.TextChannel):
            await ctx.channel.send(
                embed=util.create_wrong_channel_type("Text Channel", text_channel)
            )
            return

        # make a loading screen
        message = await ctx.channel.send(embed=util.create_loading_embed(self.bot))

        # Make sure our subreddit is formatted nicely
        # AKA remove 'r/'
        subreddit_name = util.get_formatted_subreddit_name(subreddit)

        # Create our reddit instance
        reddit = util.create_reddit_instance()

        # Grab our subreddit details
        subreddit = reddit.subreddit(subreddit_name)

        # Test to see if the subreddit even exits
        try:
            # Check that we are safe for nsfw content
            if subreddit.over18 and not text_channel.is_nsfw():
                await message.edit(embed=util.create_nsfw_content_embed(self.bot))
                return
        except:
            await message.edit(
                embed=util.create_cant_find_embed(self.bot, subreddit_name)
            )
            return

        db = firebase_admin.firestore.client()

        try:
            webhook = await text_channel.create_webhook(
                name=f"{str(subreddit_name)} - RedditBot stream"
            )
        except discord.errors.Forbidden:
            await message.delete()
            await ctx.channel.send(":x: I need the perms to manage webhooks.")
            return

        subreddit_doc_ref = db.document(f"streams/{str(subreddit_name)}")

        if not subreddit_doc_ref.get().exists:
            subreddit_doc_ref.set({})

        db.document(f"streams/{str(subreddit_name)}/webhooks/{str(webhook.id)}").set(
            {
                "id": webhook.id,
                "guild_id": webhook.guild_id,
                "channel_id": webhook.channel_id,
                "token": webhook.token,
            }
        )

        await message.delete()

        await text_channel.send(
            embed=discord.Embed(
                title=f":white_check_mark: Nice, this channel will start receiving new posts from `{subreddit_name}`",
                description="It can take up to a minute",
                timestamp=datetime.utcnow(),
            )
        )


async def setup(bot):
    cog_instance = Subscribe(bot)
    bot.add_cog(cog_instance)
