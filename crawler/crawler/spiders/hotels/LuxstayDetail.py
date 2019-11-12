from scrapy import Spider
from scrapy.http import JsonRequest
from seleniumwire import webdriver
from scrapy_selenium import SeleniumRequest
import requests
import random
import json
import re
from scrapy.utils.project import get_project_settings
from ..common.utils import request_url, set_law, config_logging, obj
from ..common.spiders import DetailSpider

settings = get_project_settings()
# TAG_RE = re.compile(r'<[^>]+>')
TAG_RE = re.compile(r'<.*?>')

class LuxstayDetail(DetailSpider):

    name = "LuxstayDetail"

    hotel_url = 'https://www.luxstay.com/api/rooms'
    hotel_headers = {
        'authority': 'www.luxstay.com',
        'accept-language': 'vi',
        'accept': 'application/json, text/plain, */*',
        'cache-control': 'no-cache',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.70 Safari/537.36',
        'content-currency': 'VND',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        # 'referer': 'https://www.luxstay.com/vi/rooms/32964?checkin=2019-11-29&guests=1',
        # 'accept-encoding': 'gzip, deflate, br',
    }

    # hotel_headers = 
    params = '206,207,208'

    def create_request(self, item):
        link = item.link
        item.hotel_city_id = {'206': 5, '207': 6, '208': 7}[item.id_web]
        hotel_id = link.split('/')[-1]
        yield JsonRequest(url='%s/%s' % (self.hotel_url, hotel_id), dont_filter=True, method='GET',
                           headers=self.hotel_headers, callback=self.parse_api, meta={'item': item})

    def parse_api(self, response):
        item = response.meta.get('item')

        # stop if data is empty
        data = obj(json.loads(response.body).get('data'))
        if not data:
            self.logger.error(f'{item.link} - fail')
            return None

        # extract data
        item.hotel_source = 'Luxstay'
        item.hotel_type = 'Khách sạn'
        item.hotel_name = data.name
        item.hotel_address = data.address.data.address_line_1
        item.hotel_latlng = '%s,%s' % (data.address.data.latitude, data.address.data.longitude)

        hotel_image = []
        for i in data.photoTags.data:
            for j in i.photos.data:
                hotel_image.append(j.photo_url)
        item.hotel_image = hotel_image

        hotel_attribute = []
        for i in data.amenityTypes.data:
            for j in i.amenities.data:
                hotel_attribute.append(j.name)
        item.hotel_attribute = hotel_attribute

        # item.hotel_description = TAG_RE.sub('\n', data.introduction)
        item.hotel_description = re.sub(TAG_RE,'', data.introduction).strip()
        
        item.hotel_price = [{
            'attribute': [],
            'guest': data.maximum_guests,
            'name': data.roomType.data.description,
            'price': data.price.data.nightly_price_vnd
        }]
        yield self.post_item(item)

#         # Review hotel
#         url, headers, data = self.review_url, self.review_headers, self.review_data.copy()
#         # update hotelid
#         data.update(
#             hotelId=re.search(r'(?<=hotelid=)\d+', item.link).group(),
#         )
#         yield JsonRequest(url=url, dont_filter=True, method='POST',
#                           headers=headers, data=data,
#                           callback=self.parse_review, meta={'item': item})

#     def parse_review(self, response):
#         item = response.meta.get('item')

#         # stop if data is empty
#         data = obj(json.loads(response.body))
#         if not data.commentList:
#             self.logger.error(f'{item.link} - fail')
#             return None

#         item.hotel_review = [dict(
#             name=review.reviewerInfo.displayMemberName,
#             rating=int(float(review.rating)/2),
#             title=review.reviewTitle,
#             content=review.reviewComments,
#             image=None
#         ) for review in data.commentList.comments]

#         self.count += 1
#         self.logger.info(f"crawl {item.hotel_name} done - total {self.count}")
#         # from pprint import pprint
#         # pprint(item)
#         yield self.post_item(item)

# class LuxstayDetail(Spider):

#     name = "LuxstayDetail"
#     custom_settings = {
#         **settings,
#         'DOWNLOADER_MIDDLEWARES': {
#             'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
#             'crawler.middlewares.ScheduleRequestSpiderMiddleware': 100,
#             'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
#             'crawler.middlewares.CustomUserAgentProxyMiddleware': 400,
#             'crawler.middlewares.CustomSeleniumMiddleware': 800,
#             'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
#         },
#     }
#     params = '208,207,206'
    
#     def __init__(self, *a, **kw):
#         config_logging()
#         super().__init__(*a, **kw)

#         params = getattr(self, 'params', '208,207,206')
#         self.url = f'http://crawler.wemarry.vn/api/get-detail-multi?id={params}'

#     def start_requests(self):
#         if not getattr(self, 'bidDatas', None):
#             self.bidDatas = request_url(self.url)

#         if self.bidDatas:
#             item = self.bidDatas.pop()
#             yield SeleniumRequest(url=item['LINK'], callback=self.parse,
#                                   meta={'request_urls': ['https://www.luxstay.com/api/rooms'],
#                                         'get_response': True, 'DATA': item})

#     def parse(self, response):
#         data = response.meta.get('DATA', None)
#         request_form = response.meta.get('request_form', None)

#         if not request_form or not data:
#             return None

#         item = dict(
#             id=data.get('ID'),
#             id_web=data.get('ID_WEB'),
#             link=data.get('LINK'),
#             domain=data.get('DOMAIN'),
#             website=data.get('WEBSITE'),
#             active=data.get('ACTIVE'),
#             post_link=data.get('POST_LINK'),
#             lang_web=data.get('LANG_WEB'),
#             detail_city_id=data.get('ARR_LAW')['detail_city_id']['value']
#         )

#         res = request_form[0]['response']

#         # Check data is empty
#         if not res or not res['data']:
#             return None

#         # name
#         item['detail_name'] = res['data']['name']

#         # address
#         item['detail_address'] = res['data']['address']['data']['full_address']
#         item['detail_latitude'] = res['data']['address']['data']['latitude']
#         item['detail_longitude'] = res['data']['address']['data']['longitude']

#         # image
#         item['detail_image'] = [x['photo_url'] for x in res['data']['photos']['data']][:20]

#         # price
#         item['detail_price'] = res['data']['price']['data']['nightly_price_formatted']

#         # description
#         item['detail_description'] = res['data']['introduction']

#         # type
#         item['detail_type'] = res['data']['propertyType']['data']['name']

#         # room type
#         item['detail_room_type'] = res['data']['roomType']['data']['name']

#         # attribute
#         item['detail_attribute'] = [x['name'] for x in res['data']['amenities']['data']]

#         # guest
#         item['detail_guest'] = res['data']['maximum_guests']

#         self.logger.info(f'{item["link"]} - done !')
#         yield item
