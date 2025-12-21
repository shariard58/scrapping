import re
import json
import pprint
import subprocess
import cloudscraper
import warnings
import base64
import requests

from urllib.parse import urlparse

from html import unescape
from zenrows import ZenRowsClient
from fake_useragent import UserAgent
from requests import Request, Session
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from ratelimit import limits, sleep_and_retry

client = ZenRowsClient("fa0f561cee2fa9ba7976f152b852a663fdcd8791")

ua = UserAgent()

# Configuration
DEBUG = False
REQUESTS_PER_MINUTE = 10  # Rate limit

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Console Colors
R = '\033[31m'
G = '\033[32m'
Y = '\033[33m'
B = '\033[34m'
E = '\033[0m'

# Rate-limited fetch function
# @sleep_and_retry
# @limits(calls=REQUESTS_PER_MINUTE, period=60)
def fetchRequest(url):
    try:
        session = requests.Session()
        headers = {"User-Agent": ua.random}
        response = session.get(url, headers=headers, timeout=10)
        response = session.get(url, headers=headers, timeout=10)
        # print(f'{response}')
        session.close()

        return response.text
    except requests.RequestException as e:
        print(f"{R}01. Error fetching {url}: {e}{E}")
        return None
    
def fetchURL(url):
    try:
        headers = {"User-Agent": ua.random}
        request = Request(url, headers=headers)
        response = urlopen(request)
        # print(f'{response}')
        return response.read().decode("utf-8")
    except Exception as e:
        print(f"{R}02. Error fetching {url}: {e}{E}")
        return None
       
def getZenResponse(url, headers=None, isJson=False, isCookies=False, isProxy=False):
    try:
        cookies = None
        if(isCookies):
            response = client.get(url, headers=headers)
            cookies = response.cookies
        params = {"premium_proxy":"true","proxy_country":"us"}
        csheaders = {
            "Referer": "https://www.google.com",
            **(headers or {}),
            **({"Cookies": cookies} if isCookies and cookies else {}),
        }

        response = client.get(url, headers=csheaders, params=params) if isProxy else client.get(url, headers=csheaders)
        
        if(isJson): return [response, response.status_code]
        else: return [response.text, response.status_code]
    except Exception as e:
        print(f"{R}Error fetching {url}: {e}{E}")
        return [None, None]

def postZenResponse(url, data=None, params=None, headers=None):
    try:
        kwargs = {}
        if data is not None:
            kwargs["data"] = data
        if params is not None:
            kwargs["params"] = params
        if headers is not None:
            kwargs["headers"] = headers

        response = client.post(url, **kwargs)
        return [response.text, response.status_code]
    except Exception as e:
        print(f"{R}Error fetching {url}: {e}{E}")
        return [None, None]

def readJson():
    with open('handles.json', 'r') as file:
        data = json.load(file)
    return data

def writeJson(data):
    with open('handles.json', 'w') as file:
        json.dump(data, file, indent=4)

def writeToFile(filename, data):
    with open(filename, 'w',  encoding='utf-8') as file:
        if(data): file.write(data)

def isExists(extDomain, storeDomain, handles):
    if storeDomain in handles:
        if extDomain in handles[storeDomain] and len(handles[storeDomain][extDomain]) > 0:
            return True
    return False

def coupert(handles, storeDomain, query):
    extDomain = 'coupert.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)
    
    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []
        
        url = f'https://www.coupert.com/api/v3/store/search_stores?keyword={storeDomain}'
        try:
            response = requests.get(url, headers=headers)
            jsondata = response.json()

            if('data' in jsondata):
                for item in jsondata['data']:
                    if('Domain' in item):
                        if(item['Domain'] == storeDomain):
                            handle = f'https://www.coupert.com/store/{item["Domain"]}'
                            extHandles[storeDomain][extDomain].append(handle)

        except Exception as e:
            print(f"{R}Error fetching {url}: {e}{E}")
        
        urls = [
            f'https://savings.coupert.com/api/browser/search?wd={storeDomain}',
            f'https://top.coupert.com/api/browser/search?wd={storeDomain}',
            f'https://ca.coupert.com/api/browser/search?wd={storeDomain}',
            f'https://fashion.coupert.com/api/browser/search?wd={storeDomain}'
        ]

        for i, url in enumerate(urls):
            try:
                # response = requests.get(url, headers=headers)
                # jsondata = response.json()
                response, status = postZenResponse(url)
                jsondata = json.loads(response)

                print(f'{Y}Fetching {url}...{E}')
                print(jsondata)

                if('data' in jsondata):
                    for item in jsondata['data']:
                        if('urlname' in item):
                            pathname = item['urlname']
                            if pathname.startswith('/'):
                                pathname = pathname[1:]

                            parsed_url = urlparse(url)
                            host = parsed_url.netloc if parsed_url.netloc else parsed_url.path
                            
                            handle = 'https://'+ host + '/' + pathname
                            extHandles[storeDomain][extDomain].append(handle)

            except Exception as e:
                print(f"{R}Error fetching {url}: {e}{E}")
    writeJson(extHandles)
    return extHandles

