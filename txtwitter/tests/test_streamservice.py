from twisted.internet.defer import Deferred
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
