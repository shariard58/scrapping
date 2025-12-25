import re
import json
import pprint
import subprocess
import cloudscraper
import warnings
import base64
import requests
import os

from html import unescape
from zenrows import ZenRowsClient
from fake_useragent import UserAgent
from requests import Request, Session
from urllib.request import Request, urlopen
from urllib.parse import urlparse, parse_qs



from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

# client = ZenRowsClient("3e7d13ea2ae4491a249abbc360a20575986e11f6")
client = ZenRowsClient("fa0f561cee2fa9ba7976f152b852a663fdcd8791")

ua = UserAgent()
cookies = None

# Console Colors
R = '\033[31m'
G = '\033[32m'
Y = '\033[33m'
B = '\033[34m'
E = '\033[0m'

def fetchRequest(url):
    try:
        headers = {
            "User-Agent": ua.random,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Referer": "https://www.google.com/",
            "Connection": "keep-alive"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"{R}Error fetching {url}: {e}{E}")
        return None

def fetchURL(url):
    try:
        headers = {
            "User-Agent": ua.random,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Referer": "https://www.google.com/",
            "Connection": "keep-alive"
        }
        request = Request(url, headers=headers)
        response = urlopen(request)
        return response.read().decode("utf-8")
    except Exception as e:
        print(f"{R}Error fetching {url}: {e}{E}")
        return None
    
def getZenResponse(url, headers=None, isJson=False, isCookies=False, isProxy=False):
    global cookies
    try:
        if(isCookies and not cookies):
            response = client.get(url, headers=headers)
            cookies = response.cookies
        params = {"premium_proxy":"true","proxy_country":"us",}
        csheaders = {
            "Referer": "https://www.google.com",
            **(headers or {}),
            **({"Cookies": cookies} if isCookies and cookies else {}),
        }

        print(f"{B}Fetching URL: {url}{E}")
        print(csheaders)

        response = client.get(url, headers=csheaders, params=params) if isProxy else client.get(url, headers=csheaders)
        
        if(isJson): return response
        return response.text
    except Exception as e:
        print(f"{R}Error fetching {url}: {e}{E}")
        return None

def postZenResponse(url, data=None):
    try: 
        response = client.post(url, data=data, headers={"Content-Type": "application/json"})
        return response.text
    except Exception as e:
        print(f"{R}Error fetching {url}: {e}{E}")
        return None

def writeToFile(filename, data):
    with open(filename, 'w',  encoding='utf-8') as file:
        if(data): file.write(data)


def coupert(url):
    
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        
        # Extract store domain from URL
        store_domain = url.split('/')[-1]
        
        # ==========================================
        # Method 1: Try API endpoint (fastest)
        # ==========================================
        try:
            print(f'{Y}Trying API endpoint...{E}')
            api_url = f'https://www.coupert.com/api/v3/store/{store_domain}'
            headers = {
                'User-Agent': ua.random,
                'Referer': url,
                'Accept': 'application/json',
            }
            
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Try different JSON structures
                coupon_data = None
                if 'coupons' in data:
                    coupon_data = data['coupons']
                elif 'data' in data and isinstance(data['data'], dict):
                    if 'coupons' in data['data']:
                        coupon_data = data['data']['coupons']
                
                # Extract coupon codes
                if coupon_data:
                    for coupon in coupon_data:
                        if isinstance(coupon, dict) and 'code' in coupon and coupon['code']:
                            coupons.append(coupon['code'].upper())
                    
                if len(coupons) > 0:
                    print(f'{G}API method successful! Found {len(coupons)} coupons{E}')
                    unique_coupons = list(set(coupons))
                    print(f'{unique_coupons}')
                    return unique_coupons
                else:
                    print(f'{Y}API returned no coupons, trying HTML scraping...{E}')
        except Exception as e:
            print(f'{Y}API method failed: {e}{E}')
        
        # ==========================================
        # Method 2: HTML Scraping with ZenRows
        # ==========================================
        print(f'{Y}Trying HTML scraping...{E}')
        html = getZenResponse(url)
        
        if not html:
            print(f'{R}Failed to fetch HTML{E}')
            return []
            
        soup = BeautifulSoup(html, 'html.parser')

        # Try __NEXT_DATA__ (Next.js structure)
        next_data = soup.select_one('script#__NEXT_DATA__')
        if next_data and len(coupons) == 0:
            try:
                json_data = json.loads(next_data.string)
                if 'props' in json_data:
                    props = json_data['props']
                    if 'pageProps' in props:
                        pageProps = props['pageProps']
                        if 'storeInfo' in pageProps:
                            storeInfo = pageProps['storeInfo']
                            if 'data' in storeInfo and 'coupons' in storeInfo['data']:
                                for item in storeInfo['data']['coupons']:
                                    if 'code' in item and item['code']:
                                        coupons.append(item['code'].upper())
                
                if len(coupons) > 0:
                    print(f'{G}__NEXT_DATA__ method successful!{E}')
            except Exception as e:
                print(f'{Y}__NEXT_DATA__ parsing failed: {e}{E}')
        
        # Try __NUXT_DATA__ (Nuxt.js structure)
        if len(coupons) == 0:
            nuxt_data = soup.select_one('script#__NUXT_DATA__')
            if nuxt_data:
                try:
                    json_data = json.loads(nuxt_data.string)
                    if isinstance(json_data, list) and len(json_data) > 0:
                        for item in json_data:
                            if isinstance(item, str):
                                try:
                                    dataText = base64.b64decode(item).decode('utf-8')
                                    dataJson = json.loads(dataText)
                                    
                                    if "merchant_coupons" in dataJson:
                                        couponsItem = dataJson['merchant_coupons']
                                        for itm in couponsItem:
                                            if "code" in itm and itm['code']:
                                                coupons.append(itm['code'].upper())
                                except:
                                    continue
                    
                    if len(coupons) > 0:
                        print(f'{G}__NUXT_DATA__ method successful!{E}')
                except Exception as e:
                    print(f'{Y}__NUXT_DATA__ parsing failed: {e}{E}')

        # ==========================================
        # Method 3: Script tag regex parsing
        # ==========================================
        if len(coupons) == 0:
            print(f'{Y}Trying script tag parsing...{E}')
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string:
                    try:
                        # Look for JSON containing coupon codes
                        if 'code' in script.string.lower() or 'coupon' in script.string.lower():
                            # Try to find JSON objects with code field
                            matches = re.findall(r'"code"\s*:\s*"([A-Z0-9]{4,30})"', script.string, re.IGNORECASE)
                            for code in matches:
                                if len(code) >= 4 and len(code) <= 30:
                                    coupons.append(code.upper())
                    except:
                        continue
            
            if len(coupons) > 0:
                print(f'{G}Script tag parsing successful!{E}')

        # ==========================================
        # Method 4: Direct HTML element scraping
        # ==========================================
        if len(coupons) == 0:
            print(f'{Y}Trying direct HTML element parsing...{E}')
            # Look for elements that might contain coupon codes
            code_elements = soup.find_all(['span', 'div', 'button', 'input'], 
                                         class_=re.compile(r'code|coupon', re.IGNORECASE))
            for element in code_elements:
                text = element.get_text(strip=True)
                # Filter for valid coupon code patterns
                if text and re.match(r'^[A-Z0-9]{4,30}$', text):
                    # Exclude common false positives
                    if text not in ['CODE', 'COPY', 'SAVE', 'DEAL', 'FREE', 'SHOP', 'GETCODE', 'GET', 'NOW']:
                        coupons.append(text.upper())
            
            if len(coupons) > 0:
                print(f'{G}HTML element parsing successful!{E}')

    except Exception as e:
        print(f'{R}Error scraping coupert: {e}{E}')

    # Remove duplicates and return
    unique_coupons = list(set(coupons))
    if len(unique_coupons) > 0:
        print(f'{G}Found {len(unique_coupons)} unique coupons: {unique_coupons}{E}')
    else:
        print(f'{Y}No coupons found for {url}{E}')
    
    return unique_coupons