def discounttime(handles, storeDomain, query):
    extDomain = 'discountime.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []

        url = f'https://www.discountime.com/system/brand/search'
        try:
            response, status = postZenResponse(url, data=json.dumps({
                "keyWord":storeDomain, "pageNo":1, "pageSize":5
            }))

            jsondata = json.loads(response)

            if('data' in jsondata):
                if 'result' in jsondata['data']:
                    result = jsondata['data']['result']
                    # print(result)
                    for  item in result:
                        print(query['handle'])
                        print(item['aliasName'])
                        if query['handle'] == item['aliasName']:
                            handle = f'https://www.discountime.com/store/{item["aliasName"]}'
                            extHandles[storeDomain][extDomain].append(handle)
                            break

        except Exception as e:
            print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def karmanow(handles, storeDomain, query):
    extDomain = 'karmanow.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []
        return extHandles
        # url = f'https://www.karmanow.com/s?query={storeDomain}'
        # url = f'https://www.karmanow.com/ws/api/my/v1/items?filter[search]=cozyearth.com&page=1&per_page=20&sort_by=created_at&sort_order=desc&include_global=true&include_user=true'
        # print(f'{Y}Fetching {url}...{E}')
        # try:
        #     response, status = getZenResponse(url,
        #         headers={
        #             'Content-Type': 'A'
        #             'Authorization': 'Bearer eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjo2Nzg1NTA5LCJleHAiOjE5MDMyNTcwNDZ9.8n5uxXuKknrguNkZU0oiGChumnZVTjF3_QDDRNCyJGY'
        #         }
        #     )
        #     print(response)
        #     return extHandles
        #     # print(response.text)
        #     jsondata = json.loads(response)
            
        #     # print(jsondata)

        #     if('data' in jsondata):
        #         if 'result' in jsondata['data']:
        #             result = jsondata['data']['result']
        #             # print(result)
        #             for  item in result:
        #                 print(query['handle'])
        #                 print(item['aliasName'])
        #                 if query['handle'] == item['aliasName']:
        #                     handle = f'https://www.discountime.com/store/{item["aliasName"]}'
        #                     extHandles[storeDomain][extDomain].append(handle)
        #                     break

        # except Exception as e:
        #     print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def rakuten(handles, storeDomain, query):
    extDomain = 'rakuten.ca'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    storeHandle = query['handle']
    searchQuery = query['query']

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []

        for i, search in enumerate(searchQuery):
            url = f'https://www.rakuten.ca/srch/suggest?q={search}&rows=10'
            try:
                isFound = False
                response, status = getZenResponse(url)
                jsondata = json.loads(response)

                if('stores' in jsondata):
                    for item in jsondata['stores']:
                        if('urlName' in item):
                            path = item['urlName'].replace('-', '')
                            if(path == storeHandle):
                                handle = f'https://www.rakuten.com/{item["urlName"]}'
                                extHandles[storeDomain][extDomain].append(handle)
                                isFound = True
                                break
                if isFound: break

            except Exception as e:
                print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def hotdeals(handles, storeDomain, query):
    extDomain = 'hotdeals.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []

        url = f'https://beta-api.hotdeals.com/search/get_term_list?keyword={storeDomain}&page_type=home&country_code=US'
        try:
            response, status = getZenResponse(url)
            jsondata = json.loads(response)

            if('data' in jsondata):
                for item in jsondata['data']:
                    if('DomainUrl' in item):
                        if(item['DomainUrl'] == storeDomain):
                            extHandles[storeDomain][extDomain].append(item['reUrl'])
                            break

        except Exception as e:
            print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def slickdeals(handles, storeDomain, query):
    extDomain = 'slickdeals.net'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    storeHandle = query['handle']
    searchQuery = query['query']

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []

        for i, search in enumerate(searchQuery):
            url = f'https://coupons.slickdeals.net/api/search/a1cf309737e64efba2197ca0d5820b5f/{search}'
            try:
                response, status = getZenResponse(url)
                jsondata = json.loads(response)

                for item in jsondata:
                    if('url' in item):
                        refineHandle = item['url'].replace('-', '').replace('/', '')
                        if(refineHandle == storeHandle):
                            extHandles[storeDomain][extDomain].append(f'https://coupons.slickdeals.net/{item["url"]}')
                            break
            except Exception as e:
                print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def capitalone(handles, storeDomain, query):
    extDomain = 'capitaloneshopping.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []

        url = f'https://capitaloneshopping.com/s/{storeDomain}/coupon'
        try:
            response, status = getZenResponse(url)
            # print(response)
            soup = BeautifulSoup(response, 'html.parser')

            elements = soup.select('.main-column .store-title h1.bold.charcoal')
            for element in elements:
                notFoundText = 'undefined Coupon Codes, Promo Codes & Discounts'
                if element.text != notFoundText:
                    handle = f'https://capitaloneshopping.com/s/{storeDomain}/coupon'
                    extHandles[storeDomain][extDomain].append(handle)
                    break

        except Exception as e:
            print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def retailmenot(handles, storeDomain, query):
    extDomain = 'retailmenot.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []

        url = f'https://www.retailmenot.com/view/{storeDomain}'
        try:
            response, status = getZenResponse(url)
            soup = BeautifulSoup(response, 'html.parser')

            elements = soup.select('[data-component-name="top_offers"]')
            if len(elements) > 0:
                extHandles[storeDomain][extDomain].append(url)
            
        except Exception as e:
            print(f"{R}Error fetching {url}: {e}{E}")

    writeJson(extHandles)
    return extHandles

