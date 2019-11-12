# -*- coding: utf8 -*-
from scrapy import Spider
from scrapy.http import Request, JsonRequest
from scrapy_selenium import SeleniumRequest
from scrapy_splash import SplashRequest
from scrapy.selector import Selector
from scrapy.utils.project import get_project_settings
from scrapy.exceptions import CloseSpider
from cssselect.parser import SelectorSyntaxError
from selenium.webdriver.remote.errorhandler import InvalidSelectorException
from twisted.internet.error import DNSLookupError
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import TimeoutError, TCPTimedOutError
import re
import json
import base64

from .utils import config_logging, obj, set_law
from .http import ApiSplashRequest


class BaseSpider(Spider):

    name = "BaseSpider"
    count = 0
    params = None
    # custom_settings = None

    def __init__(self, *a, **kw):
        config_logging()
        super().__init__(*a, **kw)

        # check params is declared
        if not getattr(self, 'params', None):
            raise CloseSpider('Spider has no params')

    def parse_data(self, response):
        self.bidDatas = json.loads(response.body)
        self.logger.info(f'{self.name} - got {len(self.bidDatas)} biddata')
        if len(self.bidDatas) == 0:
            raise CloseSpider(f'{self.name} - BidDatas is empty - crawl done')

    def post_item(self, item):
        # post_link = 'http://192.168.1.142:82/api/v1/crawl/hotel/a?log=1&json=1'
        post_link = f'{item.post_link}?json=1'
        return JsonRequest(post_link, method='POST', data=item, dont_filter=True,
                           callback=self.post_success, errback=self.post_fail)

    def post_success(self, response):
        # logs success
        self.logger.info(f'Post item done - {response.status}')

    def post_fail(self, failure):
        # logs failures
        if failure.check(HttpError): 
           response = failure.value.response 
           self.logger.error(f"HttpError occurred on {response.url} - got {response.status}")  
      
        elif failure.check(DNSLookupError): 
            self.logger.error(f"DNSLookupError occurred on {failure.request.url}") 
            raise CloseSpider("DNSLookupError")

        elif failure.check(TimeoutError, TCPTimedOutError): 
            self.logger.error(f"TimeoutError occurred on {failure.request.url}") 
            raise CloseSpider(f"TimeoutError")
        # self.logger.error(repr(failure))


class CatSpider(BaseSpider):
    """
        crawl category website
        which dont use javascript
    """
    name = "CatSpider"
    custom_settings = {
        **get_project_settings(),
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
            'crawler.middlewares.ScheduleRequestSpiderMiddleware': 100,
            'scrapy.downloadermiddlewares.UserAgentMiddleware': None,
            'crawler.middlewares.CustomUserAgentProxyMiddleware': 400,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
        },
        'RETRY_TIMES': 10,
    }

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.url = f'http://crawler.wemarry.vn/api/get-cat-multi?id={self.params}'
        self.logger.info(f'{self.name} is running')

    def start_requests(self):
        # get cat data
        if not hasattr(self, 'bidDatas'):
            yield JsonRequest(self.url, callback=self.parse_data, dont_filter=True)

        # create requests
        if getattr(self, 'bidDatas', None):
            data = self.bidDatas.pop()
            item = obj(
                id_web=data.get('ID_WEB'),
                active=data.get('ACTIVE'),
                post_link=data.get('POST_LINK'),
                link=data.get('LINK'),
                law_next_page=data.get('LAW_NEXT_PAGE'),
                link_detail=data.get('Link_DETAIl'),
                cat_link=None,
            )
            for request in self.create_request(item):
                yield request

    def create_request(self, item):
        yield Request(url=item.link, callback=self.parse, meta={'item': item})

    def parse(self, response):
        item = request.meta.get('item')
        link = response.url
        link_detail = item.link_detail
        law_next_page = item.law_next_page

        if not link_detail or not law_next_page:
            self.logger.error("Link_DETAIl or LAW_NEXT_PAGE is not set")
            raise CloseSpider("Link_DETAIl or LAW_NEXT_PAGE is not set")
        cat_link = [response.urljoin(url) for url in response.css(f"{link_detail}::attr(href)").extract()]
        if not cat_link:
            self.logger.info(f"cat link is empty url {response.url}")
            return None

        self.count += len(cat_link)
        self.logger.info(f"got {len(cat_link)} cat link - total {self.count}")
        item.cat_link = cat_link
        yield self.post_item(item)

        # follow pagination link
        try:
            # nextpage by element
            next_page_url = response.css(f"{law_next_page}::attr(href)").extract_first()
            abs_next_page_url = response.urljoin(next_page_url) if next_page_url else ''
        except SelectorSyntaxError:
            # nextpage by rule
            page_no = re.search(rf'(?<={law_next_page})\d+', link)
            if page_no:
                nextpage = int(page_no.group()) + 1
                abs_next_page_url = re.sub(rf'(?<={law_next_page})\d+', str(nextpage), link)
        except Exception as err:
            self.loger.error(err)

        if abs_next_page_url:
            yield Request(abs_next_page_url, callback=self.parse, meta={'item': item})


