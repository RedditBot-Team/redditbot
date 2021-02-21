import json
import os
import threading
import praw
import firebase_admin
import requests
from firebase_admin import firestore, credentials
import queue
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
    def __init__(
            self, client_id, client_token, reddit_id, reddit_secret
    ):
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
        for submission in self.reddit.subreddit(
                "+".join(list(self.streams.keys()))
        ).stream.submissions(skip_existing=True):
            # Quit if we have too.
            if threading.current_thread().name in self._threads_to_kill:
                return

            embed = util.create_submission_embed(submission)

            payload = {
                "embeds": [embed.to_dict()],
                "avatar_url": f"https://cdn.discordapp.com/avatars/{self.user['id']}/{self.user['avatar']}",
                "username": f"{self.user['username']} {submission.subreddit.display_name} Subscription",
            }

            for webhook_object in self.streams[submission.subreddit.display_name.lower()]:
                channel_info_response = requests.request(
                    "GET",
                    f"https://discord.com/api/channels/{webhook_object.channel_id}",
                    headers={"Content-Type": "application/json"},
                    data={},
                )

                if "nsfw" not in channel_info_response.json():
                    if submission.over_18:
                        payload["embeds"] = [util.create_nsfw_content_embed().to_dict()]
                    elif submission.subreddit.over18:
                        payload["embeds"] = [util.create_nsfw_content_embed().to_dict()]

                response = requests.request(
                    "POST",
                    f"https://discord.com/api/webhooks/{webhook_object.id}/{webhook_object.token}",
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(payload),
                )

                if response.status_code == 404:
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

                if not sub.display_name.lower() in self.streams:
                    self.streams[sub.display_name.lower()] = []

                self.streams[sub.display_name.lower()].append(
                    WebhookObject(
                        doc_dict["subreddit"],
                        doc_dict["channel_id"],
                        doc_dict["guild_id"],
                        doc.id,
                        doc_dict["token"],
                    )
                )

            if self._listen_to_reddit_thread:
                self._threads_to_kill.append(self._listen_to_reddit_thread.name)

            self._listen_to_reddit_thread = threading.Thread(
                target=self._listen_to_reddit,
            )
            self._listen_to_reddit_thread.start()

            callback_done.set()

        doc_ref = self.db.collection("webhooks")

        doc_watch = doc_ref.on_snapshot(on_snapshot)
        while True:
            try:
                changes = doc_changes.get(timeout=1)
            except queue.Empty:
                changes = None


if __name__ == "__main__":
    firebase_admin.initialize_app(
        credentials.Certificate("redditbot-discord-firebase-adminsdk.json")
    )

    streamer = Streamer(
        client_id=437439562386505730,
        client_token=os.environ["REDDITBOT_TOKEN"],
        reddit_id=os.environ["REDDIT_ID"],
        reddit_secret=os.environ["REDDIT_SECRET"],
    )
    streamer.listen()
