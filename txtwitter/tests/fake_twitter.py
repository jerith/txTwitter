from datetime import datetime
from inspect import getmembers
import json
import re
from urlparse import urlparse, parse_qsl

from twisted.internet.defer import maybeDeferred

from txtwitter.error import TwitterAPIError
from txtwitter.tests.fake_agent import FakeResponse
from txtwitter.twitter import (
    TWITTER_API_URL, TWITTER_STREAM_URL, TWITTER_USERSTREAM_URL,
    TWITTER_UPLOAD_URL, TwitterClient)


USER_MENTION_RE = re.compile(r'@[a-zA-Z0-9_]+')


def mention_from_match(twitter_data, match):
    user = twitter_data.get_user_by_screen_name(match.group(0)[1:])

    if user is None:
        return None

    return {
        'id_str': user.id_str,
        'id': int(user.id_str),
        'indices': list(match.span(0)),
        'screen_name': user.screen_name,
        'name': user.name,
    }


def extract_user_mentions(twitter_data, text):
    mentions = []
    for match in USER_MENTION_RE.finditer(text):
        mention = mention_from_match(twitter_data, match)
        if mention is not None:
            mentions.append(mention)
    return mentions


def extract_entities(twitter_data, text):
    return {
        'user_mentions': extract_user_mentions(twitter_data, text),
        # TODO: More entities
    }


class FakeImage(object):
    def __init__(self, name, file_content, size=1, height=1, width=1):
        self.name = name
        self.file_content = file_content

        self.size = size
        self.height = height
        self.width = width

    def read(self):
        return self.file_content


class FakeStream(object):
    def __init__(self):
        self.resp = FakeResponse(None)
        self._message_types = {}

    def add_message_type(self, message_type, predicate):
        self._message_types[message_type] = predicate

    def accepts(self, message_type, data):
        predicate = self._message_types.get(message_type)
        return predicate is not None and predicate(data)

    def deliver(self, data):
        self.resp.deliver_data(json.dumps(data))
        self.resp.deliver_data('\r\n')


class FakeTweet(object):
    def __init__(self, id_str, text, user_id_str, reply_to=None, **kw):
        self.id_str = id_str
        self.text = text
        self.user_id_str = user_id_str
        self.reply_to = reply_to
        self.created_at = kw.pop('created_at', datetime.utcnow())
        self.kw = kw

    def __cmp__(self, other):
        return cmp(int(self.id_str), int(other.id_str))

    def get_user(self, twitter_data):
        return twitter_data.get_user(self.user_id_str)

    def _get_reply_to_status_details(self, twitter_data):
        if self.reply_to is None:
            return {}

        reply_to_tweet = twitter_data.get_tweet(self.reply_to)

        return {
            'in_reply_to_status_id': int(reply_to_tweet.id_str),
            'in_reply_to_status_id_str': reply_to_tweet.id_str,
        }

    def _get_reply_to_user_details(self, twitter_data):
        def details(id_str, screen_name):
            return {
                'in_reply_to_user_id': int(id_str),
                'in_reply_to_user_id_str': id_str,
                'in_reply_to_screen_name': screen_name,
            }

        if self.reply_to is not None:
            reply_to_tweet = twitter_data.get_tweet(self.reply_to)
            reply_to_user = reply_to_tweet.get_user(twitter_data)
            return details(reply_to_user.id_str, reply_to_user.screen_name)

        match = USER_MENTION_RE.match(self.text)
        if match is not None:
            mention = mention_from_match(twitter_data, match)
            return details(mention['id_str'], mention['screen_name'])

        return {}

    def to_dict(self, twitter_data, trim_user=None, include_my_retweet=None,
                include_entities=None, contributor_details=None):
        if trim_user is None:
            trim_user = False
        if include_my_retweet is None:
            include_my_retweet = False
        if include_entities is None:
            include_entities = True
        if contributor_details is None:
            contributor_details = False
        else:
            raise NotImplementedError("contributer_details param")

        tweet_dict = {
            'id_str': self.id_str,
            'created_at': str(self.created_at),
            'text': self.text,
            # Defaults
            'favorite_count': 0,
            'filter_level': 'medium',
            'retweet_count': 0,
            'source': 'web',
        }
        # Calculated values
        tweet_dict.update({
            'id': int(tweet_dict['id_str']),
            'favorited': tweet_dict['favorite_count'] > 0,
            'retweeted': tweet_dict['retweet_count'] > 0,
        })
        if trim_user:
            tweet_dict['user'] = {
                'id_str': self.user_id_str,
                'id': int(self.user_id_str),
            }
        else:
            user = self.get_user(twitter_data)
            tweet_dict['user'] = user.to_dict(twitter_data)
        tweet_dict.update(self._get_reply_to_status_details(twitter_data))
        tweet_dict.update(self._get_reply_to_user_details(twitter_data))
        tweet_dict['entities'] = extract_entities(twitter_data, self.text)
        # Provided keyword args can override any of the above
        tweet_dict.update(self.kw)

        if not include_entities:
            tweet_dict.pop('entities')
        if include_my_retweet:
            raise NotImplementedError()
        return tweet_dict


