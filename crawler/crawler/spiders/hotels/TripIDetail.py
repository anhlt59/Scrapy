# -*- coding: utf8 -*-
from scrapy.http import JsonRequest
from scrapy.exceptions import CloseSpider
import json
import arrow
import re

from ..common.utils import obj
from ..common.spiders import DetailSpider


class TripiDetail(DetailSpider):

    name = "TripiDetail"
    params = '212,213,214'
    headers = {
        'Sec-Fetch-Mode': 'cors',
        'Origin': 'https://www.tripi.vn',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',
        'Content-Type': 'application/json;charset=UTF-8',
        'Accept': 'application/json, text/plain, */*',
        'deviceInfo': 'WebDesktop',
    }
    detail_data = {
        "slug": None,
        "checkIn": None,  # today,
        "checkOut": None,  # tomorrow
    }
    detail_url = 'https://hotelapi.tripi.vn/v3/hotels/detailsBySlug'
    price_data = {
        "hotelId": None,
        "checkIn": None,  # today,
        "checkOut": None,  # tomorrow
    }
    price_url = 'https://hotelapi.tripi.vn/v3/hotels/pricesGroupByAgency'

    def create_request(self, item):
        link = item.link

        # get checkin/checkout time
        now = arrow.now()
        today = now.format('DD-MM-YYYY')
        tomorrow = now.shift(days=1).format('DD-MM-YYYY')
        self.detail_data.update(
            slug=re.search(r'(?<=\/)[^\/]+(?=\.html)', link).group(),
            checkIn=today,
            checkOut=tomorrow
        )
        self.price_data.update(
            hotelId=re.search(r'\d+(?=\.html)', link).group(),
            checkIn=today,
            checkOut=tomorrow
        )
        yield JsonRequest(self.detail_url, method='POST', data=self.detail_data, headers=self.headers,
                          meta={'item': item}, callback=self.parse_detail)

    def parse_detail(self, response):
        item = response.meta.get('item')

        data = obj(json.loads(response.body))
        # Check data is empty
        if not data.data:
            self.logger.error(f'{link} data is empty')
            return None

        item.hotel_source = 'TripI'
        item.hotel_city_id = {'212': 5, '213': 6, '214': 7}[item.id_web]
        item.hotel_type = 'Khách sạn'
        item.hotel_name = data.data.name
        item.hotel_address = data.data.address
        item.hotel_description = data.data.desc
        item.hotel_star = data.data.starNumber

        item.hotel_attribute = []
        for attr in data.data.features.values():
            if attr and type(attr[0]) is str:
                item.hotel_attribute.extend(attr)

        item.hotel_image = [x.src for x in data.data.images][0:20]
        item.hotel_latlng = f'{data.data.latitude},{data.data.longitude}'

        # hotel_price
        yield JsonRequest(self.price_url, method='POST', data=self.price_data, headers=self.headers,
                          meta={'item': item}, callback=self.parse_price)

    def parse_price(self, response):
        item = response.meta.get('item')
        link = item.link

        data = obj(json.loads(response.body))
        # Check data is empty
        if not data.data:
            self.logger.error(f'{link} data is empty')
            return None

        item.hotel_price = []
        for rooms in data.data:
            for r in rooms.prices:
                attribute = ['Bao gồm bữa sáng'] if r['freeBreakfast'] else []
                if r.cancellationPoliciesList:
                    attribute.append('Miễn phí Đổi/Hủy')
                price = r.finalPrice
                name = r.roomTitle
                guest = r.maxGuests

                item.hotel_price.append(
                    {
                        'name': name,
                        'price': price,
                        'attribute': attribute,
                        'guest': guest
                    }
                )

        self.count += 1
        self.logger.info(f"crawl {item.link} done - total {self.count}")
        yield self.post_item(item)
