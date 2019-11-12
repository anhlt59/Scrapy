# -*- coding: utf8 -*-
from scrapy.http import Request, JsonRequest
from scrapy.http.cookies import CookieJar
from scrapy.utils.project import get_project_settings
from scrapy.exceptions import CloseSpider
import json
import arrow
import re

from ..common.utils import obj
from ..common.spiders import CatSpider


class TravelokaCat(CatSpider):

    name = "TravelokaCat"
    custom_settings = {
        **get_project_settings(),
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
            'crawler.middlewares.ScheduleRequestSpiderMiddleware': 100,
            'scrapy.downloadermiddlewares.UserAgentMiddleware': None,
            'crawler.middlewares.CustomUserAgentProxyMiddleware': 400,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
        }
    }
    api_url = 'https://www.traveloka.com/api/v2/hotel/search'
    api_headers = {
        'sec-fetch-mode': 'cors',
        'origin': 'https://www.traveloka.com',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'vi-VN,vi;q=0.9,en;q=0.8',
        'cookie': None,  # self.cookie,
        'user-agent': None,
        'x-domain': 'accomSearch',
        'x-route-prefix': 'vi-vn',
        'content-type': 'application/json',
        'accept': 'application/json',
        'authority': 'www.traveloka.com',
        'sec-fetch-site': 'same-origin',
    }
    api_body = {'clientInterface': 'desktop',
            'data': {'backdate': False,
                     'basicFilterSortSpec': {'accommodationTypeFilter': [],
                                             'ascending': False,
                                             'basicSortType': 'POPULARITY',
                                             'facilityFilter': [],
                                             'maxPriceFilter': None,
                                             'minPriceFilter': None,
                                             'quickFilterId': None,
                                             'skip': 0,
                                             'starRatingFilter': [True,
                                                                  True,
                                                                  True,
                                                                  True,
                                                                  True],
                                             'top': 100},
                     'boundaries': None,
                     'ccGuaranteeOptions': {'ccGuaranteeRequirementOptions': ['CC_GUARANTEE'],
                                            'ccInfoPreferences': ['CC_TOKEN',
                                                                  'CC_FULL_INFO']},
                     'checkInDate': None,  # {'day': after1day.day, 'month': after1day.month, 'year': after1day.year},
                     'checkOutDate': None,  # {'day': after2day.day, 'month': after2day.month, 'year': after2day.year},
                     'contexts': {'isFamilyCheckbox': False},
                     'criteriaFilterSortSpec': None,
                     'currency': 'VND',
                     'geoId': None,  # re.search(r'(?<=HOTEL_GEO\.)\d+', link).group(),  # '10009843',
                     'geoLocation': None,
                     'isExtraBedIncluded': True,
                     'isJustLogin': False,
                     'numAdults': 2,
                     'numChildren': 0,
                     'numInfants': 0,
                     'numOfNights': 1,
                     'numRooms': 1,
                     'rateTypes': ['PAY_NOW', 'PAY_AT_PROPERTY'],
                     'showHidden': False,
                     'sourceType': 'HOTEL_GEO',
                     'uniqueSearchId': None},
            'fields': []
            }
    params = '215,216,217'

    def create_request(self, item):
        if not self.api_headers['cookie']:
            # create cookie
            yield Request(url='https://www.traveloka.com', callback=self.parse_cookie,
                           meta={'dont_merge_cookies': True, 'item': item})
        else:
            # cookie is created
            link = item.link
            url, headers, body = self.api_url, self.api_headers, self.api_body

            # update checkInDate/checkOutDate, geoId
            now = arrow.now()
            after1day = now.shift(days=1)
            after2day = now.shift(days=2)
            body['data'].update(
                checkInDate={'day': after1day.day, 'month': after1day.month, 'year': after1day.year},
                checkOutDate={'day': after2day.day, 'month': after2day.month, 'year': after2day.year},
                geoId=re.search(r'(?<=HOTEL_GEO\.)\d+', link).group(),  # '10009843',
            )
            yield JsonRequest(url=url, method='POST', headers=headers, data=body, callback=self.parse_api,
                              meta={'dont_merge_cookies': True, 'item': item, 'form_request': [url, headers, body]})

    def parse_cookie(self, response):
        cookieJar = CookieJar()
        cookieJar.extract_cookies(response, response.request)
        cookie = '; '.join([f'{x.name}={x.value}' for x in list(cookieJar.jar)])
        if cookie:
            # add cookie to header
            self.api_headers.update(cookie=cookie)
            self.logger.info(f'got cookie - done')
        else:
            raise CloseSpider("Can't create cookie")

        for req in self.create_request(response.meta.get('item')):
            yield req

    def parse_api(self, response):
        item = response.meta.get('item', None)
        url, headers, body = response.meta.get('form_request')

        # stop if data is empty
        data = obj(json.loads(response.body))
        if not data.data.entries:
            self.logger.info(f"cat link is empty on skip {body['data']['basicFilterSortSpec']['skip']} url {response.url}")
            return None

        cat_link = [f"https://www.traveloka.com/vi-vn/{x.hotelSeoUrl}" for x in data.data.entries]
        self.count += len(cat_link)
        self.logger.info(f"got {len(cat_link)} cat link - total {self.count}")

        item.cat_link = cat_link
        yield self.post_item(item)

        # nextpage
        body['data']['basicFilterSortSpec']['skip'] += 100
        yield JsonRequest(url=url, method='POST', headers=headers, data=body, callback=self.parse_api,
                          meta={'dont_merge_cookies': True, 'item': item, 'form_request': [url, headers, body]})