class FakeDM(object):
    def __init__(self, id_str, text, sender_id_str, recipient_id_str, **kw):
        self.id_str = id_str
        self.text = text
        self.sender_id_str = sender_id_str
        self.recipient_id_str = recipient_id_str
        self.created_at = kw.pop('created_at', datetime.utcnow())
        self.kw = kw

    def __cmp__(self, other):
        return cmp(int(self.id_str), int(other.id_str))

    def _get_sender_details(self, twitter_data):
        sender = twitter_data.get_user(self.sender_id_str)
        return {
            'sender': sender.to_dict(twitter_data),
            'sender_id': int(self.sender_id_str),
            'sender_id_str': self.sender_id_str,
            'sender_screen_name': sender.screen_name
        }

    def _get_recipient_details(self, twitter_data):
        recipient = twitter_data.get_user(self.recipient_id_str)
        return {
            'recipient': recipient.to_dict(twitter_data),
            'recipient_id': int(self.recipient_id_str),
            'recipient_id_str': self.recipient_id_str,
            'recipient_screen_name': recipient.screen_name
        }

    def to_dict(self, twitter_data, skip_status=None,
                include_entities=None, **kw):
        if include_entities is None:
            include_entities = True
        if skip_status is not None:
            raise NotImplementedError("skip_status param")

        dm_dict = {
            'id': int(self.id_str),
            'id_str': self.id_str,
            'created_at': str(self.created_at),
            'text': self.text,
        }

        dm_dict.update(self._get_sender_details(twitter_data))
        dm_dict.update(self._get_recipient_details(twitter_data))
        dm_dict['entities'] = extract_entities(twitter_data, self.text)

        # Provided keyword args can override any of the above
        dm_dict.update(self.kw)

        if not include_entities:
            dm_dict.pop('entities')

        return dm_dict


class FakeUser(object):
    def __init__(self, id_str, screen_name, name, **kw):
        self.id_str = id_str
        self.screen_name = screen_name
        self.name = name
        self.created_at = kw.pop('created_at', datetime.utcnow())

        self.kw = kw

    def to_dict(self, twitter_data):
        user_dict = {
            'id_str': self.id_str,
            'screen_name': self.screen_name,
            'name': self.name,
            'created_at': str(self.created_at),
            # Defaults
        }
        # Calculated values
        user_dict.update({
            'id': int(user_dict['id_str']),
        })
        # Provided keyword args can override any of the above
        user_dict.update(self.kw)

        return user_dict


class FakeMedia(object):
    def __init__(self, media_id_str, fake_image, **kw):
        self.media_id_str = media_id_str
        self.size = fake_image.size
        self.expires_after_secs = 60
        self.image = {
            'image_type': 'image/jpeg',
            'w': fake_image.width,
            'h': fake_image.height,
        }

        self.kw = kw

    def to_dict(self, twitter_data):
        media_dict = {
            'media_id_str': self.media_id_str,
            'size': self.size,
            'expires_after_secs': self.expires_after_secs,
            'image': self.image,
            # Defaults
        }
        # Calculated values
        media_dict.update({
            'media_id': int(media_dict['media_id_str']),
        })
        # Provided keyword args can override any of the above
        media_dict.update(self.kw)

        return media_dict


