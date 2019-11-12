# -*- coding: utf-8 -*-

# Define here the models for your spider middleware
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/spider-middleware.html
from urllib.parse import parse_qsl, urlparse
from scrapy import signals
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy_selenium.middlewares import SeleniumMiddleware
from scrapy.exceptions import DontCloseSpider, CloseSpider, NotConfigured
from scrapy.http import HtmlResponse, TextResponse
from seleniumwire import webdriver
from itertools import cycle
import json
from json.decoder import JSONDecodeError
import logging
import re
import time

from .agents_n_proxies import AGENTS, PROXIES
from .spiders.common.utils import obj
from .spiders.common.http import ApiSplashRequest, ApiSeleniumRequest


logger = logging.getLogger(__name__)


class ScheduleRequestSpiderMiddleware:
    # SpiderMiddleware
    logger = logger.getChild('schedule')

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_idle, signal=signals.spider_idle)
        return s

    def spider_idle(self, spider):

        empty = True
        reqs = spider.start_requests()

        # Create new request
        for req in reqs:
            # self.logger.info('have new request')
            spider.crawler.engine.crawl(req, spider)
            if empty:
                empty = False

        # Check start_request is empty
        if not empty:
            self.logger.info(f'{spider.name} request more data')
        else:
            self.logger.info(f'Data is empty. Stop {spider.name}')
            return None

        raise DontCloseSpider


class CustomUserAgentProxyMiddleware:
    # DownloadMiddleware
    user_agent_list = cycle(AGENTS)
    proxy_list = cycle(PROXIES)

    def __init__(self, switch_user_agent, switch_proxy):
        self.switch_user_agent = switch_user_agent
        self.switch_proxy = switch_proxy

    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings

        middleware = cls(
            switch_user_agent=settings.getbool('SWITCH_USER_AGENT', True),
            switch_proxy=settings.getbool('SWITCH_PROXY', False)
        )
        return middleware

    def process_request(self, request, spider):
        if self.switch_user_agent:
            user_agent = next(self.user_agent_list)
            request.headers['User-Agent'] = user_agent

        if self.switch_proxy:
            endpoint, port = next(self.proxy_list)
            request.meta['proxy'] = f'http://{endpoint}:{port}'
            # request.headers['Proxy-Authorization'] = basic_authentication


class CustomRetryMiddleware(RetryMiddleware):

    def retry_504(self, request, spider, retries=10):
        """ Waiting for splash server restart."""
        time.sleep(30)

        reason = 'retry 504'
        response = self._retry(request, reason, spider)

        if not response and response.status == 504 and retries > 0:
            return self.retry_504(request, spider, retries - 1)
        return response

    def process_response(self, request, response, spider):
        if response.status == 504:
            logging.info('504 - wait for splash restart')
            return self.retry_504(self, request, spider)

        return super().process_response(request, response, spider)


