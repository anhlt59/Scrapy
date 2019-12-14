# -*- coding: utf-8 -*-

# Scrapy settings for crawler project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://doc.scrapy.org/en/latest/topics/settings.html
#     https://doc.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://doc.scrapy.org/en/latest/topics/spider-middleware.html
import os


ATTRIBUTES = {
    'HOTEL_REVIEW_URL': 'http://192.168.1.250:82/api/v1/crawl/hotel/general',
    'RES_REVIEW_URL': 'http://192.168.1.135:9004/nha-hang/post_restaurant/detail',#'http://ziviu.com/nha-hang/post_restaurant/detail'
}

BOT_NAME = 'crawler'

SPIDER_MODULES = ['crawler.spiders']
NEWSPIDER_MODULE = 'crawler.spiders'

# # runSpider.py
# RUNSPIDER_URL = 'http://crawler.wemarry.vn/api/get-{spider_name}-multi?id={spider_id}'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# LOG_LEVEL = 'ERROR'
# Configure maximum concurrent requests performed by Scrapy (default: 16)
CONCURRENT_REQUESTS = 4

# Configure a delay for requests for the same website (default: 0)
# See https://doc.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
# DOWNLOAD_DELAY = 3
# The download delay setting will honor only one of:
# CONCURRENT_REQUESTS_PER_DOMAIN = 8
# CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
# COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
# TELNETCONSOLE_ENABLED = False

# Override the default request headers:
# DEFAULT_REQUEST_HEADERS = {
#   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#   'Accept-Language': 'en',
# }
RANDOM_UA_PER_PROXY = True
ROTATING_PROXY_LIST = [
    '42.112.34.27:3427',
    '42.112.34.28:3428',
    '42.112.34.29:3429',
    '42.112.34.30:3430',
    '42.112.34.31:3431',
    '42.112.34.32:3432',
    '42.112.34.33:3433',
    '42.112.34.34:3434',
    '42.112.34.35:3435',
    '42.112.34.36:3436',
    '42.112.34.37:3437',
    '42.112.34.38:3438',
    '42.112.34.12:3412',
    '42.112.34.13:3413',
    '42.112.34.14:3414',
    '42.112.34.15:3415',
    '42.112.34.16:3416',
    '42.112.34.17:3417',
    '42.112.34.18:3418',
    '42.112.34.10:3410',
]
# SPLASH_SETTINGS
SPLASH_URL = 'http://127.0.0.1:8050'
DUPEFILTER_CLASS = 'scrapy_splash.SplashAwareDupeFilter'
HTTPCACHE_STORAGE = 'scrapy_splash.SplashAwareFSCacheStorage'
SPIDER_MIDDLEWARES = {'scrapy_splash.SplashDeduplicateArgsMiddleware': 100}

# SELENIUM_SETTINGS
SELENIUM_DRIVER_NAME = 'chrome'
SELENIUM_DRIVER_EXECUTABLE_PATH = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), 'seleniumdriver', 'chromedriver')
SELENIUM_DRIVER_ARGUMENTS = ['--no-sandbox', '--headless']
# SELENIUM_CHANGE_PROXY   - Boolen (default False)
# SELENIUM_CHANGE_AGENT   - Boolen (default False)
# SELENIUM_LOAD_IMAGE     - Boolen (default False)
# SELENIUM_DISABLE_NOTIFY - Boolen (default True)

ITEM_PIPELINES = {
    # 'crawler.pipelines.PostPipeline': 300,
    # 'crawler.pipelines.MongoDBPipeline': 300,
}

# MONGODB
MONGO_URI = 'mongodb://localhost:27017/'
MONGODB_DB = 'data'
# MONGODB_COLLECTION = 'test'

# Enable or disable spider middlewares
# See https://doc.scrapy.org/en/latest/topics/spider-middleware.html
# SPIDER_MIDDLEWARES = {'scrapy_splash.SplashDeduplicateArgsMiddleware': 100}
# Enable or disable downloader middlewares
# See https://doc.scrapy.org/en/latest/topics/downloader-middleware.html

# Enable or disable extensions
# See https://doc.scrapy.org/en/latest/topics/extensions.html
# EXTENSIONS = {'scrapy.extensions.telnet.TelnetConsole': None,}
# Configure item pipelines
# See https://doc.scrapy.org/en/latest/topics/item-pipeline.html

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://doc.scrapy.org/en/latest/topics/autothrottle.html
AUTOTHROTTLE_ENABLED = True
# The initial download delay
AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
AUTOTHROTTLE_TARGET_CONCURRENCY = 4.0
# Enable showing throttling stats for every response received:
# AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://doc.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
# HTTPCACHE_ENABLED = True
# HTTPCACHE_EXPIRATION_SECS = 0
# HTTPCACHE_DIR = 'httpcache'
# HTTPCACHE_IGNORE_HTTP_CODES = []
# HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'

RETRY_ENABLED = True
RETRY_TIMES = 5
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429]
