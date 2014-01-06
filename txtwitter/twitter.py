import json
from StringIO import StringIO
from urllib import urlencode

import oauth2
from twisted.internet import reactor
from twisted.python.failure import Failure
from twisted.web.client import (
    Agent, FileBodyProducer, PartialDownloadError, readBody)
from twisted.web.http_headers import Headers

from txtwitter.error import TwitterAPIError
from txtwitter.streamservice import TwitterStreamService


TWITTER_API_URL = 'https://api.twitter.com/1.1/'
TWITTER_STREAM_URL = 'https://stream.twitter.com/1.1/'
TWITTER_USERSTREAM_URL = 'https://userstream.twitter.com/1.1/'


def make_auth_header(token, consumer, method, url, parameters=None):
    if parameters is None:
        parameters = {}
    else:
        # So we can safely modify them.
        parameters = parameters.copy()

    parameters['oauth_version'] = "1.0"
    # It's handy to be able to override these if necessary.
    parameters.setdefault('oauth_nonce', oauth2.generate_nonce())
    parameters.setdefault('oauth_timestamp', oauth2.generate_timestamp())

    req = oauth2.Request(method=method, url=url, parameters=parameters)
    req.sign_request(oauth2.SignatureMethod_HMAC_SHA1(), consumer, token)

    # Extract the header value and turn it into bytes.
    [auth_value] = req.to_header().values()
    return auth_value.encode('ascii')


def _extract_partial_response(failure):
    failure.trap(PartialDownloadError)
    return failure.value.response


def _read_body(response):
    """
    Read a response body even if there is no content length.
    """
    return readBody(response).addErrback(_extract_partial_response)


class TwitterClient(object):
    reactor = reactor

    def __init__(self, token_key, token_secret, consumer_key, consumer_secret,
                 api_url=TWITTER_API_URL, stream_url=TWITTER_STREAM_URL,
                 userstream_url=TWITTER_USERSTREAM_URL, agent=None):
        self._token = oauth2.Token(key=token_key, secret=token_secret)
        self._consumer = oauth2.Consumer(
            key=consumer_key, secret=consumer_secret)
        self._api_url_base = api_url
        self._stream_url_base = stream_url
        self._userstream_url_base = userstream_url
        if agent is None:
            agent = Agent(self.reactor)
        self._agent = agent

    def make_auth_header(self, method, url, parameters=None):
        return make_auth_header(
            self._token, self._consumer, method, url, parameters)

    def _make_request(self, method, uri, body_parameters=None):
        body_producer = None
        auth_header = self.make_auth_header(method, uri, body_parameters)
        headers = Headers({'Authorization': [auth_header]})

        if body_parameters is not None:
            body_producer = FileBodyProducer(
                StringIO(urlencode(body_parameters)))
            headers.addRawHeader(
                'Content-Type', 'application/x-www-form-urlencoded')

        d = self._agent.request(method, uri, headers, body_producer)
        return d.addCallback(self._handle_error)

    def _handle_error(self, response):
        if response.code < 400:
            return response

        return _read_body(response).addCallback(lambda body: Failure(
            TwitterAPIError(response.code, response=body)))

    def _parse_response(self, response):
        # TODO: Better exception than this.
        assert response.code in (200, 201)
        return readBody(response).addCallback(json.loads)

    def _make_uri(self, base_uri, resource, parameters=None):
        uri = "%s/%s" % (base_uri.rstrip('/'), resource.lstrip('/'))
        if parameters is not None:
            uri = "%s?%s" % (uri, urlencode(parameters))
        return uri

    def _get_api(self, resource, parameters):
        uri = self._make_uri(self._api_url_base, resource, parameters)
        d = self._make_request('GET', uri)
        return d.addCallback(self._parse_response)

    def _post_api(self, resource, parameters):
        uri = self._make_uri(self._api_url_base, resource)
        d = self._make_request('POST', uri, parameters)
        return d.addCallback(self._parse_response)

    def _post_stream(self, resource, parameters):
        uri = self._make_uri(self._stream_url_base, resource)
        return self._make_request('POST', uri, parameters)

    def _get_userstream(self, resource, parameters):
        uri = self._make_uri(self._userstream_url_base, resource, parameters)
        return self._make_request('GET', uri)

    def show(self, id):
        return self._get_api('statuses/show.json', {'id': id})

    def update(self, content):
        return self._post_api('statuses/update.json', {'status': content})

    def stream_filter(self, delegate, track=None):
        params = {}
        if track is not None:
            params['track'] = ','.join(track)

        svc = TwitterStreamService(
            lambda: self._post_stream('statuses/filter.json', params),
            delegate)
        return svc

    def userstream_user(self, delegate, with_='followings'):
        params = {
            'stringify_friend_ids': 'true',
            'with': with_,
        }

        svc = TwitterStreamService(
            lambda: self._get_userstream('user.json', params),
            delegate)
        return svc
