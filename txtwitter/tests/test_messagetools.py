from twisted.trial.unittest import TestCase


class TestTweetFunctions(TestCase):
    def setUp(self):
        from txtwitter import messagetools
        self.messagetools = messagetools

    def test_is_tweet(self):
        """
        is_tweet() should return `True` for a tweet message.
        """
        self.assertEqual(True, self.messagetools.is_tweet({
            'id_str': '12345',
            'text': 'This is a tweet.',
            'user': {},
        }))

    def test_is_tweet_nontweet(self):
        """
        is_tweet() should return `False` for a non-tweet message.
        """
        self.assertEqual(False, self.messagetools.is_tweet({
            'friends': [],
        }))

    def test_ensure_tweet(self):
        """
        ensure_tweet() should return the original message for a tweet message.
        """
        msg = {
            'id_str': '12345',
            'text': 'This is a tweet.',
            'user': {},
        }
        self.assertEqual(msg, self.messagetools.ensure_tweet(msg))

    def test_ensure_tweet_nontweet(self):
        """
        ensure_tweet() should rase `ValueError` for a non-tweet message.
        """
        msg = {'friends': []}
        self.assertRaises(ValueError, self.messagetools.ensure_tweet, msg)

    def test_tweet_text(self):
        """
        tweet_text() should return the `text` field of a tweet message.
        """
        msg = {
            'id_str': '12345',
            'text': 'This is a tweet.',
            'user': {},
        }
        self.assertEqual('This is a tweet.', self.messagetools.tweet_text(msg))

    def test_tweet_text_nontweet(self):
        """
        tweet_text() should rase `ValueError` for a non-tweet message.
        """
        msg = {'friends': []}
        self.assertRaises(ValueError, self.messagetools.tweet_text, msg)

    def test_tweet_user_mentions(self):
        """
        tweet_user_mentions() should return the list of users mentioned in the
        tweet message.
        """
        user_mention = {
            'id_str': '123',
            'screen_name': 'fakeuser',
            'name': 'Fake User',
        }
        msg = {
            'entities': {'user_mentions': [user_mention]},
            'id_str': '12345',
            'text': 'This is a tweet mentioning @fakeuser.',
            'user': {},
        }
        self.assertEqual(
            [user_mention], self.messagetools.tweet_user_mentions(msg))

    def test_tweet_user_mentions_no_mentions(self):
        """
        tweet_user_mentions() should return an empty list if no users are
        mentioned in the tweet message.
        """
        msg = {
            'entities': {'user_mentions': []},
            'id_str': '12345',
            'text': 'This is a tweet mentioning @fakeuser.',
            'user': {},
        }
        self.assertEqual([], self.messagetools.tweet_user_mentions(msg))

    def test_tweet_user_mentions_nontweet(self):
        """
        tweet_user_mentions() should rase `ValueError` for a non-tweet message.
        """
        msg = {'friends': []}
        self.assertRaises(
            ValueError, self.messagetools.tweet_user_mentions, msg)

    def test_tweet_in_reply_to_id(self):
        """
        tweet_in_reply_to_id() should return the id of the tweet this tweet
        message is a reply to.
        """
        msg = {
            'id_str': '12345',
            'in_reply_to_status_id_str': '12344',
            'text': '@fakeuser This is a reply.',
            'user': {},
        }
        self.assertEqual('12344', self.messagetools.tweet_in_reply_to_id(msg))

    def test_tweet_in_reply_to_id_nonreply(self):
        """
        tweet_in_reply_to_id() should return `None` if this tweet message is
        not a reply.
        """
        msg = {
            'id_str': '12345',
            'in_reply_to_status_id_str': None,
            'text': '@fakeuser This is a reply.',
            'user': {},
        }
        self.assertEqual(None, self.messagetools.tweet_in_reply_to_id(msg))

    def test_tweet_in_reply_to_id_nontweet(self):
        """
        tweet_in_reply_to_id() should rase `ValueError` for a non-tweet
        message.
        """
        msg = {'friends': []}
        self.assertRaises(
            ValueError, self.messagetools.tweet_in_reply_to_id, msg)

    def test_tweet_is_reply(self):
        """
        tweet_in_reply_to_id() should return `True` if this tweet message is a
        reply.
        """
        msg = {
            'id_str': '12345',
            'in_reply_to_status_id_str': '12344',
            'text': '@fakeuser This is a reply.',
            'user': {},
        }
        self.assertEqual(True, self.messagetools.tweet_is_reply(msg))

    def test_tweet_is_reply_nonreply(self):
        """
        tweet_is_reply() should return `False` if this tweet message is not a
        reply.
        """
        msg = {
            'id_str': '12345',
            'in_reply_to_status_id_str': None,
            'text': '@fakeuser This is a reply.',
            'user': {},
        }
        self.assertEqual(False, self.messagetools.tweet_is_reply(msg))

    def test_tweet_is_reply_nontweet(self):
        """
        tweet_is_reply() should rase `ValueError` for a non-tweet message.
        """
        msg = {'friends': []}
        self.assertRaises(ValueError, self.messagetools.tweet_is_reply, msg)
