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
    """
    Construct an OAuth Authorization header for a request.
    """
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


def set_bool_param(params, name, value):
    """
    Set a boolean parameter if applicable.

    :param dict params: A dict containing API call parameters.

    :param str name: The name of the parameter to set.

    :param bool value:
        The value of the parameter. If ``None``, the field will not be set. If
        ``True`` or ``False``, the relevant field in ``params`` will be set to
        ``'true'`` or ``'false'``. Any other value will raise a `ValueError`.

    :returns: ``None``
    """
    if value is None:
        return

    if value is True:
        params[name] = 'true'
    elif value is False:
        params[name] = 'false'
    else:
        raise ValueError("Parameter '%s' must be boolean or None, got %r." % (
            name, value))


def set_str_param(params, name, value):
    """
    Set a string parameter if applicable.

    :param dict params: A dict containing API call parameters.

    :param str name: The name of the parameter to set.

    :param bool value:
        The value of the parameter. If ``None``, the field will not be set. If
        an instance of ``basestring``, the relevant field will be set. Any
        other value will raise a `ValueError`.

    :returns: ``None``
    """
    if value is None:
        return

    if isinstance(value, basestring):
        params[name] = value
    else:
        raise ValueError("Parameter '%s' must be a string or None, got %r." % (
            name, value))


def set_float_param(params, name, value, min=None, max=None):
    """
    Set a float parameter if applicable.

    :param dict params: A dict containing API call parameters.

    :param str name: The name of the parameter to set.

    :param float value:
        The value of the parameter. If ``None``, the field will not be set. If
        an instance of a numeric type or a string that can be turned into a
        ``float``, the relevant field will be set. Any other value will raise a
        `ValueError`.

    :param float min:
        If provided, values less than this will raise ``ValueError``.

    :param float max:
        If provided, values greater than this will raise ``ValueError``.

    :returns: ``None``
    """
    if value is None:
        return

    try:
        value = float(str(value))
    except:
        raise ValueError(
            "Parameter '%s' must be numeric (or a numeric string) or None,"
            " got %r." % (name, value))
    if min is not None and value < min:
        raise ValueError(
            "Parameter '%s' must not be less than %r, got %r." % (
            name, min, value))
    if max is not None and value > max:
        raise ValueError(
            "Parameter '%s' must not be greater than %r, got %r." % (
            name, min, value))

    params[name] = str(value)


def set_int_param(params, name, value, min=None, max=None):
    """
    Set a int parameter if applicable.

    :param dict params: A dict containing API call parameters.

    :param str name: The name of the parameter to set.

    :param int value:
        The value of the parameter. If ``None``, the field will not be set. If
        an instance of a numeric type or a string that can be turned into a
        ``int``, the relevant field will be set. Any other value will raise a
        `ValueError`.

    :param int min:
        If provided, values less than this will raise ``ValueError``.

    :param int max:
        If provided, values greater than this will raise ``ValueError``.

    :returns: ``None``
    """
    if value is None:
        return

    try:
        value = int(str(value))
    except:
        raise ValueError(
            "Parameter '%s' must be an integer (or a string representation of"
            " an integer) or None, got %r." % (name, value))
    if min is not None and value < min:
        raise ValueError(
            "Parameter '%s' must not be less than %r, got %r." % (
            name, min, value))
    if max is not None and value > max:
        raise ValueError(
            "Parameter '%s' must not be greater than %r, got %r." % (
            name, min, value))

    params[name] = str(value)


