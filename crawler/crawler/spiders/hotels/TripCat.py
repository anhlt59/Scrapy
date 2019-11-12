# -*- coding: utf8 -*-
from scrapy.http import JsonRequest
from scrapy.exceptions import CloseSpider
import json
import arrow
import re
import urllib

from ..common.utils import obj
from ..common.spiders import CatSpider


class TripCat(CatSpider):

    name = "TripCat"
    api_url = 'https://vn.trip.com/hotels/List/Hote1JsonResult'
    api_headers = {
        'sec-fetch-mode': 'cors',
        'origin': 'https://vn.trip.com',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'vi-VN,vi;q=0.9,en;q=0.8',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',
        'content-type': 'application/json',
        'accept': '*/*',
        'cache-control': 'max-age=0',
        'authority': 'vn.trip.com',
        'sec-fetch-site': 'same-origin',
    }
    api_body = {
        'FGTaxFee': '',
        'adult': '2',
        'ages': '',
        'allianceid': '',
        'checkin': '2019-10-30',
        'checkout': '2019-10-31',
        'children': '0',
        'city': '286',
        'curr': 'VND',
        'filterHotels': '',
        'hotelid': '',
        'pageno': 1,
        'showtotalamt': '0',
        'sid': ''
    }
    api_params = {
        'pageName': 'list',
        'a': 'a',
        'isScrolling': 'false',
        'seqid': ''
    }
    params = '197,198,199'

    def create_request(self, item):
        link = item.link

        url, headers, params, body = self.api_url, self.api_headers, self.api_params, self.api_body.copy()
        now = arrow.now()
        body.update(
            checkin=now.shift(days=1).format('YYYY-MM-DD'),
            checkout=now.shift(days=2).format('YYYY-MM-DD'),
            city=re.search(r'(?<=city=)\d+', link).group(),  # ha noi 2758 da nang 16440 ho chi minh 13170
        )
        yield JsonRequest(url=f"{url}?{urllib.parse.urlencode(params)}",
                           method='POST', headers=headers, data=body, callback=self.parse_api,
                           meta={'item': item, 'form_request': [url, headers, params, body]})

    def parse_api(self, response):
        item = response.meta.get('item')
        url, headers, params, body = response.meta.get('form_request')

        # stop if data is empty
        data = obj(json.loads(response.body))

        if not data.HotelResultModel:
            self.logger.info(f"cat link is empty on page {body['pageno']} url {response.url}")
            return None

        cat_link = [f"https://{x.hotelUrl.strip('/')}?latlng={x.lat},{x.lng}" for x in data.HotelResultModel]
        self.count += len(cat_link)
        self.logger.info(f"got {len(cat_link)} cat link - total {self.count}")

        item.cat_link = cat_link
        yield self.post_item(item)

        # nextpage
        body['pageno'] += 1
        yield JsonRequest(url=f"{url}?{urllib.parse.urlencode(params)}",
                          method='POST', headers=headers, data=body, callback=self.parse_api,
                          meta={'item': item, 'form_request': [url, headers, params, body]})
