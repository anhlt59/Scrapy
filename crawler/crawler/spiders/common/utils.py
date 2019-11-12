# This package will contain the spiders of your Scrapy project
#
# Please refer to the documentation for information on how to create and manage
# your spiders.
# -*- coding: utf-8 -*-
import requests
import json
import logging
import time
import os
import scrapy
from scrapy.selector import Selector
from scrapy.utils.log import configure_logging


logger = logging.getLogger('utils')
req_logger = logger.getChild('request')
law_logger = logger.getChild('law')



def config_logging():
    configure_logging(install_root_handler=False,)
    logging.config.fileConfig(
        os.path.join(os.path.dirname(__file__), '..', '..', '..', 'logging.ini'),
        disable_existing_loggers=False,
    )


def request_url(url='', method='get', retries=3, **kwargs):
    """ Request url, if fail retry max retries time.""" 
    try:
        response = eval(f'requests.{method}(url, **kwargs)')

        req_logger.info(f'requests - {url} - status code {response.status_code}')
        datajson = response.json() if response.status_code == 200 else None
    except Exception as err:

        if retries:
            return request_url(url, method, retries - 1, **kwargs)

        datajson = None
        req_logger.error(f'request {url} - ERROR - {err}')

    return datajson


def set_law(item, arr_law, selector):
    """ item must dict or scrapy items
        arr_law get from api
        selector: html response or selector."""
    for key, law in arr_law.items():
        if not int(law['array']):
            try:
                if int(law['href']) == 0 and int(law['img']) == 0 and int(law['text']) == 0\
                        and int(law['content_text']) == 0 and law['other'] == "":
                    item[key] = law['value']
                elif int(law['img']):
                    item[key] = selector.css(f"{law['value']}::attr(src)").extract_first()
                elif int(law['text']):
                    item[key] = selector.css(f"{law['value']}::text").extract_first()
                elif int(law['href']):
                    item[key] = selector.css(f"{law['value']}::attr(href)").extract_first()
                elif int(law['content_text']):
                    item[key] = selector.css(law['value']).extract_first()
                elif law['other']:
                    item[key] = selector.css(law['value']).re_first(r'url\(([^\)]+)')
            except Exception as err:
                law_logger.error(err)
                item[key] = None

        elif int(law['array']):
            if int(law['img']):
                item[key] = selector.css(f"{law['value']}::attr(src)").extract()
            elif int(law['text']):
                item[key] = selector.css(f"{law['value']}::text").extract()
            elif int(law['href']):
                item[key] = selector.css(f"{law['value']}::attr(href)").extract()
            elif int(law['content_text']):
                item[key] = selector.css(law['value']).extract()
            elif law['other']:
                item[key] = selector.css(law['value']).re(r'url\(([^\)]+)')

    return item


def cookie_to_har(cookie):
    """
    Convert a Cookie instance to a dict in HAR cookie format.
    """
    c = {
        'name': cookie.name,
        'value': cookie.value,
        'secure': cookie.secure,
    }
    if cookie.path_specified:
        c['path'] = cookie.path

    if cookie.domain_specified:
        c['domain'] = cookie.domain

    if cookie.expires:
        tm = time.gmtime(cookie.expires)
        c['expires'] = time.strftime("%Y-%m-%dT%H:%M:%SZ", tm)

    http_only = cookie.get_nonstandard_attr('HttpOnly')
    if http_only is not None:
        c['httpOnly'] = bool(http_only)

    if cookie.comment:
        c['comment'] = cookie.comment

    return c


class obj(dict):

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __getattr__(self, attr):
        if attr in self.keys():
            data = self.__getitem__(attr)

            if type(data) is dict:
                object_converted =  obj(data)
            elif type(data) is list:
                object_converted =  array_obj(data)
            else:
                return data

            self.__setitem__(attr, object_converted)
            return object_converted
        else:
            return obj(dict())


class array_obj(list):

    def __getitem__(self, attr):
        data = super().__getitem__(attr)

        if type(data) is dict:
            object_converted =  obj(data)
        elif type(data) is list:
            object_converted =  array_obj(data)
        else:
            return data

        self.__setitem__(attr, object_converted)
        return object_converted

    def __iter__(self, *args, **kwargs):
        data = super().__iter__(*args, **kwargs)

        for d in data:
            if type(d) is list:
                yield array_obj(d)

            elif type(d) is dict:
                yield obj(d)

            else:
                yield d
