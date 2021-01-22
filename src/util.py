import os
from datetime import datetime
from firebase_admin import credentials
import discord
import praw


def make_credentials():
    return credentials.Certificate("redditbot-discord-firebase-adminsdk.json")


def get_formatted_subreddit_name(str: str):
    if str[:2] == "r/":
        return str[2:]
    return str


def get_formatted_username(str: str):
    if str[:2] == "u/":
        return str[2:]
    return str


def create_reddit_instance():
    return praw.Reddit(
        client_id=os.environ["REDDIT_ID"],
        client_secret=os.environ["REDDIT_SECRET"],
        user_agent="RedditBot",
    )


def set_author(embed: discord.Embed, bot: discord.client):
    return embed.set_author(
        name="RedditBot",
        icon_url=bot.user.avatar_url,
        url="https://redditbot.bwac.dev/",
    )


def create_loading_embed(bot):
    errorEmbed = discord.Embed(
        title=f"{bot.get_emoji(650579775433474088)} Hang on, im loading..",
    )
    errorEmbed = set_author(errorEmbed, bot)
    return errorEmbed


def create_delete_integration_embed(bot):
    embed = discord.Embed(
        title=f"To delete your stream, delete your stream's integration",
    )
    embed = set_author(embed, bot)
    embed.set_image(url="https://i.imgur.com/fDgeCes.png")
    return embed


def create_cant_find_embed(bot, name: str):
    errorEmbed = discord.Embed(
        title=f'"{name}" cant be found',
        timestamp=datetime.utcnow(),
    )
    errorEmbed = set_author(errorEmbed, bot)

    return errorEmbed


def create_nsfw_content_embed():
    errorEmbed = discord.Embed(
        title="NSFW Content is only allowed in a NSFW channel.",
        url="https://bwac.gitbook.io/redditbot/topics/nsfw",
    )
    errorEmbed.set_author(
        name="RedditBot",
        url="https://redditbot.bwac.dev/",
    )
    return errorEmbed


def create_subreddit_embed(bot, subreddit, subreddit_name):
    # create our sub embed
    embed = discord.Embed(
        title=f"{subreddit.display_name}",
        description=subreddit.public_description,
        timestamp=datetime.utcnow(),
        url=f"https://reddit.com/r/{subreddit_name}",
    )
    embed.set_thumbnail(url=subreddit.icon_img)
    embed = set_author(embed, bot)
    embed.set_footer(text=f"{subreddit.id} - {subreddit.fullname}")

    # Add some fields
    embed.add_field(name="Subscribers", value=str(subreddit.subscribers))
    embed.add_field(
        name="Created (UTC)",
        value=str(datetime.utcfromtimestamp(float(subreddit.created_utc))),
    )
    return embed


def create_user_embed(bot, user, username):
    # create our sub embed
    embed = discord.Embed(
        title=f"{user.name}",
        description=f"""{user.subreddit['public_description']}
                    {'*This user is an employee of reddit*' if user.is_employee else ''}
                    {f'*{bot.get_emoji(651535364087087114)} This user has premium*' if user.is_gold else ''}
        """,
        timestamp=datetime.utcnow(),
        url=f"https://reddit.com/u/{username}",
    )
    embed.set_thumbnail(url=user.icon_img)
    embed = set_author(embed, bot)

    embed.set_footer(text=f"{user.id}")

    embed.add_field(
        name="Karma",
        value=f"{user.comment_karma + user.link_karma} ({user.comment_karma} + {user.link_karma})",
    )
    embed.add_field(
        name="Cake Day (UTC)",
        value=str(datetime.utcfromtimestamp(float(user.created_utc))),
    )
    return embed


def create_submission_embed(submission):
    # create our sub embed
    embed = discord.Embed(
        title=f"{submission.title}",
        description=f"""{f'*Is original content*' if submission.is_original_content else f''}
                    {f'*Is edited*' if submission.edited else f''}
                    """,
        timestamp=datetime.utcnow(),
        url=f"https://reddit.com{submission.permalink}",
    )
    embed.set_author(
        name=submission.author.name,
        icon_url=submission.author.icon_img,
        url=f"https://reddit.com/u/{submission.author.name}",
    )
    embed.set_image(url=submission.url)

    # Add some fields
    embed.add_field(
        name="Upvotes",
        value=submission.score,
    )
    embed.add_field(
        name="Created (UTC)",
        value=str(datetime.utcfromtimestamp(float(submission.created_utc))),
    )
    return embed


def create_unpermitted_error_embed(bot, author, target):
    return discord.Embed(
        title=f":x: {target.name} hasn't authorized RedditBot to see their connections.\nClick here to authorize",
        description="Any account linking with RedditBot expires in 7 days, to respect your privacy,\nWe don't store anything about you.",
        timestamp=datetime.utcnow(),
        url=f"https://redditbot-discord.web.app/authenticate",
    )


def create_visibility_zero_embed(bot, author, target):
    return discord.Embed(
        title=f":x: {target.name}'s connected reddit account(s) is private.",
        timestamp=datetime.utcnow(),
    )


def create_wrong_channel_type(wantedType, channel):
    return discord.Embed(
        title=f':x: {channel}"s type is not "{str(wantedType)}"',
        timestamp=datetime.utcnow(),
    )


def create_already_connected_embed():
    return discord.Embed(
        title=f":x: You already connected that channel to that subreddit",
        timestamp=datetime.utcnow(),
    )
