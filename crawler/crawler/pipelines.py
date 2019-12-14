# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html
import json
import requests
import logging


logger = logging.getLogger(__name__)


class PostPipeline(object):
    logger = logger.getChild('post')

    def process_item(self, item, spider):
        # item: object or dict
        post_link = item['post_link']

        payload = {'data': json.dumps(item)}
        if payload != "":
            try:
                requests.post(post_link, data=payload)
                self.logger.info(f'PostPipeline {post_link} done !')
            except Exception as err:
                self.logger.error(f'PostPipeline - {err} ?')
        return item
