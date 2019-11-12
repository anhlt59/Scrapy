# -*- coding: utf8 -*-
from scrapy import Spider
from scrapy.http import JsonRequest
from scrapy.utils.project import get_project_settings
from scrapy.exceptions import CloseSpider
from scrapy.http import Request
from scrapy.selector import Selector
import json
import arrow
import re
import base64

from ..common.http import ApiSplashRequest
from ..common.utils import config_logging
from ..common.spiders import DetailSpider

TAG_RE = re.compile(r'<[^>]+>')

class MytourDetail(DetailSpider):

    name = "MytourDetail"

    hotel_url = 'https://mytour.vn/hotel/get-price-detail-page'

    hotel_headers = {
        'authority': 'mytour.vn',
        'accept': '*/*',
        'origin': 'https://mytour.vn',
        # 'x-csrf-token': 'Jn4aqEhcEYeL42HTfNrF0cFGQTaolM6QYELnm4OE',
        'x-requested-with': 'XMLHttpRequest',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.70 Safari/537.36',
        'content-type': 'application/json; charset=UTF-8',
        # 'sec-fetch-site': 'same-origin',
        # 'sec-fetch-mode': 'cors',
        # 'referer': 'https://mytour.vn/16068-khach-san-cali-night-da-nang.html',
        # 'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
        # 'cookie': 'PHPSESSID=47fd193c866acaa5c08486dc1902c0dd; _gcl_au=1.1.561357489.1569463274; r_ad_token1=4iz21E005AwJ41X0VD7t; r_ad_token2=4iz21E005AwJ41X0VD7t; cto_lwid=9b78e0a1-8543-40f0-87b2-b97957160133; _hjid=fb04bc1a-ebe7-4dd6-84b0-faaaa794392c; _hjIncludedInSample=1; _ga=GA1.2.1817656743.1569463275; insLastVisitedCityUrl=https%3A%2F%2Fmytour.vn%2Fc3%2Fkhach-san-tai-ho-chi-minh.html; insLastVisitedListingCheckinDate=27%2F09%2F2019; insLastVisitedListingCity=H%E1%BB%93%20Ch%C3%AD%20Minh; scs=1; OLD-TOKEN=+; notification_config=+; time_checkin=1572886800; time_checkout=1572973200; night_booking=1; _cdhp=16068; _ccdhp=65; last_city=65; hotel_seen=%7B%2211038%22%3A%2211038%22%2C%22898%22%3A%22898%22%2C%2216068%22%3A%2216068%22%7D; AMP_TOKEN=%24NOT_FOUND; _gid=GA1.2.472509946.1572832920; _gat=1; _fbp=fb.1.1572832920123.792708340; ins-gaSSId=a81487cd-a7e9-f58e-f982-19c4043cb72b_1572832920; _gat_UA-46983583-11=1; keyword_search=Kh%26aacute%3Bch+s%E1%BA%A1n+Cali+Night+%C4%90%26agrave%3B+N%E1%BA%B5ng; room_search=1; person_search=2; _v1EmaticSolutions=%5B%2216ee28cf-fea7-11e9-bc19-0242ac160003%22%2C1572832921072%5D; insLastVisitedHotelUrl=https%3A%2F%2Fmytour.vn%2F16068-khach-san-cali-night-da-nang.html; insLastVisitedHotelCity=%C4%90%C3%A0%20N%E1%BA%B5ng; insLastVisitedHotelName=Kh%C3%A1ch%20s%E1%BA%A1n%20Cali%20Night%20%C4%90%C3%A0%20N%E1%BA%B5ng; insLastVisitedHotelCheckinDate=05%2F11%2F2019; ins-product-id=16068; current-currency=VND; XSRF-TOKEN=2e20d2b84f2364f2d820de913b1dfbe2e09ba555; insdrSV=6',
    }

    hotel_form_data = {
        # 'date_checking': '05/11/2019',
        # 'date_checkout': '06/11/2019',
        'id_hotel': None, #'16068'
        # 'num_room': '1',
        # 'keyword': 'Kh\xE1ch s\u1EA1n Cali Night \u0110\xE0 N\u1EB5ng',
        # 'num_person': '2',
        # '_token': 'Jn4aqEhcEYeL42HTfNrF0cFGQTaolM6QYELnm4OE',
        # 'show_price_email': '0'
        }

    params = '117,190,191'

    def create_request(self, item):
        link = item.link
        item.hotel_city_id = {'117': 5, '190': 6, '191': 7}[item.id_web]
        form_data = self.hotel_form_data.copy()
        # hotel_id = link.split('/')[-1]
        now = arrow.now()
        form_data.update(
            date_checking=now.format('DD/MM/YYYY'),
            date_checkout=now.shift(days=1).format('DD/MM/YYYY'),
            id_hotel=re.search(r'(?<=vn/)\d+', link).group()
            # id_hotel='507'
        )
        yield JsonRequest(url=self.hotel_url, dont_filter=True, method='POST', data=form_data,
                           headers=self.hotel_headers, callback=self.parse_api, meta={'item': item, 'link': link})

    def parse_api(self, response):
        item = response.meta.get('item')
        link = response.meta.get('link')
        # stop if data is empty
        res = Selector(text=response.body)
        hotel_price = []
        room = res.xpath("//div[@class='wrapper-room']/table/tbody")
        if room:
            i = 1
            while True:
                name = room.xpath("./tr[%s]/td/a/text()" % str(i)).extract_first()
                if not name:
                    break
                name = name.replace('/n','').strip()
                info = room.xpath("./tr[%s]//table[@class='table ']/tbody//tr[contains(@class, rate-box)]" % str(i+1))
                for j in info:
                    guest = j.xpath("./td[@class='user-group text-center']/span/text()").extract()
                    price = j.xpath("./td[@class='room-price']//p[@class='price text-lg']/strong/text()").extract_first()
                    attribute = j.xpath("./td[contains(@class,'room-condition')]//p[contains(@class,'attribute-hotel')]/text()").extract()
                    list_attr = []
                    for attr in attribute:
                        if attr.replace('\n','').strip() == "Bao gồm Bữa sáng":
                            list_attr.append('Bao gồm bữa sáng')
                    hotel_price.append({
                        'name': name,
                        'guest': int(guest[1].replace('\n','').strip().split(' ')[1]) if guest else '',
                        'price': int(price.replace(',','').strip()) if price else '',
                        'attribute': list_attr
                    })      
                i = i + 2                



        # title_room = room.xpath("//td[@class='title-room']/a/text()").extract()
        # attr_room = room.xpath("//tr[@class='book-choose']/td[2]")
        
        # for r in title_room:
        #     index = title_room.index(r)
        #     attr = attr_room[index] 
        #     price = attr.xpath("//td[@class='room-price']//p[@class='price text-lg']/strong/text()").extract()
        #     attribute = attr.xpath("//td[contains(@class, 'policy')]//p[contains(@class, 'attribute-hotel')]//text()").extract()
        #     guest = attr.xpath("//td[@class='user-group text-center']/span/text()").extract()
        #     hotel_price.append({
        #         'name': r.replace('/n','').strip(),
        #         'guest': int(guest[index * 2 + 1].replace('\n','').strip().split(' ')[1]) if guest else 0,
        #         'price': int(price[index].replace(',','').strip()) if price else '',
        #         'attribute': ['Bao gồm bữa sáng'] if attribute and attribute[index * 2 + 1].replace('\n','').strip() == 'Bao gồm Bữa sáng' else '',
        #     })
        item.hotel_price = hotel_price

        yield JsonRequest(url=link, dont_filter=True, method='GET', 
                            callback=self.parse_request, meta={'item': item})
    
    def parse_request(self, response):
        item = response.meta.get('item')
        res = Selector(text=response.body)

        hotel_name = res.xpath("//div[@class='page-header']/h1/text()").extract_first().replace('\n','').strip()
        item.hotel_name = hotel_name
        hotel_address = res.xpath("//div[@class='page-header']//p[@class='text-df']/a/span/text()").extract_first().strip()
        item.hotel_address = hotel_address
        hotel_lat = res.xpath("//div[@class='page-header']//p[@class='text-df']/a/@data-map-lat").extract_first()
        hotel_lng = res.xpath("//div[@class='page-header']//p[@class='text-df']/a/@data-map-lng").extract_first()
        item.hotel_latlng = "%s,%s" % (hotel_lat, hotel_lng)
        item.hotel_source = 'Mytour'
        item.hotel_type = 'Khách sạn'
        star = int(res.xpath("//div[@class='page-header']//span[@class='star']/span/@class").extract_first().split('-')[1])
        item.hotel_star = star
        description = res.xpath("//div[@id='property_description_content']/p/text()").extract()
        item.hotel_description = ' '.join(description)
        attribute = res.xpath("//div[@class='attribute-hotel']//ul[@class='attribute-hotel-list row']//li//span[@class='attribute-value']/text()").extract()
        item.hotel_attribute = attribute
        hotel_image = res.xpath("//div[@class='hotel-img-wrapper']//div[contains(@class, 'hotel-img')]/a//img/@src").extract()
        item.hotel_image = hotel_image
        yield self.post_item(item)
        
        # print(json.loads(response.body))
        # data = obj(json.loads(response.body).get('data'))
        # if not data:
