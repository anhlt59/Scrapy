# -*- coding: utf-8 -*-

# Define here the models for your spider middleware
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/spider-middleware.html
from urllib.parse import parse_qsl, urlparse
from scrapy import signals
from scrapy_splash import SplashRequest
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from importlib import import_module
from scrapy_selenium import SeleniumRequest
from scrapy_selenium.middlewares import SeleniumMiddleware
from scrapy.exceptions import DontCloseSpider, CloseSpider, NotConfigured
from scrapy.http import HtmlResponse, TextResponse
from seleniumwire import webdriver
from json.decoder import JSONDecodeError
import json
import logging
import re
import time
from rotating_proxies.middlewares import RotatingProxyMiddleware

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
            raise DontCloseSpider
            # self.logger.info(f'{spider.name} request more data')
        else:
            self.logger.info(f'Data is empty. Stop {spider.name}')
            # raise CloseSpider(f'Data is empty. Stop {spider.name}')


class CustomRotatingProxyMiddleware(RotatingProxyMiddleware):
    """ Random proxy per request. """

    def process_request(self, request, spider):
        """ Handle splash request."""

        if 'proxy' in request.meta and not request.meta.get('_rotating_proxy'):
            return
        proxy = self.proxies.get_random()
        if not proxy:
            if self.stop_if_no_proxies:
                raise CloseSpider("no_proxies")
            else:
                logger.warn("No proxies available; marking all proxies as unchecked")
                self.proxies.reset()
                proxy = self.proxies.get_random()
                if proxy is None:
                    logger.error("No proxies available even after a reset.")
                    raise CloseSpider("no_proxies_after_reset")

        if isinstance(request, SplashRequest):
            request.meta['splash']['proxy'] = proxy
        else:
            request.meta['proxy'] = proxy
        request.meta['download_slot'] = self.get_proxy_slot(proxy)
        request.meta['_rotating_proxy'] = True


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

        # if driver_proxy:
        #     self.proxy = cycle(PROXIES)
        # if driver_agent:
        #     self.agent = cycle(AGENTS)

    def init_driver(self):
        # settings selenium
        driver_options = webdriver.ChromeOptions()
        if self.browser_executable_path:
            driver_options.binary_location = self.browser_executable_path

        # # switch user_agent, proxy
        # if hasattr(self, 'agent'):
        #     driver_options.add_argument(f"--user-agent='{next(self.agent)}'")
        # if hasattr(self, 'proxy'):
        #     driver_options.add_argument(f"--proxy-server='{next(self.proxy)}'")

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
        result = [self.extract_form(req, spider) for req in filted_request]

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

    def extract_form(self, request, spider):
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
            self.logger.critical(f'CustomSeleniumWireMiddleware - {spider.name} - {e}')
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


