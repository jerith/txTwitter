import json

from twisted.internet.defer import Deferred, inlineCallbacks
from twisted.trial.unittest import TestCase

from txtwitter.tests.fake_agent import FakeAgent, FakeResponse
from txtwitter.tests.fake_twitter import FakeImage


def from_twitter(name):
    @property
    def prop(self):
        from txtwitter import twitter
        return getattr(twitter, name)
    return prop


class TestParamHelpers(TestCase):
    _set_bool_param = from_twitter('set_bool_param')
    _set_str_param = from_twitter('set_str_param')
    _set_float_param = from_twitter('set_float_param')
    _set_int_param = from_twitter('set_int_param')
    _set_list_param = from_twitter('set_list_param')

    def test_set_bool_param_None(self):
        """
        set_bool_param() should do nothing if the value is ``None``.
        """
        params = {}
        self._set_bool_param(params, 'foo', None)
        self.assertEqual(params, {})

    def test_set_bool_param_True(self):
        """
        set_bool_param() should set the param to 'true' if the value is
        ``True``.
        """
        params = {}
        self._set_bool_param(params, 'foo', True)
        self.assertEqual(params, {'foo': 'true'})

    def test_set_bool_param_False(self):
        """
        set_bool_param() should set the param to 'false' if the value is
        ``False``.
        """
        params = {}
        self._set_bool_param(params, 'foo', False)
        self.assertEqual(params, {'foo': 'false'})

    def test_set_bool_param_bad(self):
        """
        set_bool_param() should raise ValueError if the value is not a bool or
        ``None``.
        """
        self.assertRaises(ValueError, self._set_bool_param, {}, 'foo', 1)

    def test_set_str_param_None(self):
        """
        set_str_param() should do nothing if the value is ``None``.
        """
        params = {}
        self._set_str_param(params, 'foo', None)
        self.assertEqual(params, {})

    def test_set_str_param(self):
        """
        set_str_param() should set the param if the value is a string.
        """
        params = {}
        self._set_str_param(params, 'foo', 'some string')
        self.assertEqual(params, {'foo': 'some string'})

    def test_set_str_param_bad(self):
        """
        set_str_param() should raise ValueError if the value is not a string or
        ``None``.
        """
        self.assertRaises(ValueError, self._set_str_param, {}, 'foo', True)

    def test_set_float_param_None(self):
        """
        set_float_param() should do nothing if the value is ``None``.
        """
        params = {}
        self._set_float_param(params, 'foo', None)
        self.assertEqual(params, {})

    def test_set_float_param(self):
        """
        set_float_param() should set the param if the value is a float.
        """
        params = {}
        self._set_float_param(params, 'foo', 42.5)
        self.assertEqual(params, {'foo': '42.5'})

    def test_set_float_param_int(self):
        """
        set_float_param() should set the param if the value is an int.
        """
        params = {}
        self._set_float_param(params, 'foo', 42)
        self.assertEqual(params, {'foo': '42.0'})

    def test_set_float_param_str(self):
        """
        set_float_param() should set the param if the value is a string
        representation of a float.
        """
        params = {}
        self._set_float_param(params, 'foo', '42.5')
        self.assertEqual(params, {'foo': '42.5'})

    def test_set_float_param_min(self):
        """
        set_float_param() should raise ValueError if the value is less than the
        minimum.
        """
        self.assertRaises(
            ValueError, self._set_float_param, {}, 'foo', 42.5, min=50)

    def test_set_float_param_max(self):
        """
        set_float_param() should raise ValueError if the value is greater than
        the maximum.
        """
        self.assertRaises(
            ValueError, self._set_float_param, {}, 'foo', 42.5, max=40)

    def test_set_float_param_min_str(self):
        """
        set_float_param() should raise ValueError if the value is less than the
        minimum.
        """
        self.assertRaises(
            ValueError, self._set_float_param, {}, 'foo', '42.5', min=50)

    def test_set_float_param_max_str(self):
        """
        set_float_param() should raise ValueError if the value is greater than
        the maximum.
        """
        self.assertRaises(
            ValueError, self._set_float_param, {}, 'foo', '42.5', max=40)

    def test_set_float_param_bad(self):
        """
        set_float_param() should raise ValueError if the value is not a float
        (and cannot be turned into one) or ``None``.
        """
        self.assertRaises(ValueError, self._set_float_param, {}, 'foo', True)

    def test_set_int_param_None(self):
        """
        set_int_param() should do nothing if the value is ``None``.
        """
        params = {}
        self._set_int_param(params, 'foo', None)
        self.assertEqual(params, {})

    def test_set_int_param(self):
        """
        set_int_param() should set the param if the value is a int.
        """
        params = {}
        self._set_int_param(params, 'foo', 42)
        self.assertEqual(params, {'foo': '42'})

    def test_set_int_param_str(self):
        """
        set_int_param() should set the param if the value is a string
        representation of an int.
        """
        params = {}
        self._set_int_param(params, 'foo', '42')
        self.assertEqual(params, {'foo': '42'})

    def test_set_int_param_min(self):
        """
        set_int_param() should raise ValueError if the value is less than the
        minimum.
        """
        self.assertRaises(
            ValueError, self._set_int_param, {}, 'foo', 42, min=50)

    def test_set_int_param_max(self):
        """
        set_int_param() should raise ValueError if the value is greater than
        the maximum.
        """
        self.assertRaises(
            ValueError, self._set_int_param, {}, 'foo', 42, max=40)

    def test_set_int_param_min_str(self):
        """
        set_int_param() should raise ValueError if the value is less than the
        minimum.
        """
        self.assertRaises(
            ValueError, self._set_int_param, {}, 'foo', '42', min=50)

    def test_set_int_param_max_str(self):
        """
        set_int_param() should raise ValueError if the value is greater than
        the maximum.
        """
        self.assertRaises(
            ValueError, self._set_int_param, {}, 'foo', '42', max=40)

    def test_set_int_param_bad(self):
        """
        set_int_param() should raise ValueError if the value is not a int
        (and cannot be turned into one) or ``None``.
        """
        self.assertRaises(ValueError, self._set_int_param, {}, 42.5, True)

    def test_set_list_param(self):
        """
        set_list_param() should set the param if the value is a ``list``.
        """
        params = {}
        self._set_list_param(params, 'list', [1, 2, 3])
        self.assertEqual(params, {'list': '1,2,3,'})

    def test_set_list_param_min_len(self):
        """
        set_list_param() should raise a ``ValueError`` if the value is shorter
        than ``min_len``.
        """
        self.assertRaises(
            ValueError, self._set_list_param, {}, 'list', [1, 2], min_len=5)

    def test_set_list_param_max_len(self):
        """
        set_list_param() should raise a ``ValueError`` if the value is longer
        than ``max_len``.
        """
        self.assertRaises(
            ValueError, self._set_list_param, {}, 'list', [1, 2], max_len=1)

    def test_set_list_param_bad_types(self):
        """
        set_list_param() should raise a ``ValueError`` if the value is a
        ``dict``, or any type that cannot be turned into a ``list``.
        """
        self.assertRaises(
            ValueError, self._set_list_param, {}, 'dict', {'a': 1})
        self.assertRaises(
            ValueError, self._set_list_param, {}, 'int', 1)

    def test_set_list_param_good_types(self):
        """
        set_list_param() should set the param if the value is a type that can
        be turned into a ``list``.
        """
        params = {}
        self._set_list_param(params, 'set', {1, 2, 3})
        self._set_list_param(params, 'tuple', (1, 2, 3))
        self._set_list_param(params, 'frozenset', frozenset({1, 2, 3}))
        self._set_list_param(params, 'string', 'foo')
        self.assertEqual(params, {
            'set': '1,2,3,',
            'tuple': '1,2,3,',
            'frozenset': '1,2,3,',
            'string': 'f,o,o,',
        })


