import firebase_admin
import requests
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext, cog_ext
from discord_slash.utils import manage_commands
from firebase_admin import firestore

import util


class User(commands.Cog, name="User"):
    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_slash(name="user", description="See some info on a user")
    async def _parent_command(self, ctx: SlashContext):
        pass

    @cog_ext.cog_subcommand(
        name="username",
        base="user",
        description="See some info on a user, by their username",
        options=[
            manage_commands.create_option(
                name="username",
                description="The name of a user.",
                option_type=3,
                required=True,
            )
        ],
    )
    async def _username(self, ctx: SlashContext, username: str):
        # Make sure our token doesnt disappear
        await ctx.respond()

        # make a loading screen
        message = await ctx.send(embed=util.create_loading_embed(self.bot))

        # Make sure our username is formatted nicely
        # AKA remove 'u/'
        username = util.get_formatted_username(username)

        # Create our reddit instance
        reddit = util.create_reddit_instance()

        # Grab our user details
        try:
            user = reddit.redditor(username, fetch=True)
        except:
            # Sub doesnt exist
            await message.edit(
                embed=util.create_cant_find_embed(self.bot, username)
            )
            return

        # Check that we are safe for nsfw content
        if user.subreddit["over_18"] and not ctx.channel.is_nsfw():
            await message.edit(embed=util.create_nsfw_content_embed())
            return

        # Make user display embed
        embed = util.create_user_embed(self.bot, user, username)

        await message.edit(embed=embed)

    @cog_ext.cog_subcommand(
        name="member",
        base="user",
        description="See some info on a server member's connected reddit account",
        options=[
            manage_commands.create_option(
                name="member",
                description="The name of a user.",
                option_type=6,
                required=True,
            )
        ],
    )
    async def _whois(self, ctx: SlashContext, member):
        # Make sure our token doesnt disappear
        await ctx.respond()

        # make a loading screen
        message = await ctx.send(embed=util.create_loading_embed(self.bot))

        db = firebase_admin.firestore.client()

        doc_ref = db.collection(f"users").document(str(member.id))
        stored_user_data = doc_ref.get()
        stored_user_dict = stored_user_data.to_dict()

        if stored_user_data.exists:
            headers = {
                "Authorization": f'Bearer {stored_user_dict["access_token"]}',
            }

            response = requests.request(
                "GET",
                "https://discord.com/api/users/@me/connections",
                headers=headers,
                data={},
            )

            if response.status_code == 401:
                await message.edit(embed=util.create_unpermitted_error_embed(member))
                return

            # Make sure we check for 0 connected reddit accounts

            reddit_connections = []
            for connection in response.json():
                if connection["type"] == "reddit":
                    reddit_connections.append(connection)

            if len(reddit_connections) == 0:
                await message.delete()
                await ctx.send(
                    f"{member.name} doesnt have any connected reddit accounts"
                )
                return

            embeds = []

            for connection in reddit_connections:
                if connection["type"] == "reddit":
                    if connection["visibility"] == 0 and ctx.author == member.id:
                        await ctx.send(
                            hidden=True,
                            content=f"Your connection `{connection['name']}` is private",
                        )
                        continue
                    elif connection["visibility"] == 0:
                        embeds.append(util.create_visibility_zero_embed(member))
                        continue

                    # Make sure our username is formatted nicely
                    # AKA remove 'u/'
                    username = util.get_formatted_username(connection["name"])

                    # Create our reddit instance
                    reddit = util.create_reddit_instance()

                    # Grab our user details
                    try:
                        user = reddit.redditor(username, fetch=True)
                    except:
                        # Sub doesnt exist
                        await message.edit(
                            embed=util.create_cant_find_embed(self.bot, username)
                        )
                        return

                    # Check that we are safe for nsfw content
                    if user.subreddit["over_18"] and not ctx.channel.is_nsfw():
                        embeds.append(util.create_nsfw_content_embed())
                        continue

                    # Make user display embed
                    embeds.append(util.create_user_embed(self.bot, user, username))

            await message.delete()

            # Looks complicated, that's because it is
            # adds an 's' if there are more than 1 account
            await ctx.send(
                f"{member.name}'s account{'s' if len(embeds) > 1 else ''}:"
            )

            for embed in embeds:
                await ctx.send(embed=embed)
        else:
            await message.edit(embed=util.create_unpermitted_error_embed(member))


def setup(bot):
    bot.add_cog(User(bot))
