# -*- coding: utf8 -*-
from scrapy.http import JsonRequest
from scrapy.exceptions import CloseSpider
import json
import arrow
import re
import base64

from ..common.utils import obj
from ..common.spiders import CatSpider


class MytourCat(CatSpider):

    name = "MytourCat"
    params = '117,190,191'
    api_url = 'https://mytour.vn/graphql'
    api_headers = {
        'sec-fetch-mode': 'cors',
        'origin': 'https://mytour.vn',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'vi-VN,vi;q=0.9,en;q=0.8',
        'x-requested-with': 'XMLHttpRequest',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',
        'content-type': 'application/json',
        'accept': '*/*',
        'authority': 'mytour.vn',
        'sec-fetch-site': 'same-origin',
    }
    api_body = '{"query": "{ filterHotel( locationType: city locationId: 2 checkin: '\
        '\\"2019-10-27\\" checkout: \\"2019-10-28\\" offset: 0 limit: 100  numRoom: 1 '\
        'userId: 0 bkOffline: 0){ totalHotel hotels {id name address descListing area '\
        '{id name} conveniences { name class } price { subPrice mainPrice messageCode '\
        'hiddenPrice percentDeal stopSale promoId requiredHiddenPrice '\
        'bannerAllotmentSeason numAllotmentSeason { day quantity } '\
        'discountAllotmentSeason { day percent } dayMainPrice { day price } '\
        'priceBannerMarketing{ discount code symbol typeVoucher mainPriceDiscount } '\
        'discountDirect {id percent price} percentDiscount directDiscountShow} '\
        'starRating avatar tripAdvisor {id numberOfReviews ratingImageUrl} avgRates '\
        '{id hotelId type avgScore totalRate detailScore focusComment } bookingNotify '\
        'notReach areaId score allotmentMessage taxFee lat lng tripAdId has360pic '\
        '}}}"}'

    def create_request(self, item):
        link = item.link
        url, headers, body = self.api_url, self.api_headers, self.api_body

        # update location
        locationId = re.search(r'(?<=vn\/c)\d+', link).group()  # ha-noi 2, da nang 65, ho chi minh 3
        body = re.sub(r'(?<=locationId:\s)\d+', locationId, body)
        # update checkin/checkout date
        now = arrow.now()
        body = re.sub(r'(?<=checkin:\s\\")[^"\\]+', now.shift(days=1).format('YYYY-MM-DD'), body)
        body = re.sub(r'(?<=checkout:\s\\")[^"\\]+', now.shift(days=2).format('YYYY-MM-DD'), body)
        yield JsonRequest(url=url, method='POST', headers=headers, body=body, callback=self.parse_api,
                           meta={'item': item, 'form_request': [url, headers, body]})

    def parse_api(self, response):
        item = response.meta.get('item')
        url, headers, body = response.meta.get('form_request')
        offset = re.search(r'(?<=offset:\s)\d+', body).group()

        # stop if data is empty
        data = obj(json.loads(response.body))
        if not data.data.filterHotel.hotels:
            self.logger.info(f'cat link is empty on offset {offset} - {response.url}')
            return None

        cat_link = [f'https://mytour.vn/{x["id"]}-{x["name"]}.html' for x in data.data.filterHotel.hotels]
        self.count += len(cat_link)
        self.logger.info(f"got {len(cat_link)} cat link - total {self.count}")

        item.cat_link = cat_link
        yield self.post_item(item)

        # nextpage
        next_offset = int(offset) + 100
        body = re.sub(r'(?<=offset:\s)\d+', str(next_offset), body)
        yield JsonRequest(url=url, method='POST', headers=headers, body=body, callback=self.parse_api,
                          meta={'item': item, 'form_request': [url, headers, body]})