class FakeFollow(object):
    def __init__(self, source_id, target_id, notify=False, **kw):
        self.source_id = source_id
        self.target_id = target_id
        self.created_at = kw.pop('created_at', datetime.utcnow())
        self.notify = notify
        self.kw = kw

    def __cmp__(self, other):
        if not isinstance(other, FakeFollow):
            return NotImplemented
        return cmp(self.created_at, other.created_at)

    def to_dict(self, twitter_data, event=None):
        source = twitter_data.get_user(self.source_id)
        target = twitter_data.get_user(self.target_id)

        follow_dict = {
            'source': source.to_dict(twitter_data),
            'target': target.to_dict(twitter_data),
        }

        if event is not None:
            follow_dict['event'] = event

        # Provided keyword args can override any of the above
        follow_dict.update(self.kw)

        return follow_dict


class FakeTwitterData(object):
    def __init__(self):
        self.users = {}
        self.dms = {}
        self.tweets = {}
        self.follows = {}
        self.streams = {}
        self.media = {}
        self._next_dm_id = 1000
        self._next_tweet_id = 1000
        self._next_user_id = 1000
        self._next_media_id = 1000

    @property
    def next_tweet_id(self):
        return str(self._next_tweet_id)

    @property
    def next_dm_id(self):
        return str(self._next_dm_id)

    @property
    def next_user_id(self):
        return str(self._next_user_id)

    @property
    def next_media_id(self):
        return str(self._next_media_id)

    def streams_accepting(self, message_type, data):
        return (stream for stream in self.streams.itervalues()
                if stream.accepts(message_type, data))

    def broadcast_tweet(self, tweet):
        for stream in self.streams_accepting('tweet', tweet):
            stream.deliver(tweet.to_dict(self))

    def broadcast_dm(self, dm):
        for stream in self.streams_accepting('dm', dm):
            stream.deliver({'direct_message': dm.to_dict(self)})

    def broadcast_follow(self, follow):
        for stream in self.streams_accepting('follow', follow):
            stream.deliver(follow.to_dict(self, event='follow'))

    def broadcast_unfollow(self, follow):
        for stream in self.streams_accepting('unfollow', follow):
            stream.deliver(follow.to_dict(self, event='unfollow'))

    def new_stream(self):
        stream = FakeStream()

        def finished_callback(r):
            self.remove_stream(stream.resp)

        stream.resp.finished_callback = finished_callback
        self.streams[stream.resp] = stream
        return stream

    def remove_stream(self, resp):
        self.streams.pop(resp, None)

    def get_tweet(self, id_str):
        return self.tweets.get(id_str)

    def get_dm(self, id_str):
        return self.dms.get(id_str)

    def get_user(self, id_str):
        return self.users.get(id_str)

    def get_media(self, media_id_str):
        return self.media.get(media_id_str)

    def get_follow(self, source_id, target_id):
        return self.follows.get((source_id, target_id))

    def add_tweet(self, *args, **kw):
        tweet = FakeTweet(*args, **kw)
        self.tweets[tweet.id_str] = tweet
        self.broadcast_tweet(tweet)
        return tweet

    def add_dm(self, *args, **kw):
        dm = FakeDM(*args, **kw)
        self.dms[dm.id_str] = dm
        self.broadcast_dm(dm)
        return dm

    def add_user(self, *args, **kw):
        user = FakeUser(*args, **kw)
        self.users[user.id_str] = user
        return user

    def add_media(self, *args, **kw):
        media = FakeMedia(*args, **kw)
        self.media[media.media_id_str] = media
        return media

    def add_follow(self, source_id, target_id):
        key = (source_id, target_id)

        if key not in self.follows:
            follow = self.follows[key] = FakeFollow(source_id, target_id)
            self.broadcast_follow(follow)
        else:
            follow = self.follows[key]

        return follow

    def del_tweet(self, id_str):
        self.tweets.pop(id_str)

    def del_dm(self, id_str):
        self.dms.pop(id_str)

    def del_user(self, id_str):
        self.users.pop(id_str)

    def del_media(self, media_id_str):
        self.media.pop(media_id_str)

    def del_follow(self, source_id, target_id):
        key = (source_id, target_id)

        if key in self.follows:
            follow = self.follows[key]
            del self.follows[key]
            self.broadcast_unfollow(follow)

    def new_tweet(self, text, user_id_str, *args, **kw):
        tweet = self.add_tweet(
            self.next_tweet_id, text, user_id_str, *args, **kw)
        self._next_tweet_id += 10
        return tweet

    def new_dm(self, text, sender_id_str, recipient_id_str, *args, **kw):
        dm = self.add_dm(
            self.next_dm_id, text, sender_id_str, recipient_id_str,
            *args, **kw)

        self._next_dm_id += 10
        return dm

    def new_user(self, screen_name, name, *args, **kw):
        user = self.add_user(self.next_user_id, screen_name, name, *args, **kw)
        self._next_user_id += 10
        return user

    def new_media(self, fake_image, *args, **kw):
        media = self.add_media(self.next_media_id, fake_image, *args, **kw)
        self._next_media_id += 10
        return media

    def get_user_by_screen_name(self, screen_name):
        for user in self.users.itervalues():
            if user.screen_name == screen_name:
                return user

    def iter_tweets_from(self, user_id_str):
        for tweet in self.tweets.itervalues():
            if tweet.user_id_str == user_id_str:
                yield tweet

    def iter_tweets_mentioning(self, user_id_str):
        user = self.get_user(user_id_str)
        mention = '@%s' % (user.screen_name,)
        for tweet in self.tweets.itervalues():
            if mention in tweet.text:
                yield tweet

    def to_dicts(self, *objects, **kw):
        return [obj.to_dict(self, **kw) for obj in objects]


