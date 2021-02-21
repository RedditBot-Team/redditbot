import os
import threading

import praw
import firebase_admin
from firebase_admin import firestore, credentials
import queue


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
        self, client_id, client_token, reddit_id, reddit_secret, skip_existing
    ):
        self.client_id = client_id
        self.client_token = client_token
        self.reddit_id = reddit_id
        self.reddit_secret = reddit_secret
        self.skip_existing = skip_existing

        # Setup
        self.reddit = praw.Reddit(
            client_id=self.reddit_id,
            client_secret=self.reddit_secret,
            user_agent="RedditBot streamer",
        )

        self.db = firebase_admin.firestore.client()
        self._callback_done = threading.Event()

        self._listen_to_reddit_process = None
        self._listen_to_reddit_process_quit = False

        self.streams = []
        self.watched_subreddits = []

    def _listen_to_reddit(self):
        self._listen_to_reddit_process_quit = False

        print("Streaming!")
        for submission in self.reddit.subreddit(
            "+".join(self.watched_subreddits)
        ).stream.submissions(skip_existing=self.skip_existing):
            # Quit if we have too.
            if self._listen_to_reddit_process_quit:
                print("Quitting~!")
                return

            print(submission.subreddit)

    def listen(self):
        callback_done = threading.Event()
        doc_changes = queue.Queue()

        def on_snapshot(
            doc_snapshot: dict[firestore.firestore.DocumentSnapshot], changes, read_time
        ):
            self.streams = []
            for doc in doc_snapshot:
                doc_dict = doc.to_dict()
                self.streams.append(
                    WebhookObject(
                        doc_dict["subreddit"],
                        doc_dict["channel_id"],
                        doc_dict["guild_id"],
                        doc.id,
                        doc_dict["token"],
                    )
                )

                if doc_dict["subreddit"] not in self.watched_subreddits:
                    self.watched_subreddits.append(doc_dict["subreddit"])

            if self._listen_to_reddit_process is not None:
                self._listen_to_reddit_process_quit = True

            self._listen_to_reddit_process = threading.Thread(
                target=self._listen_to_reddit,
            )
            self._listen_to_reddit_process.start()

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
        skip_existing=os.environ["SKIP_EXISTING"],
    )
    streamer.listen()
