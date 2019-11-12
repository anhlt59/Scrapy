# -*- coding: utf8 -*-
from scrapy.http import JsonRequest
from scrapy.exceptions import CloseSpider
import json
import urllib

from ..common.utils import obj
from ..common.spiders import CatSpider


class IvivuCat(CatSpider):

    name = "IvivuCat"
    api_headers = {
        'sec-fetch-mode': 'cors',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'vi-VN,vi;q=0.9,en;q=0.8',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36',
        'accept': 'application/json, text/plain, */*',
        'authority': 'www.ivivu.com',
    }
    api_params = {
        'regionId': '114185',
        'page': 1,
        'pageSize': '100',
    }
    api_url = 'https://www.ivivu.com/hotelslist'
    params = '203,204,205'

    def create_request(self, item):
        link = item.link
        url, headers, params = self.api_url, self.api_headers, self.api_params.copy()

        if 'ha-noi' in link:
            params.update(regionId=114185)
        elif 'da-nang' in link:
            params.update(regionId=114182)
        elif 'ho-chi-minh' in link:
            params.update(regionId=114187)

        yield JsonRequest(url=f"{url}?{urllib.parse.urlencode(params)}",
                           headers=headers, callback=self.parse_api,
                           meta={'item': item, 'form_request': [url, headers, params]})

    def parse_api(self, response):
        item = response.meta.get('item')
        url, headers, params = response.meta.get('form_request')

        # stop if data is empty
        data = obj(json.loads(response.body))

        if not data.List:
            self.logger.info(f'cat link is empty on page {params["page"]} url {response.url}')
            return None

        cat_link = [f'https://www.ivivu.com{x.HotelLink}?id={x.HotelId}' for x in data.List]
        self.count += len(cat_link)
        self.logger.info(f"got {len(cat_link)} cat link - total {self.count}")

        item.cat_link = cat_link
        yield self.post_item(item)

        # nextpage
        params['page'] += 1
        yield JsonRequest(url=f"{url}?{urllib.parse.urlencode(params)}",
                          headers=headers, callback=self.parse_api,
                          meta={'item': item, 'form_request': [url, headers, params]})
