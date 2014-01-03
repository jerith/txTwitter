import json

from oauth2 import Token, Consumer
from twisted.internet.defer import Deferred, inlineCallbacks
from twisted.trial.unittest import TestCase


class TestAuthHelpers(TestCase):
    def _make_auth_header(self, *args, **kw):
        from txtwitter.twitter import make_auth_header
        return make_auth_header(*args, **kw)

    def assert_in(self, needle, haystack):
        self.assertTrue(
            needle in haystack, "%r is not in %r" % (needle, haystack))

    def test_make_auth_header(self):
        token = Token(key='token-key', secret='token-secret')
        consumer = Consumer(key='consumer-key', secret='consumer-secret')
        auth_header = self._make_auth_header(
            token, consumer, 'GET', 'https://example.com', {})

        self.assert_in('oauth_token', auth_header)
        self.assert_in('oauth_consumer_key', auth_header)
        self.assert_in('oauth_version', auth_header)
        self.assert_in('oauth_nonce', auth_header)
        self.assert_in('oauth_timestamp', auth_header)
        self.assert_in('oauth_signature', auth_header)

    def test_make_auth_header_equivalent_param_types(self):
        token = Token(key='token-key', secret='token-secret')
        consumer = Consumer(key='consumer-key', secret='consumer-secret')

        # We provide `oauth_nonce` and `oauth_timestamp` to make the hash
        # deterministic.
        auth_params_in_url = self._make_auth_header(
            token, consumer, 'GET', 'https://example.com?foo=bar', {
                'oauth_nonce': 'nonce',
                'oauth_timestamp': '1234567890',
            })
        auth_params_in_params = self._make_auth_header(
            token, consumer, 'GET', 'https://example.com', {
                'oauth_nonce': 'nonce',
                'oauth_timestamp': '1234567890',
                'foo': 'bar',
            })
        self.assertEqual(auth_params_in_url, auth_params_in_params)

        # And another one with no params to make sure it's different.
        auth_no_params = self._make_auth_header(
            token, consumer, 'GET', 'https://example.com', {
                'oauth_nonce': 'nonce',
                'oauth_timestamp': '1234567890',
            })
        self.assertNotEqual(auth_params_in_url, auth_no_params)


class TestTwitterClient(TestCase):
    timeout = 1

    def _TwitterClient(self, *args, **kw):
        from txtwitter.twitter import TwitterClient
        return TwitterClient(*args, **kw)

    def _FakeAgent(self):
        from txtwitter.tests.fake_agent import FakeAgent
        return FakeAgent()

    def _FakeResponse(self, *args, **kw):
        from txtwitter.tests.fake_agent import FakeResponse
        return FakeResponse(*args, **kw)

    def _resp_json(self, data, code=200):
        return self._FakeResponse(json.dumps(data), code)

    def _agent_and_TwitterClient(self):
        agent = self._FakeAgent()
        client = self._TwitterClient(
            'token-key', 'token-secret', 'consumer-key', 'consumer-secret',
            agent=agent)
        return agent, client

    @inlineCallbacks
    def test_show(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/statuses/show.json'
        response_dict = {
            # Truncated tweet data.
            "id_str": "123",
            "text": "Tweet!",
        }
        agent.add_expected_request(
            'GET', uri, {'id': '123'}, self._resp_json(response_dict))
        resp = yield client.show("123")
        self.assertEqual(resp, response_dict)

    @inlineCallbacks
    def test_show_HTTP_404(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/statuses/show.json'
        err_dict = {"errors": [
            {"message": "Sorry, that page does not exist", "code": 34},
        ]}
        agent.add_expected_request(
            'GET', uri, {'id': '123'}, self._resp_json(err_dict, 404))
        err = yield client.show("123").addErrback(lambda f: f.value)
        code, _phrase, body = err.args
        self.assertEqual((404, err_dict), (code, json.loads(body)))

    @inlineCallbacks
    def test_update(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/statuses/update.json'
        response_dict = {
            # Truncated tweet data.
            "id_str": "123",
            "text": "Tweet!",
        }
        agent.add_expected_request(
            'POST', uri, {'status': 'Tweet!'}, self._resp_json(response_dict))
        resp = yield client.update("Tweet!")
        self.assertEqual(resp, response_dict)

    @inlineCallbacks
    def test_stream_filter_track(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://stream.twitter.com/1.1/statuses/filter.json'
        stream = self._FakeResponse(None)
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
    def test_userstream_with_user(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://userstream.twitter.com/1.1/user.json'
        stream = self._FakeResponse(None)
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
