import json
from StringIO import StringIO
from urlparse import parse_qsl, urlsplit, urlunsplit

from oauth2 import Token, Consumer
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.python.failure import Failure
from twisted.trial.unittest import TestCase
from twisted.web.client import ResponseDone, FileBodyProducer, readBody
from twisted.web.http import RESPONSES
from twisted.web.http_headers import Headers


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


class FakeTransport(object):
    disconnecting = False


class FakeResponse(object):
    def __init__(self, body, code=200):
        self.code = code
        self.phrase = RESPONSES[code]
        self._body = body

    def deliver_data(self, data):
        self._protocol.dataReceived(data)

    def finished(self, reason=None):
        if reason is None:
            reason = Failure(ResponseDone("Response body fully received"))
        self._protocol.connectionLost(reason)

    def deliverBody(self, protocol):
        self._protocol = protocol
        protocol.makeConnection(FakeTransport())
        if self._body is not None:
            self.deliver_data(self._body)
            self.finished()


def resp_json(data, code=200):
    return FakeResponse(json.dumps(data), code)


class FakeAgent(object):
    def __init__(self):
        self.expected_requests = {}

    def add_expected_request(self, method, uri, params, response):
        key = (method, urlsplit(uri).geturl(), tuple(sorted(params.items())))
        self.expected_requests[key] = response

    @inlineCallbacks
    def request(self, method, uri, headers=None, bodyProducer=None):
        scheme, netloc, path, query, fragment = urlsplit(uri)
        uri = urlunsplit([scheme, netloc, path, '', ''])
        params = parse_qsl(query)

        if bodyProducer is not None:
            ctypes = headers.getRawHeaders('Content-Type')
            if ctypes == ['application/x-www-form-urlencoded']:
                consumer = StringIO()
                yield bodyProducer.startProducing(consumer)
                params.extend(parse_qsl(consumer.getvalue()))

        key = (method, uri, tuple(sorted(params)))
        assert key in self.expected_requests, (
            "Request key not found: %s" % (key,))

        returnValue(self.expected_requests[key])


class TestFakeAgent(TestCase):
    def test_unexpected_request(self):
        agent = FakeAgent()
        return self.assertFailure(agent.request('GET', 'foo'), AssertionError)

    @inlineCallbacks
    def test_no_params(self):
        agent = FakeAgent()
        fake_resp = object()
        agent.add_expected_request('GET', 'foo', {}, fake_resp)
        resp = yield agent.request('GET', 'foo')
        self.assertEqual(resp, fake_resp)

    @inlineCallbacks
    def test_uri_params(self):
        agent = FakeAgent()
        fake_resp = object()
        agent.add_expected_request('GET', 'foo', {'a': 'b'}, fake_resp)
        resp = yield agent.request('GET', 'foo?a=b')
        self.assertEqual(resp, fake_resp)

    @inlineCallbacks
    def test_body_params(self):
        agent = FakeAgent()
        fake_resp = object()
        agent.add_expected_request('POST', 'foo', {'a': 'b'}, fake_resp)
        resp = yield agent.request(
            'POST', 'foo', Headers({
                'Content-Type': ['application/x-www-form-urlencoded'],
            }), FileBodyProducer(StringIO('a=b')))
        self.assertEqual(resp, fake_resp)

    def test_response_static(self):
        resp = FakeResponse('foo', 400)
        body = self.successResultOf(readBody(resp))
        self.assertEqual(body, 'foo')
        self.assertEqual(resp.code, 400)

    def test_response_dynamic(self):
        resp = FakeResponse(None)
        self.assertEqual(resp.code, 200)
        d = readBody(resp)
        self.assertNoResult(d)
        resp.deliver_data('lin')
        self.assertNoResult(d)
        resp.deliver_data('e 1\nline 2\n')
        self.assertNoResult(d)
        resp.finished()
        body = self.successResultOf(d)
        self.assertEqual(body, 'line 1\nline 2\n')


class TestTwitterClient(TestCase):
    def _TwitterClient(self, *args, **kw):
        from txtwitter.twitter import TwitterClient
        return TwitterClient(*args, **kw)

    def _agent_and_TwitterClient(self):
        agent = FakeAgent()
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
            'GET', uri, {'id': '123'}, resp_json(response_dict))
        resp = yield client.show("123")
        self.assertEqual(resp, response_dict)

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
            'POST', uri, {'status': 'Tweet!'}, resp_json(response_dict))
        resp = yield client.update("Tweet!")
        self.assertEqual(resp, response_dict)

    @inlineCallbacks
    def test_stream_filter_track(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://stream.twitter.com/1.1/statuses/filter.json'
        stream = FakeResponse(None)
        agent.add_expected_request('POST', uri, {'track': 'foo,bar'}, stream)

        tweets = []

        def receive_tweet(tweet):
            tweets.append(tweet)

        resp = yield client.stream_filter(receive_tweet, track=['foo', 'bar'])
        self.assertEqual(resp.code, 200)
        self.assertEqual(tweets, [])

        stream.deliver_data('{"id_str": "1", "text": "Tweet 1"}\r\n')
        self.assertEqual(tweets, [
            {"id_str": "1", "text": "Tweet 1"},
        ])

        stream.deliver_data('{"id_str": "2", "text": "Tweet 2"}\r\n')
        self.assertEqual(tweets, [
            {"id_str": "1", "text": "Tweet 1"},
            {"id_str": "2", "text": "Tweet 2"},
        ])

        stream.finished()
