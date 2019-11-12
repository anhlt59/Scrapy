# -*- coding: utf8 -*-
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from scrapy import spiderloader
import logging
import argparse
import sys
import json
# import redis
import asyncio
import aiohttp
from aiohttp import ClientSession


logging.basicConfig(
    format="%(asctime)s %(levelname)-4.4s %(name)s: %(message)s", #"%(asctime)s %(levelname)s: %(message)s",
    level=logging.DEBUG,
    datefmt="%d-%m-%Y %H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger("run")

parser = argparse.ArgumentParser()
parser.add_argument('--spider', dest='spider', type=str, 
                    help='"cat" - run Category, "detail" - run Detail, "SpiderName,..." - run spiders with name, "all" - run all spider')
parser.add_argument('--transport', dest='transport', type=str,
                    help='"all" - run transport all spider, "SpiderName,..." - run transport with specific name')
args = parser.parse_args()
# parser.print_help()


def crawl(settings, logger):
    crawl_logger = logger.getChild('crawl')

    # get all spider_name
    spider_loader = spiderloader.SpiderLoader.from_settings(settings)
    total_spider_name_list = spider_loader.list()

    # filter by argrument passed
    if args.spider == 'all':
        filted_spider_name_list = total_spider_name_list
    elif args.spider in ['cat', 'detail']:
        filted_spider_name_list = [name for name in total_spider_name_list if args.spider.lower() in name.lower()]
    else:
        filted_spider_name_list = [name for name in total_spider_name_list if name.lower() in args.spider.lower().split(',')]

    # get spider list
    spiders = [spider_loader.load(name) for name in filted_spider_name_list]

    # run spider
    process = CrawlerProcess()
    for spider in spiders:
        process.crawl(spider)

    try:
        process.start()
    # except ReactorNotRestartable as e:
    #     crawl_logger.error
    except Exception as e:
        crawl_logger.critical(repr(e))
    finally:
        process.stop()


def transport(settings, logger):
    # HOST = '192.168.1.239'
    # PORT = '6379'
    # CHANNEL = 'hotel-crawler'
    # r = redis.Redis(host=HOST, port=PORT)

    async def progress_transport(params, session, logger):
        logger.debug(f'Start transporting {params}')

        url = f'http://crawler.wemarry.vn/api/get-data-multi'
        success_url = "http://crawler.wemarry.vn/cron_detail"
        fail_url = "http://crawler.wemarry.vn/cron_detail_die"
        params = {'id': params}

        # get data
        resp = await session.get(url=url, params=params, ssl=False)
        # raise exception if status_code != 200
        resp.raise_for_status()

        raw_data = await resp.read()
        data = json.loads(raw_data)
        logger.debug(f'Got {len(data)} data')

        for item in data:
            post_link = item['post_link']
            payload = {
                'data' : json.dumps(item)
            }
            # item = json.dumps(item)
            # pub = r.publish(
            #     channel=CHANNEL,
            #     message=item
            # )

            #publish redis ms queue

            try:
                response = await session.post(url=post_link, data=payload, params=params, ssl=False)
                resp.raise_for_status()
                await asyncio.sleep(2)

                await session.post(url=success_url, data=payload, params=params, ssl=False)
                logger.info(f"Post {item['link']} - done")

            except Exception as err:
                await session.request(method='POST',url=fail_url, data=payload, params=params, ssl=False)
                logger.info(f"Post {item['post_link']} - {err}")

    async def transport_main(params_list, logger):
        async with ClientSession() as session:
            tasks = [progress_transport(params, session, logger) for params in params_list]
            await asyncio.gather(*tasks)
    
    transport_logger = logger.getChild('transport')

    # get all spider_name 
    spider_loader = spiderloader.SpiderLoader.from_settings(settings)
    total_spider_name_list = spider_loader.list()

    # filter detail spider
    filted_spider_name_list = [name for name in total_spider_name_list if 'detail' in name.lower()]
    # filter by argrument passed
    if args.transport == 'all':
        pass
    else:
        filted_spider_name_list = [name for name in total_spider_name_list if name.lower() in args.transport.lower()]

    # get spider list
    spiders = [spider_loader.load(name) for name in filted_spider_name_list]

    # load params from spider
    params_list = [spider.params for spider in spiders if spider.params]
    # run transport_main
    # asyncio.run(transport_main(params_list, transport_logger))
    loop = asyncio.get_event_loop()
    loop.run_until_complete(transport_main(params_list, transport_logger))
    loop.close()
    

if __name__ == '__main__':
    settings = get_project_settings()

    # run
    if args.spider:
        crawl(settings, logger)
    elif args.transport:
        transport(settings, logger)
    else:
        logger.info('Unknow argument passed')
        sys.exit()
