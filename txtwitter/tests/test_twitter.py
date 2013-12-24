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


class FakeResponse(object):
    def __init__(self, code, body):
        self.code = code
        self.phrase = RESPONSES[code]
        self._body = body

    def deliverBody(self, protocol):
        protocol.dataReceived(self._body)
        protocol.connectionLost(
            Failure(ResponseDone("Response body fully received")))


class FakeAgent(object):
    def __init__(self):
        self.expected_requests = {}

    def add_expected_request(self, method, uri, params, resp_code, resp_body):
        key = (method, urlsplit(uri).geturl(), tuple(sorted(params.items())))
        self.expected_requests[key] = (resp_code, resp_body)

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
        resp_code, resp_body = self.expected_requests[key]

        returnValue(FakeResponse(resp_code, resp_body))


class TestFakeAgent(TestCase):
    def test_unexpected_request(self):
        agent = FakeAgent()
        return self.assertFailure(agent.request('GET', 'foo'), AssertionError)

    @inlineCallbacks
    def test_no_params(self):
        agent = FakeAgent()
        agent.add_expected_request('GET', 'foo', {}, 200, '')
        resp = yield agent.request('GET', 'foo')
        self.assertEqual(resp.code, 200)

    @inlineCallbacks
    def test_uri_params(self):
        agent = FakeAgent()
        agent.add_expected_request('GET', 'foo', {'a': 'b'}, 200, '')
        resp = yield agent.request('GET', 'foo?a=b')
        self.assertEqual(resp.code, 200)

    @inlineCallbacks
    def test_body_params(self):
        agent = FakeAgent()
        agent.add_expected_request('POST', 'foo', {'a': 'b'}, 200, '')
        resp = yield agent.request(
            'POST', 'foo', Headers({
                'Content-Type': ['application/x-www-form-urlencoded'],
            }), FileBodyProducer(StringIO('a=b')))
        self.assertEqual(resp.code, 200)

    @inlineCallbacks
    def test_response_body(self):
        agent = FakeAgent()
        agent.add_expected_request('GET', 'foo', {}, 200, 'blah')
        resp = yield agent.request('GET', 'foo')
        self.assertEqual(resp.code, 200)
        body = yield readBody(resp)
        self.assertEqual(body, 'blah')


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
            "created_at": "Wed Jun 06 20:07:10 +0000 2012",
            "id": 123,
            "id_str": "123",
            "text": "Tweet!",
        }
        agent.add_expected_request(
            'GET', uri, {'id': '123'}, 200, json.dumps(response_dict))
        resp = yield client.show("123")
        self.assertEqual(resp, response_dict)

    @inlineCallbacks
    def test_update(self):
        agent, client = self._agent_and_TwitterClient()
        uri = 'https://api.twitter.com/1.1/statuses/update.json'
        response_dict = {
            # Truncated tweet data.
            "created_at": "Wed Jun 06 20:07:10 +0000 2012",
            "id": 123,
            "id_str": "123",
            "text": "Tweet!",
        }
        agent.add_expected_request(
            'POST', uri, {'status': 'Tweet!'}, 200, json.dumps(response_dict))
        resp = yield client.update("Tweet!")
        self.assertEqual(resp, response_dict)

    # @inlineCallbacks
    # def test_foo(self):
    #     agent, client = self._agent_and_TwitterClient()

    #     agent.add_expected_request(
    #         'GET', 'https://example.com/', {'foo': 'bar'}, 200, '')
    #     agent.add_expected_request(
    #         'POST', 'https://example.com/', {'foo': 'bar'}, 200, '')

    #     resp = yield client._get_request('https://example.com/?foo=bar')
    #     self.assertEqual(resp.code, 200)
    #     resp = yield client._post_request(
    #         'https://example.com/', {'foo': 'bar'})
    #     self.assertEqual(resp.code, 200)
