from StringIO import StringIO
from urlparse import parse_qsl, urlsplit, urlunsplit

from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.python.failure import Failure
from twisted.web.client import ResponseDone
from twisted.web.http import RESPONSES


class FakeTransport(object):
    disconnecting = False

    def stopProducing(self):
        pass


class FakeResponse(object):
    def __init__(self, body, code=200):
        self.code = code
        if code == 420:
            self.phrase = 'Rate Limited'
        else:
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