def honey(handles, storeDomain, query):
    extDomain = 'joinhoney.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    storeHandle = query['handle']
    storeQueries = query['query']

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []

        isFound = False

        for i, search in enumerate(storeQueries):
            queryVars = json.dumps({"count": 10, "query": search})

            url = f'https://d.joinhoney.com/v3?operationName=web_autocomplete&variables={queryVars}'
           
            try:
                response, status = getZenResponse(url)
                jsondata = json.loads(response)  if response else {}

                if 'data' in jsondata:
                    data = jsondata['data']
                    if 'autocomplete' in data:
                        autocomplete = data['autocomplete']
                        if 'stores' in autocomplete:
                            results = autocomplete['stores']
                            for item in results:
                                refineHandle1 = item['name'].replace(' ', '').lower()
                                refineHandle2 = item['label'].replace('-', '').lower()

                                if storeHandle in refineHandle1 or storeHandle in refineHandle2:
                                    handle = f'https://www.joinhoney.com/store/{item["label"]}'
                                    extHandles[storeDomain][extDomain].append(handle)
                                    isFound = True
                                    break
                if isFound: break
                
            except Exception as e:
                print(f"{R}Error fetching {url}: {e}{E}")
        
    writeJson(extHandles)
    return extHandles

def rebates(handles, storeDomain, query):
    extDomain = 'rebates.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []

        url = f'https://rebates.com/search-stores'
        
        try:
            response, status = postZenResponse(url, data={ "keyword": storeDomain})
            jsondata = json.loads(response)

            if storeDomain in jsondata:
                extHandles[storeDomain][extDomain].append(f'https://rebates.com/coupons/{storeDomain}')


        except Exception as e:
            print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def coupons(handles, storeDomain, query):
    extDomain = 'coupons.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    storeHandle = query['handle']
    searchQuery = query['query']

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []

        for i, search in enumerate(searchQuery):

            url = f'https://www.coupons.com/api/search/15943717d76a8bf7eb0d5b8ad2ea2e55/{search}'
            
            try:
                response, status = getZenResponse(url)
                jsondata = json.loads(response)

                for item in jsondata:
                    if('url' in item):
                        refineHandle = item['url'].split('/')[-1]
                        if refineHandle in storeDomain:
                            extHandles[storeDomain][extDomain].append(f'https://www.coupons.com/{item["url"]}')
                            break


            except Exception as e:
                print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def dealcatcher(handles, storeDomain, query):
    extDomain = 'dealcatcher.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []
        return extHandles

        url = f'https://www.dealcatcher.com/coupons/{storeDomain}'
        
        try:
            response, status = getZenResponse(url)
            if status == 200:
                extHandles[storeDomain][extDomain].append(url)
            
        except Exception as e:
            print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def dontpayfull(handles, storeDomain, query):
    extDomain = 'dontpayfull.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []
        url = f'https://www.dontpayfull.com/at/{storeDomain}'
        
        try:
            response, status = getZenResponse(url)
            print(status)
            if status == 200:
                extHandles[storeDomain][extDomain].append(url)
            
        except Exception as e:
            print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def couponbirds(handles, storeDomain, query):
    extDomain = 'couponbirds.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []

        # url = f'https://www.couponbirds.com/codes/airestech.com'
        url = f'https://www.couponbirds.com/search/autocomplete?searchCode={storeDomain}'
        # url = f'https://www.couponbirds.com/codes/airestech.com?key=67891871667546'

        try:

            response, status = getZenResponse(url, isCookies=True, isProxy=True)
            if response:
                jsondata = json.loads(response)
                if 'items' in jsondata and len(jsondata['items']) > 0:
                    items = jsondata['items']
                    
                    for item in items:
                        if 'website' in item and storeDomain == item['website']:
                            handle = f'https://www.couponbirds.com/codes/{item["website"]}'
                            extHandles[storeDomain][extDomain].append(handle)
                            break
        except Exception as e:
            print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

# def couponbirds(handles, storeDomain, query):
#     extDomain = 'couponbirds.com'
#     extHandles = handles.copy()
#     hasAlready = isExists(extDomain, storeDomain, handles)

#     if storeDomain not in extHandles: extHandles[storeDomain] = {}
#     if not hasAlready:
#         extHandles[storeDomain][extDomain] = []

#         url = f'https://www.couponbirds.com/codes/{storeDomain}'
        
#         try:

#             response, status = getZenResponse(url)
#             print(response)
            
#         except Exception as e:
#             print(f"{R}Error fetching {url}: {e}{E}")
    
#     writeJson(extHandles)
#     return extHandles

def offers(handles, storeDomain, query, algolia):
    extDomain = 'offers.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    storeHandle = query['handle']
    storeQueries = query['query']

    app_id = algolia[extDomain]['app-id']
    api_key = algolia[extDomain]['api-key']

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []

        isFound = False
        url = f'https://{app_id.lower()}-dsn.algolia.net/1/indexes/*/queries?x-algolia-agent=Algolia%20for%20JavaScript%20(4.24.0)%3B%20Browser'

        for i, search in enumerate(storeQueries):
            try:
                response, status = postZenResponse(url,
                    data=json.dumps({
                        "requests": [{
                            "indexName": "production_companies",
                            "query": search,
                            "params": "hitsPerPage=3"
                        }]
                    }),
                    headers={
                        'X-Algolia-API-Key': api_key,
                        'X-Algolia-Application-Id': app_id,
                        'Content-Type': 'application/json'
                    })
                
                jsondata = json.loads(response)
                
                if 'results' in jsondata:
                    results = jsondata['results']
                    for result in results:
                        if 'hits' in result:
                            hits = result['hits']
                            for hit in hits:
                                if 'url' in hit and storeHandle in hit['url']:
                                    handle = f'https://www.offers.com{hit["url"]}'
                                    extHandles[storeDomain][extDomain].append(handle)
                                    isFound = True
                                    break
                        if isFound: break
                if isFound: break

            except Exception as e:
                print(f"{R}Error fetching {url}: {e}{E}")
                continue


    
    writeJson(extHandles)
    return extHandles

