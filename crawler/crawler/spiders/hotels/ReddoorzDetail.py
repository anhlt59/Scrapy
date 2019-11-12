# -*- coding: utf8 -*-
from scrapy import Spider
from scrapy.http import JsonRequest
from scrapy_selenium import SeleniumRequest
from scrapy.selector import Selector
from scrapy.utils.project import get_project_settings
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import json
import urllib
import requests
import re

from ..common.utils import request_url, set_law, config_logging, obj
from ..common.spiders import DetailSpider
from ..common.http import ApiSeleniumRequest


# TAG_RE = re.compile(r'<[^>]+>')
TAG_RE = re.compile(r'<.*?>')


class ReddoorzDetail(DetailSpider):

    name = "ReddoorzDetail"

    custom_settings = {
        **get_project_settings(),
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
            'crawler.middlewares.ScheduleRequestSpiderMiddleware': 100,
            'scrapy.downloadermiddlewares.UserAgentMiddleware': None,
            'crawler.middlewares.CustomUserAgentProxyMiddleware': 400,
            'crawler.middlewares.CustomSeleniumWireMiddleware': 800,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
        },
    }
    
    hotel_headres = {
        'Sec-Fetch-Mode': 'cors',
        'Referer': 'https://www.reddoorz.com/vi-vn/search/hotel/vietnam/ha-noi',
        'Origin': 'https://www.reddoorz.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',
        # 'Encoding': 'gzip',
        'Authorization': None,  # 'Bearer 53f4ad9cf0de25a0928f1bcec7928f4debdb0078d48a5a0bd255b6e3a95b8d2f' expires_in: 86400
    }
    hotel_url = 'https://search.reddoorz.com/api/v10/hotel/'
    hotel_params = {
        'currency': 'VND',
        'locale': 'vi'
    }

    room_url = 'https://search.reddoorz.com/api/v12/hotel/'
    room_params = {
        'currency': 'VND',
        'locale': 'vi',
        'app_type': 'web',
        'check_in_date': '04-11-2019',
        'check_out_date': '05-11-2019',
        'rooms': '1',
        'reddoorz_type': 'all'
    }

    params = '209,210,211'

    def create_request(self, item):
        if not self.hotel_headres['Authorization']:
            # create token
            yield ApiSeleniumRequest(url=item.link, request_urls=['https://www.reddoorz.com/en/oauth/token'],
                                      callback=self.parse_tooken, meta={'item': item})
        else:
            link = item.link
            hotel_path = link.split('?')[0].split('/')[-1]

            item.hotel_city_id = {'209': 5, '210': 6, '211': 7}[item.id_web]

            params = self.hotel_params
            yield JsonRequest(url=f'{self.hotel_url}{hotel_path}?{urllib.parse.urlencode(params)}', dont_filter=True, method='GET',
                            headers=self.hotel_headres, callback=self.parse_api, meta={'item': item, 'hotel_path': hotel_path})

    def parse_tooken(self, response):
        res = json.loads(response.body)[0]['response']

        if res:
            self.hotel_headres['Authorization'] = f"{res['token_type']} {res['access_token']}"
            # print(self.api_headers['Authorization'])
        else:
            raise CloseSpider("Can't create token")

        for req in self.create_request(response.meta.get('item')):
            yield req
    
    def parse_api(self, response):
        item = response.meta.get('item')
        hotel_path = response.meta.get('hotel_path')

        # stop if data is empty
        data = obj(json.loads(response.body))
        if not data:
            self.logger.error(f'{item.link} - fail')
            return None

        # extract data
        item.hotel_source = 'Reddoorz'
        item.hotel_type = 'Khách sạn'
        item.hotel_name = data.name
        item.hotel_address = "%s, %s, %s, %s" % (data.street1, data.city, data.state, data.country)
        item.hotel_latlng = '%s,%s' % (data.latitude, data.longitude)

        hotel_image = []
        for i in data.gallery_pictures:
            hotel_image.append(i.image)
        item.hotel_image = hotel_image

        # item.hotel_description = TAG_RE.sub('', data.description).replace('\r\n', '').strip()
        item.hotel_description = re.sub(TAG_RE,'', data.description).strip()

        yield JsonRequest(url=f'{self.room_url}/{hotel_path}/check_price_availability?{urllib.parse.urlencode(self.room_params)}', dont_filter=True, method='GET', 
                            headers=self.hotel_headres, callback=self.parse_room, meta={'item': item})

    def parse_room(self, response):
        item = response.meta.get('item')
        hotel_path = response.meta.get('hotel_path')
        data = obj(json.loads(response.body))
        if not data:
            self.logger.error(f'{item.link} - fail')
            return None

        hotel_price = []
        for i in data.room_prices:
            attribute = []
            for i in attribute.split('|'):  
                if i.strip() == 'Thanh toán tại khách sạn':
                    attribute.append('Thanh toán tại nơi ở')
                elif i.strip() == 'Hoàn tiền':
                    attribute.append('Miễn phí Đổi/Huỷ')
            hotel_price.append({
                'name': i.room_name,
                'price': i.total_tarrif,
                'attribute': attribute,
                'guest': 0 #i.room_type_details[1]
            })
        item.hotel_price = hotel_price
        yield self.post_item(item)

