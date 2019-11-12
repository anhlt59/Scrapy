import argparse
import json
from pprint import pprint
from model import Hotel, Session, HotelMapping
from elasticsearch import Elasticsearch, exceptions

HOST = {"host": "192.168.1.239", "port": 9200}
es = Elasticsearch([HOST])


LIST_CHARACTERS = ['/', '-', '(', ')', '!', '"']


def make_beautiful_text(text):
    for i in LIST_CHARACTERS:
        text = text.replace(i, ' ')

    text_beautiful = " ".join(text.split())
    return text_beautiful


def search(lat, lon, name):
    name =make_beautiful_text(name)
    list_of_word = name.strip().split(' ')
    query = ''
    for e in list_of_word:
        list_of_word[list_of_word.index(e)] = '(%s)' % e
    query = ' AND '.join(list_of_word)

    body = {
        "query": {
            "bool": {
                "must": {
                    "geo_distance": {
                        "distance": "1km",
                        "location": {
                            "lat": lat,
                            "lon": lon
                        }
                    }
                },
                "filter": {

                    "query_string": {
                        "default_field": "hot_name",
                        "query": query
                    }
                }
            }
        }
    }

    result = es.search(index="hotels_booking", body=body, size=10)

    hits = result['hits']['hits']

    if hits:
        return hits[0]
    else:
        return None