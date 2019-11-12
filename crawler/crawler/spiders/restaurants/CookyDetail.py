# -*- coding: utf8 -*-
from scrapy.http import Request
from scrapy.exceptions import CloseSpider
import json
import arrow
import re

from ..common.utils import obj
from ..common.spiders import DetailSpider


class CookyDetail(DetailSpider):

    name = "CookyDetail"
    params = '169'

    def parse(self, response):
        item = response.meta.get('item')
        retries = response.meta.get('retries', 3)

        item.hotel_latlng = '0.0'
        item.detail_list_img = response.css('div.step-photos.col2 > a.cooky-photo > img::attr(src)').extract_first()
        item.detail_auther = response.css('div.recipe-profile.inner > div > div > div > a.author.text-highlight.url.cooky-user-link.p-name.u-url::text').extract_first()
        item.detail_level = response.css('div.recipe-header-detail > div.recipe-header-stats > ul > li > div > span > b.stats-count::text').extract_first()
        item.detail_time = response.css('div > span.duration > span.duration-block > b > time::text').extract_first()
        item.detail_title = response.css('div.recipe-header-info > div.recipe-header-detail > div.recipe-headline > h1::text').extract_first()
        item.detail_image = response.css('.recipe-header-photo .photo.img-responsive::attr(src)').extract_first()
        item.detail_description = response.css('div.rm > div.recipe-info > div.summary.p-summary > p::text').extract_first()
        item.detail_type_id = 1

        detail_content = response.css('.recipe-direction-box .panel-group.description').extract_first()
        if detail_content:
            detail_list_img = re.findall(r'(?<=data-src=")[^\s"]+', detail_content)
            
            for src in detail_list_img:
                detail_content = detail_content.replace('https://www.cooky.vn/imgs/blank-img/400x400.jpg', src, 1)

            item.detail_content = detail_content
            item.detail_list_img = detail_list_img
            self.count += 1
            self.logger.info(f"crawl {item.link} done - total {self.count}")
            yield self.post_item(item)
        else:
            if retries:
                yield Request(url=response.url, callback=self.parse, meta={'item': item, 'retries': retries-1})

            