# class ReddoorzDetail(Spider):

#     name = "ReddoorzDetail"
#     custom_settings = {
#         **get_project_settings(),
#         'DOWNLOADER_MIDDLEWARES': {
#             'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
#             'crawler.middlewares.ScheduleRequestSpiderMiddleware': 100,
#             'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
#             'crawler.middlewares.CustomUserAgentProxyMiddleware': 400,
#             'crawler.middlewares.CustomSeleniumMiddleware': 800,
#             'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
#         },
#     }
#     params = '209,210,211'
    
#     def __init__(self, *a, **kw):
#         config_logging()
#         super().__init__(*a, **kw)
#         params = getattr(self, 'params', '209,210,211')
#         self.url = f'http://crawler.wemarry.vn/api/get-detail-multi?id={params}'

#     def start_requests(self):
#         if not getattr(self, 'bidDatas', None) or not self.bidDatas:
#             self.bidDatas = request_url(self.url)

#         if self.bidDatas:
#             item = self.bidDatas.pop()
#             yield SeleniumRequest(url=item['LINK'], callback=self.parse, meta={'DATA': item})

#     def parse(self, response):
#         driver = response.meta.get('driver', None)
#         data = response.meta.get('DATA', None)

#         if not driver or not data:
#             return None

#         item = dict(
#             id_web=data.get('ID_WEB'),
#             id=data.get('ID'),
#             link=data.get('LINK'),
#             domain=data.get('DOMAIN'),
#             website=data.get('WEBSITE'),
#             active=data.get('ACTIVE'),
#             post_link=data.get('POST_LINK'),
#             lang_web=data.get('LANG_WEB'),
#             link_detail=data.get('Link_DETAIl'),
#             law_next_page=data.get('LAW_NEXT_PAGE'),
#             detail_city_id=data.get('ARR_LAW')['detail_city_id']['value']
#         )

#         try:
#             WebDriverWait(driver, 6).until(
#                 EC.presence_of_element_located((By.CLASS_NAME, 'room-type'))
#             )
#         except Exception as e:
#             self.logger.error(e)
#             return None

#         driver.scroll_to_bottom()
#         selector = Selector(text=driver.page_source)

#         # tên khach san
#         item['detail_name'] = selector.css('h1.hotel-name::text').extract_first()

#         # dia chi
#         item['detail_address'] = ', '.join(selector.css('h6 span[ng-bind*="HotelDetailData.hotel"]::text').extract())

#         # mô tả
#         item['detail_description'] = selector.css('div.ServicesSec:last-child div').extract_first()

#         # lấy đặc trưng
#         descr_list = selector.xpath(".//div[@class='feature-categories']")
#         item['detail_attribute'] = selector.css('div.hotel-details-services h5::text').extract()

#         # ảnh
#         item['detail_img'] = selector.css(
#             'div[ng-if*="HotelDetailData.hotel.gallery_pictures"] div.popup-gallery a::attr(href)').extract()[0:20]

#         # guest
#         item['detail_guest'] = selector.css('h6[translate="sh_max_adult_hint"]::text').extract_first()

#         # room
#         item['detail_price'] = list()
#         rooms = selector.css("div.room-type")
#         for room in rooms:
#             room_name = room.css('label::text').extract_first()
#             room_price = ''.join(
#                 room.css('div.room-type span[ng-bind-html*="room_price.total_tarrif"] *::text').extract())

#             item['detail_price'].append(
#                 dict(
#                     room_name=room_name,
#                     room_price=room_price
#                 )
#             )

#         self.logger.info(f'{item["link"]} - done !')
#         # from pprint import pprint
#         # pprint(item)
#         yield item
