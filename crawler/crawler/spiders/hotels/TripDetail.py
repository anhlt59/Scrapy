# -*- coding: utf8 -*-
from scrapy.utils.project import get_project_settings
from scrapy.exceptions import CloseSpider
from scrapy_splash import SplashRequest
import re
import json
import arrow
import requests

from ..common.spiders import SplashDetail
from ..common.utils import obj
from ..common.http import ApiSeleniumRequest


class TripDetail(SplashDetail):

    name = "TripDetail"
    params = '197,198,199'
    custom_settings = {
        **get_project_settings(),
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
            'crawler.middlewares.ScheduleRequestSpiderMiddleware': 100,
            'scrapy.downloadermiddlewares.UserAgentMiddleware': None,
            'crawler.middlewares.CustomUserAgentProxyMiddleware': 400,
            'scrapy_splash.SplashCookiesMiddleware': 723,
            'scrapy_splash.SplashMiddleware': 725,
            'crawler.middlewares.CustomSeleniumWireMiddleware': 800,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
        },
    }
    api_params = None
    api_headers = {
        'sec-fetch-mode': 'cors',
        'origin': 'https://vn.trip.com',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'vi-VN,vi;q=0.9,en;q=0.8',
        'cookie': 'ibulocale=vi_vn; ibulanguage=VN; cookiePricesDisplayed=VND; _abtest_userid=c6e95939-67d7-4cd4-a0bc-152c21f5c49a; hoteluuid=UdQ3ht00D9uGTt9Sgo; __utma=1.1902207017.1572998937.1572998937.1572998937.1; __utmc=1; __utmz=1.1572998937.1.1.utmcsr=crawler.wemarry.vn|utmccn=(referral)|utmcmd=referral|utmcct=/api/get-detail-multi; __utmt=1; IBU_TRANCE_LOG_P=1573007223421; _ga=GA1.2.1902207017.1572998937; _gid=GA1.2.649176451.1572998938; _gat=1; _gcl_au=1.1.1950074658.1572998938; _gat_UA-109672825-3=1; _RF1=118.71.191.248; _RSG=fs4lv8_U81EUSvndAN9yaA; _RDG=288f08ce27cd79278c3940c5c5be205939; _RGUID=e0487bf2-39bc-4da9-a93c-2572a7c7971e; _bfi=p1%3D10320668147%26p2%3D0%26v1%3D1%26v2%3D0; intl_ht1=h4=301_713760; _bfa=1.1572998936931.32ctbn.1.1572998936931.1572998936931.1.2; _bfs=1.2; __utmb=1.4.10.1572998937',
        'if-modified-since': 'Thu, 01 Jan 1970 00:00:00 GMT',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'accept': '*/*',
        'cache-control': 'max-age=0',
        'authority': 'vn.trip.com',
        'sec-fetch-site': 'same-origin',
    }
    room_data = {
        'HotelID': '7021424',
        'checkin': '2019/11/06',
        'checkout': '2019/11/07',
        'RoomQuantity': '1',
        'occupancy': '2',
    }
    room_url = 'https://vn.trip.com/hotels/Detail/GetRoomDataJson4Hote1s'

    def create_request(self, item):
        if not getattr(self, 'api_params', None):
            # create cookie and params
            yield ApiSeleniumRequest(url=item.link, request_urls=[self.room_url],
                                     callback=self.parse_cookies, meta={'item': item})
        else:
            # tooken is created
            link = item.link
            url, headers, params, data = self.room_url, self.api_headers, self.api_params, self.room_data.copy()

            # modify form request
            now = arrow.now()
            data.update(
                checkin=now.format('YYYY/MM/DD'),
                checkout=now.shift(days=1).format('YYYY/MM/DD'),
                HotelID=re.search(r'(?<=detail-)\d+', link).group(),
                # CityID='286' if 'hanoi' in link else '301' if 'ho-chi-minh' in link else '1356'
            )
            params.update(fjs='00')
            yield SplashRequest(url=link, callback=self.parse,
                                meta={'item': item, 'form_request': [url, headers, params, data]},
                                args={'lua_source': self.script, 'wait': 1})

    def parse_cookies(self, response):
        try:
            req = obj(json.loads(response.body)[0]['request'])
            if not req.params and req.headers.Cookie:
                raise Exception()
        except:
            self.logger.critical("Can't get cookie")
            raise CloseSpider("Can't get cookie")

        self.api_params = req.params
        self.api_headers['cookie'] = req.headers.Cookie
        self.logger.info('get cookie done')

        for req in self.create_request(response.meta.get('item')):
            yield req

    def parse(self, response):

        item = response.meta.get('item')
        link = item.link

        # detail hotel
        item.hotel_source = 'Trip'
        item.hotel_city_id = {'197': 5, '198': 6, '199': 7}[item.id_web]
        item.hotel_type = 'Khách sạn'
        item.hotel_name = response.xpath(".//h1[@class='tit']/text()").extract_first().replace('\n', '').strip()
        item.hotel_address = response.xpath(".//p[@class='address']/span/text()").extract_first()
        item.hotel_image = response.xpath(".//div[contains(@class, 'pic')]/descendant::img/@src").extract()[:20]
        hotel_star = response.xpath(".//h1/span/i/@class").extract_first()
        if hotel_star:
            item.hotel_star = hotel_star[-1]
        item.hotel_attribute = []
        attrs = response.xpath('.//span[@class="m-hotelfacility_popular_body_cont"]')
        for attr in attrs:
            item.hotel_attribute.append(' '.join(attr.xpath('.//text()').extract()))

        latlng = re.search(r'(?<=latlng=)[\d\.\,]+', link)
        if latlng:
            item.hotel_latlng = latlng.group()

        # hotel review
        item.hotel_review = []
        reviews = response.xpath('.//div[@class="m-reviewCard-item"]')
        for review in reviews:
            name = review.xpath('.//p[@class="name"]/text()').extract_first()
            rating = int(review.xpath('.//div[@class="m-score_single"]/strong/text()').extract_first()[0])
            image = review.xpath('.//div[@class="user"]/img/@src').extract_first()
            content = review.xpath('.//div[@class="comment"]/p/text()').extract_first()

            item.hotel_review.append(
                dict(
                    name=name,
                    title='',
                    rating=rating,
                    content=content,
                    image=image
                )
            )

        url, headers, params, data = response.meta.get('form_request')
        res = requests.post(url, headers=headers, params=params, data=data)
        try:
            data = obj(res.json())
        except:
            data = None

        item.hotel_price = []
        for room in data.lstHtlDetailJsonModel:
            if len(item.hotel_image) < 20:
                item.hotel_image.extend([x.big for x in room.baseRoomPicList][:20-len(item.hotel_image)])
            name = room.baseRoomName
            guest = int(room.roomList[0].personNums)
            price = int(room.roomList[0].RoomAmount)

            attribute = []
            if room.roomList[0].Breakfast:
                attribute.append('Bao gồm bữa sáng')
            if room.roomList[0].Cancel:
                attribute.append('Miễn phí Đổi/Hủy')

            item.hotel_price.append(
                dict(
                    name=name,
                    guest=guest,
                    price=price,
                    attribute=attribute
                )
            )

        self.count += 1
        self.logger.info(f"crawl {item.link} done - total {self.count}")
        yield self.post_item(item)