class TestTwitterClient(TestCase):
    timeout = 1

    _TwitterClient = from_twitter('TwitterClient')

    def _resp_json(self, data, code=200):
        return FakeResponse(json.dumps(data), code)

    def _agent_and_TwitterClient(self):
        agent = FakeAgent()
        client = self._TwitterClient(
            'token-key', 'token-secret', 'consumer-key', 'consumer-secret',
            agent=agent)
        return agent, client

    # Timelines

    @inlineCallbacks
    def test_statuses_mentions_timeline(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/statuses/mentions_timeline.json'
        response_list = [{
            # Truncated tweet data.
            "id_str": "123",
            "text": "Tweet!",
        }, {
            # Truncated tweet data.
            "id_str": "122",
            "text": "Tweet!",
        }]
        agent.add_expected_request(
            'GET', uri, {}, self._resp_json(response_list))
        resp = yield client.statuses_mentions_timeline()
        self.assertEqual(resp, response_list)

    @inlineCallbacks
    def test_statuses_mentions_timeline_all_params(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/statuses/mentions_timeline.json'
        response_list = [{
            # Truncated tweet data.
            "id_str": "123",
            "text": "Tweet!",
        }, {
            # Truncated tweet data.
            "id_str": "122",
            "text": "Tweet!",
        }]
        expected_params = {
            'count': '10',
            'since_id': '121',
            'max_id': '123',
            'trim_user': 'true',
            'contributor_details': 'true',
            'include_entities': 'false',
        }
        agent.add_expected_request(
            'GET', uri, expected_params, self._resp_json(response_list))
        resp = yield client.statuses_mentions_timeline(
            count=10, since_id='121', max_id='123', trim_user=True,
            contributor_details=True, include_entities=False)
        self.assertEqual(resp, response_list)

    @inlineCallbacks
    def test_statuses_user_timeline(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/statuses/user_timeline.json'
        response_list = [{
            # Truncated tweet data.
            "id_str": "123",
            "text": "Tweet!",
        }, {
            # Truncated tweet data.
            "id_str": "122",
            "text": "Tweet!",
        }]
        agent.add_expected_request(
            'GET', uri, {}, self._resp_json(response_list))
        resp = yield client.statuses_user_timeline()
        self.assertEqual(resp, response_list)

    @inlineCallbacks
    def test_statuses_user_timeline_all_params(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/statuses/user_timeline.json'
        response_list = [{
            # Truncated tweet data.
            "id_str": "123",
            "text": "Tweet!",
        }, {
            # Truncated tweet data.
            "id_str": "122",
            "text": "Tweet!",
        }]
        expected_params = {
            'user_id': '12',
            'screen_name': 'fakeuser',
            'since_id': '121',
            'count': '10',
            'max_id': '123',
            'trim_user': 'true',
            'exclude_replies': 'true',
            'contributor_details': 'true',
            'include_rts': 'false',
        }
        agent.add_expected_request(
            'GET', uri, expected_params, self._resp_json(response_list))
        resp = yield client.statuses_user_timeline(
            user_id='12', screen_name='fakeuser', since_id='121', count=10,
            max_id='123', trim_user=True, exclude_replies=True,
            contributor_details=True, include_rts=False)
        self.assertEqual(resp, response_list)

    @inlineCallbacks
    def test_statuses_home_timeline(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/statuses/home_timeline.json'
        response_list = [{
            # Truncated tweet data.
            "id_str": "123",
            "text": "Tweet!",
        }, {
            # Truncated tweet data.
            "id_str": "122",
            "text": "Tweet!",
        }]
        agent.add_expected_request(
            'GET', uri, {}, self._resp_json(response_list))
        resp = yield client.statuses_home_timeline()
        self.assertEqual(resp, response_list)

    @inlineCallbacks
    def test_statuses_home_timeline_all_params(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/statuses/home_timeline.json'
        response_list = [{
            # Truncated tweet data.
            "id_str": "123",
            "text": "Tweet!",
        }, {
            # Truncated tweet data.
            "id_str": "122",
            "text": "Tweet!",
        }]
        expected_params = {
            'count': '10',
            'since_id': '121',
            'max_id': '123',
            'trim_user': 'true',
            'exclude_replies': 'true',
            'contributor_details': 'true',
            'include_entities': 'false',
        }
        agent.add_expected_request(
            'GET', uri, expected_params, self._resp_json(response_list))
        resp = yield client.statuses_home_timeline(
            count=10, since_id='121', max_id='123', trim_user=True,
            exclude_replies=True, contributor_details=True,
            include_entities=False)
        self.assertEqual(resp, response_list)

    # TODO: Tests for statuses_retweets_of_me()

    # Tweets

    @inlineCallbacks
    def test_statuses_retweets(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/statuses/retweets.json'
        response_list = [{
            # Truncated tweet data.
            "id_str": "124",
            "text": "Tweet!",
            "retweeted_status": {
                "id_str": "123",
                "text": "Tweet!",
            },
        }, {
            # Truncated tweet data.
            "id_str": "125",
            "text": "Tweet!",
            "retweeted_status": {
                "id_str": "123",
                "text": "Tweet!",
            },
        }]
        agent.add_expected_request(
            'GET', uri, {'id': '123'}, self._resp_json(response_list))
        resp = yield client.statuses_retweets("123")
        self.assertEqual(resp, response_list)

    @inlineCallbacks
    def test_statuses_retweets_all_params(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/statuses/retweets.json'
        response_list = [{
            # Truncated tweet data.
            "id_str": "124",
            "text": "Tweet!",
            "retweeted_status": {
                "id_str": "123",
                "text": "Tweet!",
            },
        }, {
            # Truncated tweet data.
            "id_str": "125",
            "text": "Tweet!",
            "retweeted_status": {
                "id_str": "123",
                "text": "Tweet!",
            },
        }]
        expected_params = {
            'id': '123',
            'count': '10',
            'trim_user': 'true',
        }
        agent.add_expected_request(
            'GET', uri, expected_params, self._resp_json(response_list))
        resp = yield client.statuses_retweets("123", count=10, trim_user=True)
        self.assertEqual(resp, response_list)

    @inlineCallbacks
    def test_statuses_show(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/statuses/show.json'
        response_dict = {
            # Truncated tweet data.
            "id_str": "123",
            "text": "Tweet!",
        }
        agent.add_expected_request(
            'GET', uri, {'id': '123'}, self._resp_json(response_dict))
        resp = yield client.statuses_show("123")
        self.assertEqual(resp, response_dict)

    @inlineCallbacks
    def test_statuses_show_all_params(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/statuses/show.json'
        response_dict = {
            # Truncated tweet data.
            "id_str": "123",
            "text": "Tweet!",
        }
        expected_params = {
            'id': '123',
            'trim_user': 'true',
            'include_my_retweet': 'true',
            'include_entities': 'false',
        }
        agent.add_expected_request(
            'GET', uri, expected_params, self._resp_json(response_dict))
        resp = yield client.statuses_show(
            "123", trim_user=True, include_my_retweet=True,
            include_entities=False)
        self.assertEqual(resp, response_dict)

    @inlineCallbacks
    def test_statuses_show_HTTP_404(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/statuses/show.json'
        err_dict = {"errors": [
            {"message": "Sorry, that page does not exist", "code": 34},
        ]}
        agent.add_expected_request(
            'GET', uri, {'id': '123'}, self._resp_json(err_dict, 404))
        err = yield client.statuses_show("123").addErrback(lambda f: f.value)
        code, _phrase, body = err.args
        self.assertEqual((404, err_dict), (code, json.loads(body)))

    @inlineCallbacks
    def test_statuses_destroy(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/statuses/destroy.json'
        response_dict = {
            # Truncated tweet data.
            "id_str": "123",
            "text": "Tweet!",
        }
        agent.add_expected_request(
            'POST', uri, {'id': '123'}, self._resp_json(response_dict))
        resp = yield client.statuses_destroy("123")
        self.assertEqual(resp, response_dict)

    @inlineCallbacks
    def test_statuses_destroy_all_params(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/statuses/destroy.json'
        response_dict = {
            # Truncated tweet data.
            "id_str": "123",
            "text": "Tweet!",
        }
        expected_params = {
            'id': '123',
            'trim_user': 'true',
        }
        agent.add_expected_request(
            'POST', uri, expected_params, self._resp_json(response_dict))
        resp = yield client.statuses_destroy("123", trim_user=True)
        self.assertEqual(resp, response_dict)

    @inlineCallbacks
    def test_statuses_update(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/statuses/update.json'
        response_dict = {
            # Truncated tweet data.
            "id_str": "123",
            "text": "Tweet!",
        }
        agent.add_expected_request(
            'POST', uri, {'status': 'Tweet!'}, self._resp_json(response_dict))
        resp = yield client.statuses_update("Tweet!")
        self.assertEqual(resp, response_dict)

    @inlineCallbacks
    def test_statuses_update_unicode(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/statuses/update.json'
        response_dict = {
            # Truncated tweet data.
            "id_str": "123",
            "text": u"Tw\xeb\xebt!",
        }
        agent.add_expected_request(
            'POST', uri, {'status': u"Tw\xeb\xebt!".encode('utf-8')},
            self._resp_json(response_dict))
        resp = yield client.statuses_update(u"Tw\xeb\xebt!")
        self.assertEqual(resp, response_dict)

    @inlineCallbacks
    def test_statuses_update_all_params(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/statuses/update.json'
        response_dict = {
            # Truncated tweet data.
            "id_str": "123",
            "text": "Tweet!",
        }
        expected_params = {
            'status': 'Tweet!',
            'in_reply_to_status_id': '122',
            'lat': '-33.93',
            'long': '18.42',
            'place_id': 'abc123',
            'display_coordinates': 'true',
            'trim_user': 'true',
            'media_ids': '1,2,',
        }
        agent.add_expected_request(
            'POST', uri, expected_params, self._resp_json(response_dict))
        resp = yield client.statuses_update(
            "Tweet!", in_reply_to_status_id="122", lat=-33.93, long=18.42,
            place_id='abc123', display_coordinates=True, trim_user=True,
            media_ids=[1, 2])
        self.assertEqual(resp, response_dict)

    @inlineCallbacks
    def test_statuses_retweet(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/statuses/retweet.json'
        response_dict = {
            # Truncated tweet data.
            "id_str": "124",
            "text": "Tweet!",
            "retweeted_status": {
                "id_str": "123",
                "text": "Tweet!",
            },
        }
        agent.add_expected_request(
            'POST', uri, {'id': '123'}, self._resp_json(response_dict))
        resp = yield client.statuses_retweet("123")
        self.assertEqual(resp, response_dict)

    @inlineCallbacks
    def test_statuses_retweet_all_params(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/statuses/retweet.json'
        response_dict = {
            # Truncated tweet data.
            "id_str": "124",
            "text": "Tweet!",
            "retweeted_status": {
                "id_str": "123",
                "text": "Tweet!",
            },
        }
        expected_params = {
            'id': '123',
            'trim_user': 'true',
        }
        agent.add_expected_request(
            'POST', uri, expected_params, self._resp_json(response_dict))
        resp = yield client.statuses_retweet("123", trim_user=True)
        self.assertEqual(resp, response_dict)

    @inlineCallbacks
    def test_media_upload(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://upload.twitter.com/1.1/media/upload.json'
        media = FakeImage('image', 'raw_binary_content')
        response_dict = {
            'media_id': 123,
            'media_id_string': '123',
            'size': 1,
            'expires_after_secs': 60,
            'image': {
                'image_type': 'image/jpeg',
                'h': 1,
                'w': 1,
            },
        }
        expected_body = (
            '--txtwitter\r\n'
            'Content-Disposition: form-data, name=additional_owners\r\n'
            '\r\n'
            '1,2,\r\n'
            '--txtwitter\r\n'
            'Content-Disposition: form-data; name=media; filename=image\r\n'
            'Content-Type: application/octet-stream\r\n'
            '\r\n'
            'raw_binary_content\r\n'
            '--txtwitter--\r\n'
        )
        agent.add_expected_multipart(
            uri, expected_body, self._resp_json(response_dict))
        resp = yield client.media_upload(media, additional_owners=[1, 2])
        self.assertEqual(resp, response_dict)

    # TODO: Tests for statuses_update_with_media()
    # TODO: Tests for statuses_oembed()
    # TODO: Tests for statuses_retweeters_ids()

    # Search

    # TODO: Tests for search_tweets()

    # Streaming

    @inlineCallbacks
    def test_stream_filter_track(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://stream.twitter.com/1.1/statuses/filter.json'
        stream = FakeResponse(None)
        agent.add_expected_request('POST', uri, {'track': 'foo,bar'}, stream)

        connected = Deferred()
        tweets = []
        svc = client.stream_filter(tweets.append, track=['foo', 'bar'])
        svc.set_connect_callback(connected.callback)
        svc.startService()
        connected_svc = yield connected
        self.assertIs(svc, connected_svc)
        self.assertEqual(tweets, [])

        stream.deliver_data(
            '{"id_str": "1", "text": "Tweet 1", "user": {}}\r\n')
        self.assertEqual(tweets, [
            {"id_str": "1", "text": "Tweet 1", "user": {}},
        ])
        stream.deliver_data(
            '{"id_str": "2", "text": "Tweet 2", "user": {}}\r\n')
        self.assertEqual(tweets, [
            {"id_str": "1", "text": "Tweet 1", "user": {}},
            {"id_str": "2", "text": "Tweet 2", "user": {}},
        ])
        yield svc.stopService()
        stream.finished()

    @inlineCallbacks
    def test_stream_filter_all_params(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://stream.twitter.com/1.1/statuses/filter.json'
        stream = FakeResponse(None)
        expected_params = {
            'follow': 'Alice,Bob',
            'track': 'foo,bar',
            'stall_warnings': 'true',
        }
        agent.add_expected_request('POST', uri, expected_params, stream)

        connected = Deferred()
        svc = client.stream_filter(
            lambda tweet: None, follow=['Alice', 'Bob'], track=['foo', 'bar'],
            stall_warnings=True)
        svc.set_connect_callback(connected.callback)
        svc.startService()
        connected_svc = yield connected
        self.assertIs(svc, connected_svc)
        yield svc.stopService()
        stream.finished()

    # TODO: Tests for stream_sample()
    # TODO: Tests for stream_firehose()

    @inlineCallbacks
    def test_userstream_user_with_user(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://userstream.twitter.com/1.1/user.json'
        stream = FakeResponse(None)
        agent.add_expected_request('GET', uri, {
            'stringify_friend_ids': 'true',
            'with': 'user',
        }, stream)

        connected = Deferred()
        tweets = []
        svc = client.userstream_user(tweets.append, with_='user')
        svc.set_connect_callback(connected.callback)
        svc.startService()
        connected_svc = yield connected
        self.assertIs(svc, connected_svc)
        self.assertEqual(tweets, [])

        stream.deliver_data(
            '{"friends_str": []}\r\n'
            '{"id_str": "1", "text": "Tweet 1", "user": {}}\r\n')
        self.assertEqual(tweets, [
            {"friends_str": []},
            {"id_str": "1", "text": "Tweet 1", "user": {}},
        ])
        stream.deliver_data(
            '{"id_str": "2", "text": "Tweet 2", "user": {}}\r\n')
        self.assertEqual(tweets, [
            {"friends_str": []},
            {"id_str": "1", "text": "Tweet 1", "user": {}},
            {"id_str": "2", "text": "Tweet 2", "user": {}},
        ])
        yield svc.stopService()
        stream.finished()

    @inlineCallbacks
    def test_userstream_user_all_params(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://userstream.twitter.com/1.1/user.json'
        stream = FakeResponse(None)
        agent.add_expected_request('GET', uri, {
            'stringify_friend_ids': 'true',
            'stall_warnings': 'true',
            'with': 'user',
            'replies': 'all',
        }, stream)

        connected = Deferred()
        svc = client.userstream_user(
            lambda tweet: None, stall_warnings=True, with_='user',
            replies='all')
        svc.set_connect_callback(connected.callback)
        svc.startService()
        connected_svc = yield connected
        self.assertIs(svc, connected_svc)
        yield svc.stopService()
        stream.finished()

    # Direct Messages

    @inlineCallbacks
    def test_direct_messages(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/direct_messages.json'

        response_data = [{
            # Truncated dm data.
            "id": 1,
            "id_str": "1",
            "text": "hello",
            "sender_id": 1,
            "sender_id_str": "1",
            "sender_screen_name": "fakeuser",
            "recipient_id": 2,
            "recipient_id_str": "2",
            "recipient_screen_name": "fakeuser2",
        }]

        agent.add_expected_request(
            'GET', uri, {}, self._resp_json(response_data))

        resp = yield client.direct_messages()
        self.assertEqual(resp, response_data)

    @inlineCallbacks
    def test_direct_messages_all_params(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/direct_messages.json'

        expected_params = {
            'count': '10',
            'since_id': '123',
            'max_id': '321',
            'skip_status': 'false',
            'include_entities': 'false',
        }

        response_data = [{
            # Truncated dm data.
            "id": 1,
            "id_str": "1",
            "text": "hello",
            "sender_id": 1,
            "sender_id_str": "1",
            "sender_screen_name": "fakeuser",
            "recipient_id": 2,
            "recipient_id_str": "2",
            "recipient_screen_name": "fakeuser2",
        }]

        agent.add_expected_request(
            'GET', uri, expected_params, self._resp_json(response_data))

        resp = yield client.direct_messages(
            count=10, since_id='123', max_id='321', skip_status=False,
            include_entities=False)
        self.assertEqual(resp, response_data)

    @inlineCallbacks
    def test_direct_messages_sent(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/direct_messages/sent.json'

        response_data = [{
            # Truncated dm data.
            "id": 1,
            "id_str": "1",
            "text": "hello",
            "sender_id": 1,
            "sender_id_str": "1",
            "sender_screen_name": "fakeuser",
            "recipient_id": 2,
            "recipient_id_str": "2",
            "recipient_screen_name": "fakeuser2",
        }]

        agent.add_expected_request(
            'GET', uri, {}, self._resp_json(response_data))

        resp = yield client.direct_messages_sent()
        self.assertEqual(resp, response_data)

    @inlineCallbacks
    def test_direct_messages_sent_all_params(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/direct_messages/sent.json'

        expected_params = {
            'count': '10',
            'since_id': '123',
            'max_id': '321',
            'page': '2',
            'include_entities': 'false',
        }

        response_data = [{
            # Truncated dm data.
            "id": 1,
            "id_str": "1",
            "text": "hello",
            "sender_id": 1,
            "sender_id_str": "1",
            "sender_screen_name": "fakeuser",
            "recipient_id": 2,
            "recipient_id_str": "2",
            "recipient_screen_name": "fakeuser2",
        }]

        agent.add_expected_request(
            'GET', uri, expected_params, self._resp_json(response_data))

        resp = yield client.direct_messages_sent(
            count=10, since_id='123', max_id='321', page=2,
            include_entities=False)
        self.assertEqual(resp, response_data)

    @inlineCallbacks
    def test_direct_messages_show(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/direct_messages/show.json'

        response_data = [{
            # Truncated dm data.
            "id": 1,
            "id_str": "1",
            "text": "hello",
            "sender_id": 1,
            "sender_id_str": "1",
            "sender_screen_name": "fakeuser",
            "recipient_id": 2,
            "recipient_id_str": "2",
            "recipient_screen_name": "fakeuser2",
        }]

        agent.add_expected_request(
            'GET', uri, {'id': '1'}, self._resp_json(response_data))

        resp = yield client.direct_messages_show('1')
        self.assertEqual(resp, response_data[0])

    @inlineCallbacks
    def test_direct_messages_show_not_found(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/direct_messages/show.json'

        err_dict = {
            "errors": [{
                "message": "Sorry, that page does not exist",
                "code": 34,
            }]
        }

        agent.add_expected_request(
            'GET', uri, {'id': '1'}, self._resp_json(err_dict, 404))

        d = client.direct_messages_show("1")
        d.addErrback(lambda f: f.value)
        err = yield d

        code, _phrase, body = err.args
        self.assertEqual((404, err_dict), (code, json.loads(body)))

    @inlineCallbacks
    def test_direct_messages_show_forbidden(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/direct_messages/show.json'

        err_dict = {
            "errors": [{
                "message": "There was an error sending your message: .",
                "code": 151
            }]
        }

        agent.add_expected_request(
            'GET', uri, {'id': '1'}, self._resp_json(err_dict, 403))

        d = client.direct_messages_show("1")
        d.addErrback(lambda f: f.value)
        err = yield d

        code, _phrase, body = err.args
        self.assertEqual((403, err_dict), (code, json.loads(body)))

    @inlineCallbacks
    def test_direct_messages_destroy(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/direct_messages/destroy.json'

        response_data = {
            # Truncated dm data.
            "id": 1,
            "id_str": "1",
            "text": "hello",
            "sender_id": 1,
            "sender_id_str": "1",
            "sender_screen_name": "fakeuser",
            "recipient_id": 2,
            "recipient_id_str": "2",
            "recipient_screen_name": "fakeuser2",
        }

        agent.add_expected_request(
            'POST', uri, {'id': '1'}, self._resp_json(response_data))

        resp = yield client.direct_messages_destroy('1')
        self.assertEqual(resp, response_data)

    @inlineCallbacks
    def test_direct_messages_destroy_all_params(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/direct_messages/destroy.json'

        expected_params = {
            'id': '1',
            'include_entities': 'false'
        }

        response_data = {
            # Truncated dm data.
            "id": 1,
            "id_str": "1",
            "text": "hello",
            "sender_id": 1,
            "sender_id_str": "1",
            "sender_screen_name": "fakeuser",
            "recipient_id": 2,
            "recipient_id_str": "2",
            "recipient_screen_name": "fakeuser2",
        }

        agent.add_expected_request(
            'POST', uri, expected_params, self._resp_json(response_data))

        resp = yield client.direct_messages_destroy(
            '1', include_entities=False)
        self.assertEqual(resp, response_data)

    @inlineCallbacks
    def test_direct_messages_destroy_not_found(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/direct_messages/destroy.json'

        err_dict = {
            "errors": [{
                "message": "Sorry, that page does not exist",
                "code": 34,
            }]
        }

        agent.add_expected_request(
            'POST', uri, {'id': '1'}, self._resp_json(err_dict, 404))

        d = client.direct_messages_destroy("1")
        d.addErrback(lambda f: f.value)
        err = yield d

        code, _phrase, body = err.args
        self.assertEqual((404, err_dict), (code, json.loads(body)))

    @inlineCallbacks
    def test_direct_messages_destroy_forbidden(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/direct_messages/destroy.json'

        err_dict = {
            "errors": [{
                "message": "There was an error sending your message: .",
                "code": 151
            }]
        }

        agent.add_expected_request(
            'POST', uri, {'id': '1'}, self._resp_json(err_dict, 403))

        d = client.direct_messages_destroy("1")
        d.addErrback(lambda f: f.value)
        err = yield d

        code, _phrase, body = err.args
        self.assertEqual((403, err_dict), (code, json.loads(body)))

    @inlineCallbacks
    def test_direct_messages_new_by_user_id(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/direct_messages/new.json'

        expected_params = {
            'text': 'hello',
            'user_id': '2'
        }

        response_data = {
            # Truncated dm data.
            "id": 1,
            "id_str": "1",
            "text": "hello",
            "sender_id": 1,
            "sender_id_str": "1",
            "sender_screen_name": "fakeuser",
            "recipient_id": 2,
            "recipient_id_str": "2",
            "recipient_screen_name": "fakeuser2",
        }

        agent.add_expected_request(
            'POST', uri, expected_params, self._resp_json(response_data))

        resp = yield client.direct_messages_new('hello', user_id='2')
        self.assertEqual(resp, response_data)

    @inlineCallbacks
    def test_direct_messages_new_by_screen_name(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/direct_messages/new.json'

        expected_params = {
            'text': 'hello',
            'screen_name': 'fakeuser2'
        }

        response_data = {
            # Truncated dm data.
            "id": 1,
            "id_str": "1",
            "text": "hello",
            "sender_id": 1,
            "sender_id_str": "1",
            "sender_screen_name": "fakeuser",
            "recipient_id": 2,
            "recipient_id_str": "2",
            "recipient_screen_name": "fakeuser2",
        }

        agent.add_expected_request(
            'POST', uri, expected_params, self._resp_json(response_data))

        resp = yield client.direct_messages_new(
            'hello', screen_name='fakeuser2')
        self.assertEqual(resp, response_data)

    @inlineCallbacks
    def test_direct_messages_new_bad_request(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/direct_messages/new.json'

        err_dict = {
            "errors": [{
                "message": (
                    "Recipient (user, screen name, or id) "
                    "parameter is missing."),
                "code": 38
            }]
        }

        agent.add_expected_request(
            'POST', uri, {'text': 'hello'}, self._resp_json(err_dict, 403))

        d = client.direct_messages_new('hello')
        d.addErrback(lambda f: f.value)
        err = yield d

        code, _phrase, body = err.args
        self.assertEqual((403, err_dict), (code, json.loads(body)))

    # Friends & Followers

    # TODO: Tests for friendships_no_retweets_ids()
    # TODO: Tests for friends_ids()
    # TODO: Tests for followers_ids()
    # TODO: Tests for friendships_lookup()
    # TODO: Tests for friendships_incoming()
    # TODO: Tests for friendships_outgoing()

    @inlineCallbacks
    def test_friendships_create_by_user_id(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/friendships/create.json'

        expected_params = {
            'user_id': '2'
        }

        response_data = {
            # Truncated user data.
            "id": 2,
            "id_str": "2",
            "screen_name": "fakeuser2",
        }

        agent.add_expected_request(
            'POST', uri, expected_params, self._resp_json(response_data))

        resp = yield client.friendships_create(user_id='2')
        self.assertEqual(resp, response_data)

    @inlineCallbacks
    def test_friendships_create_by_screen_name(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/friendships/create.json'

        expected_params = {
            'screen_name': 'fakeuser2'
        }

        response_data = {
            # Truncated user data.
            "id": 2,
            "id_str": "2",
            "screen_name": "fakeuser2",
        }

        agent.add_expected_request(
            'POST', uri, expected_params, self._resp_json(response_data))

        resp = yield client.friendships_create(screen_name='fakeuser2')
        self.assertEqual(resp, response_data)

    @inlineCallbacks
    def test_friendships_create_follow(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/friendships/create.json'

        expected_params = {
            'screen_name': 'fakeuser2',
            'follow': 'true'
        }

        response_data = {
            # Truncated user data.
            "id": 2,
            "id_str": "2",
            "screen_name": "fakeuser2",
        }

        agent.add_expected_request(
            'POST', uri, expected_params, self._resp_json(response_data))

        resp = yield client.friendships_create(
            screen_name='fakeuser2', follow=True)
        self.assertEqual(resp, response_data)

    @inlineCallbacks
    def test_friendships_create_forbidden(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/friendships/create.json'

        err_dict = {
            "errors": [{
                "message": "Cannot find specified user.",
                "code": 108
            }]
        }

        agent.add_expected_request(
            'POST', uri, {}, self._resp_json(err_dict, 403))

        d = client.friendships_create()
        d.addErrback(lambda f: f.value)
        err = yield d

        code, _phrase, body = err.args
        self.assertEqual((403, err_dict), (code, json.loads(body)))

    @inlineCallbacks
    def test_friendships_destroy_by_user_id(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/friendships/destroy.json'

        expected_params = {
            'user_id': '2'
        }

        response_data = {
            # Truncated user data.
            "id": 2,
            "id_str": "2",
            "screen_name": "fakeuser2",
        }

        agent.add_expected_request(
            'POST', uri, expected_params, self._resp_json(response_data))

        resp = yield client.friendships_destroy(user_id='2')
        self.assertEqual(resp, response_data)

    @inlineCallbacks
    def test_friendships_destroy_by_screen_name(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/friendships/destroy.json'

        expected_params = {
            'screen_name': 'fakeuser2'
        }

        response_data = {
            # Truncated user data.
            "id": 2,
            "id_str": "2",
            "screen_name": "fakeuser2",
        }

        agent.add_expected_request(
            'POST', uri, expected_params, self._resp_json(response_data))

        resp = yield client.friendships_destroy(screen_name='fakeuser2')
        self.assertEqual(resp, response_data)

    @inlineCallbacks
    def test_friendships_destroy_forbidden(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/friendships/destroy.json'

        err_dict = {
            "errors": [{
                "message": "Sorry, that page does not exist",
                "code": 34},
            ]
        }

        agent.add_expected_request(
            'POST', uri, {}, self._resp_json(err_dict, 404))

        d = client.friendships_destroy()
        d.addErrback(lambda f: f.value)
        err = yield d

        code, _phrase, body = err.args
        self.assertEqual((404, err_dict), (code, json.loads(body)))

    # TODO: Tests for friendships_update()
    # TODO: Tests for friendships_show()
    # TODO: Tests for friends_list()
    # TODO: Tests for followers_list()

    # Users

    # TODO: Tests for account_settings()
    # TODO: Tests for account_verify_credentials()
    # TODO: Tests for account_settings()
    # TODO: Tests for account_update_delivery_device()
    # TODO: Tests for account_update_profile()
    # TODO: Tests for account_update_profile_background_image()
    # TODO: Tests for account_update_profile_colors()
    # TODO: Tests for account_update_profile_image()
    # TODO: Tests for blocks_list()
    # TODO: Tests for blocks_ids()
    # TODO: Tests for blocks_create()
    # TODO: Tests for blocks_destroy()
    # TODO: Tests for users_lookup()
    # TODO: Tests for users_show()
    # TODO: Tests for users_search()
    # TODO: Tests for users_contributees()
    # TODO: Tests for users_contributors()
    # TODO: Tests for account_remove_profile_banner()
    # TODO: Tests for account_update_profile_banner()
    # TODO: Tests for users/profile_banner()

    # Suggested Users

    # TODO: Tests for users_suggestions()
    # TODO: Tests for users_suggestions()
    # TODO: Tests for users_suggestions_members()

    # Favorites

    # TODO: Tests for favorites_list()
    # TODO: Tests for favorites_destroy()
    # TODO: Tests for favorites_create()

    # Lists

    # TODO: Tests for lists_list()
    # TODO: Tests for lists_statuses()
    # TODO: Tests for lists_members_destroy()
    # TODO: Tests for lists_memberships()
    # TODO: Tests for lists_subscribers()
    # TODO: Tests for lists_subscribers/create()
    # TODO: Tests for lists_subscribers/show()
    # TODO: Tests for lists_subscribers/destroy()
    # TODO: Tests for lists_members_create_all()
    # TODO: Tests for lists_members_show()
    # TODO: Tests for lists_members()
    # TODO: Tests for lists_members_create()
    # TODO: Tests for lists_destroy()
    # TODO: Tests for lists_update()
    # TODO: Tests for lists_create()
    # TODO: Tests for lists_show()
    # TODO: Tests for lists_subscriptions()
    # TODO: Tests for lists_members_destroy_all()
    # TODO: Tests for lists_ownerships()

    # Saved Searches

    # TODO: Tests for saved_searches_list()
    # TODO: Tests for saved_searches_show()
    # TODO: Tests for saved_searches_create()
    # TODO: Tests for saved_searches_destroy()

    # Places & Geo

    # TODO: Tests for geo_id()
    # TODO: Tests for geo_reverse_geocode()
    # TODO: Tests for geo_search()
    # TODO: Tests for geo_similar_places()
    # TODO: Tests for geo_place()

    # Trends

    # TODO: Tests for trends_place()
    # TODO: Tests for trends_available()
    # TODO: Tests for trends_closest()

    # Spam Reporting

    # TODO: Tests for users_report_spam()

    # Help

    # TODO: Tests for help_configuration()
    # TODO: Tests for help_languages()
    # TODO: Tests for help_privacy()
    # TODO: Tests for help_tos()
    # TODO: Tests for application_rate_limit_status()
