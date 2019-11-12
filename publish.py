import redis
import time

# HOST = '192.168.1.239'
HOST = '127.0.0.1'
PORT = '6379'
CHANNEL = 'hotel-crawler'

if __name__ == '__main__':
    r = redis.Redis(host=HOST, port=PORT)
    for i in range(10):
        pub = r.publish(
            channel=CHANNEL,
            message=str(i)
        )