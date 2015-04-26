First steps
===========

.. todo::
   Finish writing this.

Authorization
-------------

.. todo::
   Do we support application-only usage?

In order to sign API requests, txTwitter needs the following credentials:
 * The ``consumer_key`` and ``consumer_secret`` identify your application and can
   be found in the Application Management page for your application at
   https://apps.twitter.com
 * The ``token_key`` and ``token_secret`` identify a Twitter account and can be
   obtained via OAuth or generated in the Application Management interface
   mentioned above for that account that owns the application.

The full application-user OAuth flow involves user interaction with a web
browser, so txTwitter leaves all of that up to the application. [#oauth]_


Making a request
----------------

.. todo::
   Finish writing this.

To make a request, you need an instance of :class:`.TwitterClient` with suitable
credentials: [#creds]_

.. code-block:: python

   twitter = self.TwitterClient(
       consumer_key='cChZNFj6T5R0TigYB9yd1w',
       consumer_secret='L8qq9PZyRg6ieKGEKhZolGC0vJWLw8iEJ88DRdyOg',
       token_key='7588892-kagSNqWge8gB1WwE3plnFsJHAZVfxWD7Vb57p0b4',
       token_secret='PbKfYqSryyeKDWz4ebtY3o5ogNLG11WJuZBc9fQrQo')

.. code-block:: python

   tweets_d = twitter.statuses_user_timeline(
       screen_name="twistedmatrix")
   tweets_d.addCallback(...)

.. rubric:: Footnotes

.. [#oauth]
   While txTwitter could probably implement parts of the flow that don't
   involve the browser, we decided the extra complexity wasn't worth the
   minimal value it may provide.

.. [#creds]
   These credentials are from Twitter's auth documentation and were valid at
   the time of writing.
