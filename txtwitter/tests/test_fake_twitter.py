import json
from datetime import datetime
from urllib import urlencode

from twisted.internet.defer import inlineCallbacks
from twisted.protocols.basic import LineOnlyReceiver
from twisted.trial.unittest import TestCase


def from_fake_twitter(name):
    @property
    def prop(self):
        from txtwitter.tests import fake_twitter
        return getattr(fake_twitter, name)
    return prop


class TestFakeTwitterHelpers(TestCase):
    _extract_user_mentions = from_fake_twitter('extract_user_mentions')
    _FakeTwitterData = from_fake_twitter('FakeTwitterData')

    def test_extract_user_mentions_none(self):
        twitter = self._FakeTwitterData()
        text = 'hello'
        self.assertEqual([], self._extract_user_mentions(twitter, text))

    def test_extract_user_mentions_not_user(self):
        twitter = self._FakeTwitterData()
        text = 'hello @notuser'
        self.assertEqual([], self._extract_user_mentions(twitter, text))

    def test_extract_user_mentions_one_user(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        text = 'hello @fakeuser'
        self.assertEqual(self._extract_user_mentions(twitter, text), [{
            'id_str': '1',
            'id': 1,
            'indices': [6, 15],
            'screen_name': 'fakeuser',
            'name': 'Fake User',
        }])

    def test_extract_user_mentions_two_users(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')
        text = 'hello @fakeuser @fakeuser2'
        self.assertEqual(self._extract_user_mentions(twitter, text), [{
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

    def test_extract_user_mentions_one_user_twice(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        text = 'hello @fakeuser @fakeuser'
        self.assertEqual(self._extract_user_mentions(twitter, text), [{
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


class TestFakeStream(TestCase):
    _FakeStream = from_fake_twitter('FakeStream')

    def test_accepts(self):
        stream = self._FakeStream()
        stream.add_message_type('foo', lambda data: data.get('bar') == 'baz')
        self.assertTrue(stream.accepts('foo', {'bar': 'baz'}))
        self.assertFalse(stream.accepts('corge', {'grault': 'garply'}))

    def test_accepts_multiple_message_types(self):
        stream = self._FakeStream()
        stream.add_message_type('foo', lambda data: data.get('bar') == 'baz')
        stream.add_message_type('ham', lambda data: data.get('eggs') == 'spam')
        self.assertTrue(stream.accepts('foo', {'bar': 'baz'}))
        self.assertTrue(stream.accepts('ham', {'eggs': 'spam'}))
        self.assertFalse(stream.accepts('ham', {'bar': 'baz'}))
        self.assertFalse(stream.accepts('foo', {'eggs': 'spam'}))

    def test_accepts_data_mismatch(self):
        stream = self._FakeStream()
        stream.add_message_type('foo', lambda data: data.get('bar') == 'baz')
        self.assertFalse(stream.accepts('foo', {'grault': 'garply'}))

    def test_accepts_message_type_mismatch(self):
        stream = self._FakeStream()
        stream.add_message_type('foo', lambda data: data.get('bar') == 'baz')
        self.assertFalse(stream.accepts('corge', {'bar': 'baz'}))

    def test_deliver(self):
        stream = self._FakeStream()

        messages = []
        protocol = FakeTwitterStreamProtocol(messages.append)
        stream.resp.deliverBody(protocol)

        stream.deliver({'foo': 'bar'})
        stream.deliver({'baz': 'qux'})

        self.assertEqual(messages, [
            {'foo': 'bar'},
            {'baz': 'qux'}
        ])


class TestFakeTweet(TestCase):
    _FakeTwitterData = from_fake_twitter('FakeTwitterData')
    _FakeTweet = from_fake_twitter('FakeTweet')
    _now = datetime(2014, 3, 11, 10, 48, 22, 687699)

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

    def test_to_dict(self):
        twitter = self._FakeTwitterData()
        twitter.add_user(
            '1', 'fakeuser', 'Fake User', created_at=self._now)
        twitter.add_user(
            '2', 'fakeuser2', 'Fake User 2', created_at=self._now)
        tweet = twitter.add_tweet(
            '1', 'hello @fakeuser2', '1', created_at=self._now)

        self.assertEqual(tweet.to_dict(twitter), {
            'created_at': '2014-03-11 10:48:22.687699',
            'entities': {
                'user_mentions': [{
                    'id': 2,
                    'id_str': '2',
                    'indices': [6, 16],
                    'name': 'Fake User 2',
                    'screen_name': 'fakeuser2'
                }]
            },
            'favorite_count': 0,
            'favorited': False,
            'filter_level': 'medium',
            'id': 1,
            'id_str': '1',
            'retweet_count': 0,
            'retweeted': False,
            'source': 'web',
            'text': 'hello @fakeuser2',
            'user': {
                'created_at': '2014-03-11 10:48:22.687699',
                'id': 1,
                'id_str': '1',
                'name': 'Fake User',
                'screen_name': 'fakeuser'
            }
        })

    def test_to_dict_trim_user(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        tweet = twitter.add_tweet('1', 'hello', '1')
        tweet_dict = tweet.to_dict(twitter, trim_user=True)
        self.assertEqual(tweet_dict['user'], {
            'id_str': '1',
            'id': 1
        })

    def test_to_dict_not_include_entities(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        tweet = twitter.add_tweet('1', 'hello', '1')
        tweet_dict = tweet.to_dict(twitter, include_entities=False)
        self.assertTrue('entities' not in tweet_dict)


class TestFakeDM(TestCase):
    _FakeTwitterData = from_fake_twitter('FakeTwitterData')
    _FakeDM = from_fake_twitter('FakeDM')
    _now = datetime(2014, 3, 11, 10, 48, 22, 687699)

    def test__get_sender_details(self):
        twitter = self._FakeTwitterData()
        twitter.add_user(
            '1', 'fakeuser', 'Fake User', created_at=self._now)
        twitter.add_user(
            '2', 'fakeuser2', 'Fake User 2', created_at=self._now)
        dm = twitter.add_dm(
            '1', 'hello', '1', '2', created_at=self._now)

        self.assertEqual(dm._get_sender_details(twitter), {
            'sender': {
                'created_at': '2014-03-11 10:48:22.687699',
                'id': 1,
                'id_str': '1',
                'name': 'Fake User',
                'screen_name': 'fakeuser'
            },
            'sender_id': 1,
            'sender_id_str': '1',
            'sender_screen_name': 'fakeuser'
        })

    def test__get_recipient_details(self):
        twitter = self._FakeTwitterData()
        twitter.add_user(
            '1', 'fakeuser', 'Fake User', created_at=self._now)
        twitter.add_user(
            '2', 'fakeuser2', 'Fake User 2', created_at=self._now)
        dm = twitter.add_dm(
            '1', 'hello', '1', '2', created_at=self._now)

        self.assertEqual(dm._get_recipient_details(twitter), {
            'recipient': {
                'created_at': '2014-03-11 10:48:22.687699',
                'id': 2,
                'id_str': '2',
                'name': 'Fake User 2',
                'screen_name': 'fakeuser2'
            },
            'recipient_id': 2,
            'recipient_id_str': '2',
            'recipient_screen_name': 'fakeuser2'
        })

    def test_to_dict(self):
        twitter = self._FakeTwitterData()
        twitter.add_user(
            '1', 'fakeuser', 'Fake User', created_at=self._now)
        twitter.add_user(
            '2', 'fakeuser2', 'Fake User 2', created_at=self._now)
        dm = twitter.add_dm(
            '1', 'hello @fakeuser2', '1', '2', created_at=self._now)

        self.assertEqual(dm.to_dict(twitter), {
            'created_at': '2014-03-11 10:48:22.687699',
            'id': 1,
            'id_str': '1',
            'text': 'hello @fakeuser2',
            'sender': {
                'created_at': '2014-03-11 10:48:22.687699',
                'id': 1,
                'id_str': '1',
                'name': 'Fake User',
                'screen_name': 'fakeuser'
            },
            'sender_id': 1,
            'sender_id_str': '1',
            'sender_screen_name': 'fakeuser',
            'recipient': {
                'created_at': '2014-03-11 10:48:22.687699',
                'id': 2,
                'id_str': '2',
                'name': 'Fake User 2',
                'screen_name': 'fakeuser2'
            },
            'recipient_id': 2,
            'recipient_id_str': '2',
            'recipient_screen_name': 'fakeuser2',
            'entities': {
                'user_mentions': [{
                    'id': 2,
                    'id_str': '2',
                    'indices': [6, 16],
                    'name': 'Fake User 2',
                    'screen_name': 'fakeuser2'
                }]
            },
        })

    def test_to_dict_not_include_entities(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User 2')
        dm = twitter.add_dm('1', 'hello @fakeuser2', '1', '2')
        dm_dict = dm.to_dict(twitter, include_entities=False)
        self.assertTrue('entities' not in dm_dict)


class TestFakeFollow(TestCase):
    _FakeTwitterData = from_fake_twitter('FakeTwitterData')
    _FakeFollow = from_fake_twitter('FakeFollow')
    _now = datetime(2014, 3, 11, 10, 48, 22, 687699)

    def test_to_dict(self):
        twitter = self._FakeTwitterData()

        user1 = twitter.add_user(
            '1', 'fakeuser', 'Fake User', created_at=self._now)
        user2 = twitter.add_user(
            '2', 'fakeuser2', 'Fake User 2', created_at=self._now)
        follow = twitter.add_follow('1', '2')

        self.assertEqual(follow.to_dict(twitter), {
            'source': user1.to_dict(twitter),
            'target': user2.to_dict(twitter)
        })

    def test_to_dict_event(self):
        twitter = self._FakeTwitterData()

        user1 = twitter.add_user(
            '1', 'fakeuser', 'Fake User', created_at=self._now)
        user2 = twitter.add_user(
            '2', 'fakeuser2', 'Fake User 2', created_at=self._now)
        follow = twitter.add_follow('1', '2')

        follow_dict = follow.to_dict(twitter, event='follow')
        self.assertEqual(follow_dict, {
            'event': 'follow',
            'source': user1.to_dict(twitter),
            'target': user2.to_dict(twitter)
        })


class TestFakeImage(TestCase):
    _FakeImage = from_fake_twitter('FakeImage')

    def test_create_fake_image_defaults(self):
        image = self._FakeImage('image', 'content')
        self.assertEqual(image.name, 'image')
        self.assertEqual(image.height, image.width, 1)
        self.assertEqual(image.size, 1)

    def test_create_fake_image_params(self):
        image = self._FakeImage('image', 'content', size=2, height=2, width=2)
        self.assertEqual(image.height, image.width, 2)
        self.assertEqual(image.size, 2)

    def test_read(self):
        image = self._FakeImage('image', 'content')
        self.assertEqual(image.read(), 'content')


class TestFakeMedia(TestCase):
    _FakeTwitterData = from_fake_twitter('FakeTwitterData')
    _FakeMedia = from_fake_twitter('FakeMedia')
    _FakeImage = from_fake_twitter('FakeImage')

    def test_create_fake_media(self):
        image = self._FakeImage('image', 'content')
        media = self._FakeMedia('1', image)
        self.assertEqual(media.media_id_str, '1')
        self.assertEqual(media.size, image.size)
        self.assertEqual(media.expires_after_secs, 60)
        self.assertEqual(media.image, {
            'image_type': 'image/jpeg',
            'w': image.width,
            'h': image.height,
        })

    def test_to_dict(self):
        media = self._FakeMedia('1', self._FakeImage('image', 'content'))
        self.assertEqual(media.to_dict(self._FakeTwitterData), {
            'media_id_str': '1',
            'media_id': 1,
            'size': 1,
            'expires_after_secs': 60,
            'image': {
                'image_type': 'image/jpeg',
                'h': 1,
                'w': 1,
            },
        })


class TestFakeTwitterData(TestCase):
    _FakeTwitterData = from_fake_twitter('FakeTwitterData')
    _FakeMedia = from_fake_twitter('FakeMedia')
    _FakeImage = from_fake_twitter('FakeImage')
    _now = datetime(2014, 3, 11, 10, 48, 22, 687699)

    def test_next_tweet_id(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')

        id1 = twitter.next_tweet_id
        tweet1 = twitter.new_tweet('hello', '1')

        self.assertEqual(id1, tweet1.id_str)

    def test_next_dm_id(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser', 'Fake User')

        id1 = twitter.next_tweet_id
        dm1 = twitter.new_dm('hello', '1', '2')

        self.assertEqual(id1, dm1.id_str)

    def test_next_user_id(self):
        twitter = self._FakeTwitterData()

        id1 = twitter.next_tweet_id
        user1 = twitter.new_user('fakeuser', 'Fake User')

        self.assertEqual(id1, user1.id_str)

    def test_next_media_id(self):
        twitter = self._FakeTwitterData()

        id1 = twitter.next_media_id
        media1 = twitter.new_media(self._FakeImage('img1', 'content'))

        self.assertEqual(id1, media1.media_id_str)

    def test_broadcast_follow(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User', created_at=self._now)
        twitter.add_user('2', 'fakeuser2', 'Fake User 2', created_at=self._now)
        follow1 = twitter.add_follow('1', '2')
        follow2 = twitter.add_follow('2', '1')
        follow1_dict = follow1.to_dict(twitter, event='follow')
        follow2_dict = follow2.to_dict(twitter, event='follow')

        stream1_messages = []
        stream1 = twitter.new_stream()
        stream1.add_message_type('follow', lambda f: f.source_id == '1')
        protocol = FakeTwitterStreamProtocol(stream1_messages.append)
        stream1.resp.deliverBody(protocol)

        stream2_messages = []
        stream2 = twitter.new_stream()
        stream2.add_message_type('follow', lambda f: f.source_id == '2')
        protocol = FakeTwitterStreamProtocol(stream2_messages.append)
        stream2.resp.deliverBody(protocol)

        twitter.broadcast_follow(follow1)
        self.assertEqual(stream1_messages, [follow1_dict])
        self.assertEqual(stream2_messages, [])

        twitter.broadcast_follow(follow2)
        self.assertEqual(stream1_messages, [follow1_dict])
        self.assertEqual(stream2_messages, [follow2_dict])

    def test_broadcast_unfollow(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User', created_at=self._now)
        twitter.add_user('2', 'fakeuser2', 'Fake User 2', created_at=self._now)
        follow1 = twitter.add_follow('1', '2')
        follow2 = twitter.add_follow('2', '1')
        follow1_dict = follow1.to_dict(twitter, event='unfollow')
        follow2_dict = follow2.to_dict(twitter, event='unfollow')

        stream1_messages = []
        stream1 = twitter.new_stream()
        stream1.add_message_type('unfollow', lambda f: f.source_id == '1')
        protocol = FakeTwitterStreamProtocol(stream1_messages.append)
        stream1.resp.deliverBody(protocol)

        stream2_messages = []
        stream2 = twitter.new_stream()
        stream2.add_message_type('unfollow', lambda f: f.source_id == '2')
        protocol = FakeTwitterStreamProtocol(stream2_messages.append)
        stream2.resp.deliverBody(protocol)

        twitter.broadcast_unfollow(follow1)
        self.assertEqual(stream1_messages, [follow1_dict])
        self.assertEqual(stream2_messages, [])

        twitter.broadcast_unfollow(follow2)
        self.assertEqual(stream1_messages, [follow1_dict])
        self.assertEqual(stream2_messages, [follow2_dict])

    def test_add_follow(self):
        twitter = self._FakeTwitterData()
        self.assertEqual(twitter.follows, {})

        twitter.add_follow('1', '2')
        follow1 = twitter.follows[('1', '2')]
        self.assertEqual(follow1.source_id, '1')
        self.assertEqual(follow1.target_id, '2')

        twitter.add_follow('2', '1')
        follow2 = twitter.follows[('2', '1')]
        self.assertEqual(follow2.source_id, '2')
        self.assertEqual(follow2.target_id, '1')

    def test_add_follow_broadcast(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User 2')

        def predicate(f):
            follows.append(f)
            return True

        follows = []
        stream = twitter.new_stream()
        stream.add_message_type('follow', predicate)

        follow = twitter.add_follow('1', '2')
        self.assertEqual(follows, [follow])

    def test_del_tweet(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        tweet1 = twitter.add_tweet('1', 'hello', '1')

        self.assertEqual(twitter.get_tweet('1'), tweet1)
        twitter.del_tweet('1')
        self.assertEqual(twitter.get_tweet('1'), None)

    def test_del_dm(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User 2')
        dm1 = twitter.add_dm('1', 'hello', '1', '2')

        self.assertEqual(twitter.get_dm('1'), dm1)
        twitter.del_dm('1')
        self.assertEqual(twitter.get_dm('1'), None)

    def test_del_media(self):
        twitter = self._FakeTwitterData()
        media = twitter.add_media('1', self._FakeImage('img1', 'content'))

        self.assertEqual(twitter.get_media('1'), media)
        twitter.del_media('1')
        self.assertEqual(twitter.get_media('1'), None)

    def test_del_follow(self):
        twitter = self._FakeTwitterData()
        twitter.add_follow('1', '2')
        twitter.add_follow('2', '1')
        self.assertEqual(set(twitter.follows.keys()), set([
            ('1', '2'),
            ('2', '1'),
        ]))

        twitter.del_follow('1', '2')
        self.assertEqual(set(twitter.follows.keys()), set([('2', '1')]))

        twitter.del_follow('2', '1')
        self.assertEqual(set(twitter.follows.keys()), set())

    def test_del_follow_broadcast(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User 2')
        follow = twitter.add_follow('1', '2')

        def predicate(f):
            follows.append(f)
            return True

        follows = []
        stream = twitter.new_stream()
        stream.add_message_type('unfollow', predicate)

        twitter.del_follow('1', '2')
        self.assertEqual(follows, [follow])

    def test_user_dm(self):
        twitter = self._FakeTwitterData()
        user1 = twitter.add_user('1', 'fakeuser', 'Fake User')

        self.assertEqual(twitter.get_user('1'), user1)
        twitter.del_user('1')
        self.assertEqual(twitter.get_user('1'), None)

    def test_new_tweet(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        tweet = twitter.new_tweet('hello', '1')
        self.assertEqual(tweet.text, 'hello')
        self.assertEqual(tweet.user_id_str, '1')

    def test_new_dm(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User 2')
        dm = twitter.new_dm('hello', '1', '2')
        self.assertEqual(dm.text, 'hello')
        self.assertEqual(dm.sender_id_str, '1')
        self.assertEqual(dm.recipient_id_str, '2')

    def test_new_user(self):
        twitter = self._FakeTwitterData()
        user = twitter.new_user('fakeuser', 'Fake User')
        self.assertEqual(user.screen_name, 'fakeuser')
        self.assertEqual(user.name, 'Fake User')

    def test_new_media(self):
        twitter = self._FakeTwitterData()
        media = twitter.new_media(self._FakeImage('img', 'content', size=10))
        self.assertEqual(media.size, 10)


class TestFakeTwitter(TestCase):
    _FakeTwitter = from_fake_twitter('FakeTwitter')
    _FakeTwitterClient = from_fake_twitter('FakeTwitterClient')
    _FakeMedia = from_fake_twitter('FakeMedia')
    _FakeImage = from_fake_twitter('FakeImage')

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

    @inlineCallbacks
    def test_dispatch_multipart(self):
        twitter = self._FakeTwitter()
        client = twitter.get_client('42')
        image = self._FakeImage('img', 'content')
        response = yield twitter.dispatch_multipart(
            client._fake_twitter_user_id_str,
            'https://upload.twitter.com/1.1/media/upload.json',
            image, [])

        # We expect the media in the response to contain FakeMedia defaults
        self.assertEqual(response, {
            'media_id': 1000,
            'media_id_str': '1000',
            'image': {'image_type': 'image/jpeg', 'h': 1, 'w': 1},
            'additional_owners': [],
            'expires_after_secs': 60,
            'size': 1,
        })


class TestFakeTwitterClient(TestCase):
    _FakeTwitter = from_fake_twitter('FakeTwitter')
    _FakeImage = from_fake_twitter('FakeImage')

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

    @inlineCallbacks
    def test_upload_media(self):
        client = self._FakeTwitterClient()
        image = self._FakeImage('img', 'content')
        media = yield client._upload_media('media/upload.json', image, [])

        # We expect the media in the response to contain FakeMedia defaults
        self.assertEqual(media, {
            'media_id': 1000,
            'media_id_str': '1000',
            'image': {'image_type': 'image/jpeg', 'h': 1, 'w': 1},
            'additional_owners': [],
            'expires_after_secs': 60,
            'size': 1,
        })


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
    _TwitterAPIError = from_fake_twitter('TwitterAPIError')
    _FakeImage = from_fake_twitter('FakeImage')

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

    def test__tweet_or_404(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        tweet = twitter.add_tweet('1', 'hello', '1')
        api = self._FakeTwitterAPI(twitter, '1')

        self.assertEqual(api._tweet_or_404('1'), tweet)
        self.assertRaises(self._TwitterAPIError, api._tweet_or_404, '2')

    def test__user_or_404(self):
        twitter = self._FakeTwitterData()
        user = twitter.add_user('1', 'fakeuser', 'Fake User')
        api = self._FakeTwitterAPI(twitter, '1')

        self.assertEqual(api._user_or_404('1'), user)
        self.assertRaises(self._TwitterAPIError, api._user_or_404, '2')

    def test__dm_or_404(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')

        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')
        dm = twitter.add_dm('1', 'hello', '1', '2')

        self.assertEqual(api._dm_or_404('1'), dm)
        self.assertRaises(self._TwitterAPIError, api._dm_or_404, '2')

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

    def test_statuses_mentions_timeline_since_id(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User 2')

        twitter.add_tweet('1', 'hello @fakeuser', '2')
        mention2 = twitter.add_tweet('2', 'hello @fakeuser', '2')
        mention3 = twitter.add_tweet('3', 'hello @fakeuser', '2')

        api = self._FakeTwitterAPI(twitter, '1')
        mentions = api.statuses_mentions_timeline(since_id='1')
        self.assertEqual(mentions, twitter.to_dicts(mention3, mention2))

    def test_statuses_mentions_timeline_max_id(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User 2')

        mention1 = twitter.add_tweet('1', 'hello @fakeuser', '2')
        mention2 = twitter.add_tweet('2', 'hello @fakeuser', '2')
        twitter.add_tweet('3', 'hello @fakeuser', '2')

        api = self._FakeTwitterAPI(twitter, '1')
        mentions = api.statuses_mentions_timeline(max_id='2')
        self.assertEqual(mentions, twitter.to_dicts(mention2, mention1))

    def test_statuses_mentions_timeline_limit(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User 2')

        mentions = [
            twitter.add_tweet(str(i), 'hello @fakeuser', '2')
            for i in range(201)]

        api = self._FakeTwitterAPI(twitter, '1')
        mention_dicts = api.statuses_mentions_timeline(count=201)

        self.assertEqual(
            mention_dicts,
            twitter.to_dicts(*mentions[::-1][:200]))

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

    def test_statuses_user_timeline_limit_by_screen_name(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')
        twitter.add_tweet('1', 'hello', '1')
        tweet1 = twitter.add_tweet('2', 'hello', '2')
        twitter.add_tweet('3', 'hello @fakeuser2', '1')
        tweet2 = twitter.add_tweet('4', 'hello @fakeuser', '2')

        api = self._FakeTwitterAPI(twitter, '1')
        mentions = api.statuses_user_timeline(screen_name='fakeuser2')
        self.assertEqual(mentions, twitter.to_dicts(tweet2, tweet1))

    def test_statuses_user_timeline_limit_by_exclude_replies(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')
        twitter.add_tweet('1', 'hello', '1')
        tweet1 = twitter.add_tweet('2', 'hello', '2')
        twitter.add_tweet('3', 'hello @fakeuser2', '1')
        twitter.add_tweet('4', 'hello @fakeuser', '2', reply_to='3')

        api = self._FakeTwitterAPI(twitter, '1')
        mentions = api.statuses_user_timeline('2', exclude_replies=True)
        self.assertEqual(mentions, twitter.to_dicts(tweet1))

    def test_statuses_user_timeline_since_id(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User 2')

        twitter.add_tweet('1', 'hello @fakeuser', '2')
        tweet2 = twitter.add_tweet('2', 'hello @fakeuser', '2')
        tweet3 = twitter.add_tweet('3', 'hello @fakeuser', '2')

        api = self._FakeTwitterAPI(twitter, '1')
        mentions = api.statuses_user_timeline('2', since_id='1')
        self.assertEqual(mentions, twitter.to_dicts(tweet3, tweet2))

    def test_statuses_user_timeline_max_id(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User 2')

        tweet1 = twitter.add_tweet('1', 'hello @fakeuser', '2')
        tweet2 = twitter.add_tweet('2', 'hello @fakeuser', '2')
        twitter.add_tweet('3', 'hello @fakeuser', '2')

        api = self._FakeTwitterAPI(twitter, '1')
        mentions = api.statuses_user_timeline('2', max_id='2')
        self.assertEqual(mentions, twitter.to_dicts(tweet2, tweet1))

    def test_statuses_user_timeline_limit(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User 2')

        tweets = [
            twitter.add_tweet(str(i), 'hello @fakeuser', '2')
            for i in range(201)]

        api = self._FakeTwitterAPI(twitter, '1')
        mention_dicts = api.statuses_user_timeline('2', count=201)
        self.assertEqual(mention_dicts, twitter.to_dicts(*tweets[::-1][:200]))

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

    def test_media_upload(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        image = self._FakeImage('image', 'content')

        api = self._FakeTwitterAPI(twitter, '1')
        media = api.media_upload(image, additional_owners=[1, 2])
        self.assertEqual(1, media['size'])
        self.assertEqual(60, media['expires_after_secs'])
        self.assertEqual(1, media['image']['h'], media['image']['w'])
        self.assertEqual('image/jpeg', media['image']['image_type'])
        self.assertEqual(twitter.media.keys(), [media['media_id_str']])

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
        self.assertEqual(twitter.streams, {})

    def test_stream_filter_follow(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')
        twitter.add_user('3', 'fakeuser2', 'Fake User')

        api = self._FakeTwitterAPI(twitter, None)
        messages = []
        resp = api.stream_filter(follow='2,3')
        self._process_stream_response(resp, messages.append)
        self.assertEqual(messages, [])

        twitter.new_tweet('hello', '1')
        self.assertEqual(messages, [])

        tweet1 = twitter.new_tweet('hello', '2')
        tweet2 = twitter.new_tweet('hello', '3')
        self.assertEqual(messages, twitter.to_dicts(tweet1, tweet2))

        resp.finished()
        self.assertEqual(twitter.streams, {})

    # TODO: Tests for fake stream_sample()
    # TODO: Tests for fake stream_firehose()

    def test_dispatch_userstream_user(self):
        from txtwitter.twitter import TWITTER_USERSTREAM_URL
        uri = self._build_uri(TWITTER_USERSTREAM_URL, 'user.json')
        self.assert_method_uri('userstream_user', uri)

    def test_userstream_user_with_user_friends(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')

        api = self._FakeTwitterAPI(twitter, '1')
        messages = []
        resp = api.userstream_user(stringify_friend_ids='true', with_='user')
        self._process_stream_response(resp, messages.append)
        self.assertEqual(messages, [{'friends_str': []}])

        resp.finished()
        self.assertEqual(twitter.streams, {})

    def test_userstream_user_with_user_tweets(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')

        api = self._FakeTwitterAPI(twitter, '1')
        messages = []
        resp = api.userstream_user(stringify_friend_ids='true', with_='user')
        self._process_stream_response(resp, messages.append)
        messages.pop(0)

        tweet1 = twitter.new_tweet('hello', '1')
        twitter.new_tweet('hello', '2')
        self.assertEqual(messages, twitter.to_dicts(tweet1))

        resp.finished()
        self.assertEqual(twitter.streams, {})

    def test_userstream_user_with_user_mentions(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')

        api = self._FakeTwitterAPI(twitter, '1')
        messages = []
        resp = api.userstream_user(stringify_friend_ids='true', with_='user')
        self._process_stream_response(resp, messages.append)
        messages.pop(0)

        twitter.new_tweet('@fakeuser2', '2')
        tweet2 = twitter.new_tweet('@fakeuser', '2')
        self.assertEqual(messages, twitter.to_dicts(tweet2))

        resp.finished()
        self.assertEqual(twitter.streams, {})

    def test_userstream_user_with_user_dms(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')
        twitter.add_user('3', 'fakeuser3', 'Fake User')

        api = self._FakeTwitterAPI(twitter, '1')
        messages = []
        resp = api.userstream_user(stringify_friend_ids='true', with_='user')
        self._process_stream_response(resp, messages.append)
        messages.pop(0)

        dm1 = twitter.new_dm('hello', '1', '2')
        dm2 = twitter.new_dm('hello', '2', '1')

        twitter.new_dm('hello', '2', '3')
        self.assertEqual(
            messages,
            [{'direct_message': dm} for dm in twitter.to_dicts(dm1, dm2)])

        resp.finished()
        self.assertEqual(twitter.streams, {})

        # TODO: Replies

    def test_userstream_user_with_follows(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')
        twitter.add_user('3', 'fakeuser3', 'Fake User')

        api = self._FakeTwitterAPI(twitter, '1')
        messages = []
        resp = api.userstream_user(stringify_friend_ids='true', with_='user')
        self._process_stream_response(resp, messages.append)
        messages.pop(0)

        follow1 = twitter.add_follow('1', '2')
        follow2 = twitter.add_follow('2', '1')
        twitter.add_follow('2', '3')

        self.assertEqual(
            messages,
            twitter.to_dicts(follow1, follow2, event='follow'))

        resp.finished()
        self.assertEqual(twitter.streams, {})

    def test_userstream_user_with_unfollows(self):
        twitter = self._FakeTwitterData()
        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')
        twitter.add_user('3', 'fakeuser3', 'Fake User')

        follow1 = twitter.add_follow('1', '2')
        twitter.add_follow('2', '1')
        twitter.add_follow('2', '3')

        api = self._FakeTwitterAPI(twitter, '1')
        messages = []
        resp = api.userstream_user(stringify_friend_ids='true', with_='user')
        self._process_stream_response(resp, messages.append)
        messages.pop(0)

        twitter.del_follow('1', '2')
        twitter.del_follow('2', '1')
        twitter.del_follow('2', '3')

        self.assertEqual(
            messages,
            twitter.to_dicts(follow1, event='unfollow'))

        resp.finished()
        self.assertEqual(twitter.streams, {})

    # TODO: More tests for fake userstream_user()

    # Direct Messages

    def test_direct_messages(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')

        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')
        twitter.add_user('3', 'fakeuser3', 'Fake User')

        dm1 = twitter.new_dm('hello', '2', '1')
        dm2 = twitter.new_dm('hello', '3', '1')
        twitter.new_dm('hello', '1', '2')
        twitter.new_dm('hello', '1', '3')

        self.assertEqual(api.direct_messages(), twitter.to_dicts(dm2, dm1))

    def test_direct_messages_limiting(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')

        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')
        dms = [twitter.new_dm('hello', '2', '1') for i in range(21)]

        self.assertEqual(
            api.direct_messages(),
            twitter.to_dicts(*dms[::-1][:20]))

    def test_direct_messages_since_id(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')

        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')

        dm1 = twitter.new_dm('hello', '2', '1')
        dm2 = twitter.new_dm('goodbye', '2', '1')

        self.assertEqual(
            api.direct_messages(since_id=dm1.id_str),
            twitter.to_dicts(dm2))

    def test_direct_messages_max_id(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')

        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')

        dm1 = twitter.new_dm('hello', '2', '1')
        dm2 = twitter.new_dm('goodbye', '2', '1')
        twitter.new_dm('hello again', '2', '1')

        self.assertEqual(
            api.direct_messages(max_id=dm2.id_str),
            twitter.to_dicts(dm2, dm1))

    def test_direct_messages_count(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')

        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')

        twitter.new_dm('hello', '2', '1')
        dm2 = twitter.new_dm('goodbye', '2', '1')
        dm3 = twitter.new_dm('hello again', '2', '1')

        self.assertEqual(
            api.direct_messages(count=2),
            twitter.to_dicts(dm3, dm2))

    def test_direct_messages_include_entities(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')

        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')

        twitter.new_dm('hello', '2', '1')
        twitter.new_dm('goodbye', '2', '1')

        dms = api.direct_messages(include_entities=False)
        self.assertTrue(all('entities' not in dm for dm in dms))

    def test_direct_messages_sent(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')

        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')
        twitter.add_user('3', 'fakeuser3', 'Fake User')

        dm1 = twitter.new_dm('hello', '1', '2')
        dm2 = twitter.new_dm('hello', '1', '3')
        twitter.new_dm('hello', '2', '1')
        twitter.new_dm('hello', '3', '1')

        self.assertEqual(
            api.direct_messages_sent(),
            twitter.to_dicts(dm2, dm1))

    def test_direct_messages_sent_since_id(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')

        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')

        dm1 = twitter.new_dm('hello', '1', '2')
        dm2 = twitter.new_dm('goodbye', '1', '2')

        self.assertEqual(
            api.direct_messages_sent(since_id=dm1.id_str),
            twitter.to_dicts(dm2))

    def test_direct_messages_sent_max_id(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')

        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')

        dm1 = twitter.new_dm('hello', '1', '2')
        dm2 = twitter.new_dm('goodbye', '1', '2')
        twitter.new_dm('hello again', '1', '2')

        self.assertEqual(
            api.direct_messages_sent(max_id=dm2.id_str),
            twitter.to_dicts(dm2, dm1))

    def test_direct_messages_sent_count(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')

        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')

        twitter.new_dm('hello', '1', '2')
        dm2 = twitter.new_dm('goodbye', '1', '2')
        dm3 = twitter.new_dm('hello again', '1', '2')

        self.assertEqual(
            api.direct_messages_sent(count=2),
            twitter.to_dicts(dm3, dm2))

    def test_direct_messages_sent_include_entities(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')

        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')

        twitter.new_dm('hello', '1', '2')
        twitter.new_dm('goodbye', '1', '2')

        dms = api.direct_messages_sent(include_entities=False)
        self.assertTrue(all('entities' not in dm for dm in dms))

    def test_direct_messages_sent_page(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')

        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')

        dms = [twitter.new_dm('hello', '1', '2') for _ in range(80)]

        self.assertEqual(
            api.direct_messages_sent(page=2, count=80),
            twitter.to_dicts(*dms[::-1][20:40]))

    def test_direct_messages_show(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')

        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')
        dm = twitter.new_dm('hello', '1', '2')

        found_dms = api.direct_messages_show(dm.id_str)
        self.assertEqual(twitter.to_dicts(dm), found_dms)

    def test_direct_messages_show_not_found(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')
        self.assertRaises(self._TwitterAPIError, api.direct_messages_show, '1')

    def test_direct_messages_show_forbidden(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')

        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')
        twitter.add_user('3', 'fakeuser3', 'Fake User 3')
        dm = twitter.new_dm('hello', '2', '3')

        self.assertRaises(
            self._TwitterAPIError, api.direct_messages_show, dm.id_str)

    def test_direct_messages_destroy(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')

        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')
        dm = twitter.new_dm('hello', '1', '2')

        found_dm = api.direct_messages_destroy(dm.id_str)
        self.assertEqual(dm.to_dict(twitter), found_dm)
        self.assertTrue(dm.id_str not in twitter.dms)

    def test_direct_messages_destroy_not_found(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')
        self.assertRaises(
            self._TwitterAPIError, api.direct_messages_destroy, '1')

    def test_direct_messages_destroy_forbidden(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')

        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')
        twitter.add_user('3', 'fakeuser3', 'Fake User 3')
        dm = twitter.new_dm('hello', '2', '3')

        self.assertRaises(
            self._TwitterAPIError, api.direct_messages_destroy, dm.id_str)

    def test_direct_messages_destroy_not_include_entities(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')

        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')
        dm = twitter.new_dm('hello', '1', '2')

        found_dm = api.direct_messages_destroy(
            dm.id_str, include_entities=False)
        self.assertTrue('entities' not in found_dm)

    def test_direct_messages_new_by_user_id(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')

        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')

        sent_dm = api.direct_messages_new('hello', user_id='2')
        actual_dm = twitter.get_dm(sent_dm['id_str'])
        self.assertEqual(sent_dm, actual_dm.to_dict(twitter))

    def test_direct_messages_new_by_screen_name(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')

        twitter.add_user('1', 'fakeuser', 'Fake User')
        twitter.add_user('2', 'fakeuser2', 'Fake User')

        sent_dm = api.direct_messages_new('hello', screen_name='fakeuser2')
        actual_dm = twitter.get_dm(sent_dm['id_str'])
        self.assertEqual(sent_dm, actual_dm.to_dict(twitter))

    def test_direct_messages_new_no_user_id_or_screen_name(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')
        self.assertRaises(
            self._TwitterAPIError, api.direct_messages_new, 'hello')

    # Friends & Followers
    # TODO: Tests for fake friendships_no_retweets_ids()
    # TODO: Tests for fake friends_ids()
    # TODO: Tests for fake followers_ids()
    # TODO: Tests for fake friendships_lookup()
    # TODO: Tests for fake friendships_incoming()
    # TODO: Tests for fake friendships_outgoing()

    def test_friendships_create_by_screen_name(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')

        twitter.add_user('1', 'fakeuser', 'Fake User')
        user2 = twitter.add_user('2', 'fakeuser2', 'Fake User')

        response = api.friendships_create(screen_name='fakeuser2')
        self.assertTrue(twitter.get_follow('1', '2') is not None)
        self.assertEqual(response, user2.to_dict(twitter))

    def test_friendships_create_by_user_id(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')

        twitter.add_user('1', 'fakeuser', 'Fake User')
        user2 = twitter.add_user('2', 'fakeuser2', 'Fake User')

        response = api.friendships_create(user_id='2')
        self.assertTrue(twitter.get_follow('1', '2') is not None)
        self.assertEqual(response, user2.to_dict(twitter))

    def test_friendships_create_by_screen_name_no_user_exists(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')
        self.assertRaises(
            self._TwitterAPIError, api.friendships_create,
            screen_name='fakeuser2')
        self.assertTrue(twitter.get_follow('1', '2') is None)

    def test_friendships_create_by_user_id_no_user_exists(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')
        self.assertRaises(
            self._TwitterAPIError, api.friendships_create, user_id='1')
        self.assertTrue(twitter.get_follow('1', '2') is None)

    def test_friendships_create_no_user_id_or_screen_name(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')
        self.assertRaises(self._TwitterAPIError, api.friendships_create)
        self.assertTrue(twitter.get_follow('1', '2') is None)

    def test_friendships_destroy_by_screen_name(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')

        twitter.add_user('1', 'fakeuser', 'Fake User')
        user2 = twitter.add_user('2', 'fakeuser2', 'Fake User')
        twitter.add_follow('1', '2')

        response = api.friendships_destroy(screen_name='fakeuser2')
        self.assertTrue(twitter.get_follow('1', '2') is None)
        self.assertEqual(response, user2.to_dict(twitter))

    def test_friendships_destroy_by_user_id(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')

        twitter.add_user('1', 'fakeuser', 'Fake User')
        user2 = twitter.add_user('2', 'fakeuser2', 'Fake User')
        twitter.add_follow('1', '2')

        response = api.friendships_destroy(user_id='2')
        self.assertTrue(twitter.get_follow('1', '2') is None)
        self.assertEqual(response, user2.to_dict(twitter))

    def test_friendships_destroy_by_screen_name_no_follow_exists(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')

        twitter.add_user('1', 'fakeuser', 'Fake User')
        user2 = twitter.add_user('2', 'fakeuser2', 'Fake User')

        response = api.friendships_destroy(screen_name='fakeuser2')
        self.assertEqual(response, user2.to_dict(twitter))

    def test_friendships_destroy_by_screen_name_no_user_exists(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')
        self.assertRaises(
            self._TwitterAPIError, api.friendships_destroy,
            screen_name='fakeuser2')

    def test_friendships_destroy_by_user_id_no_follow_exists(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')

        twitter.add_user('1', 'fakeuser', 'Fake User')
        user2 = twitter.add_user('2', 'fakeuser2', 'Fake User')

        response = api.friendships_destroy(user_id='2')
        self.assertEqual(response, user2.to_dict(twitter))

    def test_friendships_destroy_by_user_id_no_user_exists(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')
        self.assertRaises(
            self._TwitterAPIError, api.friendships_destroy, user_id='1')

    def test_friendships_destroy_no_user_id_or_screen_name(self):
        twitter = self._FakeTwitterData()
        api = self._FakeTwitterAPI(twitter, '1')
        self.assertRaises(self._TwitterAPIError, api.friendships_destroy)

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
