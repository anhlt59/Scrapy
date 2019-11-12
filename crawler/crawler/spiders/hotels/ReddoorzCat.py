# -*- coding: utf8 -*-
from scrapy.http import JsonRequest
from scrapy.exceptions import CloseSpider
from scrapy.utils.project import get_project_settings
import json
import arrow
import re
import urllib

from ..common.utils import obj
from ..common.http import ApiSeleniumRequest
from ..common.spiders import CatSpider


class ReddoorzCat(CatSpider):

    name = "ReddoorzCat"
    custom_settings = {
        **get_project_settings(),
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
            'crawler.middlewares.ScheduleRequestSpiderMiddleware': 100,
            'scrapy.downloadermiddlewares.UserAgentMiddleware': None,
            'crawler.middlewares.CustomUserAgentProxyMiddleware': 400,
            'crawler.middlewares.CustomSeleniumWireMiddleware': 800,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
        },
    }
    api_url = 'https://search.reddoorz.com/api/v12/hotels/list'
    api_headers = {
        'Sec-Fetch-Mode': 'cors',
        'Referer': 'https://www.reddoorz.com/vi-vn/search/hotel/vietnam/ha-noi',
        'Origin': 'https://www.reddoorz.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',
        'Encoding': 'gzip',
        'Authorization': None,  # 'Bearer 53f4ad9cf0de25a0928f1bcec7928f4debdb0078d48a5a0bd255b6e3a95b8d2f' expires_in: 86400
    }
    api_params = {'app_type': 'web',
                  'check_in_date': '26-10-2019',
                  'check_out_date': '27-10-2019',
                  'country': 'vietnam',
                  'currency': 'VND',
                  'locale': 'vi',
                  'location': 'ha noi',
                  'order_by': 'desc',
                  'page': 1,
                  'per_page': 10,
                  'reddoorz_type': 'all',
                  'rooms': '1',
                  'search_area_slug': 'null',
                  'search_category': 'city',
                  'sort_by': 'popular',
                  }
    params = '209,210,211'

    def create_request(self, item):
        if not self.api_headers['Authorization']:
            # create token
            yield ApiSeleniumRequest(url=item.link, request_urls=['https://www.reddoorz.com/en/oauth/token'],
                                      callback=self.parse_tooken, meta={'item': item})
        else:
            # tooken is created
            link = item.link
            url, headers, params = self.api_url, self.api_headers, self.api_params.copy()

            # modify form request
            now = arrow.now()
            params.update(
                check_in_date=now.shift(days=1).format('DD-MM-YYYY'),
                check_out_date=now.shift(days=2).format('DD-MM-YYYY'),
                location=re.search(r'(?<=vietnam\/)[\w-]+', link).group().replace('-', ' ')
            )
            yield JsonRequest(url=f"{url}?{urllib.parse.urlencode(params)}",
                              method='GET', headers=headers, callback=self.parse_api,
                              meta={'item': item, 'form_request': [url, headers, params]})

    def parse_tooken(self, response):
        try:
            res = obj(json.loads(response.body)[0]['response'])
            if not res and not res.tooken_type and not res.access_token:
                raise Exception()
        except:
            self.logger.critical("Can't get cookie")
            raise CloseSpider("Can't get cookie")  

        self.api_headers['Authorization'] = f"{res.token_type} {res.access_token}"
        # print(self.api_headers['Authorization'])
        for req in self.create_request(response.meta.get('item')):
            yield req

    def parse_api(self, response):
        item = response.meta.get('item')
        url, headers, params = response.meta.get('form_request')

        # stop if data is empty
        data = obj(json.loads(response.body))
        if not data.hotels:
            self.logger.info(f'cat link is empty on page {params["page"]} url {response.url}')
            return None

        cat_link = [f'https://www.reddoorz.com/vi-vn/hotel/vietnam/{x["custom_url"]}/{x["slug"]}?id={x["id"]}' for x in data.hotels]
        self.count += len(cat_link)
        self.logger.info(f"got {len(cat_link)} cat link - total {self.count}")

        item.cat_link = cat_link
        yield self.post_item(item)

        # nextpage
        params['page'] += 1
        yield JsonRequest(url=f"{url}?{urllib.parse.urlencode(params)}",
                          method='GET', headers=headers, callback=self.parse_api,
                          meta={'item': item, 'form_request': [url, headers, params]})
