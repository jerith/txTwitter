import json
from StringIO import StringIO
from urllib import urlencode

from oauthlib import oauth1
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
TWITTER_UPLOAD_URL = 'https://upload.twitter.com/1.1/'


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

    :param value:
        The value of the parameter. If ``None``, the field will not be set. If
        an instance of ``str``, the relevant field will be set. If an instance
        of ``unicode``, the relevant field will be set to the UTF-8 encoding.
        Any other value will raise a `ValueError`.

    :returns: ``None``
    """
    if value is None:
        return

    if isinstance(value, str):
        params[name] = value
    elif isinstance(value, unicode):
        params[name] = value.encode('utf-8')
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


def set_list_param(params, name, value, min_len=None, max_len=None):
    """
    Set a list parameter if applicable.

    :param dict params: A dict containing API call parameters.

    :param str name: The name of the parameter to set.

    :param list value:
        The value of the parameter. If ``None``, the field will not be set. If
        an instance of ``set``, ``tuple``, or type that can be turned into
        a ``list``, the relevant field will be set. If ``dict``, will raise
        ``ValueError``. Any other value will raise a ``ValueError``.

    :param int min_len:
        If provided, values shorter than this will raise ``ValueError``.

    :param int max_len:
        If provided, values longer than this will raise ``ValueError``.
    """
    if value is None:
        return

    if type(value) is dict:
        raise ValueError(
            "Parameter '%s' cannot be a dict." % name)

    try:
        value = list(value)
    except:
        raise ValueError(
            "Parameter '%s' must be a list (or a type that can be turned into"
            "a list) or None, got %r." % (name, value))

    if min_len is not None and len(value) < min_len:
        raise ValueError(
            "Parameter '%s' must not be shorter than %r, got %r." % (
                name, min_len, value))
    if max_len is not None and len(value) > max_len:
        raise ValueError(
            "Parameter '%s' must not be longer than %r, got %r." % (
                name, max_len, value))

    list_str = ''
    for item in value:
        list_str += '%s,' % item
    set_str_param(params, name, list_str)


class TwitterClient(object):
    """
    TODO: Document this.
    """
    reactor = reactor

    def __init__(self, token_key, token_secret, consumer_key, consumer_secret,
                 api_url=TWITTER_API_URL, stream_url=TWITTER_STREAM_URL,
                 userstream_url=TWITTER_USERSTREAM_URL,
                 upload_url=TWITTER_UPLOAD_URL, agent=None):
        self._token_key = token_key
        self._token_secret = token_secret
        self._consumer_key = consumer_key
        self._consumer_secret = consumer_secret
        self._api_url_base = api_url
        self._stream_url_base = stream_url
        self._userstream_url_base = userstream_url
        self._upload_url_base = upload_url
        if agent is None:
            agent = Agent(self.reactor)
        self._agent = agent

    def _make_request(self, method, uri, body_parameters=None):
        headers = {}
        body = None
        if body_parameters is not None:
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            body = urlencode(body_parameters)
        client = oauth1.Client(
            self._consumer_key, client_secret=self._consumer_secret,
            resource_owner_key=self._token_key,
            resource_owner_secret=self._token_secret, encoding='utf-8',
            decoding='utf-8')
        uri, headers, body = client.sign(
            uri, http_method=method, headers=headers, body=body)
        headers = Headers(dict((k, [v]) for k, v in headers.items()))

        body_producer = None
        if body is not None:
            body_producer = FileBodyProducer(StringIO(body))

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

    def _upload_media(self, uri, media, params):
        boundary = 'txtwitter'
        file_field = 'media'

        body = ''
        if params:
            for key, value in params.items():
                body += '--%s\r\n' % boundary
                body += 'Content-Disposition: form-data, name=%s\r\n' % key
                body += '\r\n'
                body += str(value)
                body += '\r\n'

        body += '--%s\r\n' % boundary
        body += 'Content-Disposition: form-data; name=%s; filename=%s\r\n' % (
            file_field, media.name)
        body += 'Content-Type: application/octet-stream\r\n'
        body += '\r\n'
        body += media.read()
        body += '\r\n--%s--\r\n' % boundary

        client = oauth1.Client(
            self._consumer_key, client_secret=self._consumer_secret,
            resource_owner_key=self._token_key,
            resource_owner_secret=self._token_secret, encoding='utf-8',
            decoding='utf-8')
        uri = self._make_uri(self._upload_url_base, uri)
        headers = {
            'Content-Type': 'multipart/form-data; boundary=%s' % boundary,
        }
        uri, headers, _ = client.sign(uri, http_method='POST', headers=headers)
        headers = Headers(dict((k, [v]) for k, v in headers.items()))
        body_producer = FileBodyProducer(StringIO(body))

        d = self._agent.request('POST', uri, headers, body_producer)
        d.addCallback(self._handle_error)
        d.addCallback(self._parse_response)
        return d

    # Timelines

    def statuses_mentions_timeline(self, count=None, since_id=None,
                                   max_id=None, trim_user=None,
                                   contributor_details=None,
                                   include_entities=None):
        """
        Returns a list of the most recent mentions (tweets containing a users's
        @screen_name) for the authenticating user.

        https://dev.twitter.com/docs/api/1.1/get/statuses/mentions_timeline

        :param int count:
            Specifies the number of tweets to try and retrieve, up to a maximum
            of 200.

        :param str since_id:
            Returns results with an ID greater than (that is, more recent than)
            the specified ID. Tweets newer than this may not be returned due to
            certain API limits.

        :param str max_id:
            Returns results with an ID less than (that is, older than) or equal
            to the specified ID.

        :param bool trim_user:
            When set to ``True``, the tweet's user object includes only the
            status author's numerical ID.

        :param bool contributor_details:
            This parameter enhances the contributors element of the status
            response to include the screen_name of the contributor. By default
            only the user_id of the contributor is included.

        :param bool include_entities:
            When set to ``False``, the ``entities`` node will not be included.

        :returns: A list of tweet dicts.
        """
        params = {}
        set_int_param(params, 'count', count)
        set_str_param(params, 'since_id', since_id)
        set_str_param(params, 'max_id', max_id)
        set_bool_param(params, 'trim_user', trim_user)
        set_bool_param(params, 'contributor_details', contributor_details)
        set_bool_param(params, 'include_entities', include_entities)
        return self._get_api('statuses/mentions_timeline.json', params)

    def statuses_user_timeline(self, user_id=None, screen_name=None,
                               since_id=None, count=None, max_id=None,
                               trim_user=None, exclude_replies=None,
                               contributor_details=None,
                               include_rts=None):
        """
        Returns a list of the most recent tweets posted by the specified user.

        https://dev.twitter.com/docs/api/1.1/get/statuses/user_timeline

        Either ``user_id`` or ``screen_name`` must be provided.

        :param str user_id:
            The ID of the user to return tweets for.

        :param str screen_name:
            The screen name of the user to return tweets for.

        :param str since_id:
            Returns results with an ID greater than (that is, more recent than)
            the specified ID. Tweets newer than this may not be returned due to
            certain API limits.

        :param int count:
            Specifies the number of tweets to try and retrieve, up to a maximum
            of 200.

        :param str max_id:
            Returns results with an ID less than (that is, older than) or equal
            to the specified ID.

        :param bool trim_user:
            When set to ``True``, the tweet's user object includes only the
            status author's numerical ID.

        :param bool exclude_replies:
            When set to ``True``, replies will not appear in the timeline.

        :param bool contributor_details:
            This parameter enhances the contributors element of the status
            response to include the screen_name of the contributor. By default
            only the user_id of the contributor is included.

        :param bool include_rts:
            When set to ``False``, retweets will not appear in the timeline.

        :returns: A list of tweet dicts.
        """
        params = {}
        set_str_param(params, 'user_id', user_id)
        set_str_param(params, 'screen_name', screen_name)
        set_str_param(params, 'since_id', since_id)
        set_int_param(params, 'count', count)
        set_str_param(params, 'max_id', max_id)
        set_bool_param(params, 'trim_user', trim_user)
        set_bool_param(params, 'exclude_replies', exclude_replies)
        set_bool_param(params, 'contributor_details', contributor_details)
        set_bool_param(params, 'include_rts', include_rts)
        return self._get_api('statuses/user_timeline.json', params)

    def statuses_home_timeline(self, count=None, since_id=None, max_id=None,
                               trim_user=None, exclude_replies=None,
                               contributor_details=None,
                               include_entities=None):
        """
        Returns a collection of the most recent Tweets and retweets posted by
        the authenticating user and the users they follow.

        https://dev.twitter.com/docs/api/1.1/get/statuses/home_timeline

        :param int count:
            Specifies the number of tweets to try and retrieve, up to a maximum
            of 200.

        :param str since_id:
            Returns results with an ID greater than (that is, more recent than)
            the specified ID. Tweets newer than this may not be returned due to
            certain API limits.

        :param str max_id:
            Returns results with an ID less than (that is, older than) or equal
            to the specified ID.

        :param bool trim_user:
            When set to ``True``, the tweet's user object includes only the
            status author's numerical ID.

        :param bool exclude_replies:
            When set to ``True``, replies will not appear in the timeline.

        :param bool contributor_details:
            This parameter enhances the contributors element of the status
            response to include the screen_name of the contributor. By default
            only the user_id of the contributor is included.

        :param bool include_entities:
            When set to ``False``, the ``entities`` node will not be included.

        :returns: A list of tweet dicts.
        """
        params = {}
        set_int_param(params, 'count', count)
        set_str_param(params, 'since_id', since_id)
        set_str_param(params, 'max_id', max_id)
        set_bool_param(params, 'trim_user', trim_user)
        set_bool_param(params, 'exclude_replies', exclude_replies)
        set_bool_param(params, 'contributor_details', contributor_details)
        set_bool_param(params, 'include_entities', include_entities)
        return self._get_api('statuses/home_timeline.json', params)

    # TODO: Implement statuses_retweets_of_me()

    # Tweets

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
                        trim_user=None, media_ids=None):
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

        :param list media_ids:
            A list of images previously uploaded to Twitter (referenced by
            their ``media_id``) that are to be embedded in the tweet. Maximum
            of four images.

        :returns:
            A tweet dict containing the posted tweet.
        """
        params = {}
        set_str_param(params, 'status', status)
        set_str_param(params, 'in_reply_to_status_id', in_reply_to_status_id)
        set_float_param(params, 'lat', lat, min=-90, max=90)
        set_float_param(params, 'long', long, min=-180, max=180)
        set_str_param(params, 'place_id', place_id)
        set_bool_param(params, 'display_coordinates', display_coordinates)
        set_bool_param(params, 'trim_user', trim_user)
        set_list_param(params, 'media_ids', media_ids, max_len=4)
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

    def media_upload(self, media, additional_owners=None):
        """
        Uploads an image to Twitter for later embedding in tweets.

        https://dev.twitter.com/rest/reference/post/media/upload

        :param file media:
            The image file to upload (see the API docs for limitations).

        :param list additional_owners:
            A list of Twitter users that will be able to access the uploaded
            file and embed it in their tweets (maximum 100 users).

        :returns:
            A dict containing information about the file uploaded. (Contains
            the media id needed to embed the image in the ``media_id`` field).
        """
        params = {}
        set_list_param(
            params, 'additional_owners', additional_owners, max_len=100)
        return self._upload_media('media/upload.json', media, params)

    # TODO: Implement statuses_update_with_media()
    # TODO: Implement statuses_oembed()
    # TODO: Implement statuses_retweeters_ids()

    # Search

    # TODO: Implement search_tweets()

    # Streaming

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

    # TODO: Implement stream_sample()
    # TODO: Implement stream_firehose()

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

    # Direct Messages

    def direct_messages(self, since_id=None, max_id=None, count=None,
                        include_entities=None, skip_status=None):
        """
        Gets the 20 most recent direct messages received by the authenticating
        user.

        https://dev.twitter.com/docs/api/1.1/get/direct_messages

        :param str since_id:
            Returns results with an ID greater than (that is, more recent than)
            the specified ID. There are limits to the number of Tweets which
            can be accessed through the API. If the limit of Tweets has occured
            since the since_id, the since_id will be forced to the oldest ID
            available.

        :params str max_id:
            Returns results with an ID less than (that is, older than) or equal
            to the specified ID.

        :param int count:
            Specifies the number of direct messages to try and retrieve, up to
            a maximum of ``200``. The value of count is best thought of as a
            limit to the number of Tweets to return because suspended or
            deleted content is removed after the count has been applied.

        :param bool include_entities:
            The entities node will not be included when set to ``False``.

        :param bool skip_status:
            When set to ``True``, statuses will not be included in the returned
            user objects.

        :returns:
            A list of direct message dicts.
        """
        params = {}
        set_str_param(params, 'since_id', since_id)
        set_str_param(params, 'max_id', max_id)
        set_int_param(params, 'count', count)
        set_bool_param(params, 'include_entities', include_entities)
        set_bool_param(params, 'skip_status', skip_status)
        return self._get_api('direct_messages.json', params)

    def direct_messages_sent(self, since_id=None, max_id=None, count=None,
                             include_entities=None, page=None):
        """
        Gets the 20 most recent direct messages sent by the authenticating
        user.

        https://dev.twitter.com/docs/api/1.1/get/direct_messages/sent

        :param str since_id:
            Returns results with an ID greater than (that is, more recent than)
            the specified ID. There are limits to the number of Tweets which
            can be accessed through the API. If the limit of Tweets has occured
            since the since_id, the since_id will be forced to the oldest ID
            available.

        :params str max_id:
            Returns results with an ID less than (that is, older than) or equal
            to the specified ID.

        :param int count:
            Returns results with an ID less than (that is, older than) or equal
            to the specified ID.

        :param int page:
            Specifies the page of results to retrieve.

        :param bool include_entities:
            The entities node will not be included when set to ``False``.

        :returns:
            A list of direct message dicts.
        """
        params = {}
        set_str_param(params, 'since_id', since_id)
        set_str_param(params, 'max_id', max_id)
        set_int_param(params, 'count', count)
        set_int_param(params, 'page', page)
        set_bool_param(params, 'include_entities', include_entities)
        return self._get_api('direct_messages/sent.json', params)

    def direct_messages_show(self, id):
        """
        Gets the direct message with the given id.

        https://dev.twitter.com/docs/api/1.1/get/direct_messages/show

        :param str id:
            (*required*) The ID of the direct message.

        :returns:
            A direct message dict.
        """
        params = {}
        set_str_param(params, 'id', id)
        d = self._get_api('direct_messages/show.json', params)
        d.addCallback(lambda dms: dms[0])
        return d

    def direct_messages_destroy(self, id, include_entities=None):
        """
        Destroys the direct message with the given id.

        https://dev.twitter.com/docs/api/1.1/post/direct_messages/destroy

        :param str id:
            (*required*) The ID of the direct message.
        :param bool include_entities:
            The entities node will not be included when set to ``False``.

        :returns:
            A direct message dict containing the destroyed direct message.
        """
        params = {}
        set_str_param(params, 'id', id)
        set_bool_param(params, 'include_entities', include_entities)
        return self._post_api('direct_messages/destroy.json', params)

    def direct_messages_new(self, text, user_id=None, screen_name=None):
        """
        Sends a new direct message to the given user from the authenticating
        user.

        https://dev.twitter.com/docs/api/1.1/post/direct_messages/new

        :param str text:
            (*required*) The text of your direct message.
        :param str user_id:
            The ID of the user who should receive the direct message. Required
            if ``screen_name`` isn't given.
        :param str screen_name:
            The screen name of the user who should receive the direct message.
            Required if ``user_id`` isn't given.

        :returns:
            A direct message dict containing the sent direct message.
        """
        params = {}
        set_str_param(params, 'text', text)
        set_str_param(params, 'user_id', user_id)
        set_str_param(params, 'screen_name', screen_name)
        return self._post_api('direct_messages/new.json', params)

    # TODO: Implement direct_messages_show()
    # TODO: Implement direct_messages_destroy()
    # TODO: Implement direct_messages_new()

    # Friends & Followers

    # TODO: Implement friendships_no_retweets_ids()
    # TODO: Implement friends_ids()
    # TODO: Implement followers_ids()
    # TODO: Implement friendships_lookup()
    # TODO: Implement friendships_incoming()
    # TODO: Implement friendships_outgoing()

    def friendships_create(self, user_id=None, screen_name=None,
                           follow=None):
        """
        Allows the authenticating users to follow the specified user.

        https://dev.twitter.com/docs/api/1.1/post/friendships/create

        :param str user_id:
            The screen name of the user for whom to befriend. Required if
            ``screen_name`` isn't given.
        :param str screen_name:
            The ID of the user for whom to befriend. Required if ``user_id``
            isn't given.
        :param bool follow:
            Enable notifications for the target user.

        :returns:
            A dict containing the newly followed user.
        """
        params = {}
        set_str_param(params, 'user_id', user_id)
        set_str_param(params, 'screen_name', screen_name)
        set_bool_param(params, 'follow', follow)
        return self._post_api('friendships/create.json', params)

    def friendships_destroy(self, user_id=None, screen_name=None):
        """
        Allows the authenticating user to unfollow the specified user.

        https://dev.twitter.com/docs/api/1.1/post/friendships/destroy

        :param str user_id:
            The screen name of the user for whom to unfollow. Required if
            ``screen_name`` isn't given.
        :param str screen_name:
            The ID of the user for whom to unfollow. Required if ``user_id``
            isn't given.

        :returns:
            A dict containing the newly unfollowed user.
        """
        params = {}
        set_str_param(params, 'user_id', user_id)
        set_str_param(params, 'screen_name', screen_name)
        return self._post_api('friendships/destroy.json', params)

    # TODO: Implement friendships_update()
    # TODO: Implement friendships_show()
    # TODO: Implement friends_list()
    # TODO: Implement followers_list()

    # Users

    # TODO: Implement account_settings()
    # TODO: Implement account_verify_credentials()
    # TODO: Implement account_settings()
    # TODO: Implement account_update_delivery_device()
    # TODO: Implement account_update_profile()
    # TODO: Implement account_update_profile_background_image()
    # TODO: Implement account_update_profile_colors()
    # TODO: Implement account_update_profile_image()
    # TODO: Implement blocks_list()
    # TODO: Implement blocks_ids()
    # TODO: Implement blocks_create()
    # TODO: Implement blocks_destroy()
    # TODO: Implement users_lookup()
    # TODO: Implement users_show()
    # TODO: Implement users_search()
    # TODO: Implement users_contributees()
    # TODO: Implement users_contributors()
    # TODO: Implement account_remove_profile_banner()
    # TODO: Implement account_update_profile_banner()
    # TODO: Implement users/profile_banner()

    # Suggested Users

    # TODO: Implement users_suggestions()
    # TODO: Implement users_suggestions()
    # TODO: Implement users_suggestions_members()

    # Favorites

    # TODO: Implement favorites_list()
    # TODO: Implement favorites_destroy()
    # TODO: Implement favorites_create()

    # Lists

    # TODO: Implement lists_list()
    # TODO: Implement lists_statuses()
    # TODO: Implement lists_members_destroy()
    # TODO: Implement lists_memberships()
    # TODO: Implement lists_subscribers()
    # TODO: Implement lists_subscribers/create()
    # TODO: Implement lists_subscribers/show()
    # TODO: Implement lists_subscribers/destroy()
    # TODO: Implement lists_members_create_all()
    # TODO: Implement lists_members_show()
    # TODO: Implement lists_members()
    # TODO: Implement lists_members_create()
    # TODO: Implement lists_destroy()
    # TODO: Implement lists_update()
    # TODO: Implement lists_create()
    # TODO: Implement lists_show()
    # TODO: Implement lists_subscriptions()
    # TODO: Implement lists_members_destroy_all()
    # TODO: Implement lists_ownerships()

    # Saved Searches

    # TODO: Implement saved_searches_list()
    # TODO: Implement saved_searches_show()
    # TODO: Implement saved_searches_create()
    # TODO: Implement saved_searches_destroy()

    # Places & Geo

    # TODO: Implement geo_id()
    # TODO: Implement geo_reverse_geocode()
    # TODO: Implement geo_search()
    # TODO: Implement geo_similar_places()
    # TODO: Implement geo_place()

    # Trends

    # TODO: Implement trends_place()
    # TODO: Implement trends_available()
    # TODO: Implement trends_closest()

    # Spam Reporting

    # TODO: Implement users_report_spam()

    # OAuth

    # TODO: Decide whether any of these APIs should be implemented.

    # Help

    # TODO: Implement help_configuration()
    # TODO: Implement help_languages()
    # TODO: Implement help_privacy()
    # TODO: Implement help_tos()
    # TODO: Implement application_rate_limit_status()
