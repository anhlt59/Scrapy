# -*- coding: utf8 -*-
from scrapy.http import Request
from scrapy.exceptions import CloseSpider
from scrapy_splash import SplashRequest

from scrapy.utils.project import get_project_settings
from ..common.utils import obj
from ..common.spiders import SplashCat


class FoodyCat(SplashCat):

    name = "FoodyCat"
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
      assert(splash:wait(0.5))
      return splash:html()
    end
    """

    def create_request(self, item):
        yield SplashRequest('https://www.foody.vn', callback=self.ignore)
        yield Request(url=item.link, callback=self.parse, dont_filter=True, meta={'item': item})

    def ignore(self, response):
        pass

    def parse(self, response):
        item = response.meta.get('item')
        item.link = response.url
        item.cat_link = []
        brand_link = []

        raw_link = response.css(".result-name .resname > h2 > a::attr(href)").extract()
        for link in raw_link:
            if '/thuong-hieu/' in link:
                brand_link.append(response.urljoin(link))
            else:
                item.cat_link.append(response.urljoin(link))

        if not raw_link:
            # stop if data is empty
            self.logger.info(f"cat link is empty url {response.url}")
            return None

        # nextpage
        nextpage_url = response.css('#scrollLoadingPage > a::attr(href)').extract_first()
        nextpage_abs_url = response.urljoin(nextpage_url) if nextpage_url else None

        if brand_link:
            yield Request(url=brand_link.pop(), callback=self.parse_detail, dont_filter=True,
                          meta={'item': item, 'brand_link': brand_link, 'nextpage': nextpage_abs_url})

    def parse_detail(self, response):
        item = response.meta.get('item')
        nextpage = response.meta.get('nextpage')
        brand_link = response.meta.get('brand_link')

        # extract cat link
        cat_link = [response.urljoin(x) for x in response.css("div.ldc-item-header a::attr(href)").extract() if 'Model.Url' not in x]
        item.cat_link.extend(cat_link)

        if brand_link:
            yield Request(url=brand_link.pop(), callback=self.parse_detail, 
                          meta={'item': item, 'brand_link': brand_link, 'nextpage': nextpage})
        else:
            yield self.post_item(item)
            self.count += len(item.cat_link)
            self.logger.info(f"got {len(item.cat_link)} cat link - total {self.count}")
            yield Request(url=nextpage, callback=self.parse,
                          meta={'item': item, 'brand_link': brand_link, 'nextpage': nextpage})

    # def parse_detail(self, response):
    #     item = response.meta.get('item')
    #     nextpage = response.meta.get('nextpage')
    #     brand_link = response.meta.get('brand_link')
    #     restaurant_link = response.meta.get('restaurant_link')

    #     # update cat link
    #     menu_sidebar = response.css('li[data-item-name=menu] a::attr(href)')
    #     menu_view = response.css('div.view-all-menu a::attr(href)')

    #     if menu_view:
    #         self.logger.info(f'{response.url} menu_view')
    #         item.cat_link.append(menu_view.extract_first())
    #     elif menu_sidebar:
    #         self.logger.info(f'{response.url} menu_sidebar')
    #         item.cat_link.append(response.urljoin(menu_sidebar.extract_first()))
    #     else:
    #         self.logger.error(f"{response.url} - Can't get detail link")

    #     if restaurant_link:
    #         yield SplashRequest(restaurant_link.pop(), callback=self.parse_detail, args={'lua_source': self.script, 'wait': 1}, 
    #                             meta={'item': item, 'brand_link': brand_link, 'restaurant_link': restaurant_link, 'nextpage': nextpage})
    #     else:
            # # print(item)
            # yield self.post_item(item)
            # self.count += len(item.cat_link)
            # self.logger.info(f"got {len(item.cat_link)} cat link - total {self.count}")
            # yield Request(url=nextpage, callback=self.parse,
            #               meta={'item': item, 'brand_link': brand_link, 'restaurant_link': restaurant_link, 'nextpage': nextpage})