# class MytourDetail(Spider):

#     name = "MytourDetail"
#     custom_settings = {
#         **get_project_settings(),
#         'DOWNLOADER_MIDDLEWARES': {
#             'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
#             'crawler.middlewares.ScheduleRequestSpiderMiddleware': 100,
#             'crawler.middlewares.CustomRetryMiddleware': 120,
#             'scrapy.downloadermiddlewares.UserAgentMiddleware': None,
#             'crawler.middlewares.CustomUserAgentProxyMiddleware': 400,
#             'scrapy_splash.SplashCookiesMiddleware': 723,
#             'scrapy_splash.SplashMiddleware': 725,
#             'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
#         },
#     }
#     params = '117,190,191'
#     count = 0

#     def __init__(self, *a, **kw):
#         config_logging()
#         super().__init__(*a, **kw)

#         # check params is declared
#         if not getattr(self, 'params', None):
#             raise CloseSpider('Spider has no params')

#         self.url = f'http://crawler.wemarry.vn/api/get-detail-multi?id={self.params}'
#         self.logger.info(f'{self.name} is running')


#     def start_requests(self):
#         # get cat data
#         if not hasattr(self, 'bidDatas') or not self.bidDatas:
#             yield Request(self.url, callback=self.parse_data, dont_filter=True)

