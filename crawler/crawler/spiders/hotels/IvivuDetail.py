# -*- coding: utf8 -*-
import re

from ..common.spiders import SplashDetail


class IvivuDetail(SplashDetail):

    name = "IvivuDetail"
    params = '203,204,205'
    script = """
    function main(splash, args)
      splash.private_mode_enabled = false
      assert(splash:go(args.url))
      assert(splash:wait(4))
      return splash:html()
    end
    """

    def parse(self, response):
        item = response.meta.get('item')
        hotel_id = re.search(r'\d+$', item.link).group()

        # extract data
        item.hotel_city_id = {'203': 5, '204': 6, '205': 7}[item.id_web]
        item.hotel_source = 'Ivivu'
        item.hotel_type = 'Khách sạn'
        item.hotel_name = response.xpath('.//*[@id="hotel-name-detail"]/text()').extract_first()
        item.hotel_image = response.xpath(".//div[@u='thumbnavigator']//img/@src").extract()[:20]
        item.hotel_attribute = response.xpath(".//span[@class='icon-circle']/text()").extract()
        item.hotel_description = response.xpath(".//section[contains(@class, 'htdt-description')]/div/p/text()").extract()

        hotel_address = response.xpath('.//p[@class="address description htldtl-address"]/text()').extract()
        item.hotel_address = hotel_address[1] if hotel_address else ''

        hotel_star = response.xpath(".//i[@class='fa fa-star star']").extract()
        item.hotel_star = len(hotel_star) if hotel_star else ''

        # room detail
        item.hotel_price = []
        rooms = response.xpath(".//tr[contains(@class, 'room-item')]")
        for room in rooms:
            name = room.xpath(".//p[contains(@class, 'room__title')]/text()").extract_first()
            if name and name not in [x.name for x in item.hotel_price ]:
                raw_price = room.xpath(".//p[contains(@class, 'rate__price')]/text()").extract()
                price = raw_price[1] if len(raw_price) > 1 else raw_price[0]

                guest = room.xpath(".//p[contains(@class, 'capacity')]/b/text()").extract_first()

                attribute = []
                raw_attr = ''.join(room.xpath(".//td[@class='condition']//p/text()").extract())
                if 'Gồm ăn sáng' in raw_attr:
                    attribute.append('Bao gồm ăn sáng')
                if 'Hủy miễn phí trước' in raw_attr:
                    attribute.append('Miễn phí Đổi/Hủy')

                item.hotel_price.append(
                    dict(
                        name=name,
                        price=price,
                        attribute=attribute,
                        guest=guest
                    )
                )


        # review
        item.hotel_review = []
        reviews = response.xpath('.//*[@name="sortableReviewPair"]')
        for review in reviews:
            name = review.xpath('.//div[@class="username"]/text()').extract_first()
            raw_rating = review.xpath('.//span[@class="rating"]/span/@alt').extract_first()
            rating = raw_rating[0] if raw_rating else ''
            title = review.xpath('.//div[@class="reviewTitle"]/text()').extract_first()
            content = review.xpath('.//div[@class="reviewBody"]/text()').extract_first()

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