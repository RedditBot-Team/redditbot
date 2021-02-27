import json
import os
import queue
import threading
import uuid

import firebase_admin
import praw
import requests
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