class DetailSpider(BaseSpider):
    """
        crawl detail website
        which dont use javascript
    """
    name = "DetailSpider"
    custom_settings = {
        **get_project_settings(),
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
            'crawler.middlewares.ScheduleRequestSpiderMiddleware': 100,
            'scrapy.downloadermiddlewares.UserAgentMiddleware': None,
            'crawler.middlewares.CustomUserAgentProxyMiddleware': 400,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
        },
        'RETRY_TIMES': 10,
    }

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.url = f'http://crawler.wemarry.vn/api/get-detail-multi?id={self.params}'
        self.logger.info(f'{self.name} is running')

    def start_requests(self):
        # get cat data
        if not hasattr(self, 'bidDatas'):# or not self.bidDatas:
            yield JsonRequest(self.url, callback=self.parse_data, dont_filter=True)
        # create requests   
        if getattr(self, 'bidDatas', None):
            data = self.bidDatas.pop()
            item = obj(
                id_web=data.get('ID_WEB'),
                id=data.get('ID'),
                link=data.get('LINK'),
                post_link=data.get('POST_LINK'),
                arr_law = data.get('ARR_LAW'),
                # hotel_city_id=None, # ha noi/ da nang/ ho chi minh
                # hotel_search_image='',
                # # detail hotel
                # hotel_source=None, # Agoda,...
                # hotel_type=None, # str nha nghi/ khach san, ...
                # hotel_name=None, # str Hotel name
                # hotel_star=0, # int Hotel rating
                # hotel_address=None, # str Hotel address
                # hotel_description=None, # str Hotel description
                # hotel_image=None, # list of Hotel image
                # hotel_attribute=None, # list() Hotel attribute
                # hotel_latlng=None, # str 'lat,lon'
                # hotel_price=None, # list of room info: { name, price, guest, attribute }
                # # review
                # hotel_review=None # list of reviews: { name, image, rating, title, content }
            )
            for request in self.create_request(item):
                yield request

    def create_request(self, item):
        yield Request(url=item.link, callback=self.parse, meta={'item': item})

    def parse(self, response):
        item = response.meta.get('item')
        arr_law = item.arr_law

        if not arr_law:
            self.logger.error("ARR_LAW is not set")
            raise CloseSpider("ARR_LAW is not set")

        set_law(item, arr_law, response)
        self.count += 1
        self.logger.info(f"crawl {item.link} done - total {self.count}")
        yield self.post_item(item)
        # from pprint import pprint 
        # pprint(item)


