# -*- coding: utf8 -*-
from scrapy.http import JsonRequest
from scrapy_splash import SplashRequest
from scrapy.exceptions import CloseSpider

from ..common.spiders import SplashDetail
from scrapy.utils.project import get_project_settings
from ..common.utils import obj


class TripadvisorRestaurantDetail(SplashDetail):

    name = "TripadvisorRestaurantDetail"
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
    params = '113,188,189'
    script1 = """
    function main(splash, args)
      splash.private_mode_enabled = false
      assert(splash:go(args.url))
      assert(splash:wait(0.5))
      splash:runjs('document.querySelector("a.restaurants-detail-overview-cards-DetailsSectionOverviewCard__viewDetails--ule3z").click()')
      assert(splash:wait(0.1))
      return splash:html()
    end
    """
    script2 = """
    function main(splash, args)
      splash.private_mode_enabled = false
      assert(splash:go(args.url))
      assert(splash:wait(0.5))
      splash:runjs('document.querySelector("span.public-location-hours-LocationHours__bold--2oLr-").click()')
      assert(splash:wait(0.1))
      return splash:html()
    end
    """

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
                # using script 1
                detail_city=None,
                detail_price_avg=None,
                detail_property_amenities=None,
                detail_product_style=None,
                detail_product_class=None,
                # using script 2
                detail_review_user_ranking=None,
                detail_review_user_content_img=None,
                detail_review_user_content=None,
                detail_review_user_title=None,
                detail_review_user_name=None,
                detail_review_user_avatar=None,
                detail_title=None,
                detail_phone=None,
                detail_street=None,
                detail_district=None,
                detail_country=None,
                detail_time_open_store=None,
                hotel_latlng = '0.0' 
            )
            for request in self.create_request(item):
                yield request

    def create_request(self, item):
        yield SplashRequest(item.link, callback=self.parse, endpoint='execute', dont_filter=True,
                            meta={'item': item}, args={'lua_source': self.script1, 'wait': 1},)

    def parse(self, response):
        item = response.meta.get('item')

        item.detail_city = {'113': 5, '188': 6, '189': 7}[item.id_web]
        item.detail_description = response.xpath(".//div[contains(@class,'restaurants-detail-overview-cards-DetailsSectionOverviewCard__desktopAboutText')]/text()").extract_first()
        item.detail_price_avg = response.xpath(".//div[contains(text(), 'KHOẢNG GIÁ')]/following-sibling::div[last()]/text()").extract_first()
        item.detail_product_style = response.xpath(".//div[contains(text(), 'MÓN ĂN')]/following-sibling::div[last()]/text()").extract_first()
        item.detail_product_class = response.xpath(".//div[contains(text(), 'Bữa ăn')]/following-sibling::div[last()]/text()").extract_first()

        detail_property_amenities_1 = response.xpath(".//div[contains(text(), 'ĐẶC TRƯNG')]/following-sibling::div[last()]/text()").extract_first()
        detail_property_amenities_2 = response.xpath(".//div[contains(text(), 'Chế độ ăn đặc biệt')]/following-sibling::div[last()]/text()").extract_first()
        item.detail_property_amenities = f'{detail_property_amenities_1},{detail_property_amenities_2}' if detail_property_amenities_1 else detail_property_amenities_2

        yield SplashRequest(item.link, callback=self.parse_detail, endpoint='execute', dont_filter=True,
                            meta={'item': item}, args={'lua_source': self.script2, 'wait': 1},)

    def parse_detail(self, response):
        item = response.meta.get('item')

        item.detail_title = response.css("h1.h1::text").extract_first()
        item.detail_phone = response.css("span.is-hidden-mobile.detail::text").extract_first()
        item.detail_district = response.css("span.extended-address::text").extract_first()
        item.detail_street = response.css("span.street-address::text").extract_first()
        item.detail_country = response.css("span.country-name::text").extract_first()

        item.detail_img = [x for x in response.css("div.mosaic_photos img::attr(data-lazyurl)").extract() if x.startswith('http')]
        item.detail_img.extend([x for x in response.css("div.mosaic_photos img::attr(src)").extract() if x.startswith('http')])

        # reviews
        item.detail_review_user_name = response.css("div.info_text > div::text").extract()
        item.detail_review_user_avatar = [x if x.startswith('http') else None for x in response.css(".ui_avatar.resp > .basicImg::attr(src)").extract()]
        item.detail_review_user_title = response.css(".quote > .title > span.noQuotes::text").extract()
        item.detail_review_user_ranking = response.css("div.ui_column.is-9 > span.ui_bubble_rating").extract()
        item.detail_review_user_content_img = [x if x.startswith('http') else None for x in response.css("div.ui_avatar.resp img::attr(src)").extract()]
        item.detail_review_user_content = response.css("div.ui_column.is-9 > div.prw_rup.prw_reviews_text_summary_hsx > div > p").extract()

        # opentime
        item.detail_time_open_store = response.css("#c_popover_2 > div > div > div.overlays-popover-Popover__popover--2R2s5 > div.public-location-hours-LocationHours__hoursPopover--2h1HP > div.all-open-hours").extract_first()

        self.count += 1
        self.logger.info(f"crawl {item.link} done - total {self.count}")
        yield self.post_item(item)