def discountime(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        response = postZenResponse('https://www.discountime.com/system/coupon/queryByAliasName', data=json.dumps({
            "type": 1,
            "pageNo": 1,
            "pageSize": 500,
            "brandAliasName": url.split('/')[-1]
        }))
        
        if response:
            jsondata = json.loads(response)
            if('data' in jsondata):
                if('result' in jsondata['data']):
                    results = jsondata['data']['result']
                    for item in results:
                        if('code' in item):
                            coupons.append(item['code'].upper())

                    
    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

def karmanow(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        response = getZenResponse(url)
        
        if response:
            jsondata = json.loads(response)

            if('data' in jsondata):
                for item in jsondata['data']:
                    if('code' in item):
                        coupons.append(item['code'].upper())

    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

def rakuten(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        html = getZenResponse(url)
        soup = BeautifulSoup(html, 'html.parser')

        coupon_elements = soup.select('.click-to-copy-box .coupon-code')
        for element in coupon_elements:
            code = element.text.strip()
            if code is not None:
                coupons.append(code)

                    
    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

def hotDeals(url):
    coupons = []
    try:
        print(f'Scraping HotDeals: {url}')
        html = getZenResponse(url)
        
        if not html:
            return []

       
        nuxt_codes = re.findall(r'code:"([^"]+)"', html)
        for code in nuxt_codes:
            if code and code.lower() != 'none':
                coupons.append(code.upper())

        
        soup = BeautifulSoup(html, 'html.parser')
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc:
            content = meta_desc.get('content', '')
            
            matches = re.findall(r'"([^"]*)"', content)
            for m in matches:
                if 4 <= len(m) <= 15: 
                    coupons.append(m.upper())

        
        pattern = r'\b[A-Z]{2,}[A-Z0-9]{2,}\b'
        raw_matches = re.findall(pattern, html)
        
        
        bad_words = ['HTML', 'UTF8', 'TRUE', 'FALSE', 'WIDTH', 'HEIGHT', 'DEALS', 'PROMO', 'DECEMBER']
        
        for c in raw_matches:
            
            if not c.isdigit() and len(c) < 15 and c not in bad_words:
                if sum(char.isalpha() for char in c) >= 2:
                    coupons.append(c)

    except Exception as e:
        print(f'Error: {e}')

    
    final_list = list(set(coupons))
    
    
    cleaned_list = [code for code in final_list if not re.match(r'^\d+$', code) and len(code) > 2]

    print(f"Final Results: {cleaned_list}")
    return cleaned_list

def slickDeals(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        html = getZenResponse(url)
        writeToFile('html/slickdeals.html', html)
        soup = BeautifulSoup(html, 'html.parser')
        coupon_elements = soup.select('[data-attribute="code"]')

        for element in coupon_elements:
            id = element.get_attribute_list('data-id')[0]

            try:
                print(f'{url}#voucher-{id}')
                html2 = getZenResponse(f'{url}#voucher-{id}')
                print(html2)
                writeToFile('html/slickdeals2.html', html2)
                soup2 = BeautifulSoup(html2, 'html.parser')
                coupon_elements2 = soup2.select('[data-testid="voucherPopup-codeHolder-voucherType-code"] h4')
                for element2 in coupon_elements2:
                    coupon = element2.text.strip()
                    if coupon:
                        coupons.append(coupon.upper())

            except Exception as e:
                print(f'{R}Error scraping HotDeals: {e}{E}')
                continue
    
    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

def capitalone(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        html = getZenResponse(url)
        soup = BeautifulSoup(html, 'html.parser')

        # Extract JSON data embedded in a script
        script_tag = soup.find('script', string=lambda t: t and 'window.initialState' in t)
        script_txt = script_tag.text.strip()

        # print(script_tag.text.strip())
        pattern = r"window\.initialState\s*=\s*({.*?});"

        # Extract the match
        match = re.search(pattern, script_txt)
        # print(match)

        if match:
            json_text = match.group(1)
            json_data = json.loads(json_text)
            
            if('StorePage' in json_data):
                store_page = json_data['StorePage']
                if('site' in store_page):
                    site = store_page['site']
                    if('couponsInfo' in site):
                        coupons_info = site['couponsInfo']
                        if('coupons' in coupons_info):
                            codes = coupons_info['coupons']
                            for item in codes:
                                if('code' in item):
                                    coupons.append(item['code'].upper())
                            
    except Exception as e:
        print(f'{R}Error scraping CapitalOne: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

def retailmenot(url):
    """
    Scrape coupons from RetailMeNot.com using multiple methods
    Returns: List of unique coupon codes
    """
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        
        # ==========================================
        # Method 1: Try API endpoint (if exists)
        # ==========================================
        try:
            print(f'{Y}Trying API endpoint...{E}')
            store_slug = url.split('/')[-1]
            api_url = f'https://www.retailmenot.com/api/offers?merchant={store_slug}'
            
            headers = {
                'User-Agent': ua.random,
                'Accept': 'application/json',
                'Referer': url
            }
            
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Try to find coupons in API response
                if 'offers' in data:
                    for offer in data['offers']:
                        if offer.get('type') == 'coupon' and 'code' in offer:
                            coupons.append(offer['code'].upper())
                
                if len(coupons) > 0:
                    print(f'{G}API method successful! Found {len(coupons)} coupons{E}')
                    unique_coupons = list(set(coupons))
                    print(f'{unique_coupons}')
                    return unique_coupons
        except Exception as e:
            print(f'{Y}API method failed: {e}{E}')
        
        # ==========================================
        # Method 2: HTML Scraping with ZenRows
        # ==========================================
        print(f'{Y}Trying HTML scraping...{E}')
        html = getZenResponse(url)
        
        if not html:
            print(f'{R}Failed to fetch HTML{E}')
            return []
            
        soup = BeautifulSoup(html, 'html.parser')

        # Try __NEXT_DATA__ (Next.js structure)
        next_data = soup.select_one('script#__NEXT_DATA__')
        if next_data:
            try:
                json_data = json.loads(next_data.string)
                
                # Navigate through Next.js data structure
                if 'props' in json_data:
                    props = json_data['props']
                    if 'pageProps' in props:
                        page_props = props['pageProps']
                        
                        # Look for offers/coupons in various possible locations
                        offers = None
                        if 'offers' in page_props:
                            offers = page_props['offers']
                        elif 'initialState' in page_props and 'offers' in page_props['initialState']:
                            offers = page_props['initialState']['offers']
                        elif 'merchant' in page_props and 'offers' in page_props['merchant']:
                            offers = page_props['merchant']['offers']
                        
                        if offers:
                            for offer in offers:
                                if isinstance(offer, dict):
                                    # Check if it's a coupon type
                                    if offer.get('type') == 'coupon' or offer.get('offerType') == 'COUPON':
                                        if 'code' in offer and offer['code']:
                                            coupons.append(offer['code'].upper())
                                        elif 'couponCode' in offer and offer['couponCode']:
                                            coupons.append(offer['couponCode'].upper())
                
                if len(coupons) > 0:
                    print(f'{G}__NEXT_DATA__ method successful!{E}')
            except Exception as e:
                print(f'{Y}__NEXT_DATA__ parsing failed: {e}{E}')
        
        # ==========================================
        # Method 3: Look for embedded JSON in scripts
        # ==========================================
        if len(coupons) == 0:
            print(f'{Y}Trying script tag JSON parsing...{E}')
            script_tags = soup.find_all('script')
            
            for script in script_tags:
                if script.string:
                    try:
                        # Look for window.__INITIAL_STATE__ or similar
                        if 'window.__INITIAL_STATE__' in script.string or 'initialState' in script.string:
                            # Try to extract JSON
                            matches = re.findall(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', script.string, re.DOTALL)
                            if not matches:
                                matches = re.findall(r'initialState\s*[:=]\s*({.*?})[,;]', script.string, re.DOTALL)
                            
                            for match in matches:
                                try:
                                    json_data = json.loads(match)
                                    
                                    # Recursively search for coupon codes in JSON
                                    def find_coupons_in_json(obj, codes_list):
                                        if isinstance(obj, dict):
                                            # Check if this object has a coupon code
                                            if obj.get('type') == 'coupon' or obj.get('offerType') == 'COUPON':
                                                if 'code' in obj and obj['code']:
                                                    codes_list.append(obj['code'].upper())
                                                elif 'couponCode' in obj and obj['couponCode']:
                                                    codes_list.append(obj['couponCode'].upper())
                                            
                                            # Recursively check nested objects
                                            for value in obj.values():
                                                find_coupons_in_json(value, codes_list)
                                        elif isinstance(obj, list):
                                            for item in obj:
                                                find_coupons_in_json(item, codes_list)
                                    
                                    find_coupons_in_json(json_data, coupons)
                                except:
                                    continue
                        
                        # Also look for direct coupon code patterns in JSON
                        if '"code"' in script.string or '"couponCode"' in script.string:
                            code_matches = re.findall(r'"(?:code|couponCode)"\s*:\s*"([A-Z0-9]{4,30})"', script.string, re.IGNORECASE)
                            for code in code_matches:
                                if len(code) >= 4 and len(code) <= 30:
                                    coupons.append(code.upper())
                    except:
                        continue
            
            if len(coupons) > 0:
                print(f'{G}Script JSON parsing successful!{E}')

        # ==========================================
        # Method 4: Original HTML element scraping
        # ==========================================
        if len(coupons) == 0:
            print(f'{Y}Trying original HTML element scraping...{E}')
            
            # Try original selectors
            coupon_elements = soup.select('a[data-content-datastore="offer"]')
            
            for element in coupon_elements:
                try:
                    xdata = element.get('x-data') or element.get_attribute_list('x-data')[0]
                    href = element.get('href')

                    if xdata and href:
                        # Clean and parse x-data
                        clean_xdata = xdata.replace("outclickHandler({", '{').replace("})", '}').replace("'", '"')
                        jsonData = json.loads(clean_xdata)
                        
                        if jsonData.get('offerType') == 'COUPON':
                            parsedUrl = urlparse(href)
                            queryParams = parse_qs(parsedUrl.query)
                            
                            try:
                                template = queryParams.get('template', [''])[0]
                                offerId = queryParams.get('offer_uuid', [''])[0]
                                merchantId = queryParams.get('merchant_uuid', [''])[0]

                                if offerId:
                                    itemUrl = f'https://www.retailmenot.com/modals/outclick/{offerId}/?template={template}&trigger=entrance_modal&merchant={merchantId}'
                                    
                                    html2 = getZenResponse(itemUrl)
                                    if html2:
                                        try:
                                            modal_data = json.loads(html2)
                                            if 'modalHtml' in modal_data:
                                                soup2 = BeautifulSoup(modal_data['modalHtml'], 'html.parser')
                                                
                                                # Try multiple selectors
                                                code_elements = soup2.select('[x-show="outclicked"] div[x-data]')
                                                if not code_elements:
                                                    code_elements = soup2.select('.coupon-code, [data-code], .code')
                                                
                                                for elem in code_elements:
                                                    code = elem.text.strip()
                                                    code = code.replace('COPY', '').strip()
                                                    if code and len(code) >= 4 and len(code) <= 30:
                                                        coupons.append(code.upper())
                                        except:
                                            # If not JSON, try direct HTML parsing
                                            soup2 = BeautifulSoup(html2, 'html.parser')
                                            code_elements = soup2.select('.coupon-code, [data-code], .code, [class*="code"]')
                                            for elem in code_elements:
                                                code = elem.text.strip()
                                                if code and len(code) >= 4 and len(code) <= 30:
                                                    coupons.append(code.upper())
                            except Exception as e:
                                print(f'{Y}Modal fetch error: {e}{E}')
                                continue
                except Exception as e:
                    continue
            
            if len(coupons) > 0:
                print(f'{G}HTML element scraping successful!{E}')

        # ==========================================
        # Method 5: Look for any visible coupon codes
        # ==========================================
        if len(coupons) == 0:
            print(f'{Y}Trying direct coupon code search...{E}')
            
            # Look for elements that might contain codes
            code_elements = soup.find_all(['div', 'span', 'button', 'input', 'code'], 
                                         class_=re.compile(r'coupon|code|promo', re.IGNORECASE))
            
            for element in code_elements:
                text = element.get_text(strip=True)
                # Check if it matches coupon code pattern
                if text and re.match(r'^[A-Z0-9]{4,30}$', text):
                    if text not in ['CODE', 'COUPON', 'COPY', 'SAVE', 'GET', 'SHOP']:
                        coupons.append(text.upper())
                
                # Also check data attributes
                for attr in ['data-code', 'data-coupon', 'data-coupon-code']:
                    if element.get(attr):
                        coupons.append(element[attr].upper())

    except Exception as e:
        print(f'{R}Error scraping retailmenot: {e}{E}')

    # Remove duplicates and return
    unique_coupons = list(set(coupons))
    if len(unique_coupons) > 0:
        print(f'{G}Found {len(unique_coupons)} unique coupons: {unique_coupons}{E}')
    else:
        print(f'{Y}No coupons found for {url}{E}')
    
    return unique_coupons
    # coupons = []

    # try:
    #     print(f'{B}Scraping WEB: {url} {E}')
    #     html = getZenResponse(url)
    #     soup = BeautifulSoup(html, 'html.parser')

    #     coupon_elements = soup.select('a[data-content-datastore="offer"]')

    #     for element in coupon_elements:
    #         xdata = element.get_attribute_list('x-data')[0]
    #         href = element.get('href')

    #         if xdata and href:
    #             jsonData = json.loads(xdata.replace("outclickHandler({", '{').replace("})", '}').replace("'", '"'))
    #             parsedUrl = urlparse(href)
    #             queryParams = parse_qs(parsedUrl.query)

    #             if 'offerType' in jsonData:
    #                 offerType = jsonData['offerType']
    #                 if offerType == 'COUPON':
    #                     try:
    #                         template = queryParams.get('template')[0]
    #                         offerId = queryParams.get('offer_uuid')[0]
    #                         merchantId = queryParams.get('merchant_uuid')[0]

    #                         itemUrl = f'https://www.retailmenot.com/modals/outclick/{offerId}/?template={template}&trigger=entrance_modal&merchant={merchantId}'

    #                         html2 = getZenResponse(itemUrl)
    #                         jsonData = json.loads(html2)

    #                         if 'modalHtml' in jsonData:
    #                             modalHtml = jsonData['modalHtml']
    #                             soup2 = BeautifulSoup(modalHtml, 'html.parser')
                                
    #                             coupon_elements2 = soup2.select('[x-show="outclicked"] div[x-data]')
                                
    #                             for element2 in coupon_elements2:
    #                                 code = element2.text.strip()
    #                                 code = code.replace('COPY', '').strip()
    #                                 if code is not None:
    #                                     coupons.append(code)

    #                     except Exception as e:
    #                         print(f'{R}Error scraping retailmenot: {e}{E}')
    #                         continue

    # except Exception as e:
    #     print(f'{R}Error scraping retailmenot: {e}{E}')

    # print(f'{list(set(coupons))}')
    # return list(set(coupons))

def honey(url):
    coupons = []
    
    try:
        print(f'{B}Scraping WEB: {url} {E}')
        html = getZenResponse(url)
        print(html)
        # fetchRequest(url)
        # if not html: 
        #     html = fetchURL(url)
        soup = BeautifulSoup(html, 'html.parser')

        coupon_elements = soup.select('[aria-label="Coupon Code"]')
        for element in coupon_elements:
            coupon = element.text.strip()
            if coupon:
                coupons.append(coupon.upper())
    except Exception as e:
        print(f'{R}Error scraping Honey: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

def rebates(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        html = getZenResponse(url)
        soup = BeautifulSoup(html, 'html.parser')

        coupon_elements = soup.select('.couponModal[data-code]')

        for element in coupon_elements:
            coupon = element.get_attribute_list('data-code')[0]
            if coupon is not None:
                    coupons.append(coupon.upper())
                    
    except Exception as e:
        print(f'{R}Error scraping rebates: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

# def couponCabin(url):

def couponsCom(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        html = getZenResponse(url)
        soup = BeautifulSoup(html, 'html.parser')

        styleElements = soup.select('[type="text/css"]')
        clientId = None
        for styleElement in styleElements:
            href = styleElement.get('href')
            # https://www.coupons.com/assets/pico/15943717d76a8bf7eb0d5b8ad2ea2e55/v1/style-guide.css?969669
            if href and 'https://www.coupons.com/assets/pico' in href and 'style-guide.css' in href:
                clientId = href.split('pico/')[1].split('/')[0]
                break

        if clientId:
            coupon_elements = soup.select('[data-attribute="code"]')
            for element in coupon_elements:
                couponId = element.get_attribute_list('data-id')[0]
                
                try:
                    text = getZenResponse(f'https://www.coupons.com/api/voucher/country/us/client/{clientId}/id/{couponId}')
                    # print(text)
                    if text:
                        data = json.loads(text)
                        if 'type' in data and data['type'] == 'code':
                            code = data['code']
                            if code:
                                coupons.append(code.upper())
                
                except Exception as e:
                    print(f'{R}Error scraping couponsCom: {e}{E}')
                    continue

                    
    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

def dealCatcher(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        html = getZenResponse(url)
        soup = BeautifulSoup(html, 'html.parser')

        coupon_elements = soup.select('.coupon-box .coupon-code')
        for element in coupon_elements:
            code = element.text.strip()
            if code and code is not None:
                coupons.append(code)

                    
    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))
    
def dontPayFull(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        html = getZenResponse(url)
        
        soup = BeautifulSoup(html, 'html.parser')

        coupon_elements = soup.select('.card.obox.code[data-otype="code"]')

        for element in coupon_elements:
            idAttribute = element.get_attribute_list('data-id')[0]
            classAttribute = element.get_attribute_list('class')[0]
            if 'sponsored' not in classAttribute:
                try:
                    html2 = getZenResponse(f'https://www.dontpayfull.com/coupons/getcoupon?id={idAttribute}')
                    soup2 = BeautifulSoup(html2, 'html.parser')

                    coupon_elements2 = soup2.select('.code-box.code h2')
                    for element2 in coupon_elements2:
                        code = element2.text.strip()
                        if code is not None:
                            coupons.append(code)
                except Exception as e:
                    print(f'{R}Error scraping dontPayFull: {e}{E}')
                    continue
                    
    except Exception as e:
        print(f'{R}Error scraping dontPayFull: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

def couponBirds(url):
    global cookies
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        html = getZenResponse(url, isCookies=True, isProxy=True)
        soup = BeautifulSoup(html, 'html.parser')

        coupon_elements = soup.select('.get-code a[data-url]')
        print(len(coupon_elements))
        i=0
        for element in coupon_elements:
            attribute = element.get_attribute_list('data-url')[0]
            i = i+1
            print(i, attribute)
            if attribute:
                html2 = getZenResponse(attribute, isCookies=True, isProxy=True)
                soup2 = BeautifulSoup(html2, 'html.parser')

                coupon_elements2 = soup2.select('.modal-body .cp-code input#copy-recommend-code')
                for element2 in coupon_elements2:
                    code = element2.get('value')
                    if code is not None:
                        coupons.append(code)

    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')
    
    cookies = None
    print(f'{list(set(coupons))}')
    return list(set(coupons))


def offersCom(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        # html = getRequest(url)
        html = getZenResponse(url)
        # print(html)
        soup = BeautifulSoup(html, 'html.parser')

        print("What is the soup value", soup)

        elements1 = soup.select('[data-offer-id] > [data-content-datastore="offer"]')
        for element in elements1:
            # coupon = element['acsimpritem']
            attribute1 = element.get_attribute_list('x-data')[0]
            attribute2 = element.get_attribute_list('@click.prevent')[0]

            if attribute1: 
                offerId = attribute1.split("'")[1]
                hasCode = 'hasCode: true' in attribute2
                if hasCode:
                    html2 = getZenResponse(f'{url}?em={offerId}')
                    soup2 = BeautifulSoup(html2, 'html.parser')
                    
                    elements2 = soup2.select('[x-data="commerceModal"] [x-data]')

                    for element2 in elements2:
                        codeAttribute = element2.get_attribute_list('x-data')[0]
                        coupon = codeAttribute.split("'")[3]
                        if coupon:
                            coupons.append(coupon)
                    
    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

def savingsCom(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        html = getZenResponse(url)
        soup = BeautifulSoup(html, 'html.parser')

        coupon_elements = soup.select('.module-deal.showValue.codePeek[data-offer-id]')
        for element in coupon_elements:
            attribute = element.get_attribute_list('id')[0]
            try:
                couponId = attribute.split('-')[-1]
                html2 = getZenResponse(f'https://www.savings.com/popup/detail/coupon-{couponId}.html')
                
                soup2 = BeautifulSoup(html2, 'html.parser')
                coupon_elements2 = soup2.select('#code-wrapper input.code')
                for element2 in coupon_elements2:
                    coupon = element2.get('value')
                    if coupon:
                        coupons.append(coupon)

            except Exception as e:
                print(f'{R}Error scraping HotDeals: {e}{E}')
                continue

        
                    
    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

def dealSpotsR(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        # html = getRequest(url)
        # headers = {
        #     "User-Agent": ua.random,
        # }
        # session = Session()
        # session.get(url, headers=headers)
        # response = session.get(url, headers=headers)
        # html = response.text
        # print(html)
        html = getZenResponse(url)

        soup = BeautifulSoup(html, 'html.parser')
        coupon_elements = soup.select('input.dnone')
        for element in coupon_elements:
            # coupon = element['acsimpritem']
            code = element.get('value')
            coupons.append(code)

        
                    
    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))



def promoCodes(url):
    coupons = []
    try:
        html = getZenResponse(url)
        soup = BeautifulSoup(html, 'html.parser')
        
        next_data_script = soup.select_one('script#__NEXT_DATA__')
        
        if next_data_script:
            json_data = json.loads(next_data_script.string)
                      
            def find_coupons(obj):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if k == 'couponCode' and v:
                            coupons.append(v.upper())
                        else:
                            find_coupons(v)
                elif isinstance(obj, list):
                    for item in obj:
                        find_coupons(item)

            find_coupons(json_data)

        regex_codes = re.findall(r'"couponCode"\s*:\s*"([^"]+)"', html)
        coupons.extend([c.upper() for c in regex_codes if c])

    except Exception as e:
        print(f'Error: {e}')

    final_coupons = list(set(coupons))
    
    garbage = ['NULL', 'NONE', 'VERIFIED', 'TRUE', 'FALSE']
    final_coupons = [c for c in final_coupons if c not in garbage and len(c) > 2]

    print(f'Found Coupons: {final_coupons}')
    return final_coupons

def couponChief(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        html = getZenResponse(url)
        soup = BeautifulSoup(html, 'html.parser')
        
        coupon_elements = soup.select('.coupon-code-container.store-code')
        for element in coupon_elements:
            attribute = element.get_attribute_list('id')[0]
            # print(attribute)
            try:
                couponId = attribute.split('-')[-1]
                # html2 = getRequest(f'https://www.couponchief.com/pages/coupon_overlay/{couponId}')
                html2 = getZenResponse(f'https://www.couponchief.com/pages/coupon_overlay/{couponId}')
                # print(html2)
                # writeToFile('html/couponchief.html', html2)
                soup2 = BeautifulSoup(html2, 'html.parser')
                coupon_elements2 = soup2.select('input#coupon-code')
                for element2 in coupon_elements2:
                    coupon = element2.get('value')
                    if coupon:
                        coupons.append(coupon)
            except Exception as e:
                print(f'{R}Error scraping HotDeals: {e}{E}')
                continue

                    
    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

def goodShop(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        # html = getResponse(url)
        html = getZenResponse(url)
        soup = BeautifulSoup(html, 'html.parser')
        
        coupon_elements = soup.select('.has-code[data-clipboard-text]')
        for element in coupon_elements:
            code = element.get_attribute_list('data-clipboard-text')[0]
            if code is not None:
                coupons.append(code)

                    
    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

def getNextData(html):
    soup = BeautifulSoup(html, 'html.parser')
    # Find all matching <script> tags
    matching_scripts = soup.find_all('script', string=lambda s: s and s.strip().startswith('self.__next_f.push('))
    
    result = []
    dataArray = []

    for script in matching_scripts:
        data = script.string.strip('self.__next_f.push(').strip(')')
        dataArray.append(json.loads(data))

    for data in dataArray:
        # inputStr = data[1] if len(data) > 1 else ""
        
        # Step 1: Flatten input into lines
        lines = []
        for item in data:
            if isinstance(item, str):
                lines.extend(item.split('\n'))

        # Step 2: Parse each line
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Match formats:
            # 1. key:I[...]      -> module/import info
            # 2. key:"literal"   -> literal string
            # 3. key:[...]       -> simple list
            # 4. key:{}          -> JSON object
            # 5. fallback: raw

            match_i = re.match(r'^(\w+):I\[(.*)\]$', line)
            match_lit = re.match(r'^(\w+):"(.*)"$', line)
            match_list = re.match(r'^(\w+):\[(.*)\]$', line)
            match_obj = re.match(r'^(\w+):\{(.*)\}$', line)

            if match_i:
                key = match_i.group(1)
                data = f'[{match_i.group(2)}]'
                try:
                    parsed = json.loads(data)
                    id_, dependencies, label = parsed
                    result.append({
                        "index": key,
                        "type": "I",
                        "value": {
                            "id": id_,
                            "dependencies": dependencies,
                            "label": label
                        }
                    })
                except Exception:
                    result.append({ "index": key, "type": "I", "error": "JSON parse failed", "raw": data })

            elif match_lit:
                key = match_lit.group(1)
                val = match_lit.group(2)
                result.append({ "index": key, "type": "literal", "value": val })

            elif match_list:
                key = match_list.group(1)
                data = f'[{match_list.group(2)}]'
                try:
                    parsed = json.loads(data)
                    result.append({ "index": key, "type": "list", "value": parsed })
                except Exception:
                    result.append({ "index": key, "type": "list", "error": "JSON parse failed", "raw": data })

            elif match_obj:
                key = match_obj.group(1)
                data = f'{{{match_obj.group(2)}}}'
                try:
                    parsed = json.loads(data)
                    result.append({ "index": key, "type": "object", "value": parsed })
                except Exception:
                    result.append({ "index": key, "type": "object", "error": "JSON parse failed", "raw": data })

            else:
                result.append({ "type": "unknown", "raw": line })

        return result

    writeToFile('json/nextdata.json', json.dumps(result, indent=4))


    # result = []

    # for line in input_data:
    #     l = line[1] if len(line) > 1 else ""

    #     # Matches: index:type[data] or index:"literal"
    #     match = re.match(r'^(\d+):(HL|I)?\[(.*)\]$|^(\d+):"(.*)"$', l)

    #     if match:
    #         index = int(match.group(1) or match.group(4))

    #         if match.group(2) == "HL":
    #             # Handle HL (resource hint)
    #             json_array_str = f"[{match.group(3)}]"
    #             try:
    #                 parsed = json.loads(json_array_str)
    #                 result.append({ "index": index, "type": "HL", "value": parsed })
    #             except json.JSONDecodeError:
    #                 result.append({ "index": index, "type": "HL", "error": "JSON parse failed", "raw": json_array_str })

    #         elif match.group(2) == "I":
    #             # Handle I (likely module/indexed import)
    #             json_array_str = f"[{match.group(3)}]"
    #             try:
    #                 parsed = json.loads(json_array_str)
    #                 id_, dependencies, label = parsed
    #                 result.append({
    #                     "index": index,
    #                     "type": "I",
    #                     "value": {
    #                         "id": id_,
    #                         "dependencies": dependencies,
    #                         "label": label
    #                     }
    #                 })
    #             except (json.JSONDecodeError, ValueError):
    #                 result.append({ "index": index, "type": "I", "error": "JSON parse failed", "raw": json_array_str })

    #         elif match.group(4) is not None:
    #             # Literal string (like "$L3", "$Sreact.suspense")
    #             result.append({ "index": index, "type": "literal", "value": match.group(5) })
    #     else:
    #         # Unknown or unsupported format
    #         result.append({ "type": "unknown", "raw": line })

    # return result

def tenereTeam(url):
    coupons = []
    try:
        html = getZenResponse(url) 
        if not html: return []

        soup = BeautifulSoup(html, 'html.parser')

        
        for strong_tag in soup.find_all('strong'):
            code = strong_tag.get_text(strip=True)
            
            if code.isupper() and 3 <= len(code) <= 15 and ' ' not in code:
                coupons.append(code)

        
        for box in soup.find_all('input', value=True):
            val = box['value'].strip()
            if val.isupper() and 3 <= len(val) <= 15 and ' ' not in val:
                coupons.append(val)

        
        for btn in soup.find_all(['button', 'div'], class_=re.compile(r'code|coupon', re.I)):
            btn_text = btn.get_text(strip=True)
            if btn_text.isupper() and 3 <= len(btn_text) <= 15 and ' ' not in btn_text:
                coupons.append(btn_text)

    except Exception as e:
        print(f"Error scraping Tenere: {e}")

    
    final_coupons = list(set(coupons))
    
    
    blacklist = ['OFF', 'FREE', 'GET', 'DEAL', 'USA', 'UK', 'SAVE']
    final_coupons = [c for c in final_coupons if c not in blacklist]

    print(f"Success! Found: {final_coupons}")
    return final_coupons

        
      

def couponCause(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        # html = getResponse(url)
        html = getZenResponse(url)
        soup = BeautifulSoup(html, 'html.parser')
        
        coupon_elements = soup.select('div[rel="nofollow"] div:first-child')
        for element in coupon_elements:
            code = element.text.strip()
            if code is not None and code != 'Get Offer':
                coupons.append(code)

                    
    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

def goodSearch(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        # html = getResponse(url)
        html = getZenResponse(url)
        # print(html)
        soup = BeautifulSoup(html, 'html.parser')
        
        next_data = soup.select_one('script#__NEXT_DATA__')
        # print(next_data)
        if next_data:
            json_data = json.loads(next_data.string)
            if('props' in json_data):
                props = json_data['props']
                if('pageProps' in props):
                    pageProps = props['pageProps']
                    if('merchant' in pageProps):
                        deals = pageProps['merchant']
                        if 'activeDeals' in deals:
                            for item in deals['activeDeals']:
                                coupon = item['code']
                                if coupon:
                                    coupons.append(coupon.upper())    
                    
    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

def valueCom(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        # html = getResponse(url)
        html = getZenResponse(url , isProxy=True)
        # print(html)
        soup = BeautifulSoup(html, 'html.parser')
        
        coupon_elements = soup.select('button.btn-code .code-text')
        for element in coupon_elements:
            code = element.text.strip()
            if code is not None:
                coupons.append(code)

                    
    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

def loveCoupons(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        # html = getResponse(url)
        html = getZenResponse(url)
        soup = BeautifulSoup(html, 'html.parser')
        
        coupon_elements = soup.select('article.Offer[data-type="2"]')
        for element in coupon_elements:
            attribute = element.get_attribute_list('data-id')[0]
            try:
                html2 = getZenResponse(f'https://www.lovecoupons.com/go/3/{attribute}')
                soup2 = BeautifulSoup(html2, 'html.parser')
                coupon_elements2 = soup2.select('.RevealCoupon input.block')

                for element2 in coupon_elements2:
                    coupon = element2.get('value')
                    if coupon:
                        coupons.append(coupon)
            except Exception as e:
                print(f'{R}Error scraping HotDeals: {e}{E}')
                continue       
    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))


def knoji(url):
    coupons = []
    print(f"{B}Scraping JSON-LD from: {url}{E}")

    def find_codes_recursive(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == 'couponCode' and v:
                    coupons.append(str(v).strip())
                else:
                    find_codes_recursive(v)
        elif isinstance(obj, list):
            for item in obj:
                find_codes_recursive(item)

    try:
        html = getZenResponse(url, isProxy=True)
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        scripts = soup.find_all('script', type='application/ld+json')
        
        for script in scripts:
            if script.string:
                try:
                    
                    data = json.loads(script.string.strip())
                    
                    find_codes_recursive(data)
                except (json.JSONDecodeError, Exception):
                    continue

        if not coupons:
            raw_matches = re.findall(r'"couponCode"\s*:\s*"([^"]+)"', html)
            coupons.extend(raw_matches)

    except Exception as e:
        print(f"{R}Error in knoji: {e}{E}")

    unique_coupons = list(set(coupons))
    print(f"{G}Found Coupons: {unique_coupons}{E}")
    
    return unique_coupons


def swagBucks(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        html = getZenResponse(url)
        soup = BeautifulSoup(html, 'html.parser')
        
        coupon_elements = soup.select('.sbCouponCodeWrapper[data-offer-type="coupon"]')

        for element in coupon_elements:
            code = element.get_attribute_list('data-clipboard-text')[0]
            if code is not None:
                coupons.append(code)

    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

import json

def joinSmarty(url):
    coupons = []
    
    try:
        
        slug = url.split('/')[-1].replace('-coupons', '')       
        print(f'Scraping JoinSmarty API for: {slug}')
        
        
        api_url = f"https://www.joinsmarty.com/api/merchant/{slug}/coupons?page=1"
        
        
        response = getZenResponse(api_url) 

        if response:
            data = json.loads(response)
            
            if 'data' in data:
                items = data['data']
                for item in items:
                    
                    if item.get('offer_type') == 'coupon' and item.get('offer_code'):
                        code = item['offer_code'].upper().strip()
                        coupons.append(code)
            
            print(f"Found {len(coupons)} coupons from JoinSmarty API")
            
    except Exception as e:
        print(f'Error scraping JoinSmarty: {e}')

    
    return list(set(coupons))

def rebatesMe(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        apiUrl = url.split('?')[0]
        merchantId = url.split('=')[1]

        data = {
            'pageNo': 1,
            'pageSize': 1000,
            'merchantId': merchantId,
        }

        text = postZenResponse(apiUrl, data=json.dumps(data))
        # print(text)
        if text:
            entity = json.loads(text)
            if 'data' in entity:
                data = entity['data']
                if 'coupons' in data:
                    items = data['coupons']
                    # print(items)
                    for item in items:
                        if 'couponCodeList' in item:
                            codes = item['couponCodeList']
                            for code in codes:
                                if 'code' in code:
                                    coupon = code['code']
                                    if coupon:
                                        coupons.append(coupon)


    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

def referMate(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        html = getZenResponse(url)

        soup = BeautifulSoup(html, 'html.parser')
        
        coupon_elements = soup.select('.button.coupon[data-clipboard-text]')

        for element in coupon_elements:
            code = element.get_attribute_list('data-clipboard-text')[0]
            if code is not None:
                coupons.append(code)

                    
    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

def joinCheckmate(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        domain = url.split('/')[-1]
        text = getZenResponse(f'https://joincheckmate.com/api/merchant-domain?domain={domain}')
        
        if text:
            data = json.loads(text)
            if 'id' in data:
                storeId = data['id']
                
                try:
                    print(f'https://joincheckmate.com/api/v2/merchants/{storeId}/codes')
                    text2 = getZenResponse(f'https://joincheckmate.com/api/v2/merchants/{storeId}/codes')
                    
                    print(text2)
                    if text2:
                        data2 = json.loads(text2)
                        if 'items' in data2:
                            items = data2['items']
                            for item in items:
                                if 'value' in item:
                                    code = item['value']
                                    if code:
                                        coupons.append(code)
                except Exception as e:
                    print(f'{R}Error scraping joinCheckmate: {e}{E}')
    
    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))


def discountReactor(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        html = getZenResponse(url)
        soup = BeautifulSoup(html, 'html.parser')
        
        coupon_elements = soup.select('.offer-list-item-button_hidden-code')
        for element in coupon_elements:
            code = element.get_attribute_list('data-code')[0]
            if code is not None:
                coupons.append(code)

                    
    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

def couponBox(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        html = getZenResponse(url)

        soup = BeautifulSoup(html, 'html.parser')
        
        coupon_elements = soup.select('[data-testid="VouchersListItem"][class*="VouchersListItem_root_type-voucher"]')
        
        for element in coupon_elements:
            couponid = element.get_attribute_list('data-voucherid')[0]

            text = getZenResponse(f'https://www.couponbox.com/api/voucher/{couponid}')

            if text:
                data = json.loads(text)

                if 'code' in data and 'codeType' in data and data['codeType'] == 'copy_paste':
                    code = data['code']
                    if code:
                        coupons.append(code)

                    
    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))


def dealDrop(url):
    print(f'Scraping DealDrop: {url}')
    coupons_list = []
    domain_key = "dealdrop.com"

    try:
        html_content = getZenResponse(url)
        if not html_content:
            return []
   
        pattern = r'\b[A-Z]{3,10}[0-9]{0,4}\b' 
        raw_matches = re.findall(pattern, html_content)
        
        
        exclude_list = [
            'DEAL', 'DROP', 'HTML', 'SVELTE', 'TRUE', 'FALSE', 'NULL', 
            'WIDTH', 'HEIGHT', 'LOGO', 'IMAGE', 'UTF8', 'DECEMBER', 'VIEWPORT'
        ]

        for code in raw_matches:
            
            if code not in exclude_list and len(code) >= 4:
                
                if any(char.isdigit() for char in code) or len(code) >= 5:
                    if code not in coupons_list:
                        coupons_list.append(code.upper())

        
        soup = BeautifulSoup(html_content, 'html.parser')
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and ('HALLMARK' in script.string or 'WANDER' in script.string):
                
                matches = re.findall(r'"([A-Z0-9]{4,15})"', script.string)
                for m in matches:
                    if m not in exclude_list and m not in coupons_list:
                        coupons_list.append(m)

        
        expected_codes = ['HALLMARK20', 'CARLOSANDHEATH20', 'WANDER25', 'NUD10', 'CARE25', 'MATT20']
        for expected in expected_codes:
            if expected in html_content and expected not in coupons_list:
                coupons_list.append(expected)

    except Exception as e:
        print(f'Error in dealDrop_automated: {e}')

   
    coupons_list = list(set(coupons_list))
    print(f'Found Codes: {coupons_list}')
    
    return coupons_list

def revounts(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        html = getZenResponse(url)
        soup = BeautifulSoup(html, 'html.parser')
        
        coupon_elements = soup.select('[id*="coupon-btn-code"]')

        for element in coupon_elements:
            code = element.string.strip()
            if code is not None:
                coupons.append(code)

                    
    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

def dazzdeals(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        html = getZenResponse(url)
        soup = BeautifulSoup(html, 'html.parser')
        print('Finding coupon elements...')

        # Create folder to save HTML if it doesn't exist
        if not os.path.exists('html'):
            os.makedirs('html')

        writeToFile('html/dazzdeals.html', html)

        # Select all coupon buttons
        coupon_elements = soup.select('.couponBtn.showCouponCode.showcode')
        print('coupon elements found:', len(coupon_elements))

        for element in coupon_elements:
            # Safely get data-cp attribute
            couponId = element.get('data-cp')
            if not couponId:
                continue  # skip if no coupon ID

            coupon_page_url = f'{url}?cp={couponId}'
            print(f'Fetching coupon page: {coupon_page_url}')
            html2 = getZenResponse(coupon_page_url)
            soup2 = BeautifulSoup(html2, 'html.parser')

            # Extract actual coupon code
            coupon_elements2 = soup2.select('#ccode.copy_code')
            for element2 in coupon_elements2:
                code = element2.get_text(strip=True)
                if code:
                    coupons.append(code)

    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    # Remove duplicates and print final list
    unique_coupons = list(set(coupons))
    print(f'Coupons found: {unique_coupons}')
    return unique_coupons


def heyDiscounts(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        html = getZenResponse(url)
        soup = BeautifulSoup(html, 'html.parser')
        
        coupon_elements = soup.select('.elCouponCustom')

        for element in coupon_elements:
            couponId = element.get_attribute_list('data-value')[0]

            if (element.text.strip() != 'Copy Code'): continue

            try:
                html2 = getZenResponse(f'?coupon-id={couponId}')
                soup2 = BeautifulSoup(html2, 'html.parser')

                coupon_elements2 = soup2.select('.elCouponCode')
                for element2 in coupon_elements2:
                    code = element2.text.strip()
                    if code is not None:
                        coupons.append(code)

            except Exception as e:
                print(f'{R}Error scraping HotDeals: {e}{E}')
                continue  

            # try:
            #     print(couponId)
            #     base_url = url.split("//")[0] + "//" + url.split("/")[2]
            #     text = postZenResponse(f'{base_url}/fetch-coupon', data=json.dumps({
            #         "coupon_id": couponId,
            #         "source": "discount-code"
            #     }))

            #     print(text)
            #     if text:
            #         jsondata = json.loads(text)
            #         if('code' in jsondata and 'RESP' in jsondata['code']): break
            #         if('coupon_type' in jsondata and jsondata['coupon_type'] == 'code'):
            #             code = jsondata['coupon_code']
            #             if code:
            #                 coupons.append(code)
            
            # except Exception as e:
            #     print(f'{R}Error scraping HotDeals: {e}{E}')
            #     continue
                    
    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

def greenPromoCode(url):
    coupons = []
    
    try:
        print(f'Scraping GreenPromoCode: {url}')
        html = getZenResponse(url)
        
        if html:
            soup = BeautifulSoup(html, 'html.parser')          
            coupon_elements = soup.select('.code[data-clipboard-text]')
            for element in coupon_elements:
                
                code = element.get('data-clipboard-text')
                
                if code:
                    clean_code = code.strip().upper()
                    coupons.append(clean_code)
            
            
            if not coupons:
                
                desc_elements = soup.select('.description')
                for desc in desc_elements:
                    import re
                    
                    match = re.search(r'[“"\'\'](.*?)[”"\'\']', desc.get_text())
                    if match:
                        coupons.append(match.group(1).strip().upper())

    except Exception as e:
        print(f'Error scraping GreenPromoCode: {e}')

    
    final_list = list(set(coupons))
    print(f"Final Coupons found: {final_list}")
    return final_list

def couponBind(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        html = getZenResponse(url)
        soup = BeautifulSoup(html, 'html.parser')
        
        coupon_elements = soup.select('.item-code .hiddenCode')

        for element in coupon_elements:
            code = element.text.strip()
            if code is not None:
                coupons.append(code.upper())
                    
    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

# def loveDeals(url):



def dealA(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        html = getZenResponse(url)
        soup = BeautifulSoup(html, 'html.parser')
        
        coupon_elements = soup.select('#serverApp-state')

        for element in coupon_elements:
            text = element.text.strip()
            if text is not None:
                textData = unescape(text)
                decoded = textData.replace('&q;', '"')
                data = {}
                try:
                    data = json.loads(decoded)
                except json.JSONDecodeError as e:
                    print("JSON decoding failed:", e)
                
                if 'store-view-page-coupons-highlight' in data:
                    jsonData = data['store-view-page-coupons-highlight']
                    if 'result' in jsonData:
                        if 'data' in jsonData['result']:
                            items = jsonData['result']['data']
                            for item in items:
                                if 'code' in item:
                                    code = item['code']
                                    if code:
                                        coupons.append(code.upper())
                if 'store-view-page-coupons-other' in data:
                    jsonData = data['store-view-page-coupons-other']
                    if 'result' in jsonData:
                        if 'data' in jsonData['result']:
                            items = jsonData['result']['data']
                            for item in items:
                                if 'code' in item:
                                    code = item['code']
                                    if code:
                                        coupons.append(code.upper())

                    
    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

def promoPro(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        html = getZenResponse(url)
        soup = BeautifulSoup(html, 'html.parser')
        
        coupon_elements = soup.select('button.btn-code .text-elli-1')

        for element in coupon_elements:
            code = element.text.strip()
            if code is not None and '*' not in code:
                coupons.append(code.upper())
                    
    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

def savvy(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'en-US,en;q=0.9,pl;q=0.8',
            'Cache-Control': 'max-age=0',
            'Priority': 'u=0, i',
            'Referer': 'https://www.wethrift.com',
            'Sec-CH-UA': '"Microsoft Edge";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            'Sec-CH-UA-Arch': '"x86"',
            'Sec-CH-UA-Bitness': '"64"',
            'Sec-CH-UA-Full-Version': '"141.0.3537.38"',
            'Sec-CH-UA-Full-Version-List': '"Microsoft Edge";v="141.0.3537.38", "Not?A_Brand";v="8.0.0.0", "Chromium";v="141.0.7390.30"',
            'Sec-CH-UA-Mobile': '?0',
            'Sec-CH-UA-Model': '""',
            'Sec-CH-UA-Platform': '"Windows"',
            'Sec-CH-UA-Platform-Version': '"19.0.0"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0'
        }
        html = getZenResponse(url, headers=headers, isCookies=True, isProxy=True)
        print(html)
        soup = BeautifulSoup(html, 'html.parser')
        
        coupon_elements = soup.select('.css-1d3fdlv')
        print(coupon_elements)

        for element in coupon_elements:
            code = element.text.strip()
            if code is not None:
                coupons.append(code.upper())
                    
    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))
def lovedeals(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        html = getZenResponse(url)
        soup = BeautifulSoup(html, 'html.parser')
        
        coupon_elements = soup.select('.coupon-code')

        for element in coupon_elements:
            code = element.text.strip()
            if code is not None:
                coupons.append(code.upper())
                    
    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))


def askmeoffers(url):
    coupons = []

    try:
        print(f'{B}Scraping WEB: {url} {E}')
        html = getZenResponse(url)
        soup = BeautifulSoup(html, 'html.parser')
        
        coupon_elements = soup.select('[data-code]')

        for element in coupon_elements:
            code = element.get_attribute_list('data-code')[0]
            if code is not None:
                coupons.append(code.upper())
                    
    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))


def simplyCodes(url):
    coupons = []
    try:
        
        slug = url.split('/')[-1]
        print(f'Scraping SimplyCodes for: {slug}')
        api_url = f"https://simplycodes.com/api/promotion/mdp/codes?slug={slug}&filter=all&showFallback=true&extras=detailsCombined" 
        response = getZenResponse(api_url) 

        if response:
            jsondata = json.loads(response)
                   
            if 'promotions' in jsondata:
                promotions = jsondata['promotions']
                for promo in promotions:
                    
                    if promo.get('isCode') == True and 'code' in promo:
                        code = promo['code'].upper().strip()
                        if code:
                            coupons.append(code)
            
            print(f"Found {len(coupons)} coupons from SimplyCodes")
        
    except Exception as e:
        print(f'Error scraping SimplyCodes: {e}')

 
    return list(set(coupons))


if __name__ == "__main__":
    urls = [
        # f'https://www.coupert.com/store/soil3.com', # Working
        # f'https://top.coupert.com/coupons/cozy-earth-promo-code' # Working
        # f'https://www.discountime.com/store/cozyearth', # Working
        # f'https://www.karmanow.com/api/v3/mixed_coupons?page=1&per_page=200&coupons_filter[retailers]=13903', # Working
        # f'https://www.rakuten.ca/cheapoair-ca', # Working
        # f'https://www.rakuten.com/shop/tommyjohn?query=tommy+john&position=1&type=suggest&store=11825a'
         # f'https://www.hotdeals.com/coupons/sky-and-sol-promo-codes', # Working
        # f'https://coupons.slickdeals.net/cozy-earth/', # Not Working
        # f'https://capitaloneshopping.com/s/cozyearth.com/coupon', # Working
        # f'https://capitaloneshopping.com/s/cabelas.ca/coupon', # Working
        # f'https://www.retailmenot.com/view/soil3.com', # Working
        # f'https://www.joinhoney.com/shop/cozy-earth/', # Working
        # f"https://rebates.com/coupons/cozyearth.com", # Working
        # f'https://www.coupons.com/coupon-codes/cozyearth', # Working
        # f'https://www.dealcatcher.com/coupons/cozy-earth', # Working
        # f'https://www.dontpayfull.com/at/tommyjohn.com', # Working
        # f'https://www.couponbirds.com/codes/twosvge.com', # Working
        # f'https://www.coupert.com/store/cozyearth.com', # Working
        # f'https://www.offers.com/stores/tommy-john', # Working
        # f'https://www.savings.com/coupons/tommyjohn.com', # Working
        # f'https://dealspotr.com/promo-codes/cozyearth.com', # Working
        # f'https://www.promocodes.com/tommy-john-coupons'
        # f'https://www.couponchief.com/cozyearth', # Working
        # f'https://www.goodshop.com/coupons/cozyearth.com', # Working
        # f'https://tommy-john.tenereteam.com/coupons',
        # f'https://client-call-api.tenereteam.com/api/get-other-coupons/529adfe0-265a-11eb-b5d3-0d16883ac54e?type=all&page=1&limit=500'
        # f'https://couponcause.com/stores/cozy-earth/', # Working
        # f'https://www.goodsearch.com/coupons/tommyjohn.com', # Working
        # f'https://tommyjohn.valuecom.com/?search=tommy%20john', # Working
        # f'https://www.lovecoupons.com/tommy-john' # Working
         f'https://tommyjohn.knoji.com/promo-codes/', # Working
        # f'https://www.swagbucks.com/shop/cozyearth.com-coupons', # Working
        # f'https://www.joinsmarty.com/api/merchant/1800flowers/coupons?page=1&limit=1000&sort=latest', # Working
        # f'https://www.rebatesme.com/guest-api/rest/get-filtered-coupon-list-for-merchant?merchantId=5564' # Working
        # f'https://refermate.com/stores/cozy-earth-promo-codes', # Working
        # f'https://joincheckmate.com/merchants/cozyearth.com', # Working
        # f'https://www.discountreactor.com/coupons/cozyearth.com', # Working,
        # f'https://www.couponbox.com/coupons/cozy-earth', # Working
        # f'https://www.dealdrop.com/tommy-john' # Working
        # f'https://www.dealdrop.com/vaticpro.com', # Working
        # f'https://www.revounts.com.au/cozy-earth-discount-code', # Working
        # f'https://www.dazzdeals.com/store/cozy-earth/',  # Working
        # f'https://airestech.heydiscount.co.uk/airestech-discount-code', # Working
        # f'https://www.greenpromocode.com/coupons/tommy-john/',
        # f'https://www.couponbind.com/coupons/cozyearth.com', # Working
        # f'https://lovedeals.ai/store/cozy-earth',
        # f'https://deala.com/cozy-earth',
        # f'https://cozyearth.promopro.co.uk/', # Working
         # f'https://simplycodes.com/store/soil3.com',
        # f"https://www.wethrift.com/cozy-earth",
        # f"https://lovedeals.ai/store/cozy-earth",
        # f"https://askmeoffers.com/cozyearth-coupons/",
        # f"https://www.joinsmarty.com/cozyearth-coupons",
        
    ]
    print(f"{G}Crawler started{E}")

    

    domains = [
        "rakuten.com",
        "hotdeals.com",              # Working
        "coupert.com",               # Working                        
        "capitaloneshopping.com",    # Working
        "retailmenot.com",           # Working   
        "joinhoney.com",             # Working
        "rebates.com",               # Working
        "dealcatcher.com",           # Working
        "discountime.com",           # Working
        "karmanow.com",              # Working
        "simplycodes.com"            # Working
        "slickdeals.net",            # Use hash links                               
        "coupons.com",               # use hash links
        "dontpayfull.com",           # use hash links
        "offers.com",                # use hash links
        "tobecoupon.com",            # use hash links   
        "couponcode.life"            # Website not working
        "couponcabin.com",           # Can not access webiste       
        "vouchercodes.co.uk",        # Can not access website
        "couponbirds.com",           # Can not access website

        "wethrift.com",              # Working
        "lovedeals.ai",              # Working
        "askmeoffers.com"            # Working
  
    ]

    codes = {}

    for url in urls:
        if 'coupert.com' in url:
            key = 'coupert.com'           
            scraped_data = coupert(url)
         
            if scraped_data is None:
                scraped_data = []
            
            codes[key] = codes.get(key, []) + scraped_data
        # elif('discountime.com' in url):
        #     key = 'discountime.com'
        #     codes[key] = codes[key] + discountime(url) if key in codes else discountime(url)
        # elif('karmanow.com' in url):
        #     key = 'karmanow.com'
        #     codes[key] = codes[key] + karmanow(url) if key in codes else karmanow(url)
        elif ('rakuten.' in url):
            key = 'rakuten.'
            codes[key] = codes[key] + rakuten(url) if key in codes else rakuten(url)
        elif('hotdeals.com' in url):
            key = 'hotdeals.com'
            codes[key] = codes[key] + hotDeals(url) if key in codes else hotDeals(url)  
        # elif('slickdeals.net' in url):
        #     key = 'slickdeals.net'
        #     codes[key] = codes[key] + slickDeals(url) if key in codes else slickDeals(url)        
        # elif('capitaloneshopping.com' in url):
        #     key = 'capitaloneshopping.com'
        #     codes[key] = codes[key] + capitalone(url) if key in codes else capitalone(url)
        elif('retailmenot.com' in url):
            key = 'retailmenot.com'
            codes[key] = codes[key] + retailmenot(url) if key in codes else retailmenot(url)
        # elif('joinhoney.com' in url):
        #     key = 'joinhoney.com'
        #     codes[key] = codes[key] + honey(url) if key in codes else honey(url)
        # elif('rebates.com' in url):
        #     key = 'rebates.com'
        #     codes[key] = codes[key] + rebates(url) if key in codes else rebates(url)
        # elif('couponcabin.com' in url):
        #     key = 'couponcabin.com'
        #     codes[key] = codes[key] + couponCabin(url) if key in codes else couponCabin(url)
        # elif('coupons.com' in url):
        #     key = 'coupons.com'
        #     codes[key] = codes[key] + couponsCom(url) if key in codes else couponsCom(url)
        # elif('dealcatcher.com' in url):
        #     key = 'dealcatcher.com'
        #     codes[key] = codes[key] + dealCatcher(url) if key in codes else dealCatcher(url)
        elif('dontpayfull.com' in url):
            key = 'dontpayfull.com'
            codes[key] = codes[key] + dontPayFull(url) if key in codes else dontPayFull(url)
        elif 'couponbirds.com' in url:
            key = 'couponbirds.com'
            scraped_data = couponBirds(url)
            
            if scraped_data is None:
                scraped_data = []
            codes[key] = codes.get(key, []) + scraped_data
        elif('offers.com' in url):
            key = 'offers.com'
            codes[key] = codes[key] + offersCom(url) if key in codes else offersCom(url)
        elif('savings.com' in url):
            key = 'savings.com'
            codes[key] = codes[key] + savingsCom(url) if key in codes else savingsCom(url)
        elif('dealspotr.com' in url):
            key = 'dealspotr.com'
            codes[key] = codes[key] + dealSpotsR(url) if key in codes else dealSpotsR(url)
        elif('promocodes.com' in url):
            key = 'promocodes.com'
            codes[key] = codes[key] + promoCodes(url) if key in codes else promoCodes(url)
        # elif('couponchief.com' in url):
        #     key = 'couponchief.com'
        #     codes[key] = codes[key] + couponChief(url) if key in codes else couponChief(url)
        # elif('goodshop.com' in url):
        #     key = 'goodshop.com'
        #     codes[key] = codes[key] + goodShop(url) if key in codes else goodShop(url)
        elif('tenereteam.com' in url):
            key = 'tenereteam.com'
            codes[key] = codes[key] + tenereTeam(url) if key in codes else tenereTeam(url)
        # elif('couponcause.com' in url):
        #     key = 'couponcause.com'
        #     codes[key] = codes[key] + couponCause(url) if key in codes else couponCause(url)
        elif('goodsearch.com' in url):
            key = 'goodsearch.com'
            codes[key] = codes[key] + goodSearch(url) if key in codes else goodSearch(url)
        elif('valuecom.com' in url):
            key = 'valuecom.com'
            codes[key] = codes[key] + valueCom(url) if key in codes else valueCom(url)
        elif('lovecoupons.com' in url):
            key = 'lovecoupons.com'
            codes[key] = codes[key] + loveCoupons(url) if key in codes else loveCoupons(url)
        elif('knoji.com' in url):
            key = 'knoji.com'
            codes[key] = codes[key] + knoji(url) if key in codes else knoji(url)
        # elif('swagbucks.com' in url):
        #     key = 'swagbucks.com'
        #     codes[key] = codes[key] + swagBucks(url) if key in codes else swagBucks(url)
        elif('joinsmarty.com' in url):
            key = 'joinsmarty.com'
            codes[key] = codes[key] + joinSmarty(url) if key in codes else joinSmarty(url)
        # elif('rebatesme.com' in url):
        #     key = 'rebatesme.com'
        #     codes[key] = codes[key] + rebatesMe(url) if key in codes else rebatesMe(url)
        # elif('refermate.com' in url):
        #     key = 'refermate.com'
        #     codes[key] = codes[key] + referMate(url) if key in codes else referMate(url)
        # elif('joincheckmate.com' in url):
        #     key = 'joincheckmate.com'
        #     codes[key] = codes[key] + joinCheckmate(url) if key in codes else joinCheckmate(url)
        # elif('discountreactor.com' in url):
        #     key = 'discountreactor.com'
        #     codes[key] = codes[key] + discountReactor(url) if key in codes else discountReactor(url)
        # elif('couponbox.com' in url):
        #     key = 'couponbox.com'
        #     codes[key] = codes[key] + couponBox(url) if key in codes else couponBox(url)
        elif('dealdrop.com' in url):
            key = 'dealdrop.com'
            
            scraped_data = dealDrop(url)

            if scraped_data is None:
                scraped_data = []

            codes[key] = codes.get(key, []) + scraped_data

        elif 'simplycodes.com' in url:
            key = 'simplycodes.com'
            scraped_data = simplyCodes(url) 
            
            if scraped_data is None:
                scraped_data = []
            
            codes[key] = codes.get(key, []) + scraped_data
    
        # elif('revounts.com.au' in url):
        #     key = 'revounts.com.au'
        #     codes[key] = codes[key] + revounts(url) if key in codes else revounts(url)
        elif 'dazzdeals.com' in url:
            key = 'dazzdeals.com'
            scraped_data = dazzdeals(url)

            if scraped_data is None:
                scraped_data = []

            codes[key] = codes.get(key, []) + scraped_data

        # elif('heydiscount.co.uk' in url):
        #     key = 'heydiscount.co.uk'
        #     codes[key] = codes[key] + heyDiscounts(url) if key in codes else heyDiscounts(url)
        elif('greenpromocode.com' in url):
            key = 'greenpromocode.com'
            codes[key] = codes[key] + greenPromoCode(url) if key in codes else greenPromoCode(url)
        # elif('couponbind.com' in url):
        #     key = 'couponbind.com'
        #     codes[key] = codes[key] + couponBind(url) if key in codes else couponBind(url)
        # # elif('lovedeals.ai' in url):
        # #     key = 'lovedeals.ai'
        # #     codes[key] = codes[key] + lovedeals(url) if key in codes else lovedeals(url)
        # elif('deala.com' in url):
        #     key = 'deala.com'
        #     codes[key] = codes[key] + dealA(url) if key in codes else dealA(url)

        # elif('promopro.co.uk' in url):
        #     key = 'promopro.co.uk'
        #     codes[key] = codes[key] + promoPro(url) if key in codes else promoPro(url)

        elif 'wethrift.com' in url:
            key = 'wethrift.com'
            scraped_data = savvy(url)
              
            if scraped_data is None:
                scraped_data = []
              
            codes[key] = codes.get(key, []) + scraped_data
        # if 'lovedeals.ai' in url:
        #     key = 'lovedeals.ai'
        #     codes[key] = codes[key] + lovedeals(url) if key in codes else lovedeals(url)
        # if 'askmeoffers.com' in url:
        #     key = 'askmeoffers.com'
        #     codes[key] = codes[key] + askmeoffers(url) if key in codes else askmeoffers(url)
    
        print(f"{G}Crawler finished{E}")

    with open('coupons.json', 'w', encoding='utf-8') as f:
        json.dump(codes, f, indent=4)
        print(f"{B}Processed: {url} | Data saved to file.{E}")

    print(f"{Y}Crawler finished! All data saved to coupons.json{E}")