class CustomSeleniumMiddleware(SeleniumMiddleware):

    def __init__(self, driver_name, driver_executable_path, driver_arguments,
                 browser_executable_path, driver_proxy, driver_agent,
                 driver_load_img, driver_disable_notify):
        webdriver_base_path = f'selenium.webdriver.{driver_name}'

        driver_klass_module = import_module(f'{webdriver_base_path}.webdriver')
        driver_klass = getattr(driver_klass_module, 'WebDriver')

        driver_options_module = import_module(f'{webdriver_base_path}.options')
        driver_options_klass = getattr(driver_options_module, 'Options')

        driver_options = driver_options_klass()
        if browser_executable_path:
            driver_options.binary_location = browser_executable_path
        for argument in driver_arguments:
            driver_options.add_argument(argument)

        # if driver_proxy:
        #     agent = random.choice(AGENTS)
        #     driver_options.add_argument(f"--user-agent='{agent}'")
        # if driver_agent:
        #     proxy = random.choice(PROXY)
        #     driver_options.add_argument(f"--proxy-server='{PROXY}'")
        #
        #     driver_load_img = driver_load_img,
        #     driver_disable_notify = driver_disable_notify

        chrome_prefs = {"disk-cache-size": 4096}
        if not driver_load_img:
            chrome_prefs.update(
                {
                    "profile.default_content_settings": {"images": 2},
                    "profile.managed_default_content_settings": {"images": 2}
                }
            )
        if driver_disable_notify:
            chrome_prefs.update(
                {"profile.default_content_setting_values.notifications": 2}
            )
        driver_options.add_experimental_option("prefs", chrome_prefs)

        driver_kwargs = {
            'executable_path': driver_executable_path,
            f'{driver_name}_options': driver_options
        }

        self.driver = driver_klass(**driver_kwargs)
        # self.driver.__setattr__('click_element', self.__click_element)
        # self.driver.__setattr__('scroll_to_bottom', self.__scroll_to_bottom)

    @classmethod
    def from_crawler(cls, crawler):
        """Initialize the middleware with the crawler settings"""

        driver_name = crawler.settings.get('SELENIUM_DRIVER_NAME')
        driver_executable_path = crawler.settings.get('SELENIUM_DRIVER_EXECUTABLE_PATH')
        browser_executable_path = crawler.settings.get('SELENIUM_BROWSER_EXECUTABLE_PATH')
        driver_arguments = crawler.settings.get('SELENIUM_DRIVER_ARGUMENTS')
        driver_proxy = crawler.settings.get('CHANGE_PROXY', False)
        driver_agent = crawler.settings.get('CHANGE_AGENT', False)
        driver_load_img = crawler.settings.get('LOAD_IMAGE', True)
        driver_disable_notify = crawler.settings.get('DISABLE_NOTIFY', True)

        if not driver_name or not driver_executable_path:
            raise NotConfigured(
                'SELENIUM_DRIVER_NAME and SELENIUM_DRIVER_EXECUTABLE_PATH must be set'
            )

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
        """Process a request using the selenium driver if applicable"""
        if not isinstance(request, SeleniumRequest):
            return None

        self.driver.get(request.url)
        time.sleep(1)
        for cookie_name, cookie_value in request.cookies.items():
            self.driver.add_cookie(
                {
                    'name': cookie_name,
                    'value': cookie_value
                }
            )

        if request.wait_until:
            WebDriverWait(self.driver, request.wait_time).until(
                request.wait_until
            )

        if request.screenshot:
            request.meta['screenshot'] = self.driver.get_screenshot_as_png()

        if request.script:
            self.driver.execute_script(request.script)

        # if 'scroll_to_bottom' in request.meta and request.meta['scroll_to_bottom']:
        #     self.driver.scroll_to_bottom()

        body = str.encode(self.driver.page_source)

        # Expose the driver via the "meta" attribute
        request.meta.update({'driver': self.driver})

        return HtmlResponse(
            self.driver.current_url,
            body=body,
            encoding='utf-8',
            request=request
        )

    # def __click_element(self, element_to_click, offset=50, retries=5):
    #     """ Try scroll and click element."""
    #     try:
    #         time.sleep(0.05)
    #         location = element_to_click.location
    #         self.driver.execute_script(f"window.scrollTo(0, {location['y'] - offset})")
    #
    #         ActionChains(self.driver).move_to_element(element_to_click).double_click().perform()
    #     except:
    #         if retries:
    #             self.__click_element(element_to_click, offset + 50, retries - 1)
    #         else:
    #             raise Exception("Can't click element")
    #
    # def __scroll_to_bottom(self, scroll_px=2160, max_scroll=25, scroll_delay_time=0.15):
    #     """ Scroll to bottom of page."""
    #     location = scroll_px
    #     # scroll_height = self.driver.execute_script("return document.body.scrollHeight")
    #     while location < self.driver.execute_script("return document.body.scrollHeight") and max_scroll:
    #         self.driver.execute_script(f"window.scrollTo(0, {location});")
    #         time.sleep(scroll_delay_time)
    #         location += scroll_px
    #         max_scroll -= 1
