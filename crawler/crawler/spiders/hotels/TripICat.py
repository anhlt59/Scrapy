# -*- coding: utf8 -*-
from scrapy.http import JsonRequest
from scrapy.exceptions import CloseSpider
import json
import arrow
import re

from ..common.utils import obj
from ..common.spiders import CatSpider


class TripiCat(CatSpider):

    name = "TripiCat"
    api_headers = {
        'Sec-Fetch-Mode': 'cors',
        'Origin': 'https://www.tripi.vn',
        'Content-Type': 'application/json;charset=UTF-8',
        'Accept': 'application/json, text/plain, */*',
        'deviceInfo': 'WebDesktop',
    }
    api_body = {
        'filters': {'priceMax': 1000000000,
                    'priceMin': 0,
                    'ratings': [],
                    'relaxes': [],
                    'services': [],
                    'stars': [],
                    'subLocationIds': [],
                    'types': []},
        'pageOffset': 1,
        'rooms': 1,
        'size': 100,
        'slug': 'ha-noi-s0-d0-p11',
        'sortBy': 'default'
    }
    api_url = 'https://hotelapi.tripi.vn/v3/hotels/searchBySlug'
    params = '212,213,214'

    def create_request(self, item):
        link = item.link
        url, headers, body = self.api_url, self.api_headers, self.api_body.copy()

        body.update(slug=re.search(r'[\w-]+(?=\.html)', link).group())
        yield JsonRequest(url=url, method='POST', headers=headers, data=body, callback=self.parse_api,
                           meta={'item': item, 'form_request': [url, headers, body]})

    def parse_api(self, response):
        item = response.meta.get('item')
        url, headers, body = response.meta.get('form_request')

        # stop if data is empty
        data = obj(json.loads(response.body))
        if not data.data.hotels:
            self.logger.info(f"cat link is empty on pageOffset {body['pageOffset']} url {response.url}")
            return None

        cat_link = [f"https://www.tripi.vn/hotels/{x.slug}.html" for x in data.data.hotels]
        self.count += len(cat_link)
        self.logger.info(f"got {len(cat_link)} cat link - total {self.count}")

        # yield item
        item.cat_link = cat_link
        yield self.post_item(item)

        # nextpage
        body['pageOffset'] += 1
        yield JsonRequest(url=url, method='POST', headers=headers, body=json.dumps(body), callback=self.parse_api,
                          meta={'item': item, 'form_request': [url, headers, body]})
