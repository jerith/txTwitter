import json
from urllib import urlencode

from twisted.protocols.basic import LineOnlyReceiver
from twisted.trial.unittest import TestCase


def from_fake_twitter(name):
    @property
    def prop(self):
        from txtwitter.tests import fake_twitter
        return getattr(fake_twitter, name)
    return prop


class TestFakeTweet(TestCase):
    _FakeTwitterData = from_fake_twitter('FakeTwitterData')
    _FakeTweet = from_fake_twitter('FakeTweet')

    def test__get_user_mentions_none(self):
        twitter = self._FakeTwitterData()
        tweet = self._FakeTweet('1', 'hello', '1')
        self.assertEqual([], tweet._get_user_mentions(twitter))

    def test__get_user_mentions_not_user(self):
        twitter = self._FakeTwitterData()
        tweet = self._FakeTweet('1', 'hello @notuser', '1')
        self.assertEqual([], tweet._get_user_mentions(twitter))

    def test__get_user_mentions_one_user(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        tweet = self._FakeTweet('1', 'hello @fakeuser', '1')
        self.assertEqual(tweet._get_user_mentions(twitter), [{
            'id_str': '1',
            'id': 1,
            'indices': [6, 15],
            'screen_name': 'fakeuser',
            'name': 'Fake User',
        }])

    def test__get_user_mentions_two_users(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')
        tweet = self._FakeTweet('1', 'hello @fakeuser @fakeuser2', '1')
        self.assertEqual(tweet._get_user_mentions(twitter), [{
            'id_str': '1',
            'id': 1,
            'indices': [6, 15],
            'screen_name': 'fakeuser',
            'name': 'Fake User',
        }, {
            'id_str': '2',
            'id': 2,
            'indices': [16, 26],
            'screen_name': 'fakeuser2',
            'name': 'Fake User',
        }])

    def test__get_user_mentions_one_user_twice(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        tweet = self._FakeTweet('1', 'hello @fakeuser @fakeuser', '1')
        self.assertEqual(tweet._get_user_mentions(twitter), [{
            'id_str': '1',
            'id': 1,
            'indices': [6, 15],
            'screen_name': 'fakeuser',
            'name': 'Fake User',
        }, {
            'id_str': '1',
            'id': 1,
            'indices': [16, 25],
            'screen_name': 'fakeuser',
            'name': 'Fake User',
        }])

    def test__get_reply_to_status_details_nonreply(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        tweet = self._FakeTweet('1', 'hello', '1')
        self.assertEqual(tweet._get_reply_to_status_details(twitter), {})

    def test__get_reply_to_status_details_reply(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User 2')

        twitter.add_tweet('1', 'hello', '1')
        tweet = twitter.add_tweet('2', 'goodbye', '2', reply_to='1')

        self.assertEqual(tweet._get_reply_to_status_details(twitter), {
            'in_reply_to_status_id': 1,
            'in_reply_to_status_id_str': '1'
        })

    def test__get_reply_to_user_details_nonmention(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        tweet = self._FakeTweet('1', 'hello', '1')
        self.assertEqual(tweet._get_reply_to_user_details(twitter), {})

    def test__get_reply_to_user_details_nonreply(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User 2')

        tweet = self._FakeTweet('1', '@fakeuser2 hello', '1')

        self.assertEqual(tweet._get_reply_to_user_details(twitter), {
            'in_reply_to_screen_name': 'fakeuser2',
            'in_reply_to_user_id': 2,
            'in_reply_to_user_id_str': '2'
        })

    def test__get_reply_to_user_details_reply(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User 2')

        twitter.add_tweet('1', 'hello', '1')
        tweet = twitter.add_tweet('2', 'goodbye', '2', reply_to='1')

        self.assertEqual(tweet._get_reply_to_user_details(twitter), {
            'in_reply_to_screen_name': 'fakeuser',
            'in_reply_to_user_id': 1,
            'in_reply_to_user_id_str': '1'
        })


class TestFakeTwitter(TestCase):
    _FakeTwitter = from_fake_twitter('FakeTwitter')
    _FakeTwitterClient = from_fake_twitter('FakeTwitterClient')

    def test_get_client(self):
        twitter = self._FakeTwitter()
        client = twitter.get_client()
        self.assertEqual(self._FakeTwitterClient, type(client))
        self.assertEqual(client._fake_twitter_user_id_str, None)

    def test_get_client_user(self):
        twitter = self._FakeTwitter()
        client = twitter.get_client('42')
        self.assertEqual(self._FakeTwitterClient, type(client))
        self.assertEqual(client._fake_twitter_user_id_str, '42')


class TestFakeTwitterClient(TestCase):
    _FakeTwitter = from_fake_twitter('FakeTwitter')

    def _FakeTwitterClient(self, user_id_str=None, fake_twitter=None):
        if fake_twitter is None:
            fake_twitter = self._FakeTwitter()
        return fake_twitter.get_client(user_id_str)

    def test_call_statuses_show_404(self):
        client = self._FakeTwitterClient()
        failure = self.failureResultOf(client.statuses_show('1'))
        self.assertEqual(failure.value.args[0], 404)

    def test_call_statuses_show(self):
        twitter = self._FakeTwitter()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_tweet('1', 'hello', '1')
        client = self._FakeTwitterClient(fake_twitter=twitter)
        tweet = self.successResultOf(client.statuses_show('1'))
        self.assertEqual(tweet['text'], 'hello')


class FakeTwitterStreamProtocol(LineOnlyReceiver):
    def __init__(self, delegate):
        self.delegate = delegate

    def lineReceived(self, line):
        if line:
            self.delegate(json.loads(line))


class TestFakeTwitterAPI(TestCase):
    _FakeTwitter = from_fake_twitter('FakeTwitter')
    _FakeTwitterData = from_fake_twitter('FakeTwitterData')
    _FakeTwitterAPI = from_fake_twitter('FakeTwitterAPI')

    def _build_uri(self, base, path, params=None):
        uri = '%s%s' % (base, path)
        if params:
            uri += '?' + urlencode(params)
        return uri

    def _api_uri(self, path, params=None):
        from txtwitter.twitter import TWITTER_API_URL
        return self._build_uri(TWITTER_API_URL, path, params)

    def assert_method_uri(self, method_name, uri):
        method = self._FakeTwitter().get_api_method(None, uri)
        self.assertEqual(method_name, method.__name__)

    def assert_api_method_uri(self, method_name, uri_path):
        self.assert_method_uri(method_name, self._api_uri(uri_path))

    # Timelines

    def test_dispatch_statuses_mentions_timeline(self):
        self.assert_api_method_uri(
            'statuses_mentions_timeline', 'statuses/mentions_timeline.json')

    def test_statuses_mentions_timeline(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')
        twitter.add_tweet('1', 'hello', '1')
        twitter.add_tweet('2', 'hello', '2')
        mention1 = twitter.add_tweet('3', 'hello @fakeuser', '2')
        mention2 = twitter.add_tweet('4', 'hello again @fakeuser', '2')

        api = self._FakeTwitterAPI(twitter, '1')
        mentions = api.statuses_mentions_timeline()
        self.assertEqual(mentions, twitter.to_dicts(mention2, mention1))

    # TODO: More tests for fake statuses_mentions_timeline()

    def test_dispatch_statuses_user_timeline(self):
        self.assert_api_method_uri(
            'statuses_user_timeline', 'statuses/user_timeline.json')

    def test_statuses_user_timeline(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')
        twitter.add_tweet('1', 'hello', '1')
        tweet1 = twitter.add_tweet('2', 'hello', '2')
        twitter.add_tweet('3', 'hello @fakeuser2', '1')
        tweet2 = twitter.add_tweet('4', 'hello @fakeuser', '2')

        api = self._FakeTwitterAPI(twitter, '1')
        mentions = api.statuses_user_timeline('2')
        self.assertEqual(mentions, twitter.to_dicts(tweet2, tweet1))

    # TODO: More tests for fake statuses_user_timeline()

    # TODO: Tests for fake statuses_home_timeline()
    # TODO: Tests for fake statuses_retweets_of_me()

    # Tweets

    # TODO: Tests for fake statuses_retweets()

    def test_dispatch_statuses_show(self):
        self.assert_api_method_uri('statuses_show', 'statuses/show.json')

    def test_statuses_show(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_tweet('1', 'hello', '1')

        api = self._FakeTwitterAPI(twitter, None)
        tweet = api.statuses_show('1')
        self.assertEqual('hello', tweet['text'])
        self.assertEqual('fakeuser', tweet['user']['screen_name'])

    # TODO: More tests for fake statuses_show()

    def test_dispatch_statuses_destroy(self):
        self.assert_api_method_uri('statuses_destroy', 'statuses/destroy.json')

    def test_statuses_destroy(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_tweet('1', 'hello', '1')

        api = self._FakeTwitterAPI(twitter, '1')
        tweet = api.statuses_destroy('1')
        self.assertEqual('hello', tweet['text'])
        self.assertEqual('fakeuser', tweet['user']['screen_name'])
        self.assertEqual(twitter.tweets, {})

    # TODO: More tests for fake statuses_destroy()

    def test_dispatch_statuses_update(self):
        self.assert_api_method_uri('statuses_update', 'statuses/update.json')

    def test_statuses_update(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')

        api = self._FakeTwitterAPI(twitter, '1')
        tweet = api.statuses_update('hello')
        self.assertEqual('hello', tweet['text'])
        self.assertEqual('fakeuser', tweet['user']['screen_name'])
        self.assertEqual(twitter.tweets.keys(), [tweet['id_str']])

    # TODO: More tests for fake statuses_update()

    # TODO: Tests for fake statuses_retweet()
    # TODO: Tests for fake statuses_update_with_media()
    # TODO: Tests for fake statuses_oembed()
    # TODO: Tests for fake statuses_retweeters_ids()

    # Search

    # TODO: Tests for fake search_tweets()

    # Streaming

    def _process_stream_response(self, resp, delegate):
        protocol = FakeTwitterStreamProtocol(delegate)
        resp.deliverBody(protocol)

    def test_dispatch_stream_filter(self):
        from txtwitter.twitter import TWITTER_STREAM_URL
        uri = self._build_uri(TWITTER_STREAM_URL, 'statuses/filter.json')
        self.assert_method_uri('stream_filter', uri)

    def test_stream_filter_track(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')

        api = self._FakeTwitterAPI(twitter, None)
        messages = []
        resp = api.stream_filter(track='foo,bar')
        self._process_stream_response(resp, messages.append)
        self.assertEqual(messages, [])

        twitter.new_tweet('hello', '1')
        twitter.new_tweet('hello', '2')
        self.assertEqual(messages, [])

        tweet1 = twitter.new_tweet('foo', '1')
        tweet2 = twitter.new_tweet('bar', '2')
        self.assertEqual(messages, twitter.to_dicts(tweet1, tweet2))

        resp.finished()
        self.assertEqual(twitter.tweet_streams, {})

    # TODO: More tests for fake stream_filter()

    # TODO: Tests for fake stream_sample()
    # TODO: Tests for fake stream_firehose()

    def test_dispatch_userstream_user(self):
        from txtwitter.twitter import TWITTER_USERSTREAM_URL
        uri = self._build_uri(TWITTER_USERSTREAM_URL, 'user.json')
        self.assert_method_uri('userstream_user', uri)

    def test_userstream_user_with_user(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')

        api = self._FakeTwitterAPI(twitter, '1')
        messages = []
        resp = api.userstream_user(stringify_friend_ids='true', with_='user')
        self._process_stream_response(resp, messages.append)
        self.assertEqual(messages, [{'friends_str': []}])
        messages.pop(0)

        tweet1 = twitter.new_tweet('hello', '1')
        twitter.new_tweet('hello', '2')
        self.assertEqual(messages, twitter.to_dicts(tweet1))

        twitter.new_tweet('@fakeuser2', '2')
        tweet2 = twitter.new_tweet('@fakeuser', '2')
        self.assertEqual(messages, twitter.to_dicts(tweet1, tweet2))

        resp.finished()
        self.assertEqual(twitter.tweet_streams, {})

        # TODO: Replies

    # TODO: More tests for fake userstream_user()

    # Direct Messages

    # TODO: Tests for fake direct_messages()
    # TODO: Tests for fake direct_messages_sent()
    # TODO: Tests for fake direct_messages_show()
    # TODO: Tests for fake direct_messages_destroy()
    # TODO: Tests for fake direct_messages_new()

    # Friends & Followers

    # TODO: Tests for fake friendships_no_retweets_ids()
    # TODO: Tests for fake friends_ids()
    # TODO: Tests for fake followers_ids()
    # TODO: Tests for fake friendships_lookup()
    # TODO: Tests for fake friendships_incoming()
    # TODO: Tests for fake friendships_outgoing()
    # TODO: Tests for fake friendships_create()
    # TODO: Tests for fake friendships_destroy()
    # TODO: Tests for fake friendships_update()
    # TODO: Tests for fake friendships_show()
    # TODO: Tests for fake friends_list()
    # TODO: Tests for fake followers_list()

    # Users

    # TODO: Tests for fake account_settings()
    # TODO: Tests for fake account_verify_credentials()
    # TODO: Tests for fake account_settings()
    # TODO: Tests for fake account_update_delivery_device()
    # TODO: Tests for fake account_update_profile()
    # TODO: Tests for fake account_update_profile_background_image()
    # TODO: Tests for fake account_update_profile_colors()
    # TODO: Tests for fake account_update_profile_image()
    # TODO: Tests for fake blocks_list()
    # TODO: Tests for fake blocks_ids()
    # TODO: Tests for fake blocks_create()
    # TODO: Tests for fake blocks_destroy()
    # TODO: Tests for fake users_lookup()
    # TODO: Tests for fake users_show()
    # TODO: Tests for fake users_search()
    # TODO: Tests for fake users_contributees()
    # TODO: Tests for fake users_contributors()
    # TODO: Tests for fake account_remove_profile_banner()
    # TODO: Tests for fake account_update_profile_banner()
    # TODO: Tests for fake users/profile_banner()

    # Suggested Users

    # TODO: Tests for fake users_suggestions()
    # TODO: Tests for fake users_suggestions()
    # TODO: Tests for fake users_suggestions_members()

    # Favorites

    # TODO: Tests for fake favorites_list()
    # TODO: Tests for fake favorites_destroy()
    # TODO: Tests for fake favorites_create()

    # Lists

    # TODO: Tests for fake lists_list()
    # TODO: Tests for fake lists_statuses()
    # TODO: Tests for fake lists_members_destroy()
    # TODO: Tests for fake lists_memberships()
    # TODO: Tests for fake lists_subscribers()
    # TODO: Tests for fake lists_subscribers/create()
    # TODO: Tests for fake lists_subscribers/show()
    # TODO: Tests for fake lists_subscribers/destroy()
    # TODO: Tests for fake lists_members_create_all()
    # TODO: Tests for fake lists_members_show()
    # TODO: Tests for fake lists_members()
    # TODO: Tests for fake lists_members_create()
    # TODO: Tests for fake lists_destroy()
    # TODO: Tests for fake lists_update()
    # TODO: Tests for fake lists_create()
    # TODO: Tests for fake lists_show()
    # TODO: Tests for fake lists_subscriptions()
    # TODO: Tests for fake lists_members_destroy_all()
    # TODO: Tests for fake lists_ownerships()

    # Saved Searches

    # TODO: Tests for fake saved_searches_list()
    # TODO: Tests for fake saved_searches_show()
    # TODO: Tests for fake saved_searches_create()
    # TODO: Tests for fake saved_searches_destroy()

    # Places & Geo

    # TODO: Tests for fake geo_id()
    # TODO: Tests for fake geo_reverse_geocode()
    # TODO: Tests for fake geo_search()
    # TODO: Tests for fake geo_similar_places()
    # TODO: Tests for fake geo_place()

    # Trends

    # TODO: Tests for fake trends_place()
    # TODO: Tests for fake trends_available()
    # TODO: Tests for fake trends_closest()

    # Spam Reporting

    # TODO: Tests for fake users_report_spam()

    # OAuth

    # TODO: Decide whether any of these APIs should be implemented.

    # Help

    # TODO: Tests for fake help_configuration()
    # TODO: Tests for fake help_languages()
    # TODO: Tests for fake help_privacy()
    # TODO: Tests for fake help_tos()
    # TODO: Tests for fake application_rate_limit_status()