class SplashCat(CatSpider):

    name = "SplashCat"
    custom_settings = {
        **get_project_settings(),
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
            'crawler.middlewares.ScheduleRequestSpiderMiddleware': 100,
            # 'crawler.middlewares.CustomRetryMiddleware': 120,
            'scrapy.downloadermiddlewares.UserAgentMiddleware': None,
            'crawler.middlewares.CustomUserAgentProxyMiddleware': 400,
            'scrapy_splash.SplashCookiesMiddleware': 723,
            'scrapy_splash.SplashMiddleware': 725,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
        },
        'RETRY_TIMES': 10,
    }
    script = """
    function main(splash, args)
      assert(splash:go(args.url))
      assert(splash:wait(2))
      local num_scrolls = 3
      local scroll_delay = 0.2
      local scroll_to = splash:jsfunc("window.scrollTo")
      local get_body_height = splash:jsfunc("function() {return document.body.scrollHeight;}")
        for _ = 1, num_scrolls do
            scroll_to(0, get_body_height())
            splash:wait(scroll_delay)
      end
      return splash:html()
    end
    """

    def create_request(self, item, retries=3):
        yield SplashRequest(item.link, callback=self.parse, errback=self.retry_request, endpoint='execute',
                            dont_filter=True, meta={'item': item, 'retries':retries}, 
                            args={'lua_source': self.script, 'wait': 1},)  

    def retry_request(self, failure):
        retries = failure.request.meta.get('retries')
        item = failure.request.meta.get('item')
        if retries:
            self.logger.info('retry request')
            yield SplashRequest(item.link, callback=self.parse, errback=self.retry_request, endpoint='execute',
                                dont_filter=True, meta={'item': item, 'retries':retries - 1}, 
                                args={'lua_source': self.script, 'wait': 1},)  
        else:
            self.logger.critical('error 404')

    # def parse(self, response):
    #     super()


class SplashDetail(DetailSpider):

    name = "SplashDetail"
    custom_settings = {
        **get_project_settings(),
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
            'crawler.middlewares.ScheduleRequestSpiderMiddleware': 100,
            # 'crawler.middlewares.CustomRetryMiddleware': 120,
            'scrapy.downloadermiddlewares.UserAgentMiddleware': None,
            'crawler.middlewares.CustomUserAgentProxyMiddleware': 400,
            'scrapy_splash.SplashCookiesMiddleware': 723,
            'scrapy_splash.SplashMiddleware': 725,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
        },
        'RETRY_TIMES': 10,
    }
    script = """
    function main(splash, args)
      assert(splash:go(args.url))
      assert(splash:wait(2))
      local num_scrolls = 3
      local scroll_delay = 0.2
      local scroll_to = splash:jsfunc("window.scrollTo")
      local get_body_height = splash:jsfunc("function() {return document.body.scrollHeight;}")
        for _ = 1, num_scrolls do
            scroll_to(0, get_body_height())
            splash:wait(scroll_delay)
      end
      return splash:html()
    end
    """

    # def __init__(self, *a, **kw):
    #     super()

    # def start_requests(self):
    #     super()

    def create_request(self, item, retries=3):
        yield SplashRequest(item.link, callback=self.parse, endpoint='execute',#, errback=self.retry_request
                            dont_filter=True, meta={'item': item, 'retries':retries}, 
                            args={'lua_source': self.script, 'wait': 1},)  

    def retry_request(self, failure):
        retries = failure.request.meta.get('retries')
        item = failure.request.meta.get('item')
        if retries:
            self.logger.info('retry request')
            yield SplashRequest(item.link, callback=self.parse, errback=self.retry_request, endpoint='execute',
                                dont_filter=True, meta={'item': item, 'retries':retries - 1}, 
                                args={'lua_source': self.script, 'wait': 1},)  
        else:
            self.logger.critical('error 404')

    # def parse(self, response):
    #     super()


