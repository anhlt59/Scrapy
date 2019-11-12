# -*- coding: utf8 -*-
from scrapy.http import JsonRequest
from scrapy.exceptions import CloseSpider
import urllib
import json

from ..common.spiders import CatSpider
from ..common.utils import obj


class CookyCat(CatSpider):

    name = "CookyCat"
    params = '169'
    api_headers = {
        'Connection': 'keep-alive',
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.87 Safari/537.36',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'cors',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'vi-VN,vi;q=0.9,en;q=0.8',
    }
    api_params = {'append': 'true',
         'cm': '',
         'crs': '',
         'cs': '',
         'dt': '',
         'igt': '',
         'lv': '',
         'oc': '',
         'p': '',
         'page': 1,
         'pageSize': '12',
         'q': 'null',
         'st': '2',
         'video': 'false'
         }
    api_url = 'https://www.cooky.vn/directory/search'

    def create_request(self, item):
        url, headers, params = self.api_url, self.api_headers, self.api_params.copy()
        yield JsonRequest(url=f"{url}?{urllib.parse.urlencode(params)}",
                          method='GET', headers=headers, callback=self.parse,
                          meta={'item': item, 'form_request': [url, headers, params]})

    def parse(self, response):
        item = response.meta.get('item')
        url, headers, params = response.meta.get('form_request')
        
        data = obj(json.loads(response.body))
        # stop if data is empty
        if not data.recipes:
            self.logger.info(f'cat link is empty on page {params["page"]} url {response.url}')
            return None

        # extract cat link
        cat_link = [f'https://www.cooky.vn{x.DetailUrl}' for x in data.recipes]

        self.count += len(cat_link)
        self.logger.info(f"got {len(cat_link)} cat link - total {self.count}")
        item.cat_link = cat_link
        yield self.post_item(item)

        # nextpage
        params['page'] += 1
        yield JsonRequest(url=f"{url}?{urllib.parse.urlencode(params)}",
                          method='GET', headers=headers, callback=self.parse,
                          meta={'item': item, 'form_request': [url, headers, params]})