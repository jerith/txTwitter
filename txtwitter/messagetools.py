"""
A collection of utilities for working with Twitter API messages.
"""


def is_tweet(message):
    return set(['id_str', 'text', 'user']).issubset(set(message.keys()))


def ensure_tweet(message):
    if not is_tweet(message):
        raise ValueError("Message is not a tweet: %r" % (message,))
    return message


def tweet_text(message):
    return ensure_tweet(message)['text']


def tweet_user_mentions(message):
    return ensure_tweet(message)['entities'].get('user_mentions', [])


def tweet_in_reply_to_id(message):
    return ensure_tweet(message).get('in_reply_to_status_id_str', None)


def tweet_is_reply(message):
    return tweet_in_reply_to_id(message) is not None
