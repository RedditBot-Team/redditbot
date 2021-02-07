import requests
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash import SlashCommand
from discord_slash import SlashContext
from discord_slash.utils import manage_commands
import util
import firebase_admin
from firebase_admin import firestore


class User(commands.Cog):
    def __init__(self, bot):
        if not hasattr(bot, "slash"):
            # Creates new SlashCommand instance to bot if bot doesn't have.
            bot.slash = SlashCommand(bot, override_type=True, auto_register=True)
        self.bot = bot
        self.bot.slash.get_cog_commands(self)

    def cog_unload(self):
        self.bot.slash.remove_cog_commands(self)

    @cog_ext.cog_slash(
        name="user", description="See some info on a user"
    )
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
        await ctx.send(5)

        # make a loading screen
        message = await ctx.channel.send(embed=util.create_loading_embed(self.bot))

        # Make sure our username is formatted nicely
        # AKA remove 'u/'
        username = util.get_formatted_username(username)

        # Create our reddit instance
        reddit = util.create_reddit_instance()

        # Grab our user details
        user = reddit.redditor(username)

        # Test to see if the user even exits
        try:
            # Check that we are safe for nsfw content
            if user.subreddit["over_18"] and not ctx.channel.is_nsfw():
                await message.edit(embed=util.create_nsfw_content_embed())
                return
        except:
            await message.edit(embed=util.create_cant_find_embed(self.bot, username))
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
        await ctx.send(5)

        # make a loading screen
        message = await ctx.channel.send(embed=util.create_loading_embed(self.bot))

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

            multiple = 0
            for connection in response.json():
                if connection["type"] == "reddit":
                    if connection["visibility"] == 0 and ctx.author == member.id:
                        await message.delete()
                        await ctx.send(
                            hidden=True,
                            content=f"Your connection `{connection['name']}` is private, so you cant use this",
                        )
                        return
                    elif connection["visibility"] == 0:
                        await message.edit(
                            embed=util.create_visibility_zero_embed(member)
                        )
                        return

                    # Make sure our username is formatted nicely
                    # AKA remove 'u/'
                    username = util.get_formatted_username(connection["name"])

                    # Create our reddit instance
                    reddit = util.create_reddit_instance()

                    # Grab our user details
                    user = reddit.redditor(username)

                    # Test to see if the user even exits
                    try:
                        # Check that we are safe for nsfw content
                        if user.subreddit["over_18"] and not ctx.channel.is_nsfw():
                            await message.edit(embed=util.create_nsfw_content_embed())
                            return
                    except:
                        await message.edit(
                            embed=util.create_cant_find_embed(self.bot, username)
                        )
                        return

                    # Make user display embed
                    embed = util.create_user_embed(self.bot, user, username)

                    if multiple > 0:
                        await ctx.channel.send(embed=embed)
                    else:
                        await message.edit(
                            embed=embed, content=f"{member.name}'s account(s):"
                        )
                    multiple = multiple + 1

        else:
            await message.edit(embed=util.create_unpermitted_error_embed(member))
            return


def setup(bot):
    bot.add_cog(User(bot))
