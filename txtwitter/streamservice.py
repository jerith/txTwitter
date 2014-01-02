import json

from twisted.application.service import Service
from twisted.protocols.basic import LineOnlyReceiver
from twisted.protocols.policies import TimeoutMixin
from twisted.python.failure import Failure
from twisted.web.client import ResponseDone
from twisted.web.http import PotentialDataLoss


class TwitterStreamProtocol(LineOnlyReceiver, TimeoutMixin):
    def __init__(self, service):
        self.service = service

    def lineReceived(self, line):
        if line:
            self.service.delegate(json.loads(line))

    def connectionLost(self, reason):
        self.service.connection_lost(reason)


class TwitterStreamService(Service):
    """
    Streaming API service.

    This service handles reconnection, but does not backfill.

    From Twitter's API docs, regarding reconnections:
        <https://dev.twitter.com/docs/streaming-apis/connecting>

        Once an established connection drops, attempt to reconnect immediately.
        If the reconnect fails, slow down your reconnect attempts according to
        the type of error experienced:

         * Back off linearly for TCP/IP level network errors. These problems
           are generally temporary and tend to clear quickly. Increase the
           delay in reconnects by 250ms each attempt, up to 16 seconds.

         * Back off exponentially for HTTP errors for which reconnecting would
           be appropriate. Start with a 5 second wait, doubling each attempt,
           up to 320 seconds.

         * Back off exponentially for HTTP 420 errors. Start with a 1 minute
           wait and double each attempt. Note that every HTTP 420 received
           increases the time you must wait until rate limiting will no longer
           will be in effect for your account.
    """

    # TODO: Reconnections and backoff.

    _stream_response = None
    _stream_protocol = None
    connect_callback = None
    disconnect_callback = None

    def __init__(self, connect_func, delegate):
        self.connect_func = connect_func
        self.delegate = delegate

    def _setup_stream(self, response):
        self._stream_response = response
        self._stream_protocol = TwitterStreamProtocol(self)
        response.deliverBody(self._stream_protocol)
        if self.connect_callback is not None:
            self.connect_callback(self)

    def startService(self):
        Service.startService(self)
        self.connect_func().addCallback(self._setup_stream)

    def stopService(self):
        Service.stopService(self)
        if self._stream_protocol is not None:
            self._stream_protocol.transport.stopProducing()
        self.connected.cancel()

    def connection_lost(self, reason):
        self._stream_response = None
        self._stream_protocol = None
        if reason.check(PotentialDataLoss):
            reason = Failure(ResponseDone())
        if self.disconnect_callback is not None:
            self.disconnect_callback(self, reason)

    def set_connect_callback(self, callback):
        self.connect_callback = callback

    def set_disconnect_callback(self, callback):
        self.disconnect_callback = callback
