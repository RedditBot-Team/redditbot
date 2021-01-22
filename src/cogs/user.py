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
            bot.slash = SlashCommand(
                bot, override_type=True, auto_register=True, auto_delete=True
            )
        self.bot = bot
        self.bot.slash.get_cog_commands(self)

    def cog_unload(self):
        self.bot.slash.remove_cog_commands(self)

    @cog_ext.cog_slash(
        name="user",
        description="See some info on a user",
        options=[
            manage_commands.create_option(
                name="username",
                description="The name of a user.",
                option_type=3,
                required=True,
            )
        ],
    )
    async def _user(self, ctx: SlashContext, username: str):
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

    @cog_ext.cog_slash(
        name="whois",
        description="See some info on a members connected reddit account",
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
        storedUserData = doc_ref.get()
        storedUserDict = storedUserData.to_dict()

        if storedUserData.exists:
            headers = {
                "Authorization": f'Bearer {storedUserDict["access_token"]}',
            }

            response = requests.request(
                "GET",
                "https://discord.com/api/users/@me/connections",
                headers=headers,
                data={},
            )
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
                            await message.edit(
                                embed=util.create_nsfw_content_embed(self.bot)
                            )
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
