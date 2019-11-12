# -*- coding: utf8 -*-
from scrapy.utils.project import get_project_settings

from ..common.spiders import SeleniumDetail


class ExpediaDetail(SeleniumDetail):

    name = "ExpediaDetail"
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
        super().__init__(*a, **kw)
        print(f'{self.name } - !!!!!!!!!!!!!!!!')
        params = getattr(self, 'params', '184,185,186')
        self.url = f'http://crawler.wemarry.vn/api/get-detail-multi?id={params}'