class CustomSeleniumWireMiddleware(SeleniumMiddleware):
    # DownloadMiddleware
    logger = logger.getChild('seleniumwire')

    def __init__(self,
                 driver_name,
                 driver_executable_path,
                 browser_executable_path,
                 driver_arguments,
                 driver_proxy,
                 driver_agent,
                 driver_load_img,
                 driver_disable_notify):

        self.driver_name = driver_name
        self.driver_executable_path = driver_executable_path
        self.driver_arguments = driver_arguments
        self.browser_executable_path = browser_executable_path
        self.driver_load_img = driver_load_img
        self.driver_disable_notify = driver_disable_notify

        if driver_proxy:
            self.proxy = cycle(PROXIES)
        if driver_agent:
            self.agent = cycle(AGENTS)

    def init_driver(self):
        # settings selenium
        driver_options = webdriver.ChromeOptions()
        if self.browser_executable_path:
            driver_options.binary_location = self.browser_executable_path

        # switch user_agent, proxy
        if hasattr(self, 'agent'):
            driver_options.add_argument(f"--user-agent='{next(self.agent)}'")
        if hasattr(self, 'proxy'):
            driver_options.add_argument(f"--proxy-server='{next(self.proxy)}'")

        # add SELENIUM_DRIVER_ARGUMENTS options
        for argument in self.driver_arguments:
            driver_options.add_argument(argument)

        # add experimental option: on/off image and notify
        chrome_prefs = {"disk-cache-size": 4096}
        if not self.driver_load_img:
            chrome_prefs.update(
                {
                    "profile.default_content_settings": {"images": 2},
                    "profile.managed_default_content_settings": {"images": 2}
                }
            )
        if self.driver_disable_notify:
            chrome_prefs.update(
                {"profile.default_content_setting_values.notifications": 2}
            )
        driver_options.add_experimental_option("prefs", chrome_prefs)

        self.driver = webdriver.Chrome(
            executable_path=self.driver_executable_path,
            options=driver_options
        )

    @classmethod
    def from_crawler(cls, crawler):
        """Initialize the middleware with the crawler settings"""
        driver_name = crawler.settings.get('SELENIUM_DRIVER_NAME')
        driver_executable_path = crawler.settings.get('SELENIUM_DRIVER_EXECUTABLE_PATH')
        browser_executable_path = crawler.settings.get('SELENIUM_BROWSER_EXECUTABLE_PATH')
        driver_arguments = crawler.settings.get('SELENIUM_DRIVER_ARGUMENTS')
        driver_proxy = crawler.settings.get('SELENIUM_CHANGE_PROXY', False)
        driver_agent = crawler.settings.get('SELENIUM_CHANGE_AGENT', False)
        driver_load_img = crawler.settings.get('SELENIUM_LOAD_IMAGE', False)
        driver_disable_notify = crawler.settings.get('SELENIUM_DISABLE_NOTIFY', True)

        if not driver_name or not driver_executable_path:
            raise NotConfigured('SELENIUM_DRIVER_NAME and SELENIUM_DRIVER_EXECUTABLE_PATH must be set')

        middleware = cls(
            driver_name=driver_name,
            driver_executable_path=driver_executable_path,
            driver_arguments=driver_arguments,
            browser_executable_path=browser_executable_path,
            driver_proxy=driver_proxy,
            driver_agent=driver_agent,
            driver_load_img=driver_load_img,
            driver_disable_notify=driver_disable_notify
        )

        crawler.signals.connect(middleware.spider_closed, signals.spider_closed)
        return middleware

    def process_request(self, request, spider):
        """ Process a request using the selenium driver if applicable. """
        if not isinstance(request, ApiSeleniumRequest):
            return None

        # init driver selenium
        if not hasattr(self, 'driver'):
            self.init_driver()

        # list of request which you want to catch
        request_urls = request.request_urls
        if not request_urls:
            return TextResponse(
                request.url,
                request=request,
                body='[]',
                encoding='utf-8'
            )

        # restrict request capture for performance reasons
        self.driver.scopes = [f'{url_restrict}*' for url_restrict in request_urls]

        # clear driver.requests
        del self.driver.requests
        self.driver.get(request.url)

        # wait untill request is called
        timeout = request.wait_time
        for url in request_urls:
            self.driver.wait_for_request(url, timeout=timeout)

        body = str.encode(self.driver.page_source)

        # filter request
        filted_request = []
        for req in self.driver.requests:
            for req_url in request_urls:
                # search advance with regex
                if req_url in req.path and req.method in ['GET', 'POST']:
                    filted_request.append(req)

        # extract form request. #if fail stop process
        result = [self.extract_form(req) for req in filted_request]

        # quit driver if keep_browser is false
        if not request.keep_browser:
            self.driver.quit()

        # return a Response wont calling any other process_request() or process_exception() from another middleware
        return TextResponse(
            request.url,
            request=request,
            body=json.dumps(result),
            encoding='utf-8'
        )

    def spider_closed(self):
        """Shutdown the driver when spider is closed"""
        if hasattr(self, 'driver'):
            self.driver.quit()

    def extract_form(self, request):
        # get method (GET or POST)
        method = request.method.lower()

        # get headers(dict)
        headers = dict(request.headers)

        # get body(dict)
        body = request.body
        try:
            body = json.loads(body.decode()) if body else None
        except JSONDecodeError:
            body = dict(parse_qsl(body.decode()))

        # get url(str) and params(dict)
        full_url = request.path

        # get params and url
        resultparse = urlparse(full_url)
        str_params = resultparse.query
        params = dict(parse_qsl(str_params))
        url = full_url.replace(f'?{str_params}', '') if params else full_url

        # get response
        try:
            response = json.loads(request.response.body.decode())
        except Exception as e:
            self.logger.critical(f'CustomSeleniumWireMiddleware - {e}')
            response = None

        # form request
        return {
            "request": {
                "url": url,
                "method": method,
                "headers": headers,
                "params": params,
                "data": body
            },
            "response": response
        }
