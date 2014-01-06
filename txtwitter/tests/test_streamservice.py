from twisted.internet.defer import Deferred
from twisted.internet.task import Clock
from twisted.python.failure import Failure
from twisted.trial.unittest import TestCase


class TestTwitterClient(TestCase):
    def _TwitterStreamService(self, *args, **kw):
        from txtwitter.streamservice import TwitterStreamService
        return TwitterStreamService(*args, **kw)

    def _FakeResponse(self, *args, **kw):
        from txtwitter.tests.fake_agent import FakeResponse
        return FakeResponse(*args, **kw)

    def test_set_connect_callback(self):
        """
        set_connect_callback() should set the service's connect callback.
        """
        svc = self._TwitterStreamService(None, None)
        self.assertEqual(svc.connect_callback, None)
        svc.set_connect_callback('foo')
        self.assertEqual(svc.connect_callback, 'foo')

    def test_connect_callback(self):
        """
        The connect callback should be called on a successful connection.
        """
        d = Deferred()
        called = []
        svc = self._TwitterStreamService(lambda: d, None)
        svc.set_connect_callback(lambda s: called.append(s))
        svc.startService()
        self.assertEqual(called, [])
        d.callback(self._FakeResponse(None))
        self.assertEqual(called, [svc])

    def test_connect_callback_None(self):
        """
        The connect callback should not be called if it is unset.

        It's hard to assert that something /doesn't/ happen, so we make sure we
        see something else that happens at connect time and assert that no
        errors were logged.
        """
        d = Deferred()
        svc = self._TwitterStreamService(lambda: d, None)
        svc.startService()
        self.assertEqual(None, svc.connect_callback)
        self.assertEqual(None, svc._stream_response)
        d.callback(self._FakeResponse(None))
        self.assertNotEqual(None, svc._stream_response)
        self.assertEqual([], self.flushLoggedErrors())

    def test_set_disconnect_callback(self):
        """
        set_disconnect_callback() should set the service's disconnect callback.
        """
        svc = self._TwitterStreamService(None, None)
        self.assertEqual(svc.disconnect_callback, None)
        svc.set_disconnect_callback('foo')
        self.assertEqual(svc.disconnect_callback, 'foo')

    def test_disconnect_callback(self):
        """
        The disconnect callback should be called on disconnection.
        """
        called = []
        svc = self._TwitterStreamService(None, None)
        svc.set_disconnect_callback(lambda s, r: called.append((s, r)))
        self.assertEqual(called, [])
        failure = Failure(Exception())
        svc.connection_lost(failure)
        self.assertEqual(called, [(svc, failure)])

    def test_disconnect_callback_None(self):
        """
        The disconnect callback should not be called if it is unset.

        It's hard to assert that something /doesn't/ happen, so we make sure we
        see something else that happens at disconnect time and assert that no
        errors were logged.
        """
        svc = self._TwitterStreamService(None, None)
        svc._stream_response = 'foo'
        self.assertEqual(svc.disconnect_callback, None)
        failure = Failure(Exception())
        svc.connection_lost(failure)
        self.assertEqual([], self.flushLoggedErrors())

    def test_HTTP_500_initial_reconnect_delay(self):
        """
        The first HTTP error response should set the initial reconnect delay to
        one second.
        """
        d = Deferred()
        svc = self._TwitterStreamService(lambda: d, None)
        svc.clock = Clock()
        svc.startService()

        self.assertEqual(svc.reconnect_delay, 0)
        d.callback(self._FakeResponse(None, 500))
        self.assertEqual(svc.reconnect_delay, 1)

    def test_HTTP_500_second_reconnect_delay(self):
        """
        An HTTP error response when we already have a reconnect delay should
        double the delay and attempt to reconnect again.
        """
        d = Deferred()
        svc = self._TwitterStreamService(lambda: d, None)
        svc.clock = Clock()
        svc.reconnect_delay = 1
        svc.startService()

        self.assertEqual(svc.reconnect_delay, 1)
        d.callback(self._FakeResponse(None, 500))
        self.assertEqual(svc.reconnect_delay, 2)

    def test_HTTP_500_max_reconnect_delay(self):
        """
        The reconnect delay should never go over the maximum of ten minutes.
        """
        d = Deferred()
        svc = self._TwitterStreamService(lambda: d, None)
        svc.clock = Clock()
        svc.reconnect_delay = 60 * 60 * 24
        svc.startService()

        self.assertEqual(svc.reconnect_delay, 60 * 60 * 24)
        d.callback(self._FakeResponse(None, 500))
        self.assertEqual(svc.reconnect_delay, 60 * 10)

    def test_HTTP_500_schedules_reconnect(self):
        """
        An HTTP error should schedule a reconnection attempt.
        """
        d = Deferred()
        svc = self._TwitterStreamService(lambda: d, None)
        svc.clock = Clock()
        svc.startService()

        d.callback(self._FakeResponse(None, 500))
        self.assertEqual(svc._connect, svc._reconnect_delayedcall.func)

    def test_HTTP_500_calls_disconnect_callback(self):
        """
        An HTTP error should schedule a reconnection attempt.
        """
        from txtwitter.error import TwitterAPIError
        d = Deferred()
        called = []
        svc = self._TwitterStreamService(lambda: d, None)
        svc.set_disconnect_callback(lambda s, r: called.append(r))
        svc.clock = Clock()
        svc.startService()

        d.callback(self._FakeResponse(None, 500))
        [failure] = called
        self.assertEqual(TwitterAPIError, type(failure.value))

    def test_reconnect(self):
        """
        A reconnect should wait for the required amount of time and then
        attempt to connect again.
        """
        d1 = Deferred()
        d2 = Deferred()
        connect_deferreds = [d1, d2]
        called = []
        svc = self._TwitterStreamService(
            lambda: connect_deferreds.pop(0), None)
        svc.set_connect_callback(lambda s: called.append(s))
        svc.clock = Clock()
        svc.startService()
        d1.callback(self._FakeResponse(None, 500))
        self.assertEqual([], called)

        svc.clock.advance(svc.reconnect_delay)
        self.assertEqual(svc._reconnect_delayedcall, None)
        d2.callback(self._FakeResponse(None))
        self.assertEqual([svc], called)
