# -*- coding: utf8 -*-
from scrapy.http import JsonRequest
from scrapy.exceptions import CloseSpider
import json
import arrow
import re
import urllib
import requests

from ..common.utils import obj
from ..common.spiders import DetailSpider


class AgodaDetail(DetailSpider):

    name = "AgodaDetail"
    hotel_url = 'https://www.agoda.com/api/vi-vn/pageparams/property'
    hotel_headers = {
    'sec-fetch-mode': 'cors',
    'accept-encoding': 'gzip, deflate, br',
    'accept-language': 'vi-VN,vi;q=0.9,en;q=0.8',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',
    'accept': '*/*',
    'authority': 'www.agoda.com',
    'sec-fetch-site': 'same-origin',
    'x-referer': '',
    }
    hotel_cookies = None
    hotel_params = {
        'checkin': None,  # '2019-10-31',
        'los': '1',
        'adults': '2',
        'tabbed': 'true',
        'hotel_id': None,  # '7430890',
        'all': 'false'
    }
    review_url = 'https://www.agoda.com/NewSite/vi-vn/Review/HotelReviews'
    review_headers = {
        'sec-fetch-mode': 'cors',
        'origin': 'https://www.agoda.com',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'vi-VN,vi;q=0.9,en;q=0.8',
        'x-requested-with': 'XMLHttpRequest',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',
        'content-type': 'application/json; charset=UTF-8',
        'accept': 'application/json',
        'authority': 'www.agoda.com',
        'sec-fetch-site': 'same-origin',
    }
    review_data = {
        'demographicId': 0,
        'hotelId': None,  # 926594,
        'isCrawlablePage': True,
        'isReviewPage': False,
        'pageNo': 1,
        'pageSize': 20,
        'paginationSize': 5,
        'sorting': 5}
    params = '181,182,183'

    def create_request(self, item):
        link = item.link

        if not self.hotel_cookies:
            # create cookie
            s = requests.Session()
            s.get(link, headers=self.hotel_headers)
            cookies = s.cookies
            if cookies:
                self.hotel_cookies = {'agoda.version.03': cookies.get('agoda.version.03')}
            else:
                raise CloseSpider("Can't get cookies")

        # latitude/longtitude
        item.hotel_latlng = re.search(r'(?<=latlng=)[\d\,\.]+', link).group()
        # city id - ha noi 1, da nang 2, ho chi minh 3
        item.hotel_city_id = {'181': 5, '182': 6, '183': 7}[item.id_web]

        # Detail hotel
        url, headers, cookies, params = self.hotel_url, self.hotel_headers, self.hotel_cookies ,self.hotel_params.copy()
        # update checkin, hotel_id
        now = arrow.now()
        params.update(
            checkin=now.shift(days=1).format('YYYY-MM-DD'),
            hotel_id=re.search(r'(?<=hotelid=)\d+', link).group(),
        )
        yield JsonRequest(url=f'{url}?{urllib.parse.urlencode(params)}', dont_filter=True, method='GET',
                          cookies=cookies, headers=headers, callback=self.parse_api, meta={'item': item})

    def parse_api(self, response):
        item = response.meta.get('item')

        # stop if data is empty
        data = obj(json.loads(response.body))
        if not data:
            self.logger.error(f'{item.link} - fail')
            return None

        # extract data
        item.hotel_source = 'Agoda'
        item.hotel_search_image = 'agoda.net'
        item.hotel_type = 'Khách sạn'
        item.hotel_name = data.aboutHotel.translatedHotelName
        item.hotel_star = int(data.hotelInfo.starRating.value)
        item.hotel_address = data.hotelInfo.address.full
        item.hotel_image = [f'https:{x.location}' for x in data.mosaicInitData.images][:20]
        item.hotel_attribute = list(set([x.name for y in data.aboutHotel.featureGroups for x in y.feature if x.available]))

        if data.aboutHotel.hotelDesc.overview:
            item.hotel_description = re.sub(r'<.*?>', '\n', data.aboutHotel.hotelDesc.overview)

        item.hotel_price = []
        for room in data.roomGridData.masterRooms:
            name=re.sub(r'\(.+\)', '', room.name)
            price=room.cheapestPrice
            guest=room.maxOccupancy

            attribute=[]
            for attr in [x.title for x in room.rooms[0].features]:
                if 'Ăn sáng miễn phí' in attr:
                    attribute.append('Bao gồm bữa sáng')
                elif 'MIỄN PHÍ hủy phòng' in attr:
                    attribute.append('Miễn phí Đổi/Hủy')
                elif 'Thanh toán tại nơi ở' in attr:
                    attribute.append('Thanh toán tại nơi ở')

            item.hotel_price.append(
                dict(
                    name=name,
                    price=price,
                    guest=guest,
                    attribute=attribute
                )
            )

        # Review hotel
        url, headers, data = self.review_url, self.review_headers, self.review_data.copy()
        # update hotelid
        data.update(
            hotelId=re.search(r'(?<=hotelid=)\d+', item.link).group(),
        )
        yield JsonRequest(url=url, dont_filter=True, method='POST',
                          headers=headers, data=data,
                          callback=self.parse_review, meta={'item': item})

    def parse_review(self, response):
        item = response.meta.get('item')

        # stop if data is empty
        data = obj(json.loads(response.body))
        if not data.commentList:
            self.logger.error(f'{item.link} - fail')
            return None

        item.hotel_review = [dict(
            name=review.reviewerInfo.displayMemberName,
            rating=int(float(review.rating)/2),
            title=review.reviewTitle,
            content=review.reviewComments,
            image=''
        ) for review in data.commentList.comments]

        self.count += 1
        self.logger.info(f"crawl {item.hotel_name} done - total {self.count}")
        yield self.post_item(item)