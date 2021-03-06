from datetime import datetime
import json
import os
import queue
import random
import threading
import time
import uuid

import discord
import firebase_admin
import praw
import requests
import schedule
from firebase_admin import firestore

import util


class WebhookObject:
    def __init__(self, subreddit, channel_id, guild_id, id, token):
        self.channel_id = channel_id
        self.guild_id = guild_id
        self.id = id
        self.token = token
        self.subreddit = subreddit

    @property
    def url(self):
        return f"https://discord.com/api/webhooks/{self.id}/{self.token}"


def _summary():
    db = firestore.client()

    summary_collection = db.collection("summaries")
    reddit = praw.Reddit(
        client_id=os.environ["REDDIT_ID"],
        client_secret=os.environ["REDDIT_SECRET"],
        user_agent="RedditBot summary streamer",
    )

    user = requests.request(
        "GET",
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bot {os.environ['REDDITBOT_TOKEN']}"},
        data={},
    ).json()

    subreddits = {}
    for webhook in summary_collection.get():
        doc_dict = webhook.to_dict()

        sub = reddit.subreddit(webhook.to_dict()["subreddit"])
        if sub.display_name.lower() not in subreddits:
            subreddits[sub.display_name.lower()] = []
        subreddits[sub.display_name.lower()].append(
            WebhookObject(
                doc_dict["subreddit"],
                doc_dict["channel_id"],
                doc_dict["guild_id"],
                webhook.id,
                doc_dict["token"],
            )
        )

    for subreddit in subreddits:
        sub = reddit.subreddit(subreddit)
        description = ""
        nsfw_description = ""
        for submission in sub.top(limit=5, time_filter="day"):
            # Huge strings!
            submission_string = f"**[{submission.title}](https://reddit.com/r/{subreddit}/comments/{submission.id})**\n{submission.score} upvotes • {submission.num_comments} comments • Posted by [{submission.author.name}](https://reddit.com/u/{submission.author.name})\n\n"

            nsfw_description += submission_string
            if submission.over_18:
                description += "*nsfw content blocked*\n\n"
            else:
                description += submission_string

        for webhook in subreddits[subreddit]:
            # Send the embeds.

            channel_info_response = requests.request(
                "GET",
                f"https://discord.com/api/channels/{webhook.channel_id}",
                headers={"Authorization": f"Bot {os.environ['REDDITBOT_TOKEN']}"},
                data={},
            ).json()

            embed = None
            try:
                if channel_info_response["nsfw"]:
                    embed = discord.Embed(
                        title=f"{sub.display_name}'s top posts today:",
                        timestamp=datetime.utcnow(),
                        description=nsfw_description,
                        url=f"https://reddit.com/r/{sub.display_name}/top/?t=day",
                    )
                else:
                    embed = discord.Embed(
                        title=f"{sub.display_name}'s top posts today:",
                        timestamp=datetime.utcnow(),
                        description=description,
                        url=f"https://reddit.com/r/{sub.display_name}",
                    )
            except KeyError:
                # Delete if this channel doesnt exist
                db.document(f"summaries/{webhook.id}").delete()
                continue

            embed.set_author(
                name=f"{user['username']}",
                icon_url=f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}",
                url=f"https://redditbot.bwac.dev/",
            )
            embed.set_thumbnail(url=sub.icon_img)

            payload = {
                "embeds": [embed.to_dict()],
                "avatar_url": f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}",
                "username": f"{user['username']} {sub.display_name} Subscription",
            }

            response = requests.request(
                "POST",
                webhook.url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
            )

            if response.status_code == 404:
                # Delete if this webhook doesnt exist
                db.document(f"summaries/{webhook.id}").delete()
                continue


def schedule_summary():
    schedule.every().day.at("00:00").do(_summary)
    while True:
        schedule.run_pending()
        time.sleep(1)


