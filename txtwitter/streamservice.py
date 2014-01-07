import json

from twisted.application.service import Service
from twisted.internet.defer import CancelledError
from twisted.protocols.basic import LineOnlyReceiver
from twisted.protocols.policies import TimeoutMixin
from twisted.python.failure import Failure
from twisted.web.client import ResponseDone
from twisted.web.http import PotentialDataLoss

from txtwitter.error import RateLimitedError, TwitterAPIError


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

    For now, we just do an exponential backoff starting at one second and
    doubling every time we reconnect to a maximum of ten minutes. For explicit
    rate limiting, we start at 30 seconds instead of one second.
    """

    RECONNECT_DELAY_INITIAL = 1
    RECONNECT_DELAY_RATE_LIMIT = 30  # This gets doubled the first time.
    RECONNECT_DELAY_MULTIPLIER = 2
    RECONNECT_DELAY_MAX = 60 * 10

    clock = None

    _connect_d = None
    _stream_response = None
    _stream_protocol = None
    _reconnect_delayedcall = None

    connect_callback = None
    disconnect_callback = None
    reconnect_delay = 0

    def __init__(self, connect_func, delegate):
        self.connect_func = connect_func
        self.delegate = delegate

    def startService(self):
        Service.startService(self)

        if self.clock is None:
            from twisted.internet import reactor
            self.clock = reactor

        self._connect()

    def stopService(self):
        Service.stopService(self)
        if self._stream_protocol is not None:
            self._stream_protocol.transport.stopProducing()
        if self._reconnect_delayedcall is not None:
            self._reconnect_delayedcall.cancel()
            self._reconnect_delayedcall = None
        if self._connect_d is not None:
            self._connect_d.addErrback(lambda f: f.trap(CancelledError))
            self._connect_d.cancel()
            self._connect_d = None
        self.reconnect_delay = 0

    def connection_lost(self, reason):
        self._stream_response = None
        self._stream_protocol = None
        if reason.check(PotentialDataLoss):
            reason = Failure(ResponseDone())
        if self.disconnect_callback is not None:
            self.disconnect_callback(self, reason)
        self._reconnect()

    def set_connect_callback(self, callback):
        self.connect_callback = callback

    def set_disconnect_callback(self, callback):
        self.disconnect_callback = callback

    def _setup_stream(self, response):
        self._connect_d = None
        if response.code != 200:
            self._handle_HTTP_error(response)
            return

        self.reconnect_delay = self.RECONNECT_DELAY_INITIAL
        self._stream_response = response
        self._stream_protocol = TwitterStreamProtocol(self)
        response.deliverBody(self._stream_protocol)
        if self.connect_callback is not None:
            self.connect_callback(self)

    def _handle_HTTP_error(self, response):
        if response.code == 420:
            # We've been rate-limited.
            if self.reconnect_delay < self.RECONNECT_DELAY_RATE_LIMIT:
                self.reconnect_delay = self.RECONNECT_DELAY_RATE_LIMIT
            self.connection_lost(Failure(RateLimitedError(response.code)))
        else:
            # General HTTP error.
            self.connection_lost(Failure(TwitterAPIError(response.code)))

    def _connect(self):
        self._reconnect_delayedcall = None
        self._connect_d = self.connect_func()
        self._connect_d.addCallback(self._setup_stream)

    def _reconnect(self):
        if not self.running:
            return

        self._update_reconnect_delay()
        self._reconnect_delayedcall = self.clock.callLater(
            self.reconnect_delay, self._connect)

    def _update_reconnect_delay(self):
        if self.reconnect_delay < self.RECONNECT_DELAY_INITIAL:
            self.reconnect_delay = self.RECONNECT_DELAY_INITIAL
        else:
            self.reconnect_delay *= self.RECONNECT_DELAY_MULTIPLIER
        if self.reconnect_delay > self.RECONNECT_DELAY_MAX:
            self.reconnect_delay = self.RECONNECT_DELAY_MAX
