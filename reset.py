import json
import requests 


LIST_PROJECT_ID = [117,190,191,181,182,183,145,148,147,163,164,165,203,204,205,206,207,208,209,210,211,215,216,217,115,161,162,197,198,199,212,213,214,194,195,196]

for i in LIST_PROJECT_ID:
    r = requests.get("http://crawler.wemarry.vn/reset/%s" % i)
