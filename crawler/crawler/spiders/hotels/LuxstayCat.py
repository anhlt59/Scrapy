# -*- coding: utf8 -*-
from scrapy.http import JsonRequest
from scrapy.exceptions import CloseSpider
import json
import arrow
import re

from ..common.utils import obj
from ..common.spiders import CatSpider


class LuxstayCat(CatSpider):

    name = "LuxstayCat"
    api_url = 'https://www.luxstay.com/api/search/destination'
    headers = {
        'sec-fetch-mode': 'cors',
        'origin': 'https://www.luxstay.com',
        'accept-language': 'vi',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',
        'content-type': 'application/json;charset=UTF-8',
        'accept': 'application/json, text/plain, */*',
        'cache-control': 'no-cache',
        'authority': 'www.luxstay.com',
        'sec-fetch-site': 'same-origin',
        'content-currency': 'VND',
    }
    body = {'limit': 50, 'page': 1, 'path': '/vietnam/ha-noi'}
    params = '208,207,206'

    def create_request(self, item):
        link = item.link
        url, headers, body = self.api_url, self.headers, self.body.copy()
        # update body
        path = re.search(r'(ha-noi)|(da-nang)|(ho-chi-minh)', link).group()
        body.update(path=f'/vietnam/{path}')
        yield JsonRequest(url=url, method='POST', headers=headers, data=body, callback=self.parse_api,
                           meta={'item': item, 'form_request': [url, headers, body]})

    def parse_api(self, response):
        item = response.meta.get('item')
        url, headers, body = response.meta.get('form_request')

        # stop if data is empty
        data = obj(json.loads(response.body))
        if not data.data:
            self.logger.warning(f'cat link is empty - {item.link}')
            return None

        cat_link = [x["url"] for x in data.data]
        self.count += len(cat_link)
        self.logger.info(f"got {len(cat_link)} cat link - total {self.count}")

        item.cat_link = cat_link
        yield self.post_item(item)

        # nextpage
        body['page'] += 1
        yield JsonRequest(url=url, method='POST', headers=headers, data=body, callback=self.parse_api,
                          meta={'item': item, 'form_request': [url, headers, body]})
