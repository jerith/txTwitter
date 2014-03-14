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


def tweet_id(message):
    return ensure_tweet(message)['id_str']


def tweet_in_reply_to_id(message):
    return ensure_tweet(message).get('in_reply_to_status_id_str', None)


def tweet_in_reply_to_screen_name(message):
    return ensure_tweet(message).get('in_reply_to_screen_name', None)


def tweet_is_reply(message):
    return tweet_in_reply_to_id(message) is not None


def tweet_user(message):
    return ensure_tweet(message)['user']


def is_dm(message):
    fields = ['id_str', 'text', 'sender', 'recipient']
    return set(fields).issubset(set(message.keys()))


def ensure_dm(message):
    if not is_dm(message):
        raise ValueError("Message is not a direct message: %r" % (message,))
    return message


def dm_text(message):
    return ensure_dm(message)['text']


def dm_user_mentions(message):
    return ensure_dm(message)['entities'].get('user_mentions', [])


def dm_id(message):
    return ensure_dm(message)['id_str']


def dm_sender(message):
    return ensure_dm(message)['sender']


def dm_recipient(message):
    return ensure_dm(message)['recipient']


def is_user(user):
    return set(['id_str', 'screen_name']).issubset(set(user.keys()))


def ensure_user(user):
    if not is_user(user):
        raise ValueError("Data is not user data: %r" % (user,))
    return user


def user_id(user):
    return ensure_user(user).get('id_str', None)


def user_screen_name(user):
    return ensure_user(user).get('screen_name', None)
