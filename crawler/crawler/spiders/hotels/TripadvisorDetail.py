# -*- coding: utf8 -*-
from ..common.spiders import SplashDetail, DetailSpider
from scrapy_splash import SplashRequest
from scrapy.http import Request

import re
from pprint import pprint


class TripadvisorDetail(SplashDetail):

    name = "TripadvisorDetail"
    params = '115,161,162'
    script = """
    function main(splash, args)
      splash.private_mode_enabled = false
      assert(splash:go(args.url))
      assert(splash:wait(3))
      return splash:html()
    end
    """

    def parse(self, response):
        item = response.meta.get('item')
        hotel_reg = re.search(r'-d(\d+)-', item.link)
        if hotel_reg:
            hotel_id = hotel_reg.group(1)
        else:
            return None

        item.link = response.url
        # city id - ha noi 1, da nang 2, ho chi minh 3
        item.hotel_city_id = {'115': 5, '162': 6, '161': 7}[item.id_web]

        # extract data
        item.hotel_type = 'Khách sạn'
        item.hotel_name = response.css("#HEADING::text").extract_first()
        hotel_star = response.css("span[class*='ui_bubble_rating bubble']::attr(class)").extract_first()
        item.hotel_star = hotel_star[-2] if hotel_star else ''
        item.hotel_address = response.css("span[class*='public-business-listing-ContactInfo__ui_link--1_7Zp']::text").extract_first()
        item.description = response.xpath(".//div[contains(@class, 'Description__description')]/div/text()").extract_first()
        item.hotel_attribute = response.css("div.hotels-hr-about-amenities-AmenityGroup__amenitiesList--3MdFn div[class*='hotels-hr-about-amenities-Amenity']::text").extract()
        item.hotel_price = ''
        
        hotel_image = response.xpath('.//div[contains(@class,"hotels-media-album-parts-Mediastrip")]/div[contains(@class,"media-image-ResponsiveImage")]/@style|.//li[contains(@class,"hotels-media-album-parts")]/div[contains(@class,"media-image-ResponsiveImage")]/@style').extract()
        item.hotel_image = [re.search(r'https:.+jpg', tag).group() for tag in hotel_image if 'http' in tag][:20]

        item.hotel_review = []
        reviews = response.xpath('.//div[contains(@class,"hotels-community-tab-common-Card")]')
        for review in reviews:
            name = review.xpath('.//a[contains(@class,"ui_header_link social-member-event-MemberEventOnObjectBlock")]/text()').extract_first()
            title = review.xpath('.//a[contains(@class,"hotels-review-list-parts-ReviewTitle")]/span//text()').extract_first()
            raw_rating = review.xpath('.//div[@data-test-target="review-rating"]/span/@class').extract_first()
            rating = raw_rating[-2] if raw_rating else 0
            content = review.xpath('.//q[contains(@class,"hotels-review-list-parts-ExpandableReview")]/span//text()').extract_first()
            image = review.xpath('.//a[contains(@class,"styleguide-avatar-Avatar")]/img/@src').extract()
            item.hotel_review.append(
                dict(
                    name=name,
                    title=title,
                    rating=rating,
                    content=content,
                    image=image
                )
            )
        self.count += 1
        self.logger.info(f"crawl {item.link} done - total {self.count}")
        yield self.post_item(item)
