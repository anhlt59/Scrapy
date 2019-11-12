# -*- coding: utf8 -*-
import re

from ..common.spiders import SplashDetail

class BookingDetail(SplashDetail):

    name = "BookingDetail"
    params = '145,148,147'
    script = """
    function main(splash, args)
      assert(splash:go(args.url))
      assert(splash:wait(3))
      return splash:html()
    end
    """

    def parse(self, response):
        item = response.meta.get('item')
        item.link = response.url
        
        # detail hotel
        item.hotel_source = 'Booking'
        item.hotel_search_image = '/images'
        item.hotel_city_id = {'145': 5, '147': 6, '148': 7}[item.id_web]
        item.hotel_type = response.xpath('.//*[@id="hp_hotel_name"]/span/text()').extract_first()
        item.hotel_name = response.xpath('.//*[@id="hp_hotel_name"]/text()[2]').extract_first().strip('\n')
        item.hotel_address = response.xpath('.//span[contains(@class, "hp_address_subtitle")]/text()').extract_first().strip('\n')
        hotel_image = response.xpath('.//div[@id="photos_distinct"]//img/@src | .//div[@id="photos_distinct"]//a/@href | .//div[@id="hotel_main_content"]//a/@href').extract()[:20]
        item.hotel_image = [x.replace('1024x768', '1280x900') for x in hotel_image]

        star = response.xpath('.//span[@class="hp__hotel_ratings__stars nowrap"]/i/@title').extract_first() 
        item.hotel_star = int(re.search(r'\d', star).group()) if star else 0

        item.hotel_description = '\n'.join(response.xpath(".//*[@id='property_description_content']/p/text()").extract())
        item.hotel_latlng = response.xpath('.//a[@id="hotel_address"]/@data-atlas-latlng').extract_first()

        item.hotel_attribute = []
        attributie = response.xpath('.//div[@class="facilitiesChecklist"]//li')
        for attr in attributie:
            item.hotel_attribute.append(' '.join(x.replace('\n', '') for x in attr.xpath('.//text()').extract() if x != '\n'))

        # price
        item.hotel_price = []
        rooms = response.xpath(" .//tbody/tr[@data-et-view] | .//tbody/tr[contains(@class, 'hprt-table')]")
        for room in rooms:
            # ten phong
            raw_name = ''.join(room.xpath(".//a[contains(@class, 'roomtype-link')]//text()").extract())
            reg_name = re.search(r'[^\n]+', raw_name)
            name = reg_name.group().strip() if reg_name else ''

            raw_guest = room.xpath(".//div[contains(@class, 'occupancy')]/@data-title|.//div[contains(@class, 'occupancy')]/span[@class='bui-u-sr-only']/text()").extract_first()
            # so nguoi
            guest = re.search(r'\d+', raw_guest).group() if raw_guest else 0

            # gia phong
            raw_price = room.xpath(".//div[contains(@class, 'table__price__number')]/text()|.//div[contains(@class, 'bui-price-display__value')]/text()").extract_first()
            price = int(re.search(r'(?<=VND\s)[\d\.]+', raw_price).group().replace('.', ''))if raw_price else 0

            attrs = []
            raw_attr = ' '.join(room.xpath(".//ul[contains(@class, 'hprt-conditions')]//text()").extract())
            if 'KHÔNG CẦN TRẢ TRƯỚC' in raw_attr:
                attrs.append('Thanh toán tại nơi ở')
            if 'Bao bữa sáng' in raw_attr:
                attrs.append('Bao gồm bữa sáng')
            if 'Miễn Phí hủy phòng' in raw_attr:
                attrs.append('Miễn phí Đổi/Hủy')

            item.hotel_price.append(
                dict(
                    name=name,
                    guest=guest,
                    price=price,
                    attribute=attrs
                )
            )
        # review hotel
        item.hotel_review = []
        reviews = response.xpath(".//ul[@class='review_list hp_recent_property_reviews_container']/li")
        for review in reviews:
            name = review.xpath(".//p[@class='reviewer_name']/text()").extract_first().strip('\n')
            title = review.xpath(".//div[@class='review_item_header_content_container']/div/text()").extract_first().strip('\n')
            if not title:
                title = 'Review'
            rating = int(float(review.xpath(".//span[@class='review-score-badge']/text()").extract_first().strip('\n').replace(',', '.'))/2)
            raw_content = review.xpath(".//p[@class='review_pos ']//text()").extract()
            content = raw_content[-1] if raw_content else ''

            item.hotel_review.append(
                dict(
                    name=name,
                    title=title,
                    rating=rating,
                    content=content,
                    image=''
                )
            )
        self.count += 1
        self.logger.info(f"crawl {item.link} done - total {self.count}")
        yield self.post_item(item)
