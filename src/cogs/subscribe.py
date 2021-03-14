import json
import os
from datetime import datetime

import discord
import firebase_admin
import praw
import requests
from discord.ext import commands, tasks
from discord_slash import SlashCommand, SlashContext, cog_ext
from discord_slash.utils import manage_commands
from firebase_admin import firestore

import util


class Subscribe(commands.Cog, name="Subscribe"):
    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_slash(
        name="subscriptions", description="live updating posts to channels"
    )
    async def _parent_command(self, ctx: SlashContext):
        pass

    @cog_ext.cog_subcommand(
        base="subscriptions",
        name="unsubscribe",
        description="Unsubscribe a channel from a subreddit",
    )
    async def _unsubscribe(self, ctx: SlashContext):
        await ctx.respond()
        await ctx.send(embed=util.create_delete_integration_embed(self.bot))

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
        await ctx.respond()

        if not ctx.guild.owner_id == ctx.author_id:
            await ctx.send(
                embed=discord.Embed(
                    title="Only a server owner can use this command",
                    url="https://bwac.gitbook.io/redditbot/get-info/subscriptions#creating-a-stream",
                )
            )
            return

        if not isinstance(text_channel, discord.TextChannel):
            await ctx.send(
                embed=util.create_wrong_channel_type("Text Channel", text_channel)
            )
            return

        # Make sure our subreddit is formatted nicely
        # AKA remove 'r/'
        subreddit_name = util.get_formatted_subreddit_name(subreddit)

        # Create our reddit instance
        reddit = util.create_reddit_instance()

        # Grab our reddit details
        try:
            subreddit = await reddit.subreddit(subreddit_name, fetch=True)
        except:
            # Sub doesnt exist
            await ctx.send(embed=util.create_cant_find_embed(self.bot, subreddit_name))
            return

        # Check that we are safe for nsfw content
        if subreddit.over18 and not text_channel.is_nsfw():
            await text_channel.send(embed=util.create_nsfw_content_embed(self.bot))
            return

        db = firebase_admin.firestore.client()

        try:
            webhook = await text_channel.create_webhook(
                name=f"{str(subreddit_name)} - RedditBot stream"
            )
        except discord.errors.Forbidden:
            await ctx.send(":x: I need the perms to manage webhooks.")
            return

        db.document(f"webhooks/{str(webhook.id)}").set(
            {
                "guild_id": webhook.guild_id,
                "channel_id": webhook.channel_id,
                "token": webhook.token,
                "subreddit": subreddit.display_name,
            }
        )

        await text_channel.send(
            content=f"{ctx.author.mention}",
            embed=discord.Embed(
                title=f":white_check_mark: This channel will start receiving new posts from `{subreddit_name}`",
                timestamp=datetime.utcnow(),
            ),
        )

    @cog_ext.cog_subcommand(
        base="subscriptions",
        name="summary",
        description="Get a daily summary of the top posts in a channel",
        options=[
            manage_commands.create_option(
                name="text_channel",
                description="The channel to subscribe summaries the subreddit to.",
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
    async def _summary(self, ctx: SlashContext, text_channel, subreddit):
        await ctx.respond()

        if not ctx.guild.owner_id == ctx.author_id:
            await ctx.send(
                embed=discord.Embed(
                    title="Only a server owner can use this command",
                    url="https://bwac.gitbook.io/redditbot/get-info/subscriptions#creating-a-stream",
                )
            )
            return

        if not isinstance(text_channel, discord.TextChannel):
            await ctx.send(
                embed=util.create_wrong_channel_type("Text Channel", text_channel)
            )
            return

        # Make sure our subreddit is formatted nicely
        # AKA remove 'r/'
        subreddit_name = util.get_formatted_subreddit_name(subreddit)

        # Create our reddit instance
        reddit = util.create_reddit_instance()

        # Grab our reddit details
        try:
            subreddit = await reddit.subreddit(subreddit_name, fetch=True)
        except:
            # Sub doesnt exist
            await ctx.send(embed=util.create_cant_find_embed(self.bot, subreddit_name))
            return

        # Check that we are safe for nsfw content
        if subreddit.over18 and not text_channel.is_nsfw():
            await text_channel.send(embed=util.create_nsfw_content_embed(self.bot))
            return

        db = firebase_admin.firestore.client()

        try:
            webhook = await text_channel.create_webhook(
                name=f"{str(subreddit_name)} - RedditBot summary stream"
            )
        except discord.errors.Forbidden:
            await ctx.send(":x: I need the perms to manage webhooks.")
            return

        db.document(f"summaries/{str(webhook.id)}").set(
            {
                "guild_id": webhook.guild_id,
                "channel_id": webhook.channel_id,
                "token": webhook.token,
                "subreddit": subreddit.display_name,
            }
        )

        await text_channel.send(
            embed=discord.Embed(
                title=f":white_check_mark: This channel will start receiving daily summaries of the top posts "
                f"from `{subreddit_name}` every day.",
                timestamp=datetime.utcnow(),
            ),
        )


async def setup(bot):
    cog_instance = Subscribe(bot)
    bot.add_cog(cog_instance)
