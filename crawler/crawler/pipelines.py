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
        post_link = item['post_link'] #'http://192.168.1.142:82/api/v1/crawl/a?log=1'#

        payload = {'data': json.dumps(item)}
        if payload != "":
            try:
                requests.post(post_link, data=payload)
                self.logger.info(f'PostPipeline {post_link} done !')
            except Exception as err:
                self.logger.error(f'PostPipeline - {err} ?')
        return item


# class MongoDBPipeline:
#     logger = logger.getChild('mongo')

#     def __init__(self, mongo_uri, mongo_db, mongo_collection):
#         self.mongo_uri = mongo_uri
#         self.mongo_db = mongo_db
#         self.mongo_collection = mongo_collection

#     @classmethod
#     def from_crawler(cls, crawler):
#         # if define settings in crawler
#         return cls(
#             mongo_uri=crawler.settings.get('MONGO_URI'),
#             mongo_db=crawler.settings.get('MONGODB_DB'),
#             # mongo_collection=crawler.settings.get('MONGODB_COLLECTION')
#             # mongo_collection=crawler.spider.name
#         )

#     def open_spider(self, spider):
#         self.connection = pymongo.MongoClient(self.mongo_uri)
#         self.db = self.connection[self.mongo_db]
#         self.collection = self.db[self.mongo_collection]
#         self.logger.info(f"{spider.name} - Connect to MongoDB database!")

#     def close_spider(self, spider):
#         self.connection.close()
#         self.logger.info(f"{spider.name} - Close connect!")

#     def process_item(self, item, spider):
#         # item: object or dict
#         valid = True
#         # for data in item:
#         #     if not data:
#         #         valid = False
#         #         raise DropItem("Missing {0}!".format(data))
#         # if valid:
#         self.collection.insert_one(dict(item))
#         self.logger.info(f"Added to {self.mongo_collection}!")
#         return item


# class MySQLPipeline:

#     def __init__(self, mysql_host, mysql_db, mysql_user, mysql_password):
#         self.db = mysql_db
#         self.db_args = {
#             'host': mysql_host,
#             'db': mysql_db,
#             'user': mysql_user,
#             'passwd': mysql_password,
#             'charset': 'utf8',
#             'cursorclass': pymysql.cursors.DictCursor,
#         }

#     @classmethod
#     def from_crawler(cls, crawler):
#         # if define settings in crawler
#         return cls(
#             mysql_host=crawler.settings.get('MYSQL_HOST'),
#             mysql_db=crawler.settings.get('MYSQL_DB'),
#             mysql_user=crawler.settings.get('MYSQL_USER'),
#             mysql_password=crawler.settings.get('MYSQL_PASSWORD'),
#         )

#     def open_spider(self, spider):
#         self.connection = pymysql.connect('MySQLdb', **self.db_args)
#         logger.info(f"{spider.name} - Connect to {self.db}!")

#     def close_spider(self, spider):
#         self.connection.close()
#         logger.info(f"{spider.name} - Close connect to {self.db}!")

#     def process_item(self, item, spider):
#         # item: object or dict
#         colums = ', '.join([f"`{x}`" for x in item.keys()])
#         values = ', '.join([['%s'] * len(item)])

#         # Create a new record
#         with self.connection.cursor() as cursor:
#             query = f"INSERT INTO `{self.db}` ({colums}) VALUES ({values})"

#             try:
#                 # Execute the SQL command
#                 cursor.execute(query, item.values())
#                 # Commit your changes in the database
#                 self.connection.commit()
#                 logger.info(f"Added {dict(item)} to {self.db}!")
#             except Exception as err:
#                 # Rollback in case there is any error
#                 self.connection.rollback()
#                 logger.error(f"Added {dict(item)} to {self.db} - {err}!")
#         return item
