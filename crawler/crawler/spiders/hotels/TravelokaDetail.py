# -*- coding: utf8 -*-
# test pending - nhieu trang loi k tra ve api
from scrapy import Spider
from scrapy.http import Request, JsonRequest
from scrapy.http.cookies import CookieJar
from scrapy.exceptions import CloseSpider
import json
import arrow
import re

from ..common.spiders import DetailSpider
from ..common.utils import obj


class TravelokaDetail(DetailSpider):

    name = "TravelokaDetail"
    api_url = 'https://www.traveloka.com/api/v2/hotel/searchRooms'
    api_headers = {
        'sec-fetch-mode': 'cors',
        'origin': 'https://www.traveloka.com',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'vi-VN,vi;q=0.9,en;q=0.8',
        'cookie': None,  # self.cookie,
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',
        'x-domain': 'accomSearch',
        'x-route-prefix': 'vi-vn',
        'content-type': 'application/json',
        'accept': 'application/json',
        'authority': 'www.traveloka.com',
        'sec-fetch-site': 'same-origin',
    }
    api_body = {'clientInterface': 'desktop',
            'data': {'ccGuaranteeOptions': {'ccGuaranteeRequirementOptions': ['CC_GUARANTEE'],
                                            'ccInfoPreferences': ['CC_TOKEN',
                                                                  'CC_FULL_INFO']},
                     'checkInDate': None,  # {'day': after1day.day, 'month': after1day.month, 'year': after1day.year},
                     'checkOutDate': None,  # {'day': after2day.day, 'month': after2day.month, 'year': after2day.year},
                     'contexts': {'bookingId': None, 'shouldDisplayAllRooms': False},
                     'currency': 'VND',
                     'hasPromoLabel': False,
                     'hotelId': '1000000471104',  # re.search(r'\d+$', data.get('LINK')).group(),  # '1000000471104',
                     'isExtraBedIncluded': True,
                     'isJustLogin': False,
                     'isReschedule': False,
                     'labelContext': {},
                     'numAdults': 2,
                     'numChildren': 0,
                     'numInfants': 0,
                     'numOfNights': 1,
                     'numRooms': 1,
                     'prevSearchId': 'undefined',
                     'preview': False,
                     'rateTypes': ['PAY_NOW', 'PAY_AT_PROPERTY']},
            'fields': []
            }
    params = '215,216,217'
    
    def create_request(self, item):
        if not self.api_headers['cookie']:
            # init cookie once
            yield Request(url='https://www.traveloka.com', callback=self.parse_cookies, meta={'dont_merge_cookies': True})
        else:
            # cookie has been created
            link = item.link
            url, headers, data = self.api_url, self.api_headers, self.api_body.copy()

            # update checkInDate/checkOutDate, hotelId
            now = arrow.now()
            after1day = now.shift(days=1)
            after2day = now.shift(days=2)
            data['data'].update(
                checkInDate={'day': after1day.day, 'month': after1day.month, 'year': after1day.year},
                checkOutDate={'day': after2day.day, 'month': after2day.month, 'year': after2day.year},
                hotelId=re.search(r'\d+$', link).group(),
            )
            yield JsonRequest(url=url, method='POST', headers=headers, data=data,
                              callback=self.parse_api, meta={'dont_merge_cookies': True, 'item': item})

    def parse_cookies(self, response):
        cookieJar = CookieJar()
        cookieJar.extract_cookies(response, response.request)
        self.api_headers['cookie'] = '; '.join([f'{x.name}={x.value}' for x in list(cookieJar.jar)])
        self.logger.info(f'got cookie - done')

    def parse_api(self, response):
        item = response.meta.get('item', None)

        # stop if data is empty
        data = obj(json.loads(response.body))
        if not data.data.recommendedEntries:
            self.logger.error(f'{item.link} - fail')
            return None

        # extract data
        item.hotel_image = set()
        item.hotel_price = []

        for room in data.data.recommendedEntries:
            for r in room.roomList:

                item.hotel_image.update(r.roomImages)
                name = r.inventoryName

                if name not in [x.name for x in item.hotel_price]:
                    price = r.rateDisplay.totalFare.amount
                    guest = r.maxOccupancy
                    attribute = []
                    if r.breakfastIncluded:
                        attribute.append('Bao gồm bữa sáng')
                    if r.roomCancellationPolicy.freeCancel:
                        attribute.append('Miễn phí Đổi/Hủy')
                    item.hotel_price.append(
                        dict(
                            name=name,
                            price=price,
                            attribute=attribute,
                            guest=guest
                        )
                    )

        yield Request(url=item.link, callback=self.parse, meta={'dont_merge_cookies': True, 'item': item})

    def parse(self, response):
        item = response.meta.get('item')

        # detail hotel
        item.hotel_source = 'Traveloka'
        item.hotel_city_id = {'215': 1, '216': 2, '217': 3}[item.id_web]
        item.hotel_name = response.xpath(".//h1/text()").extract_first()
        item.hotel_type = response.xpath(".//span[@class='_1kzbT']/text()").extract_first()
        item.hotel_star = response.xpath('.//div[@itemprop="starRating"]/@content').extract_first()
        item.hotel_address = response.xpath('.//span[@itemprop="streetAddress"]/text()').extract_first()
        item.hotel_image.update(response.xpath('.//div[@class="_39hOG"]//img/@src').extract())
        item.hotel_image = list(item.hotel_image)[:20]

        item.hotel_attribute = response.xpath('.//div[@id="hotelFacility"]//li/text()').extract()
        item.hotel_description = response.xpath('.//div[@class="_2eCs0 _13N_G _1ZMCB _3Q9F4"]//text()').extract()
        
        item.hotel_review = []
        reviews = response.xpath('.//div[@itemprop="review"]')
        for review in reviews:
            name = review.xpath('.//div[@itemprop="author"]//text()').extract_first()
            rating = review.xpath(".//div[@class='css-1dbjc4n r-1awozwy r-18u37iz']/div[2]/text()").extract_first()
            image = review.xpath('.//div[@itemprop="review"]/div[1]//img/@src').extract_first()
            title = review.xpath('.//div[@class="css-901oao r-1ud240a r-1b43r93 r-b88u0q r-1d4mawv r-tsynxw"][last()]/text()').extract_first()
            content = review.xpath('.//div[@itemprop="reviewBody"]/text()').extract_first()

            item.hotel_review.append(
                dict(
                    name=name,
                    rating=rating,
                    title=title,
                    content=content,
                    image=image
                )
            )

        self.count += 1
        self.logger.info(f'item {item["link"]} - done - total {self.count}')
        yield self.post_item(item)