class FakeTwitterClient(TwitterClient):
    def __init__(self, fake_twitter, user_id_str,
                 api_url=TWITTER_API_URL, stream_url=TWITTER_STREAM_URL,
                 userstream_url=TWITTER_USERSTREAM_URL,
                 upload_url=TWITTER_UPLOAD_URL):
        self._fake_twitter = fake_twitter
        self._fake_twitter_user_id_str = user_id_str
        self._api_url_base = api_url
        self._stream_url_base = stream_url
        self._userstream_url_base = userstream_url
        self._upload_url = upload_url

    def _make_request(self, method, uri, body_parameters=None):
        return self._fake_twitter.dispatch(
            self._fake_twitter_user_id_str, method, uri, body_parameters)

    def _upload_media(self, uri, media, params):
        return self._fake_twitter.dispatch_multipart(
            self._fake_twitter_user_id_str,
            self._make_uri(self._upload_url, uri), media, params)

    def _parse_response(self, response):
        return response


class FakeTwitter(object):
    def __init__(self, api_url=TWITTER_API_URL, stream_url=TWITTER_STREAM_URL,
                 userstream_url=TWITTER_USERSTREAM_URL,
                 upload_url=TWITTER_UPLOAD_URL):
        self.urls = {
            'api': api_url,
            'stream': stream_url,
            'userstream': userstream_url,
            'upload': upload_url,
        }
        self.twitter_data = FakeTwitterData()

    def __getattr__(self, name):
        return getattr(self.twitter_data, name)

    def get_client(self, user_id_str=None):
        return FakeTwitterClient(
            self, user_id_str, api_url=self.urls['api'],
            stream_url=self.urls['stream'],
            userstream_url=self.urls['userstream'],
            upload_url=self.urls['upload'])

    def get_api_method(self, user, uri):
        uri = uri.split('?')[0]

        user_view = FakeTwitterAPI(self.twitter_data, user)
        for name, method in getmembers(user_view):
            if not getattr(method, 'is_api', False):
                continue
            method_url_base = self.urls[method.api_host_prefix]
            if uri == method_url_base + method.api_path:
                return method

        raise ValueError("Unexpected URI: %r" % (uri,))

    def dispatch(self, user, method, uri, body_parameters):
        """
        Dispatch a fake request to the appropriate place.

        We don't actually care about the method here, since that's validated
        elsewhere and Twitter's API doesn't have different behaviour for the
        same URI depending on the method.

        """
        params = {}
        if body_parameters is not None:
            params.update(body_parameters)
        else:
            params.update(dict(parse_qsl(urlparse(uri).query)))

        method = self.get_api_method(user, uri)
        return maybeDeferred(method, **params)

    def dispatch_multipart(self, user, uri, body, params):
        method = self.get_api_method(user, uri)
        return maybeDeferred(method, body, params)


