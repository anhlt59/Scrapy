import redis
import time

# HOST = '192.168.1.239'
HOST = '127.0.0.1'
PORT = '6379'
CHANNEL = 'hotel-crawler'

if __name__ == '__main__':
    r = redis.Redis(host=HOST, port=PORT)
    pub = r.pubsub()
    pub.subscribe(CHANNEL)
    while True:
        data = pub.get_message()
        if data:
            message = data['data']
            if message and message != 1:
                print("Message: {}".format(message))
                time.sleep(2)