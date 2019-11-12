# -*- coding: utf8 -*-
from scrapy.http import Request
from ..common.spiders import CatSpider


class TripadvisorRestaurantCat(CatSpider):

    name = "TripadvisorRestaurantCat"
    params = '113,188,189'

    def create_request(self, item):
        yield Request(url=item.link, callback=self.parse, meta={'item': item})

    def parse(self, response):
        item = response.meta.get('item')
        item.link = response.url

        # extract cat link
        raw_cat_link = response.css("div[class*=restaurants-list-ListCell__photoWrapper] a::attr(href)").extract()
        cat_link = [response.urljoin(url) for url in  raw_cat_link]

        # stop if data is empty
        if not cat_link:
            self.logger.info(f"cat link is empty url {response.url}")
            return None

        self.count += len(cat_link)
        self.logger.info(f"got {len(cat_link)} cat link - total {self.count}")

        item.cat_link = cat_link
        yield self.post_item(item)

        # nextpage
        nextpage_url = response.css('a.next::attr(href)').extract_first()
        if nextpage_url:
            nextpage_abs_url = response.urljoin(nextpage_url)
            yield Request(url=nextpage_abs_url, callback=self.parse, meta={'item': item})
