# NSFW content, and where its allowed

Rules for when RedditBot allows nsfw content in a channel.

If something like a [**/user**](../get-info/user.md) or a [**/subreddit**](../get-info/subreddit.md) ****command is run, it does a few checks. If the content is marked [over\_18](https://praw.readthedocs.io/en/latest/search.html?q=over_18) by reddit **and** the channel **isn't** marked nsfw on discord, it fails. If the channel _is_ marked nsfw on discord, it succeeds. 

![Example checks fail message](../.gitbook/assets/image%20%284%29.png)

{% hint style="info" %}
This is all to follow the discord TOS and other services like [top.gg](https://top.gg/)
{% endhint %}