def savings(handles, storeDomain, query):
    extDomain = 'savings.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []
        url = f'https://www.savings.com/coupons/{storeDomain}'
        
        try:
            response, status = getZenResponse(url)
            if status == 200:
                extHandles[storeDomain][extDomain].append(url)
            
        except Exception as e:
            print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def dealspotr(handles, storeDomain, query):
    extDomain = 'dealspotr.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []

        url = f'https://dealspotr.com/ajax/lookup.php?datatype=merchants&term={storeDomain}'
        
        try:
            response, status = getZenResponse(url)
            jsondata = json.loads(response)

            if len(jsondata) > 0:
                for item in jsondata:
                    if 'url' in item and storeDomain in item['url']:
                        handle = f'https://dealspotr.com{item["url"]}'
                        extHandles[storeDomain][extDomain].append(handle)
                        break
            
        except Exception as e:
            print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def promocodes(handles, storeDomain, query):
    extDomain = 'promocodes.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    storeHandle = query['handle']
    storeQueries = query['query']

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []

        for i, search in enumerate(storeQueries):
            url = f'https://www.promocodes.com/api/search'
            try:
                response, status = postZenResponse(url,
                    data=json.dumps({
                        "includeCategories": True,
                        "onlyCashback": False,
                        "q": search
                    }),
                    headers={
                        'Content-Type': 'application/json',
                        'Referer': 'https://www.promocodes.com'
                    }
                )

                jsondata = json.loads(response) if response else {}

                if 'data' in jsondata:
                    data = jsondata['data']
                    if 'merchants' in data:
                        for item in data['merchants']:
                            slug = item['slug']
                            refineHandle = slug.replace('-', '').replace('/', '')
                            if storeHandle in refineHandle:
                                handle = f'https://www.promocodes.com/{slug}-coupons'
                                extHandles[storeDomain][extDomain].append(handle)
                                break
            
            except Exception as e:
                print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def couponchief(handles, storeDomain, query):
    extDomain = 'couponchief.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []

        url = f'https://www.couponchief.com/ajaxsearch/store_search.php'
        
        try:
            response, status = postZenResponse(url,
                data=f'tb_search={storeDomain}',
                headers={'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
            )

            jsondata = json.loads(response) if response else []
            
            for item in jsondata:
                path = item['path']
                label = item['label']

                if label:
                    soup = BeautifulSoup(label, 'html.parser')
                    domain = soup.find('span', class_='storeSearchLabel').text

                    if domain.lower() == storeDomain.lower():
                        path = path.replace("\\", "")
                        handle = f'https://www.couponchief.com{path}'
                        extHandles[storeDomain][extDomain].append(handle)
                        break
            
        except Exception as e:
            print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def goodshop(handles, storeDomain, query):
    extDomain = 'goodshop.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []

        url = f'https://www.goodshop.com/shop/merchants?term={storeDomain}'
        
        try:
            response, status = getZenResponse(url)
            jsondata = json.loads(response) if response else []

            for item in jsondata:
                if storeDomain in item['urlname']:
                    handle = f'https://www.goodshop.com/coupons/{storeDomain}'
                    extHandles[storeDomain][extDomain].append(handle)
                    break

        except Exception as e:
            print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def simplycodes(handles, storeDomain, query):
    extDomain = 'simplycodes.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []

        url = f'https://api.simplycodes.com/v2/merchants/search?query={storeDomain}&isUs=true'
        
        try:
            response, status = getZenResponse(url)
            jsondata = json.loads(response) if response else {}

            if 'merchants' in jsondata:
                for item in jsondata['merchants']:
                    if storeDomain in item['urlSlug'] or storeDomain in item['displayUrl']:
                        handle = f'https://simplycodes.com/store/{item["urlSlug"]}'
                        extHandles[storeDomain][extDomain].append(handle)
                        break

        except Exception as e:
            print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def tenereteam(handles, storeDomain, query):
    extDomain = 'tenereteam.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    storeHandle = query['handle']
    storeQueries = query['query']

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []

        isFound = False
        for i, search in enumerate(storeQueries):
            url = f'https://www.tenereteam.com/v2/store/search?q={search}'
            
            try:
                response, status = getZenResponse(url)
                jsondata = json.loads(response) if response else []

                for item in jsondata:
                    refineHandle1 = item['alias'].replace('-', '').replace('\\', '').lower()
                    refineHandle2 = item['name'].replace(' ', '').lower()
                    if storeHandle in refineHandle1 or storeHandle in refineHandle2:
                        handle = f'https://{item["alias"]}.tenereteam.com/coupons'
                        extHandles[storeDomain][extDomain].append(handle)
                        isFound = True
                        break
                if isFound: break
            except Exception as e:
                print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def couponcause(handles, storeDomain, query):
    extDomain = 'couponcause.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    storeHandle = query['handle']
    storeQueries = query['query']

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []
        isFound = False

        for i, search in enumerate(storeQueries):
            url = f'https://couponcause.com/ajax?merchant={search}'
            
            try:
                response, status = getZenResponse(url)
                jsondata = json.loads(response) if response else {}
                if 'merchants' in jsondata:
                    for item in jsondata['merchants']:
                        refineHandle1 = item['url'].replace('-', '').lower()
                        refineHandle2 = item['name'].replace(' ', '').lower()
                        if storeHandle in refineHandle1 or storeHandle in refineHandle2:
                            handle = f'https://couponcause.com{item["url"]}'
                            extHandles[storeDomain][extDomain].append(handle)
                            isFound = True
                            break
                
                if isFound: break

            except Exception as e:
                print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def goodsearch(handles, storeDomain, query):
    extDomain = 'goodsearch.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []
        url = f'https://www.goodsearch.com/coupons/{storeDomain}'
        
        try:
            response, status = getZenResponse(url)
            if status == 200:
                extHandles[storeDomain][extDomain].append(url)
            
        except Exception as e:
            print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def valuecom(handles, storeDomain, query):
    extDomain = 'valuecom.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    storeHandle = query['handle']
    storeQueries = query['query']

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []
        isFound = False

        for i, search in enumerate(storeQueries):
            url = f'https://www.valuecom.com/api/search?wd={search}'
            
            try:
                response, status = postZenResponse(url)
                jsondata = json.loads(response) if response else {}
                
                if 'data' in jsondata:
                    for item in jsondata['data']:
                        if storeDomain in item['domain']:
                            handle = item['urlname']
                            extHandles[storeDomain][extDomain].append(handle)
                            isFound = True
                            break
                
                if isFound: break

            except Exception as e:
                print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def lovecoupons(handles, storeDomain, query):
    extDomain = 'lovecoupons.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    storeHandle = query['handle']
    storeQueries = query['query']

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []
        isFound = False

        for i, search in enumerate(storeQueries):
            url = f'https://www.lovecoupons.com/search/term?q={search}'
            
            try:
                response, status = getZenResponse(url)
                
                if response is not None:
                    soup = BeautifulSoup(response, 'html.parser')
                    elements = soup.select('ul li a')
                    for element in elements:
                        href = element.get('href')
                        refineHandle = href.replace('-', '').replace('/', '')
                        if storeHandle in refineHandle:
                            handle = f'https://www.lovecoupons.com{href}'
                            extHandles[storeDomain][extDomain].append(handle)
                            isFound = True
                            break
                
                if isFound: break

            except Exception as e:
                print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def knoji(handles, storeDomain, query):
    extDomain = 'knoji.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    storeHandle = query['handle']
    storeQueries = query['query']

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []
        isFound = False

        for i, search in enumerate(storeQueries):
            url = f'https://knoji.com/lookup-jump/all/?term={search}'
            
            try:
                response, status = getZenResponse(url)
                jsondata = json.loads(response) if response else []
                
                for item in jsondata:
                    refineHandle1 = item['label'].replace('-', '').lower()
                    refineHandle2 = item['url'].replace('-', '').lower()
                    if storeHandle in refineHandle1 or storeHandle in refineHandle2:
                        extHandles[storeDomain][extDomain].append(item['url'])
                        isFound = True
                        break
                
                if isFound: break

            except Exception as e:
                print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def swagbucks(handles, storeDomain, query):
    extDomain = 'swagbucks.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    storeHandle = query['handle']
    storeQueries = query['query']

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []
        isFound = False

        for i, search in enumerate(storeQueries):
            url = f'https://www.swagbucks.com/?cmd=sh-search-autocomplete&term={search}'
            
            try:
                response, status = postZenResponse(url)
                jsondata = json.loads(response) if response else {}
                
                if 'data' in jsondata:
                    for item in jsondata['data']:
                        if item['category'] == 'Stores':
                            refineHandle1 = item['name'].replace(' ', '').lower()
                            refineHandle2 = item['url'].replace('-', '').lower()
                            if storeHandle in refineHandle1 or storeHandle in refineHandle2:
                                handle = item['url'].split('?')[0]
                                extHandles[storeDomain][extDomain].append(handle)
                                isFound = True
                                break
                
                if isFound: break

            except Exception as e:
                print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def joinsmarty(handles, storeDomain, query):
    extDomain = 'joinsmarty.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    storeHandle = query['handle']
    storeQueries = query['query']

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []
        isFound = False
        return extHandles

        for i, search in enumerate(storeQueries):
            url = f'https://www.joinsmarty.com/api/search?q=Cozy'
            
            try:
                response, status = postZenResponse(url,
                    headers={
                        'Content-Type': 'application/json',
                        'Referer': 'https://www.joinsmarty.com'
                    }
                )
                jsondata = json.loads(response) if response else {}
                print(jsondata)
                
                # if 'data' in jsondata:
                #     for item in jsondata['data']:
                #         if storeDomain in item['domain']:
                #             handle = item['urlname']
                #             extHandles[storeDomain][extDomain].append(handle)
                #             isFound = True
                #             break
                
                # if isFound: break

            except Exception as e:
                print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def rebatesme(handles, storeDomain, query):
    extDomain = 'rebatesme.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    storeHandle = query['handle']
    storeQueries = query['query']

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []
        isFound = False
        url = f'https://www.rebatesme.com/guest-api/rest/search-keywords'
        for i, search in enumerate(storeQueries):
            try:
                response, status = postZenResponse(url,
                    data=json.dumps({
                        "pageNo":1,
                        "pageSize":5,
                        "keywords":search,
                        "searchType": "all"
                    }),
                    headers={
                        'Content-Type': 'application/json',
                        'Referer': 'https://www.rebatesme.com'
                    }
                )

                jsondata = json.loads(response) if response else {}

                if 'data' in jsondata:
                    data = jsondata['data']
                    if 'resultMap' in data:
                        resultMap = data['resultMap']
                        if 'store' in resultMap:
                            result = resultMap['store']
                            if 'list' in result:
                                for item in result['list']:
                                    refineHandle1 = item['displayName'].replace(' ', '').lower()
                                    refineHandle2 = item['url'].replace('-', '').lower()
                                    if storeHandle in refineHandle1 or storeHandle in refineHandle2:
                                        extHandles[storeDomain][extDomain].append(item['url'])
                                        isFound = True
                                        break
                if isFound: break

            except Exception as e:
                print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def refermate(handles, storeDomain, query):
    extDomain = 'refermate.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    storeHandle = query['handle']
    storeQueries = query['query']

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []
        return extHandles
        isFound = False

        for i, search in enumerate(storeQueries):
            url = f'https://www.refermate.com/api/search?keyword={search}'
            
            try:
                response, status = getZenResponse(url)
                jsondata = json.loads(response) if response else {}

                if 'data' in jsondata:
                    for item in jsondata['data']:
                        refineHandle1 = item['name'].replace(' ', '').lower()
                        refineHandle2 = item['url'].replace('-', '').lower()
                        if storeHandle in refineHandle1 or storeHandle in refineHandle2:
                            handle = f'https://www.refermate.com{item["url"]}'
                            extHandles[storeDomain][extDomain].append(handle)
                            isFound = True
                            break
                
                if isFound: break

            except Exception as e:
                print(f"{R}Error fetching {url}: {e}{E}")
        
    
    writeJson(extHandles)
    return extHandles

def discountreactor(handles, storeDomain, query):
    extDomain = 'discountreactor.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    storeQueries = query['query']
    storeHandle = query['handle']

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []
        isFound = False

        url = f'https://www.discountreactor.com/api/search/results'

        for i, search in enumerate(storeQueries):
            try:
                response, status = postZenResponse(url,
                    data=f'term={search}',
                    headers={
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Referer': 'https://www.discountreactor.com'
                    }
                )

                jsondata = json.loads(response) if response else {}

                if 'data' in jsondata:
                    for item in jsondata['data']:
                        if storeDomain in item['domain']:
                            handle = item['url']
                            extHandles[storeDomain][extDomain].append(handle)
                            isFound = True
                            break

                if isFound: break

            except Exception as e:
                print(f"{R}Error fetching {url}: {e}{E}")
        
        
    
    writeJson(extHandles)
    return extHandles

def couponbox(handles, storeDomain, query):
    extDomain = 'couponbox.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    storeQueries = query['query']
    storeHandle = query['handle']

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []

        isFound = False
        for i, search in enumerate(storeQueries):
            url = f'https://www.couponbox.com/api/search?query={search}&page=1&shopLimit=5'
            
            try:
                response, status = getZenResponse(url)
                jsondata = json.loads(response) if response else {}

                if 'shops' in jsondata:
                    for item in jsondata['shops']:
                        refineHandle1 = item['name'].replace(' ', '').lower()
                        refineHandle2 = item['resource'].replace('-', '').lower()
                        if storeHandle in refineHandle1 or storeHandle in refineHandle2:
                            handle = f'https://www.couponbox.com{item["resource"]}'
                            extHandles[storeDomain][extDomain].append(handle)
                            isFound = True
                            break

                if isFound: break

            except Exception as e:
                print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def dealdrop(handles, storeDomain, query):
    extDomain = 'dealdrop.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    storeHandle = query['handle']
    storeQueries = query['query']

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []

        isFound = False
        url = f'https://www.dealdrop.com/api/deals'
        
        for i, search in enumerate(storeQueries):
            try:
                response, status = postZenResponse(url,
                    data=json.dumps({'domain': storeDomain}),
                    headers={
                        'Content-Type': 'application/json',
                        'Referer': 'https://www.dealdrop.com'
                    }
                )
                jsondata = json.loads(response) if response else {}
                
                if 'merchant' in jsondata:
                    for item in jsondata['merchant']:
                        print(item)
                        if storeDomain in item['domain']:
                            handle = f'https://www.dealdrop.com/{item["slug"]}'
                            extHandles[storeDomain][extDomain].append(handle)
                            isFound = True
                            break
                
                if isFound: break

            except Exception as e:
                print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def revounts(handles, storeDomain, query):
    extDomain = 'revounts.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    storeQueries = query['query']
    storeHandle = query['handle']

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []
        isFound = False
        url = f'https://www.revounts.com.au/ajax/search_call.php'
        for i, search in enumerate(storeQueries):
            try:
                response, status = postZenResponse(url,
                    data=f'searchvalue={search}',
                    headers={'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
                )

                jsondata = json.loads(response) if response else {}
                
                if 'stores' in jsondata:
                    data = jsondata['stores']
                    if data is not False:
                        for item in data:
                            refineHandle1 = item['href'].replace('-', '').lower()
                            refineHandle2 = item['name'].replace(' ', '').lower()
                            if storeHandle in refineHandle1 or storeHandle in refineHandle2:
                                extHandles[storeDomain][extDomain].append(item['href'])
                                isFound = True
                                break

                if isFound: break
            except Exception as e:
                print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def dazzdeals(handles, storeDomain, query):
    extDomain = 'dazzdeals.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    storeQueries = query['query']
    storeHandle = query['handle']

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []
        isFound = False
        url = f'https://www.dazzdeals.com/searchsuggest/'
        for i, search in enumerate(storeQueries):
            try:
                response, status = postZenResponse(url,
                    data=f'q={search}',
                    headers={'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
                )

                jsondata = json.loads(response) if response else {}
                
                if 'data' in jsondata:
                    data = jsondata['data']
                    if 'store' in data:
                        for item in data['store']:
                            if item['catetype'] == 'store':
                                refineHandle1 = item['slug'].replace('-', '').lower()
                                refineHandle2 = item['title'].replace(' ', '').lower()
                                if storeHandle in refineHandle1 or storeHandle in refineHandle2:
                                    handle = f'https://www.dazzdeals.com/store/{item["slug"]}'
                                    extHandles[storeDomain][extDomain].append(handle)
                                    isFound = True
                                    break

                if isFound: break
            except Exception as e:
                print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def greenpromocodes(handles, storeDomain, query):
    extDomain = 'greenpromocodes.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    storeQueries = query['query']
    storeHandle = query['handle']

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []

        url = f'https://www.greenpromocode.com/search/'
        
        try:
            response = client.post(url,
                data=f'q={storeDomain}',
                headers={'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
            )

            if 'Zr-Final-Url' in response.headers:
                reUrl = response.headers['Zr-Final-Url']
                refineHandle = reUrl.replace('-', '').lower()
                if storeHandle in refineHandle:
                    extHandles[storeDomain][extDomain].append(reUrl)
             
        except Exception as e:
            print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def couponbind(handles, storeDomain, query):
    extDomain = 'couponbind.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    storeHandle = query['handle']
    storeQueries = query['query']

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []

        url = f'https://www.couponbind.com/suggest/'
        
        try:
            response, status = postZenResponse(url,
                data=f'tp=se&kw={storeDomain}',
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'Referer': 'https://www.couponbind.com'
                }
            )
            jsondata = json.loads(response) if response else []
            
            for item in jsondata:
                if storeDomain in item['Domain']:
                    if 'UrlName' in item:
                        handle = f'https://www.couponbind.com{item["UrlName"]}'
                        extHandles[storeDomain][extDomain].append(handle)
                        break

        except Exception as e:
            print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def deala(handles, storeDomain, query):
    extDomain = 'deala.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    storeHandle = query['handle']
    storeQueries = query['query']

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []
        isFound = False
        url = f'https://api.deala.com/v1/shops/search'
        for i, search in enumerate(storeQueries):
        
            try:
                response, status = postZenResponse(url,
                    data=json.dumps({
                        "query": search,
                        "limit": 5,
                        "sorting": [{
                            "order": "ASC",
                            "type": "TITLE"
                        }]
                    }),
                    headers={
                        'Content-Type': 'application/json',
                        'Referer': 'https://www.deala.com'
                    }
                )
                jsondata = json.loads(response) if response else {}
                # print(jsondata)
                
                if 'result' in jsondata:
                    result = jsondata['result']
                    if 'data' in result:
                        data = result['data']
                        for item in data:
                            if storeDomain in item['link']:
                                handle = f'https://www.deala.com/{item["alias"]}'
                                extHandles[storeDomain][extDomain].append(handle)
                                isFound = True
                                break

                if isFound: break

            except Exception as e:
                print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def promopro(handles, storeDomain, query):
    extDomain = 'promopro.co.uk'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    storeHandle = query['handle']
    storeQueries = query['query']

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []

        isFound = False
        for i, search in enumerate(storeQueries):
            url = f'https://www.promopro.co.uk/api/search?wd={search}'
        
            try:
                response, status = postZenResponse(url,
                    headers={
                            'Content-Type': 'application/json',
                            'Referer': 'https://www.promopro.co.uk'
                    }
                )
                                                   
                jsondata = json.loads(response) if response else {}

                if 'data' in jsondata:
                    for item in jsondata['data']:
                        if storeDomain in item['domain']:
                            extHandles[storeDomain][extDomain].append(item['urlname'])
                            isFound = True
                            break

                if isFound: break

            except Exception as e:
                print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles


def savvy(handles, storeDomain, query, alogolia):
    extDomain = 'wethrift.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    storeHandle = query['handle']
    storeQueries = query['query']

    # 'x-algolia-agent': 'Algolia for JavaScript (4.22.0); Browser (lite)',
    # 'x-algolia-api-key': '541fc96cc6c2fce16e7188d768389ccd',
    # 'x-algolia-application-id': 'JJ05T1BWQJ'

    agent = alogolia[extDomain]['x-algolia-agent']
    api_key = alogolia[extDomain]['x-algolia-api-key']
    app_id = alogolia[extDomain]['x-algolia-application-id']
    
    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []

        isFound = False
        # https://jj05t1bwqj-1.algolianet.com/1/indexes/prod_STORES/query?x-algolia-agent=Algolia%20for%20JavaScript%20(4.22.0)%3B%20Browser%20(lite)&x-algolia-api-key=541fc96cc6c2fce16e7188d768389ccd&x-algolia-application-id=JJ05T1BWQJ
        url = f'https://{app_id.lower()}-1.algolianet.com/1/indexes/prod_STORES/query?x-algolia-agent={agent}&x-algolia-api-key={api_key}&x-algolia-application-id={app_id}'

        for i, search in enumerate(storeQueries):
            try:
                response, status = postZenResponse(url,
                    data=json.dumps({
                        "query": search
                    })
                )
                
                jsondata = json.loads(response)
                print(jsondata)
                
                
                if 'hits' in jsondata:
                    hits = jsondata['hits']
                    for hit in hits:
                        if 'objectID' in hit and storeHandle in hit['objectID'].replace('-', '').lower():
                            handle = f'https://www.wethrift.com/{hit["objectID"]}'
                            extHandles[storeDomain][extDomain].append(handle)
                            isFound = True
                            break
                if isFound: break

            except Exception as e:
                print(f"{R}Error fetching {url}: {e}{E}")
                continue


    
    writeJson(extHandles)
    return extHandles

def lovedeals(handles, storeDomain, query):
    extDomain = 'lovedeals.ai'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    storeHandle = query['handle']
    storeQueries = query['query']

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []

        isFound = False
        for i, search in enumerate(storeQueries):
            url = f'https://lovedeals.ai/search?keyword={search}'
            
            try:
                response, status = getZenResponse(url)
                jsondata = json.loads(response)
                print(jsondata)

                if 'result' in jsondata:
                    for item in jsondata['result']:
                        print(storeDomain, item['domain'], storeHandle)
                        if storeDomain == item['domain']:
                            url = item['url']
                            print(url)
                            extHandles[storeDomain][extDomain].append('https://' + extDomain + url)
                            isFound = True
                            break
                
                if isFound: break

            except Exception as e:
                print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

def askmeoffers(handles, storeDomain, query):
    extDomain = 'askmeoffers.com'
    extHandles = handles.copy()
    hasAlready = isExists(extDomain, storeDomain, handles)

    storeHandle = query['handle']
    storeQueries = query['query']

    if storeDomain not in extHandles: extHandles[storeDomain] = {}
    if not hasAlready:
        extHandles[storeDomain][extDomain] = []

        url = f'https://askmeoffers.com/wp-admin/admin-ajax.php?action=get_askme_search_results&searchtopbox={storeDomain}&__amp_source_origin=https%3A%2F%2Faskmeoffers.com'
        
        try:
            response, status = getZenResponse(url)
            jsondata = json.loads(response) if response else {}

            if 'items' in jsondata:
                for item in jsondata['items']:
                    isFound = False
                    if storeDomain in item['serdata']:
                        isFound = True
                    if storeDomain in item['title']:
                        isFound = True

                    if isFound and 'link' in item:
                        handle = item['link']
                        extHandles[storeDomain][extDomain].append(handle)

        except Exception as e:
            print(f"{R}Error fetching {url}: {e}{E}")
    
    writeJson(extHandles)
    return extHandles

if __name__ == "__main__":
    algolia ={
        'offers.com': {
            'app-id': 'ZC0GPM38IX',
            'api-key': '80e8b1435748e719ae1373e1a8d067c8'
        },
        'wethrift.com': {
            'x-algolia-agent': 'Algolia for JavaScript (4.22.0); Browser (lite)',
            'x-algolia-api-key': '541fc96cc6c2fce16e7188d768389ccd',
            'x-algolia-application-id': 'JJ05T1BWQJ'
        }
    }

    queries = {
        'cozyearth.com': {
            'handle': 'cozyearth',
            'query': ['cozy earth','cozyearth']
        },
        # 'airestech.com': {
        #     'handle': 'airestech',
        #     'query': ['aires', 'airestech', 'aires tech']
        # },
    }

    handles = readJson()
    if not handles: handles = {}

    for storeDomain, storeQuery in queries.items():
        print(f'{Y}Scraping Handle: {storeDomain} {E}')
        
        # handles = coupert(handles, storeDomain, storeQuery)
        # handles = discounttime(handles, storeDomain, storeQuery)
        # handles = karmanow(handles, storeDomain, storeQuery)
        # handles = rakuten(handles, storeDomain, storeQuery)
        # handles = hotdeals(handles, storeDomain, storeQuery)
        # handles = slickdeals(handles, storeDomain, storeQuery)
        # handles = capitalone(handles, storeDomain, storeQuery)
        # handles = retailmenot(handles, storeDomain, storeQuery)
        # handles = honey(handles, storeDomain, storeQuery)
        # handles = rebates(handles, storeDomain, storeQuery)
        # handles = coupons(handles, storeDomain, storeQuery)
        # handles = dealcatcher(handles, storeDomain, storeQuery)
        # handles = dontpayfull(handles, storeDomain, storeQuery)
        # handles = couponbirds(handles, storeDomain, storeQuery)
        # handles = offers(handles, storeDomain, storeQuery, algolia)
        # handles = savings(handles, storeDomain, storeQuery)
        # handles = dealspotr(handles, storeDomain, storeQuery)
        # handles = promocodes(handles, storeDomain, storeQuery)
        # handles = couponchief(handles, storeDomain, storeQuery)
        # handles = goodshop(handles, storeDomain, storeQuery)
        # handles = simplycodes(handles, storeDomain, storeQuery)
        # handles = tenereteam(handles, storeDomain, storeQuery)
        # handles = couponcause(handles, storeDomain, storeQuery)
        # handles = goodsearch(handles, storeDomain, storeQuery)
        # handles = valuecom(handles, storeDomain, storeQuery)
        # handles =  lovecoupons(handles, storeDomain, storeQuery)
        # handles = knoji(handles, storeDomain, storeQuery)
        # handles = swagbucks(handles, storeDomain, storeQuery)
        # handles = joinsmarty(handles, storeDomain, storeQuery)
        # handles = rebatesme(handles, storeDomain, storeQuery)
        # handles = refermate(handles, storeDomain, storeQuery)
        # handles = discountreactor(handles, storeDomain, storeQuery)
        # handles = couponbox(handles, storeDomain, storeQuery)
        # handles = dealdrop(handles, storeDomain, storeQuery)
        # handles = revounts(handles, storeDomain, storeQuery)
        # handles = dazzdeals(handles, storeDomain, storeQuery)
        # handles = greenpromocodes(handles, storeDomain, storeQuery)
        # handles = couponbind(handles, storeDomain, storeQuery)
        # handles = deala(handles, storeDomain, storeQuery)
        # handles = promopro(handles, storeDomain, storeQuery)
        handles = savvy(handles, storeDomain, storeQuery, algolia)
        # x handles = coupertpure(handles, storeDomain, storeQuery) // AI prompot
        handles = lovedeals(handles, storeDomain, storeQuery)
        # x handles = couponuts(handles, storeDomain, storeQuery) // Server Down
        handles = askmeoffers(handles, storeDomain, storeQuery)
        # x handles = dealdazzle(handles, storeDomain, storeQuery) // Server Down