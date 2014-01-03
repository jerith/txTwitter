from twisted.web import error


class TwitterAPIError(error.Error):
    pass


class RateLimitedError(TwitterAPIError):
    pass