class Streamer:
    def __init__(self, client_id, client_token, reddit_id, reddit_secret):
        self.client_id = client_id
        self.client_token = client_token
        self.reddit_id = reddit_id
        self.reddit_secret = reddit_secret

        # Setup
        self.reddit = praw.Reddit(
            client_id=self.reddit_id,
            client_secret=self.reddit_secret,
            user_agent="RedditBot streamer",
        )

        self.db = firebase_admin.firestore.client()
        self._callback_done = threading.Event()

        self._listen_to_reddit_thread = False
        self._threads_to_kill = []

        self.user = requests.request(
            "GET",
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bot {os.environ['REDDITBOT_TOKEN']}"},
            data={},
        ).json()

        self.streams = {}
        self.watched_subreddits = []

    def _listen_to_reddit(self):
        # Combine all the subreddits into a string that reddit likes.
        for submission in self.reddit.subreddit(
            "+".join(list(self.streams.keys()))
        ).stream.submissions(skip_existing=True):
            # Quit if we have too.
            if threading.current_thread().name in self._threads_to_kill:
                self._threads_to_kill.remove(threading.current_thread().name)
                return

            # Create a submission embed
            embed = util.create_submission_embed(submission)

            # Collect all the webhooks we have to send too.
            for webhook_object in self.streams[
                submission.subreddit.display_name.lower()
            ]:
                # Make payloads for the webhook request
                payload = {
                    "embeds": [embed.to_dict()],
                    "avatar_url": f"https://cdn.discordapp.com/avatars/{self.user['id']}/{self.user['avatar']}",
                    "username": f"{self.user['username']} {submission.subreddit.display_name} Subscription",
                }

                # NSFW checks.
                channel_info_response = requests.request(
                    "GET",
                    f"https://discord.com/api/channels/{webhook_object.channel_id}",
                    headers={"Content-Type": "application/json"},
                    data={},
                )

                if "nsfw" not in channel_info_response.json():
                    # Change the embed
                    if submission.over_18:
                        payload["embeds"] = [util.create_nsfw_content_embed().to_dict()]
                    elif submission.subreddit.over18:
                        payload["embeds"] = [util.create_nsfw_content_embed().to_dict()]

                if random.randint(0, 9) == 0:
                    payload["embeds"].append(
                        discord.Embed(
                            title=f"Enjoying? It would be great if you voted!",
                            url="https://redditbot.bwac.dev/vote",
                            timestamp=datetime.utcnow(),
                        ).to_dict()
                    )

                # Send the embeds.
                response = requests.request(
                    "POST",
                    webhook_object.url,
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(payload),
                )

                if response.status_code == 404:
                    # Delete if this webhook doesnt exist
                    self.db.document(f"webhooks/{webhook_object.id}").delete()
                    return

    def listen(self):
        callback_done = threading.Event()
        doc_changes = queue.Queue()

        def on_snapshot(
            doc_snapshot: dict[firestore.firestore.DocumentSnapshot], changes, read_time
        ):
            self.streams = {}
            for doc in doc_snapshot:
                doc_dict = doc.to_dict()

                sub = self.reddit.subreddit(doc_dict["subreddit"])

                # Make everything lowercase so we have no key errors.
                if not sub.display_name.lower() in self.streams:
                    # Make a new key for every new subreddit detected.
                    self.streams[sub.display_name.lower()] = []

                # Create a webhook object class and add it to the streams dict under the webhook's subreddit
                self.streams[sub.display_name.lower()].append(
                    WebhookObject(
                        doc_dict["subreddit"],
                        doc_dict["channel_id"],
                        doc_dict["guild_id"],
                        doc.id,
                        doc_dict["token"],
                    )
                )

            # If this is isn't the first time we are getting a snapshot.
            if self._listen_to_reddit_thread:
                # Tell the old thread to kill itself.
                self._threads_to_kill.append(self._listen_to_reddit_thread.name)

            # Create a new reddit watching thread
            self._listen_to_reddit_thread = threading.Thread(
                target=self._listen_to_reddit, name=str(uuid.uuid4())
            )
            # Start it.
            self._listen_to_reddit_thread.start()

            # What this does? I have no idea. It just works if its there.
            callback_done.set()

        doc_ref = self.db.collection("webhooks")

        # I have no idea what this does. It just works. OK.
        doc_watch = doc_ref.on_snapshot(on_snapshot)
        while True:
            try:
                changes = doc_changes.get(timeout=1)
            except queue.Empty:
                changes = None