#         # get form request
#         if getattr(self, 'bidDatas', None):
#             # data = self.bidDatas.pop()
#             data = self.bidDatas[0]

#             item = dict(
#                 id_web=data.get('ID_WEB'),
#                 domain=data.get('DOMAIN'),
#                 website=data.get('WEBSITE'),
#                 active=data.get('ACTIVE'),
#                 post_link=data.get('POST_LINK'),
#                 lang_web=data.get('LANG_WEB'),
#                 detail_city_id=data.get('ARR_LAW')['detail_city_id']['value'],
#             )

#             yield ApiRequest(url=data['LINK'], callback=self.parse_request, dont_filter=True,
#                              meta={'item': item, 'api_urls': ['https://mytour.vn/hotel/get-price-detail-page$']})

#     def parse_data(self, response):
#         self.bidDatas = json.loads(response.body)
#         self.logger.info(f'{self.name} - got {len(self.bidDatas)} biddata')
#         if len(self.bidDatas) == 0:
#             raise CloseSpider(f'{self.name} - BidDatas is empty - crawl done')

#     def parse_request(self, response):
#         data = self.bidDatas.pop()
#         item = response.meta.get('item')
#         api_urls = response.meta.get('api_urls')

#         link = data['LINK']

#         # update item
#         item.update(link=link)



#         # filter form request
#         filted_requests = self.filted_requests(response, api_urls)
#         form_requests = [self.get_form_request(x) for x in filted_requests]
#         # modify form request
        
#         from pprint import pprint
#         pprint(form_requests)
#         raise CloseSpider(f'{link}')

#         form = form_requests[0]
#         del form['headers']['Content-Length']
#         del form['headers']['Cookie']
#         del form['headers']['X-CSRF-Token']
#         del form['headers']['Referer']

#         # update holtel id in body  
#         hotel_id = re.search(r'(?<=mytour\.vn\/)\d+', link)

#         form['body'] = re.sub(r'(?<=limit:\s)\d+', '100', json.dumps(form['body']))

#         yield Request(form['url'], method=form['method'], headers=form['headers'], body=form['body'], 
#                       callback=self.parse_api, meta={'item': item, 'form_requests': form})

#     def parse_api(self, response):
#         item = response.meta.get('item')
#         form = response.meta.get('form_requests')

#         data = json.loads(response.body)
#         if data and data.get('data', None) and data['data'].get('filterHotel', None) and data['data']['filterHotel'].get('hotels', None):
#             cat_link = [f'https://mytour.vn/{x["id"]}-{x["name"]}.html' for x in data['data']['filterHotel']['hotels']]

#             self.count += len(cat_link)
#             self.logger.info(f'{self.name} - got total {self.count} cat link')
#         else:
#             # stop if data is empty
#             self.logger.info(f'{item["link"]} - category is empty')
#             return None

#         # nextpage
#         body = form['body']
#         offset = re.search(r'(?<=offset:\s)\d+', body).group()
#         next_offset = int(offset) + 100
#         form['body'] = re.sub(r'(?<=offset:\s)\d+', str(next_offset), body)

#         yield Request(form['url'], method=form['method'], headers=form['headers'], body=form['body'], 
#                       callback=self.parse, meta={'item': item, 'form_requests': form})

#     @staticmethod
#     def filted_requests(response, patterns):
#         har = json.loads(response.text)
#         har_requests = har['log']['entries']

#         filted_req = list()
#         for req in har_requests:
#             for pattern in patterns:
#                 if re.search(rf'{pattern}', req['request']['url']):
#                     filted_req.append(req)

#         return filted_req

#     @staticmethod
#     def get_form_request(har_request):
#         request = har_request['request']

#         url = request.get('url')
#         method = request.get('method')
#         headers = {item.get('name', 'null'): item.get('value') for item in request.get('headers')}
#         params = request.get('queryString')

#         try:
#             body = json.loads(base64.b64decode(request['postData']['text']))
#         except Exception as e:
#             body = None

#         return dict(
#                 url=url,
#                 method=method,
#                 params=params,
#                 headers=headers,
#                 body=body
#             )
