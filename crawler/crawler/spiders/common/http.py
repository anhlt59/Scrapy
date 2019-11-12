# -*- coding: utf8 -*-
from scrapy import Request
from scrapy_splash import SlotPolicy
from scrapy_splash.utils import to_native_str
import logging
import copy
import sys
import json


logger = logging.getLogger(__name__)


class ApiSeleniumRequest(Request):
    """ Scrapy ``Request`` subclass providing additional arguments
        return request/response which has url match in request_urls
    """

    def __init__(self, wait_time=60, script=None, request_urls=[], keep_browser=False, *args, **kwargs):
        """Initialize a new selenium request
        Parameters
        ----------
        wait_time: int
            The number of seconds to wait.
        request_urls: list
            The list of urls to get
        keep_browser: Boolen
            True - keep browser until the spider closed
            False - close browser when this request done
        script: str
            JavaScript code to execute.
        """

        self.wait_time = wait_time
        self.script = script
        self.request_urls = request_urls
        self.keep_browser = keep_browser

        super().__init__(*args, **kwargs)


class ApiSplashRequest(Request):
    script = """
    function main(splash, args)
        splash.private_mode_enabled = false
        splash.request_body_enabled = true
        splash.response_body_enabled = false

        assert(splash:go(splash.args.url))
        splash:wait(0.5)

        return splash:har()
    end
    """

    def __init__(self,
                 url=None,
                 callback=None,
                 method='GET',
                 endpoint='execute',
                 args=None,
                 splash_url=None,
                 slot_policy=SlotPolicy.PER_DOMAIN,
                 splash_headers=None,
                 dont_process_response=False,
                 dont_send_headers=False,
                 magic_response=True,
                 session_id='default',
                 http_status_from_error_code=True,
                 cache_args=None,
                 meta=None,
                 **kwargs):

        if url is None:
            url = 'about:blank'

        url = to_native_str(url)

        meta = copy.deepcopy(meta) or {}
        splash_meta = meta.setdefault('splash', {})
        splash_meta.setdefault('endpoint', endpoint)
        splash_meta.setdefault('slot_policy', slot_policy)

        if splash_url is not None:
            splash_meta['splash_url'] = splash_url
        if splash_headers is not None:
            splash_meta['splash_headers'] = splash_headers

        if dont_process_response:
            splash_meta['dont_process_response'] = True
        else:
            splash_meta.setdefault('magic_response', magic_response)

        if dont_send_headers:
            splash_meta['dont_send_headers'] = True

        if http_status_from_error_code:
            splash_meta['http_status_from_error_code'] = True

        if cache_args is not None:
            splash_meta['cache_args'] = cache_args

        if session_id is not None:
            if splash_meta['endpoint'].strip('/') == 'execute':
                splash_meta.setdefault('session_id', session_id)

        args = {'lua_source': self.script, 'wait': 1}
        _args = {'url': url}  # put URL to args in order to preserve #fragment
        _args.update(args or {})
        _args.update(splash_meta.get('args', {}))
        splash_meta['args'] = _args

        # This is not strictly required, but it strengthens Splash
        # requests against AjaxCrawlMiddleware
        meta['ajax_crawlable'] = True

        super(ApiSplashRequest, self).__init__(url, callback, method, meta=meta,
                                            **kwargs)

    @property
    def _processed(self):
        return self.meta.get('_splash_processed')

    @property
    def _splash_args(self):
        return self.meta.get('splash', {}).get('args', {})

    @property
    def _original_url(self):
        return self._splash_args.get('url')

    @property
    def _original_method(self):
        return self._splash_args.get('http_method', 'GET')

    def __str__(self):
        if not self._processed:
            return super(ApiSplashRequest, self).__str__()
        return "<%s %s via %s>" % (self._original_method, self._original_url, self.url)

    __repr__ = __str__
