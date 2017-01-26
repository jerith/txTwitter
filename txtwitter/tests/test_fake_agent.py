from StringIO import StringIO

from twisted.internet.defer import inlineCallbacks
from twisted.trial.unittest import TestCase
from twisted.web.client import FileBodyProducer, readBody
from twisted.web.http_headers import Headers


def from_fake_agent(name):
    @property
    def prop(self):
        from txtwitter.tests import fake_agent
        return getattr(fake_agent, name)
    return prop


class TestFakeAgent(TestCase):
    _FakeAgent = from_fake_agent('FakeAgent')
    _FakeResponse = from_fake_agent('FakeResponse')

    def test_unexpected_request(self):
        agent = self._FakeAgent()
        return self.assertFailure(agent.request('GET', 'foo'), AssertionError)

    @inlineCallbacks
    def test_no_params(self):
        agent = self._FakeAgent()
        fake_resp = object()
        agent.add_expected_request('GET', 'foo', {}, fake_resp)
        resp = yield agent.request('GET', 'foo')
        self.assertEqual(resp, fake_resp)

    @inlineCallbacks
    def test_uri_params(self):
        agent = self._FakeAgent()
        fake_resp = object()
        agent.add_expected_request('GET', 'foo', {'a': 'b'}, fake_resp)
        resp = yield agent.request('GET', 'foo?a=b')
        self.assertEqual(resp, fake_resp)

    @inlineCallbacks
    def test_body_params(self):
        agent = self._FakeAgent()
        fake_resp = object()
        agent.add_expected_request('POST', 'foo', {'a': 'b'}, fake_resp)
        resp = yield agent.request(
            'POST', 'foo', Headers({
                'Content-Type': ['application/x-www-form-urlencoded'],
            }), FileBodyProducer(StringIO('a=b')))
        self.assertEqual(resp, fake_resp)

    @inlineCallbacks
    def test_multipart_request(self):
        agent = self._FakeAgent()
        fake_resp = object()
        agent.add_expected_multipart('foo', 'multipart_body', fake_resp)
        resp = yield agent.request(
            'POST', 'foo', Headers({
                'Content-Type': ['multipart/form-data; boundary=txtwitter'],
            }), FileBodyProducer(StringIO('multipart_body')))
        self.assertEqual(resp, fake_resp)

    def test_response_static(self):
        resp = self._FakeResponse('foo', 400)
        body = self.successResultOf(readBody(resp))
        self.assertEqual(body, 'foo')
        self.assertEqual(resp.code, 400)

    def test_response_dynamic(self):
        resp = self._FakeResponse(None)
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

    def test_response_dynamic_delayed(self):
        resp = self._FakeResponse(None)
        self.assertEqual(resp.code, 200)
        resp.deliver_data('line 1\nli')
        d = readBody(resp)
        self.assertNoResult(d)
        resp.deliver_data('ne 2\n')
        self.assertNoResult(d)
        resp.finished()
        body = self.successResultOf(d)
        self.assertEqual(body, 'line 1\nline 2\n')