class TwitterClient(object):
    """
    TODO: Document this.
    """
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
        """
        Construct an OAuth Authorization header for a request.
        """
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

    def statuses_retweets(self, id, count=None, trim_user=None):
        """
        Returns a list of the most recent retweets of the Tweet specified by
        the id parameter.

        https://dev.twitter.com/docs/api/1.1/get/statuses/retweets/%3Aid

        :param str id:
            (*required*) The numerical ID of the desired tweet.

        :param int count:
            The maximum number of retweets to return. (Max 100)

        :param bool trim_user:
            When set to ``True``, the tweet's user object includes only the
            status author's numerical ID.

        :returns: A tweet dict.
        """
        params = {'id': id}
        set_int_param(params, 'count', count)
        set_bool_param(params, 'trim_user', trim_user)
        return self._get_api('statuses/retweets.json', params)

    def statuses_show(self, id, trim_user=None, include_my_retweet=None,
                      include_entities=None):
        """
        Returns a single Tweet, specified by the id parameter.

        https://dev.twitter.com/docs/api/1.1/get/statuses/show/%3Aid

        :param str id:
            (*required*) The numerical ID of the desired tweet.

        :param bool trim_user:
            When set to ``True``, the tweet's user object includes only the
            status author's numerical ID.

        :param bool include_my_retweet:
            When set to ``True``, any Tweet returned that has been retweeted by
            the authenticating user will include an additional
            ``current_user_retweet`` node, containing the ID of the source
            status for the retweet.

        :param bool include_entities:
            When set to ``False``, the ``entities`` node will not be included.

        :returns: A tweet dict.
        """
        params = {'id': id}
        set_bool_param(params, 'trim_user', trim_user)
        set_bool_param(params, 'include_my_retweet', include_my_retweet)
        set_bool_param(params, 'include_entities', include_entities)
        return self._get_api('statuses/show.json', params)

    def statuses_destroy(self, id, trim_user=None):
        """
        Destroys the status specified by the ID parameter.

        https://dev.twitter.com/docs/api/1.1/post/statuses/destroy/%3Aid

        :param str id:
            (*required*) The numerical ID of the desired tweet.

        :param bool trim_user:
            When set to ``True``, the return value's user object includes only
            the status author's numerical ID.

        :returns:
            A tweet dict containing the destroyed tweet.
        """
        params = {'id': id}
        set_bool_param(params, 'trim_user', trim_user)
        return self._post_api('statuses/destroy.json', params)

    def statuses_update(self, status, in_reply_to_status_id=None, lat=None,
                        long=None, place_id=None, display_coordinates=None,
                        trim_user=None):
        """
        Posts a tweet.

        https://dev.twitter.com/docs/api/1.1/post/statuses/update

        :param str status:
            (*required*) The text of your tweet, typically up to 140
            characters. URL encode as necessary. t.co link wrapping may affect
            character counts.

            There are some special commands in this field to be aware of. For
            instance, preceding a message with "D " or "M " and following it
            with a screen name can create a direct message to that user if the
            relationship allows for it.

        :param str in_reply_to_status_id:
            The ID of an existing status that the update is in reply to.

            Note: This parameter will be ignored unless the author of the tweet
            this parameter references is mentioned within the status text.
            Therefore, you must include @username, where username is the author
            of the referenced tweet, within ``status``.

        :param float lat:
            The latitude of the location this tweet refers to. This parameter
            will be ignored unless it is inside the range -90.0 to +90.0 (North
            is positive) inclusive. It will also be ignored if there isn't a
            corresponding long parameter.

        :param float long:
            The longitude of the location this tweet refers to. The valid
            ranges for longitude is -180.0 to +180.0 (East is positive)
            inclusive. This parameter will be ignored if outside that range, if
            it is not a number, if geo_enabled is disabled, or if there not a
            corresponding lat parameter.

        :param str place_id:
            A place in the world. These IDs can be retrieved from GET
            geo/reverse_geocode. (TODO: Reference method when it exists.)

        :param bool display_coordinates:
            Whether or not to put a pin on the exact coordinates a tweet has
            been sent from.

        :param bool trim_user:
            When set to ``True``, the return value's user object includes only
            the status author's numerical ID.

        :returns:
            A tweet dict containing the posted tweet.
        """
        params = {'status': status}
        set_str_param(params, 'in_reply_to_status_id', in_reply_to_status_id)
        set_float_param(params, 'lat', lat, min=-90, max=90)
        set_float_param(params, 'long', long, min=-180, max=180)
        set_str_param(params, 'place_id', place_id)
        set_bool_param(params, 'display_coordinates', display_coordinates)
        set_bool_param(params, 'trim_user', trim_user)
        return self._post_api('statuses/update.json', params)

    def statuses_retweet(self, id, trim_user=None):
        """
        Retweets the status specified by the ID parameter.

        https://dev.twitter.com/docs/api/1.1/post/statuses/retweet/%3Aid

        :param str id:
            (*required*) The numerical ID of the desired tweet.

        :param bool trim_user:
            When set to ``True``, the return value's user object includes only
            the status author's numerical ID.

        :returns:
            A tweet dict containing the retweet. (Contains the retweeted tweet
            in the ``retweeted_status`` field.)
        """
        params = {'id': id}
        set_bool_param(params, 'trim_user', trim_user)
        return self._post_api('statuses/retweet.json', params)

    def stream_filter(self, delegate, follow=None, track=None, locations=None,
                      stall_warnings=None):
        """
        Streams public messages filtered by various parameters.

        https://dev.twitter.com/docs/api/1.1/post/statuses/filter

        At least one of ``follow``, ``track``, or ``locations`` must be
        provided. See the API documentation linked above for details on these
        parameters and the various limits on this API.

        :param delegate:
            A delegate function that will be called for each message in the
            stream and will be passed the message dict as the only parameter.
            The message dicts passed to this function may represent any message
            type and the delegate is responsible for any dispatch that may be
            required. (:mod:`txtwitter.messagetools` may be helpful here.)

        :param list follow:
            A list of user IDs, indicating the users to return statuses for in
            the stream.

        :param list track:
            List of keywords to track.

        :param list locations:
            List of location bounding boxes to track.
            XXX: Currently unsupported.

        :param bool stall_warnings:
            Specifies whether stall warnings should be delivered.

        :returns: An unstarted :class:`TwitterStreamService`.
        """
        params = {}
        if not (follow or track or locations):
            raise ValueError(
                "At least one of `follow`, `track`, or `locations` must be"
                " non-empty.")

        if follow is not None:
            params['follow'] = ','.join(follow)
        if track is not None:
            params['track'] = ','.join(track)
        if locations is not None:
            raise NotImplementedError(
                "The `locations` parameter is not yet supported.")
        set_bool_param(params, 'stall_warnings', stall_warnings)

        svc = TwitterStreamService(
            lambda: self._post_stream('statuses/filter.json', params),
            delegate)
        return svc

    def userstream_user(self, delegate, stall_warnings=None,
                        with_='followings', replies=None):
        """
        Streams messages for a single user.

        https://dev.twitter.com/docs/api/1.1/get/user

        The ``stringify_friend_ids`` parameter is always set to ``'true'`` for
        consistency with the use of string identifiers elsewhere.

        :param delegate:
            A delegate function that will be called for each message in the
            stream and will be passed the message dict as the only parameter.
            The message dicts passed to this function may represent any message
            type and the delegate is responsible for any dispatch that may be
            required. (:mod:`txtwitter.messagetools` may be helpful here.)

        :param bool stall_warnings:
            Specifies whether stall warnings should be delivered.

        :param str with_:
            If ``'followings'`` (the default), the stream will include messages
            from both the authenticated user and the authenticated user's
            followers. If ``'user'``, the stream will only include messages
            from (or mentioning) the autheticated user. All other values are
            invalid. (The underscore appended to the parameter name is to avoid
            conflicting with Python's ``with`` keyword.)

        :param str replies:
            If set to ``'all'``, replies to tweets will be included even if the
            authenticated user does not follow both parties.

        :returns: An unstarted :class:`TwitterStreamService`.
        """
        params = {'stringify_friend_ids': 'true'}
        set_bool_param(params, 'stall_warnings', stall_warnings)
        set_str_param(params, 'with', with_)
        set_str_param(params, 'replies', replies)

        svc = TwitterStreamService(
            lambda: self._get_userstream('user.json', params),
            delegate)
        return svc
