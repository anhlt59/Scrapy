# -*- coding: utf8 -*-
from scrapy.http import JsonRequest
from scrapy.exceptions import CloseSpider
import json
import arrow
import re

from ..common.utils import obj
from ..common.spiders import CatSpider


class AgodaCat(CatSpider):

    name = "AgodaCat"
    api_url = 'https://www.agoda.com/api/vi-vn/Main/GetSearchResultList'
    api_headers = {
        'Accept': '*/*',
        'Origin': 'https://www.agoda.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',
        'Sec-Fetch-Mode': 'cors',
        'Content-Type': 'application/json;charset=UTF-8',
    }
    api_body = {'AddressName': None,
                'Adults': 1,
                'BankCid': None,
                'BankClpId': None,
                'CheckIn': '2019-10-31T13:59:13.3868278+07:00',
                'CheckOut': '2019-10-31T13:59:13.3868278+07:00',
                'CheckboxType': 0,
                'ChildAges': [],
                'ChildAgesStr': None,
                'Children': 0,
                'Cid': -1,  # cid
                'CityEnglishName': None,
                'CityId': 2758,
                'CityName': None,
                'CountryEnglishName': None,
                'CountryId': 0,
                'CountryName': None,
                'CultureInfo': 'vi-VN',
                'CurrencyCode': None,
                'CurrentDate': '2019-10-22T13:59:13.3868278+07:00',
                'DefaultChildAge': 8,
                'FamilyMode': False,
                'Filters': {'AccomodationType': None,
                            'AffordableCategories': [],
                            'AllGuestCleanlinessRating': None,
                            'AllGuestComfortRating': None,
                            'AllGuestFacilitiesRating': None,
                            'AllGuestLocationRating': None,
                            'AllGuestStaffRating': None,
                            'AllGuestValueRating': None,
                            'Areas': None,
                            'Beachs': None,
                            'Benefits': None,
                            'BrandsAndChains': None,
                            'Cities': None,
                            'Deals': None,
                            'Facilities': None,
                            'HotelName': '',
                            'Landmarks': None,
                            'LocationHighlights': None,
                            'LocationScore': None,
                            'LocationScoreMin': 0,
                            'NumberOfBedrooms': None,
                            'PaymentOptions': None,
                            'PriceRange': {'IsHavePriceFilterQueryParamter': False,
                                           'Max': 0,
                                           'Min': 0},
                            'ProductType': None,
                            'ReviewLocationScores': None,
                            'ReviewScoreMin': 0,
                            'ReviewScores': [],
                            'RoomAmenities': None,
                            'RoomOffers': None,
                            'Size': 0,
                            'StarRating': [],
                            'TopGuestRatedArea': None,
                            'Transportations': None,
                            'TravellerChoiceAward': None},
                'FinalPriceView': 0,
                'FlightSearchCriteria': None,
                'HasFilter': False,
                'HashId': None,
                'IsAllowYesterdaySearch': False,
                'IsApsPeek': False,
                'IsComparisonMode': False,
                'IsCriteriaDatesChanged': False,
                'IsDateless': False,
                'IsEnableAPS': False,
                'IsPackages': False,
                'IsPollDmc': False,
                'IsRetina': False,
                'IsShowMobileAppPrice': False,
                'IsWysiwyp': False,
                'LandingParameters': {'FooterBannerUrl': None,
                                      'HeaderBannerUrl': None,
                                      'LandingCityId': 0,
                                      'SelectedHotelId': 0},
                'Latitude': 0.0,
                'LengthOfStay': 1,
                'Longitude': 0.0,
                'MapType': 0,
                'MaxPollTimes': 0,
                'NewSSRSearchType': 0,
                'NumberOfBedrooms': [],
                'ObjectID': 0,
                'ObjectName': '',
                'PackagesToken': None,
                'PageNumber': 1,
                'PageSize': 45,
                'PlatformID': 1001,
                'PointsMaxProgramId': 0,
                'PollTimes': 0,
                'PreviewRoomFinalPrice': None,
                'ProductType': -1,
                'Radius': 0.0,
                'RateplanIDs': None,
                'RectangleSearchParams': None,
                'ReferrerUrl': None,
                'RequestPriceView': None,
                'RequestedDataStatus': 1,
                'Rooms': 1,
                'SearchType': 1,
                'SelectedColumnTypes': {},
                'SelectedHotelId': 0,
                'ShouldHideSoldOutProperty': False,
                'ShouldShowHomesFirst': False,
                'SortField': 0,
                'SortOrder': 1,
                'Tag': None,
                'Text': '',
                'TotalHotels': 0,
                'TotalHotelsFormatted': '0',
                'TravellerType': -1,
                'UnavailableHotelId': 0,
                'ccallout': False,
                'defdate': False,
                'isAgMse': False
                }
    params = '181,182,183'

    def create_request(self, item):
        link = item.link
        url, headers, body = self.api_url, self.api_headers, self.api_body.copy()

        # update body
        now = arrow.now()
        body.update(
            CheckIn=now.shift(days=1).isoformat(),
            CheckOut=now.shift(days=2).isoformat(),
            CityId=re.search(r'(?<=city=)\d+', link).group(), # ha noi 2758 da nang 16440 ho chi minh 13170
            CurrentDate=now.isoformat()
        )
        yield JsonRequest(url=url, method='POST', headers=headers, data=body, callback=self.parse_api,
                           meta={'item': item, 'form_request': [url, headers, body]})

    def parse_api(self, response):
        item = response.meta.get('item')
        url, headers, body = response.meta.get('form_request')

        # stop if data is empty
        data = obj(json.loads(response.body))
        if not data.ResultList:
            self.logger.info(f"cat link is empty on page {body['PageNumber']} - {response.url}")
            return None

        cat_link = [f'https://www.agoda.com{x.HotelUrl.split("?")[0]}?hotelid={x.HotelID}&latlng={x.Latitude},{x.Longitude}' for x in data.ResultList]
        self.count += len(cat_link)
        self.logger.info(f"got {len(cat_link)} cat link - total {self.count}")

        item.cat_link = cat_link
        yield self.post_item(item)

        # nextpage
        body['PageNumber'] += 1
        yield JsonRequest(url=url, method='POST', headers=headers, data=body, callback=self.parse_api,
                      meta={'item': item, 'form_request': [url, headers, body]})