def fake_api(path, host_prefix='api'):
    def deco(func):
        func.is_api = True
        func.api_path = path
        func.api_host_prefix = host_prefix
        return func
    return deco


class FakeTwitterAPI(object):
    def __init__(self, twitter_data, user_id_str):
        self._twitter_data = twitter_data
        self._user_id_str = user_id_str

    def _404(self):
        raise TwitterAPIError(404, "Not Found", json.dumps({
            "errors": [
                {"message": "Sorry, that page does not exist", "code": 34},
            ]}))

    def _tweet_or_404(self, id_str):
        tweet = self._twitter_data.get_tweet(id_str)
        if tweet is None:
            self._404()
        return tweet

    def _user_or_404(self, id_str):
        user = self._twitter_data.get_user(id_str)
        if user is None:
            self._404()
        return user

    def _dm_or_404(self, id_str):
        dm = self._twitter_data.get_dm(id_str)
        if dm is None:
            self._404()
        return dm

    # Timelines

    def _filter_timeline(self, tweets_iter, count, since_id, max_id):
        tweets = []
        for tweet in tweets_iter:
            tweet_id = int(tweet.id_str)
            if since_id is not None and tweet_id <= int(since_id):
                continue
            if max_id is not None and tweet_id > int(max_id):
                continue
            tweets.append(tweet)
        if count is None:
            count = 20
        if count > 200:
            count = 200
        return sorted(tweets, reverse=True)[:count]

    @fake_api('statuses/mentions_timeline.json')
    def statuses_mentions_timeline(self, count=None, since_id=None,
                                   max_id=None, trim_user=None,
                                   contributor_details=None,
                                   include_entities=None):
        tweets = self._filter_timeline(
            self._twitter_data.iter_tweets_mentioning(self._user_id_str),
            count, since_id, max_id)
        return [
            tweet.to_dict(
                self._twitter_data, trim_user=trim_user,
                contributor_details=contributor_details,
                include_entities=include_entities)
            for tweet in tweets]

    @fake_api('statuses/user_timeline.json')
    def statuses_user_timeline(self, user_id=None, screen_name=None,
                               since_id=None, count=None, max_id=None,
                               trim_user=None, exclude_replies=None,
                               contributor_details=None,
                               include_rts=None):
        if user_id is None and screen_name is not None:
            user = self._twitter_data.get_user_by_screen_name(screen_name)
            user_id = user.id_str
            screen_name = None
        if user_id is None or screen_name is not None:
            raise NotImplementedError("user_id/screen_name params")

        tweets = self._filter_timeline(
            self._twitter_data.iter_tweets_from(user_id), count, since_id,
            max_id)
        if exclude_replies:
            tweets = [tweet for tweet in tweets if tweet.reply_to is None]
        if include_rts is not None:
            raise NotImplementedError("exclude_rts param")
        return [
            tweet.to_dict(
                self._twitter_data, trim_user=trim_user,
                contributor_details=contributor_details)
            for tweet in tweets]

    @fake_api('statuses/home_timeline.json')
    def statuses_home_timeline(self, count=None, since_id=None, max_id=None,
                               trim_user=None, exclude_replies=None,
                               contributor_details=None,
                               include_entities=None):
        raise NotImplementedError()

    # TODO: Implement statuses_retweets_of_me()

    # Tweets

    @fake_api('statuses/retweets.json')
    def statuses_retweets(self, id, count=None, trim_user=None):
        raise NotImplementedError()

    @fake_api('statuses/show.json')
    def statuses_show(self, id, trim_user=None, include_my_retweet=None,
                      include_entities=None):
        return self._tweet_or_404(id).to_dict(
            self._twitter_data, trim_user=trim_user,
            include_my_retweet=include_my_retweet,
            include_entities=include_entities)

    @fake_api('statuses/destroy.json')
    def statuses_destroy(self, id, trim_user=None):
        tweet = self._tweet_or_404(id)
        # TODO: Better error
        if tweet.user_id_str != self._user_id_str:
            raise NotImplementedError()
        tweet_dict = tweet.to_dict(self._twitter_data, trim_user=trim_user)
        self._twitter_data.del_tweet(id)
        return tweet_dict

    @fake_api('statuses/update.json')
    def statuses_update(self, status, in_reply_to_status_id=None, lat=None,
                        long=None, place_id=None, display_coordinates=None,
                        trim_user=None, media_ids=None):
        if set([lat, long, place_id, display_coordinates]) != set([None]):
            raise NotImplementedError("Unsupported parameter")
        tweet = self._twitter_data.new_tweet(
            status, self._user_id_str, reply_to=in_reply_to_status_id,
            media_ids=media_ids)
        return tweet.to_dict(self._twitter_data, trim_user=trim_user)

    @fake_api('statuses/retweet.json')
    def statuses_retweet(self, id, trim_user=None):
        raise NotImplementedError()

    @fake_api('media/upload.json', host_prefix='upload')
    def media_upload(self, media, additional_owners=None):
        media = self._twitter_data.new_media(
            media, additional_owners=additional_owners)
        return media.to_dict(self._twitter_data)

    # TODO: Implement statuses_oembed()
    # TODO: Implement statuses_retweeters_ids()

    # Search

    # TODO: Implement search_tweets()

    # Streaming

    @fake_api('statuses/filter.json', 'stream')
    def stream_filter(self, follow=None, track=None, locations=None,
                      stall_warnings=None):
        track_res = []
        if track:
            for term in track.split(','):
                track_res.append(re.compile(r'\b%s\b' % (re.escape(term),)))

        follow = [] if follow is None else follow.split(',')

        def stream_filter_predicate(tweet):
            for user_id_str in follow:
                if tweet.user_id_str == user_id_str:
                    return True
            for track_re in track_res:
                if track_re.search(tweet.text):
                    return True
            return False

        stream = self._twitter_data.new_stream()
        stream.add_message_type('tweet', stream_filter_predicate)
        return stream.resp

    # TODO: Implement stream_sample()
    # TODO: Implement stream_firehose()

    @fake_api('user.json', 'userstream')
    def userstream_user(self, stringify_friend_ids, stall_warnings=None,
                        with_='followings', replies=None, **kw):
        with_ = kw.pop('with', with_)
        assert kw == {}
        user = self._twitter_data.get_user(self._user_id_str)
        mention_re = re.compile(r'@%s\b' % (user.screen_name,))

        if with_ != 'user':
            raise NotImplementedError("with != followings")

        def userstream_follow_predicate(follow):
            return (
                follow.source_id == self._user_id_str or
                follow.target_id == self._user_id_str)

        def userstream_unfollow_predicate(follow):
            return follow.source_id == self._user_id_str

        def userstream_tweet_predicate(tweet):
            if tweet.user_id_str == self._user_id_str:
                return True
            if mention_re.search(tweet.text):
                return True
            if with_ == 'followings':
                pass
            return False

        def userstream_dm_predicate(dm):
            if dm.recipient_id_str == self._user_id_str:
                return True
            if dm.sender_id_str == self._user_id_str:
                return True
            return False

        stream = self._twitter_data.new_stream()
        stream.add_message_type('tweet', userstream_tweet_predicate)
        stream.add_message_type('dm', userstream_dm_predicate)
        stream.add_message_type('follow', userstream_follow_predicate)
        stream.add_message_type('unfollow', userstream_unfollow_predicate)

        # TODO: Proper friends.
        stream.deliver({'friends_str': []})

        return stream.resp

    # Direct Messages
    def _clamp_dms(self, dms, since_id=None, max_id=None, count=None):
        if since_id is not None:
            since_id = int(since_id)
            dms = [dm for dm in dms if int(dm.id_str) > since_id]
        if max_id is not None:
            max_id = int(max_id)
            dms = [dm for dm in dms if int(dm.id_str) <= max_id]

        dms = sorted(dms, reverse=True)
        count = 20 if count is None else min(count, 200)
        return dms[:count]

    @fake_api('direct_messages.json')
    def direct_messages(self, since_id=None, max_id=None, count=None,
                        include_entities=None, skip_status=None):
        dms = self._twitter_data.dms.values()
        dms = [dm for dm in dms if dm.recipient_id_str == self._user_id_str]
        dms = self._clamp_dms(dms, since_id, max_id, count)

        return self._twitter_data.to_dicts(
            *dms, include_entities=include_entities, skip_status=skip_status)

    @fake_api('direct_messages/sent.json')
    def direct_messages_sent(self, since_id=None, max_id=None, count=None,
                             include_entities=None, page=None):
        dms = self._twitter_data.dms.values()
        dms = [dm for dm in dms if dm.sender_id_str == self._user_id_str]
        dms = self._clamp_dms(dms, since_id, max_id, count)

        if page is None:
            page = 1

        page_end = page * 20
        dms = dms[page_end - 20:page_end]

        return self._twitter_data.to_dicts(
            *dms, include_entities=include_entities)

    @fake_api('direct_messages/show.json')
    def direct_messages_show(self, id):
        dm = self._dm_or_404(id)

        if (dm.recipient_id_str != self._user_id_str and
                dm.sender_id_str != self._user_id_str):
            # The actual response given to us by Twitter
            raise TwitterAPIError(403, "Forbidden", json.dumps({
                "errors": [{
                    "message": "There was an error sending your message: .",
                    "code": 151
                }]}))

        return self._twitter_data.to_dicts(dm)

    @fake_api('direct_messages/destroy.json')
    def direct_messages_destroy(self, id, include_entities=None):
        dm = self._dm_or_404(id)

        if (dm.recipient_id_str != self._user_id_str and
                dm.sender_id_str != self._user_id_str):
            # The actual response given to us by Twitter
            raise TwitterAPIError(403, "Forbidden", json.dumps({
                "errors": [{
                    "message": "There was an error sending your message: .",
                    "code": 151
                }]}))

        del self._twitter_data.dms[dm.id_str]
        return dm.to_dict(
            self._twitter_data, include_entities=include_entities)

    @fake_api('direct_messages/new.json')
    def direct_messages_new(self, text, user_id=None, screen_name=None):
        if user_id is None and screen_name is None:
            raise TwitterAPIError(400, "Bad Request", json.dumps({
                "errors": [{
                    "message": (
                        "Recipient (user, screen name, or id) "
                        "parameter is missing."),
                    "code": 38
                }]}))

        if user_id is None:
            user = self._twitter_data.get_user_by_screen_name(screen_name)
            user_id = user.id_str

        dm = self._twitter_data.new_dm(text, self._user_id_str, user_id)
        return dm.to_dict(self._twitter_data)

    # Friends & Followers

    # TODO: Implement friendships_no_retweets_ids()
    # TODO: Implement friends_ids()
    # TODO: Implement followers_ids()
    # TODO: Implement friendships_lookup()
    # TODO: Implement friendships_incoming()
    # TODO: Implement friendships_outgoing()

    @fake_api('friendships/create.json')
    def friendships_create(self, user_id=None, screen_name=None, follow=None):
        if follow is not None:
            raise NotImplementedError("follow param")

        user = None
        if screen_name is not None:
            user = self._twitter_data.get_user_by_screen_name(screen_name)
        elif user_id is not None:
            user = self._twitter_data.get_user(user_id)

        if user is None:
            # The actual response given to us by Twitter if no user was found
            # or if both user_id and screen_name were not specified
            raise TwitterAPIError(403, "Forbidden", json.dumps({
                "errors": [{
                    "message": "Cannot find specified user.",
                    "code": 108
                }]}))

        self._twitter_data.add_follow(self._user_id_str, user.id_str)
        return user.to_dict(self._twitter_data)

    @fake_api('friendships/destroy.json')
    def friendships_destroy(self, user_id=None, screen_name=None):
        user = None
        if screen_name is not None:
            user = self._twitter_data.get_user_by_screen_name(screen_name)
        elif user_id is not None:
            user = self._twitter_data.get_user(user_id)

        if user is None:
            # The actual response given to us by Twitter if no user was found
            # or if both user_id and screen_name were not specified
            raise self._404()

        self._twitter_data.del_follow(self._user_id_str, user.id_str)
        return user.to_dict(self._twitter_data)

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
