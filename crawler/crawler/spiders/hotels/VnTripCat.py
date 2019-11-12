# -*- coding: utf8 -*-
from scrapy.http import JsonRequest
from scrapy.exceptions import CloseSpider
import json
import arrow
import re
import urllib

from ..common.utils import obj
from ..common.spiders import CatSpider


class VnTripCat(CatSpider):

    name = "VnTripCat"
    api_headers = {
        'Sec-Fetch-Mode': 'cors',
        'Access-Control-Request-Method': 'GET',
        'Origin': 'https://www.vntrip.vn',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',
        'Access-Control-Request-Headers': 'authorization,customeripaddress,customersessionid,customeruseragent,x-requested-with',
    }
    api_params = {
        'check_in_date': None,  # datetime.now().format("YYYYMMDD"),  # '20191021',
        'nights': 1,
        'page': 1,
        'page_size': 100,
        'request_source': 'web_frontend',
        'seo_code': None,  # re.search(r'(ha-noi)|(da-nang)|(sai-gon-ho-chi-minh)', link).group()
    }
    api_url = 'https://micro-services.vntrip.vn/search-engine/search/vntrip-hotel-availability/'
    params = '194,195,196'

    def create_request(self, item):
        link = item.link
        url, headers, params = self.api_url, self.api_headers, self.api_params.copy()

        # update body
        now = arrow.now()
        params.update(
            check_in_date=now.shift(days=1).format('YYYYMMDD'),
            seo_code=re.search(r'(ha-noi)|(da-nang)|(sai-gon-ho-chi-minh)', link).group(),
        )
        yield JsonRequest(f'{url}?{urllib.parse.urlencode(params)}', headers=headers, callback=self.parse,
                           meta={'item': item, 'form_request': [url, headers, params]})

    def parse(self, response):
        item = response.meta.get('item')
        url, headers, params = response.meta.get('form_request')

        # stop if data is empty
        data = obj(json.loads(response.body))
        if not data.data:
            self.logger.info(f"cat link is empty on page {params['page']} url {response.url}")
            return None

        re_pattern = re.compile(r'[^\w]+')
        cat_link = [f"https://www.vntrip.vn/khach-san/{re.sub(re_pattern, '-', x.name)}-{x.vntrip_id}" for x in data.data]
        self.count += len(cat_link)
        self.logger.info(f"got {len(cat_link)} cat link - total {self.count}")

        item.cat_link = cat_link
        yield self.post_item(item)

        # nextpage
        params['page'] += 1
        yield JsonRequest(f'{url}?{urllib.parse.urlencode(params)}', headers=headers, callback=self.parse,
                          meta={'item': item, 'form_request': [url, headers, params]})
