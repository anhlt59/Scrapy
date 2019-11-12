# -*- coding: utf8 -*-
from scrapy import Spider
from scrapy_selenium import SeleniumRequest
from scrapy.selector import Selector
from scrapy.utils.project import get_project_settings
from ..common.utils import request_url, config_logging


class ExpediaCat(Spider):

    name = "ExpediaCat"
    custom_settings = {
        **get_project_settings(),
        'SELENIUM_DRIVER_ARGUMENTS': ['--no-sandbox'],
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
            'crawler.middlewares.ScheduleRequestSpiderMiddleware': 100,
            'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
            'crawler.middlewares.CustomUserAgentProxyMiddleware': 400,
            'crawler.middlewares.CustomSeleniumMiddleware': 800,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
        },
    }
    params = '184,185,186'
    
    def __init__(self, *a, **kw):
        config_logging()
        super().__init__(*a, **kw)
        print(f'{self.name } - !!!!!!!!!!!!!!!!')
        self.url = "{url}&count=100&startingIndex={index}"
        self.index = 0

        params = getattr(self, 'params', '184,185,186')
        url = f'http://crawler.wemarry.vn/api/get-cat-multi?id={params}'
        self.bidDatas = request_url(url, params={'reset': 1})

        
    def start_requests(self):
        if self.bidDatas:
            item = self.bidDatas.pop()
            url = self.url.format(url=item["LINK"], index=0)
            yield SeleniumRequest(url=url, callback=self.parse, meta={'DATA': item, 'scroll_to_bottom': True})

    def parse(self, response):
        driver = response.meta.get('driver', None)
        data = response.meta.get('DATA', None)

        if not driver or not data:
            return None

        link_detail = data.get('Link_DETAIl')
        law_next_page = data.get('LAW_NEXT_PAGE')

        item = dict(
            id_web=data.get('ID_WEB'),
            link=data.get('LINK'),
            domain=data.get('DOMAIN'),
            website=data.get('WEBSITE'),
            active=data.get('ACTIVE'),
            post_link=data.get('POST_LINK'),
            lang_web=data.get('LANG_WEB'),
            link_detail=link_detail,
            law_next_page=law_next_page,
        )

        selector = Selector(text=driver.page_source)
        cat_link = [response.urljoin(url) for url in selector.css(f"{item['link_detail']}::attr(href)").extract()]
        if cat_link:
            yield dict(**item, cat_link=cat_link)
            self.logger.info(f'{item["link"]} - done !')
            
            self.index += 50
            url = self.url.format(url=data["LINK"], index=self.index)
            yield SeleniumRequest(url=url, callback=self.parse, meta={'DATA': data, 'scroll_to_bottom': True})
        else:
            return None