class SeleniumCat(CatSpider):

    name = "SeleniumCat"
    custom_settings = {
        **get_project_settings(),
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
            'crawler.middlewares.ScheduleRequestSpiderMiddleware': 100,
            'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
            'crawler.middlewares.CustomUserAgentProxyMiddleware': 400,
            'crawler.middlewares.CustomSeleniumMiddleware': 800,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
        },
    }
    params = None

    def create_request(self, item):
        yield SeleniumRequest(url=item.link, callback=self.parse, meta={'item': item})

    def parse(self, response):
        driver = response.meta.get('driver', None)
        if not driver or not item:
            self.logger.error("Cant init ")
            raise CloseSpider("Cant init ")
        
        item = response.meta.get('item', None)
        link_detail = item.link_detail
        law_next_page = item.law_next_page

        if not link_detail or not law_next_page:
            self.logger.error("Link_DETAIl or LAW_NEXT_PAGE is not set")
            raise CloseSpider("Link_DETAIl or LAW_NEXT_PAGE is not set")


        link_detail = data.get('Link_DETAIl')
        law_next_page = data.get('LAW_NEXT_PAGE')

        item = dict(
            id_web=data.get('ID_WEB'),
            # link=data.get('LINK'),
            domain=data.get('DOMAIN'),
            website=data.get('WEBSITE'),
            active=data.get('ACTIVE'),
            post_link=data.get('POST_LINK'),
            lang_web=data.get('LANG_WEB'),
            link_detail=link_detail,
            law_next_page=law_next_page,
        )

        if not law_next_page:
            yield self.parse_item(driver, response, item)
        else:
            driver.scroll_to_bottom()

            try:
                element_next_page = driver.find_element_by_css_selector(law_next_page)
            except InvalidSelectorException:
                element_next_page = None

            while True:
                link = driver.current_url
                item.update(link=link)

                result = self.parse_item(driver, response, item)
                if result['cat_link']:
                    yield result
                else:
                    return None

                if element_next_page:
                    # nextpage by interac with browser
                    next_page_url = element_next_page.get_attribute("href")

                    if next_page_url:
                        driver.get(next_page_url)
                    else:
                        driver.click_element(element_next_page)

                    driver.scroll_to_bottom()
                    try:
                        element_next_page = driver.find_element_by_css_selector(law_next_page)
                    except:
                        return None

                else:
                    # nextpage by rule
                    page_no = re.search(rf'(?<={law_next_page})\d+', link)
                    if page_no:
                        nextpage = int(page_no.group()) + 1
                        abs_next_page_url = re.sub(rf'(?<={law_next_page})\d+', str(nextpage), link)
                        # print(abs_next_page_url)
                        driver.get(abs_next_page_url)
                        driver.scroll_to_bottom()
                    else:
                        return None

    def parse_item(self, driver, response, item):
        selector = Selector(text=driver.page_source)
        cat_link = [response.urljoin(url) for url in selector.css(f"{item['link_detail']}::attr(href)").extract()]
        self.logger.info(f'{item["link"]} - done !')
        return dict(**item, cat_link=cat_link)


class SeleniumDetail(Spider):

    name = "SeleniumDetail"
    custom_settings = {
        **get_project_settings(),
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
            'crawler.middlewares.ScheduleRequestSpiderMiddleware': 100,
            'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
            'crawler.middlewares.CustomUserAgentProxyMiddleware': 400,
            'crawler.middlewares.CustomSeleniumMiddleware': 800,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
        },
    }
    params = None

    def __init__(self, *a, **kw):
        config_logging()
        super().__init__(*a, **kw)
        # self.url must be declared

    def start_requests(self):
        if not getattr(self, 'url', None):
            return None

        if not getattr(self, 'bidDatas', None) or not self.bidDatas:
            self.bidDatas = request_url(self.url, params={'reset': 1})

        if self.bidDatas:
            item = self.bidDatas.pop()
            yield SeleniumRequest(url=item['LINK'], callback=self.parse, meta={'DATA': item, 'scroll_to_bottom': True})

    def parse(self, response):
        driver = response.meta.get('driver', None)
        data = response.meta.get('DATA', None)

        if not driver or not data:
            return None

        driver.implicitly_wait(2)

        item = dict(
            id_web=data.get('ID_WEB'),
            id=data.get('ID'),
            link=data.get('LINK'),
            domain=data.get('DOMAIN'),
            website=data.get('WEBSITE'),
            active=data.get('ACTIVE'),
            post_link=data.get('POST_LINK'),
            lang_web=data.get('LANG_WEB'),
            link_detail=data.get('Link_DETAIl'),
            law_next_page=data.get('LAW_NEXT_PAGE')
        )

        set_law(item, data['ARR_LAW'], Selector(text=driver.page_source))
        self.logger.info(f'{item["link"]} - done !')

        yield item
