# -*- coding: utf8 -*-
from scrapy.http import JsonRequest
from scrapy_splash import SplashRequest
from scrapy.exceptions import CloseSpider
import json
import urllib
from scrapy.utils.project import get_project_settings

from ..common.spiders import SplashDetail
from ..common.utils import obj


class FoodyDetail(SplashDetail):

    name = "FoodyDetail"
    custom_settings = {
        **get_project_settings(),
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
            'crawler.middlewares.ScheduleRequestSpiderMiddleware': 100,
            'scrapy.downloadermiddlewares.UserAgentMiddleware': None,
            'crawler.middlewares.CustomUserAgentProxyMiddleware': 400,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
        },
        'RETRY_TIMES': 10,
        'SPLASH_URL': 'http://192.168.1.239:8010',
    }
    params = "120,179,180"
    script = """
    function main(splash, args)
      splash.private_mode_enabled = false
      assert(splash:go(args.url))
      assert(splash:wait(1))
      return splash:html()
    end
    """
    api_url = 'https://gappapi.deliverynow.vn/api/dish/get_delivery_dishes'
    api_headers = {
        'X-Foody-Api-Version': '1',
        'Origin': 'https://www.foody.vn',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.87 Safari/537.36',
        'X-Foody-Client-Type': '1',
        'X-Foody-App-Type': '1004',
        'Accept': 'application/json, text/plain, */*',
        'X-Foody-Client-Id': '',
        'X-Foody-Client-Version': '1',
    }
    api_params ={'request_id': '152325', 'id_type': '1'}

    def start_requests(self):
        # get data
        if not hasattr(self, 'bidDatas'):  # or not self.bidDatas:
            yield JsonRequest(self.url, callback=self.parse_data, dont_filter=True)
        # create requests
        if getattr(self, 'bidDatas', None):
            data = self.bidDatas.pop()
            item = obj(
                id_web=data.get('ID_WEB'),
                id=data.get('ID'),
                link=data.get('LINK'),
                post_link=data.get('POST_LINK'),
                detail_city=None,
                detail_menuFood_name=[],
                detail_menuFood_image=[],
                detail_menuFood_price=[],
                detail_menuFood_desc=[],
                detail_times=None,
                detail_property_style=None,
                detail_property_class=None,
                detail_property_purpose=None,
                detail_time_open_store=None,
                detail_review_user_name=None,
                detail_review_user_avatar=None,
                detail_title=None,
                detail_phone=None,
                detail_street=None,
                detail_district=None,
                detail_country=None,
                hotel_latlng = '0.0'
            )
            for request in self.create_request(item):
                yield request

    def create_request(self, item):
        yield SplashRequest(item.link, callback=self.parse_info, endpoint='execute', meta={'item': item}, 
                            args={'lua_source': self.script, 'wait': 1})

    def parse_info(self, response):
        item = response.meta.get('item')
        item.detail_city = {'120':5,'179':6,'180':7}[item.id_web]

        item.detail_times = response.css('.micro-timesopen > span:nth-child(3)::text').extract_first()
        item.detail_property_style = response.css('div.category > div.category-cuisines > div.cuisines-list > a::text').extract_first()
        item.detail_property_class = response.css('div.microsite-res-info > div:nth-child(1) > div:nth-child(2) > div:nth-child(2) > a::text').extract()
        item.detail_property_purpose = response.css('div.category > div.category-cuisines > div.audiences::text').extract_first()
        item.detail_time_open_store = response.css('div.micro-timesopen > span:nth-child(3)::text').extract_first()
        item.detail_property_amenities = response.css('.micro-property > li > a:nth-child(2)').extract_first()
        item.detail_price_avg = response.css('div.res-common-minmaxprice > span:nth-child(2) > span').extract()
        item.detail_img = response.css('.microsite-box-content .foody-photo img::attr(src)').extract()
        item.detail_thumb = response.css('img.pic-place::attr(src)').extract()
        item.detail_review_user_ranking = response.css('div.micro-right1000 > section > div > div > div > div > div.micro-left > div > div > div.list-reviews > div > ul > li > div.review-user.fd-clearbox.ng-scope > div > div.review-points.ng-scope > span::text').extract()
        item.detail_review_user_content_img = response.css('div.micro-right1000 > section > div > div > div > div > div.micro-left > div > div > div.list-reviews > div > ul > li > ul > li > a > img::attr(src)').extract()
        item.detail_review_user_content = response.css('div.micro-right1000 > section > div > div > div > div > div.micro-left > div > div > div.list-reviews > div > ul > li > div.review-des.fd-clearbox.ng-scope > div > span').extract()
        item.detail_review_user_title = response.css('div.micro-right1000 > section > div > div > div > div > div.micro-left > div > div > div.list-reviews > div > ul > li > div.review-des.fd-clearbox.ng-scope > a::text').extract()
        item.detail_review_user_name = response.css('div.micro-right1000 > section > div > div > div > div > div.micro-left > div > div > div.list-reviews > div > ul > li > div.review-user.fd-clearbox.ng-scope > div > div.ru-row > a::text').extract()
        item.detail_review_user_avatar = response.css('div.micro-right1000 > section > div > div > div > div > div.micro-left > div > div > div.list-reviews > div > ul > li > div.review-user.fd-clearbox.ng-scope > div.review-avatar > a > img::attr(src)').extract()
        item.detail_country = response.css('div.disableSection > div:nth-child(1) > div > span:nth-child(5)::text').extract_first()
        item.detail_district = response.css('div.disableSection > div:nth-child(1) > div > span:nth-child(4) > a > span::text').extract_first()
        item.detail_street = response.css('div.disableSection > div:nth-child(1) > div > span:nth-child(2) > a > span::text').extract_first()
        item.detail_point = response.css('.microsite-point-avg::text').extract_first()
        item.detail_title = response.css('.main-info-title > h1::text').extract_first()

        request_id = response.css('div[data-item-id]::attr(data-item-id)').extract_first()
        if not request_id:
            self.logger.info("Can't get menu food")
            yield self.post_item(item)
            self.count += 1
            self.logger.info(f"crawl {item.link} done - total {self.count}")
        else:
            self.api_params.update(request_id=request_id)
            yield JsonRequest(url=f'{self.api_url}?{urllib.parse.urlencode(self.api_params)}',
                              dont_filter=True, method='GET', headers=self.api_headers,
                              callback=self.parse_menu, meta={'item': item})

    def parse_menu(self, response):
        item = response.meta.get('item')
        data = obj(json.loads(response.body))

        for menu in data.reply.menu_infos:
            for dish in menu.dishes:
                item.detail_menuFood_name.append(dish.name)
                item.detail_menuFood_image.append(dish.photos[1].value)
                item.detail_menuFood_price.append(dish.price.text)
                item.detail_menuFood_desc.append(dish.description)

        yield self.post_item(item)
        self.count += 1
        self.logger.info(f"crawl {item.link} done - total {self.count}")
