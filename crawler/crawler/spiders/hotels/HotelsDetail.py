# -*- coding: utf8 -*-
from scrapy.http import Request
import re

from ..common.spiders import DetailSpider


class HotelsDetail(DetailSpider):

    name = "HotelsDetail"
    params = '163,164,165'

    def create_request(self, item):
        yield Request(url=item.link, callback=self.parse, meta={'item': item})

    def parse(self, response):
        item = response.meta.get('item')
        item.link = response.url

        # detail hotel
        item.hotel_source = 'Hotels'
        item.hotel_city_id = {'163': 5, '164': 6, '165': 7}[item.id_web]
        item.hotel_type = 'Khách sạn'
        item.hotel_name = response.xpath('.//div[@class="vcard"]/h1/text()').extract_first()
        hotel_star = response.xpath('.//div[@class="vcard"]/span/text()').extract_first()
        item.hotel_star = hotel_star.split(' ')[0] if hotel_star else 0
        item.hotel_address = response.xpath('.//span[@class="postal-addr"]/text()').extract_first()
        item.hotel_description = response.xpath(".//div[@class='tagline']/b/text()").extract_first()
        item.hotel_image = response.xpath('.//div[@class="canvas widget-carousel-enabled"]//li[@class="image"]/@data-desktop').extract()[:20]
        item.hotel_attribute = response.xpath('.//div[@id="overview-section-4"]//li/text()').extract()

        lat = response.xpath('.//meta[@property="place:location:latitude"]/@content').extract_first()
        lon = response.xpath('.//meta[@property="place:location:longitude"]/@content').extract_first()
        item.hotel_latlng = f'{lat},{lon}'

        # detail room
        item.hotel_price = []
        rooms = response.xpath('.//ul[@class="rooms"]/li')
        for room in rooms:
            name = room.xpath('.//span[@class="room-name"]/text()').extract_first()
            raw_guest = room.xpath('.//span[@class="occupancy-info"]//text()').extract_first()
            guest = re.search(r'\d+', raw_guest).group() if raw_guest else ''

            price=room.xpath('.//*[@class="current-price"]/text()').extract_first().split(' ')[0]
            attrs = []
            raw_attr = ''.join(response.xpath('//ul[@class="rateplan-features"]//text()').extract())
            if 'Bữa sáng cho' in raw_attr:
                attrs.append('Bao gồm bữa sáng')

            item.hotel_price.append(
                dict(
                    name=name,
                    price=price,
                    guest=guest,
                    attribute=attrs,
                    )
            )

        # detail review
        item.hotel_review = []
        reviews = response.xpath(".//div[contains(@class, 'review-card ')]")
        for review in reviews:
            name = review.xpath(".//span[@class='review-card-reviewer']/span[1]/text()").extract_first()
            rating = review.xpath(".//span[@class='rating']/text()").extract_first()
            title = review.xpath(".//div[@class='review-summary']/text()").extract_first()
            content = review.xpath(".//div[@class='review-content']/blockquote/text()").extract_first()

            item.hotel_review.append(
                dict(
                    name=name,
                    rating=rating,
                    title=title,
                    content=content,
                    image=''
                    )
            )

        self.count += 1
        self.logger.info(f"crawl {item.link} done - total {self.count}")
        yield self.post_item(item)