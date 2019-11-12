# -*- coding: utf8 -*-
from scrapy.exceptions import CloseSpider
import re

from ..common.spiders import SplashDetail


class VnTripDetail(SplashDetail):

    name = "VnTripDetail"
    params = '194,195,196'
    script = """
    function main(splash, args)
      splash.private_mode_enabled = false
      assert(splash:go(args.url))
      assert(splash:wait(5))
      return splash:html()
    end
    """

    def parse(self, response):
        item = response.meta.get('item')
        hotel_id = item.link.split('/')[-1]

        # extract data
        item.hotel_city_id = {'194': 5, '195': 6, '196': 7}[item.id_web]
        item.hotel_source = 'VnTrip'
        item.hotel_type = 'Khách sạn'
        item.hotel_name = response.xpath('.//div[@class="detail-title"]/h1/text()').extract_first().replace('\n', '').strip()
        item.hotel_address = response.xpath('.//span[@class="address"]/text()').extract_first()

        hotel_star = response.xpath(".//h1//i[@class='number']/text()").extract_first()
        item.hotel_star = re.search(r'\d', hotel_star).group() if hotel_star else None

        item.hotel_description= response.xpath(".//p[@class='full']/text()").extract_first()

        latitude = response.xpath('.//div[@latitude]/@latitude').extract_first()
        longitude = response.xpath('.//div[@latitude]/@longitude').extract_first()
        item.hotel_latlng = f'{latitude},{longitude}'

        image = response.xpath(".//div[@class='detail-slider-fancy hidden-xs']//img/@src").extract()
        item.hotel_image = [x.strip() for x in image if f'hotels/{hotel_id}' in x][:20]

        item.hotel_attribute = response.xpath(".//div[@class='feature-categories']/div[@class='row']//text()").extract()

        # reviews
        item.hotel_review = []
        reviews = response.xpath(".//div[@class='detail-notable-line']")
        for review in reviews:
            name = review.xpath('.//p[@class="user"]/strong//text()').extract_first()
            rating = review.xpath('.//span[@class="notable-mark"]//text()').extract_first()
            title = review.xpath('.//p[@class="comment"]//text()').extract_first()
            positive_comment = review.xpath('.//p[@class="positive"]//text()').extract_first()
            negative_comment = review.xpath('.//p[@class="negative"]//text()').extract_first()
            content = f'{positive_comment}\n{negative_comment}'
            image = None

            item.hotel_review.append(
                dict(
                    name=name,
                    rating=rating,
                    title=title,
                    content=content,
                    image=image
                )
            )

        item.hotel_price = []
        rooms = response.xpath(".//div[@class='room-group']")
        for room in rooms:
            name = room.xpath(".//div[@class='room-group__info']/h2/text()").extract_first()

            raw_guest = ''.join(room.xpath(".//div[@class='room-group__cell room-group_capacity']//p//text()").extract())
            guest = re.search(r'\d', raw_guest).group() if raw_guest else None

            raw_price = room.xpath(".//p[@class='price-number']/text()").extract_first()
            price = re.search(r'[\d\.]+', raw_price).group() if raw_price else None

            attribute = [] 
            raw_attr = ''.join(room.xpath('.//div[@class="list-benefit__item"]//text()').extract())
            if 'Có hoàn hủy' in raw_attr:
                attribute.append('Miễn phí Đổi/Hủy')
            if 'Bao gồm ăn sáng' in raw_attr:
                attribute.append('Bao gồm ăn sáng')
            
            item.hotel_price.append(
                dict(
                    name=name,
                    price=price,
                    attribute=attribute,
                    guest=guest
                )
            )

        self.count += 1
        self.logger.info(f"crawl {item.link} done - total {self.count}")
        yield self.post_item(item)
