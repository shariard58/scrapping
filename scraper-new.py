import re
import json
import base64
import asyncio
import njsparser

from bs4 import BeautifulSoup
from zenrows import ZenRowsClient
from urllib.parse import urlparse, parse_qs


params = {
    "wait": "5000",
    "js_render": "true",
    "proxy_country":"us",
    "premium_proxy":"true",
    "custom_headers": "true",
}

headers = {
    "Referer": "https://www.google.com",
}

# Console Colors
R = '\033[31m'
G = '\033[32m'
Y = '\033[33m'
B = '\033[34m'
E = '\033[0m'

client = ZenRowsClient("fa0f561cee2fa9ba7976f152b852a663fdcd8791", concurrency=5, retries=1)

def writeToFile(filename, data):
    with open(filename, 'w',  encoding='utf-8') as file:
        if(data): file.write(data)

def coupert(html):
    coupons = []

    try:
        soup = BeautifulSoup(html, 'html.parser')

        next_data = soup.select_one('script#__NEXT_DATA__')
        if next_data:
            print("Next Data found")
            json_data = json.loads(next_data.string)
            print(json.dumps(json_data))
            if('props' in json_data):
                props = json_data['props']
                if('pageProps' in props):
                    pageProps = props['pageProps']
                    if('storeInfo' in pageProps):
                        storeInfo = pageProps['storeInfo']
                        if('coupons' in storeInfo):
                            for item in storeInfo['coupons']:
                                coupon = item['code']
                                if coupon:
                                    coupons.append(coupon.upper())
        
        nuxt_data = soup.select_one('script#__NUXT_DATA__')
        if nuxt_data:           
            json_data = json.loads(nuxt_data.string)
            if len(json_data) > 0:
                for item in json_data:
                    if type(item) is str:
                        dataJson = {}
                        try:
                            dataText = base64.b64decode(item).decode('utf-8')
                            dataJson = json.loads(dataText)
                        except Exception as e:
                            continue
                        
                        if "merchant_coupons" in dataJson:
                            couponsItem = dataJson['merchant_coupons']
                            for itm in couponsItem:
                                if "code" in itm:
                                    if itm['code']:
                                        coupons.append(itm['code'].upper())

    except Exception as e:
        print(f'{R}Error scraping coupert: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

def hotDeals(html):
    coupons = []
    try:
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

def capitalone(html):
    coupons = []

    try:
        writeToFile('html/capitalone.html', html)
        soup = BeautifulSoup(html, 'html.parser')

        # Extract JSON data embedded in a script
        # script_tag = soup.find('script', string=lambda t: t and 'window.initialState' in t)
        script_tag = soup.find('script', string=lambda t: t and 'window.__remixContext' in t)
        script_txt = script_tag.text.strip()

        # print(script_tag.text.strip())
        # pattern = r"window\.initialState\s*=\s*({.*?});"
        pattern = r"window\.__remixContext\s*=\s*({.*?});"

        # Extract the match
        match = re.search(pattern, script_txt)
        # print(match)
        if match:
            json_text = match.group(1)
            json_data = json.loads(json_text)
            
            json_data = json_data['state']['loaderData']['routes/__app/s.$store.coupon']

            
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

def honey(html):
    coupons = []
    
    try:
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

def rebates(html):
    coupons = []

    try:
        soup = BeautifulSoup(html, 'html.parser')

        coupon_elements = soup.select('.couponModal[data-code]')

        for element in coupon_elements:
            coupon = element.get_attribute_list('data-code')[0]
            if coupon: coupons.append(coupon.upper())
                    
    except Exception as e:
        print(f'{R}Error scraping rebates: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

def couponsCom(html):
    fd = None
    coupons = []

    try:
        fd = njsparser.BeautifulFD(html)
    except Exception as e:
        print(f'{R}Error initializing njsparser: {e}{E}')
    
    try:
        for data in fd.find_iter([njsparser.Element]):
            value = data.value
            if type(value) is dict:
                if "voucherTypeName" in value and value["voucherTypeName"] == "Code":
                    if 'code' in value and value['code']:
                        code = value['code']
                        if code:
                            coupons.append(code.upper())
    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

def karmanow(response):
    coupons = []

    try:
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

def dealCatcher(html):
    coupons = []

    try:
        soup = BeautifulSoup(html, 'html.parser')

        coupon_elements = soup.select('.coupon-card .promo-code')
        for element in coupon_elements:
            code = element.text.strip()
            if code and code is not None:
                coupons.append(code)

                    
    except Exception as e:
        print(f'{R}Error scraping HotDeals: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

async def retailmenot(html):
    coupons = []

    try:
        urls = []
        soup = BeautifulSoup(html, 'html.parser')
        coupon_elements = soup.select('a[data-content-datastore="offer"]')

        for element in coupon_elements:
            xdata = element.get_attribute_list('x-data')[0]
            href = element.get('href')

            if xdata and href:
                jsonData = json.loads(xdata.replace("outclickHandler({", '{').replace("})", '}').replace("'", '"'))
                parsedUrl = urlparse(href)
                queryParams = parse_qs(parsedUrl.query)

                if 'offerType' in jsonData:
                    offerType = jsonData['offerType']
                    if offerType == 'COUPON':
                        template = queryParams.get('template')[0]
                        offerId = queryParams.get('offer_uuid')[0]
                        merchantId = queryParams.get('merchant_uuid')[0]


                        urls.append(f'https://www.retailmenot.com/modals/outclick/{offerId}/?template={template}&trigger=entrance_modal&merchant={merchantId}')

        try:
            responses = await asyncio.gather(*[client.get_async(url, params=params, headers=headers) for url in urls])

            for response in responses:
                html2 = response.text
                jsonData = json.loads(html2)

                if 'modalHtml' in jsonData:
                    modalHtml = jsonData['modalHtml']
                    soup2 = BeautifulSoup(modalHtml, 'html.parser')
                    
                    coupon_elements2 = soup2.select('[x-show="outclicked"] div[x-data]')
                    
                    for element2 in coupon_elements2:
                        code = element2.text.strip()
                        code = code.replace('COPY', '').strip()
                        if code is not None:
                            coupons.append(code)
        except Exception as e:
            print(f'{R}Error scraping retailmenot: {e}{E}')

    except Exception as e:
        print(f'{R}Error scraping retailmenot: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

async def couponBirds(html):
    global cookies
    coupons = []

    try:
        urls = []
        soup = BeautifulSoup(html, 'html.parser')
        coupon_elements = soup.select('.get-code a[data-url]')
        
        for element in coupon_elements:
            attribute = element.get_attribute_list('data-url')[0]
            
            if attribute:
                urls.append(attribute)
        
        try:
            responses = await asyncio.gather(*[client.get_async(url, params=params, headers=headers) for url in urls])

            for response in responses:
                html2 = response.text
                soup2 = BeautifulSoup(html2, 'html.parser')

                coupon_elements2 = soup2.select('.modal-body .cp-code input#copy-recommend-code')
                for element2 in coupon_elements2:
                    code = element2.get('value')
                    if code is not None:
                        coupons.append(code)
        except Exception as e:
            print(f'{R}Error scraping couponBirds: {e}{E}')

    except Exception as e:
        print(f'{R}Error scraping couponBirds: {e}{E}')
    
    cookies = None
    print(f'{list(set(coupons))}')
    return list(set(coupons))

async def offersCom(html, url):
    coupons = []

    try:
        urls = []
        soup = BeautifulSoup(html, 'html.parser')
        elements1 = soup.select('[data-offer-id] > [data-content-datastore="offer"]')
        
        for element in elements1:
            attribute1 = element.get_attribute_list('x-data')[0]
            attribute2 = element.get_attribute_list('@click.prevent')[0]

            if attribute1: 
                offerId = attribute1.split("'")[1]
                hasCode = 'hasCode: true' in attribute2
                if hasCode:
                    urls.append(f'{url}?em={offerId}')

        try:
            responses = await asyncio.gather(*[client.get_async(url, params=params, headers=headers) for url in urls])

            for response in responses:
                html2 = response.text
                soup2 = BeautifulSoup(html2, 'html.parser')
                
                elements2 = soup2.select('[x-data="commerceModal"] [x-data]')

                for element2 in elements2:
                    codeAttribute = element2.get_attribute_list('x-data')[0]
                    coupon = codeAttribute.split("'")[3]
                    if coupon:
                        coupons.append(coupon)
        except Exception as e:
            print(f'{R}Error scraping offers.com: {e}{E}')
                    
    except Exception as e:
        print(f'{R}Error scraping offers.com: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

async def savingsCom(html):
    coupons = []

    try:
        urls = []
        soup = BeautifulSoup(html, 'html.parser')
        coupon_elements = soup.select('.module-deal.showValue.codePeek[data-offer-id]')
        
        for element in coupon_elements:
            attribute = element.get_attribute_list('id')[0]
            try:
                couponId = attribute.split('-')[-1]
                urls.append(f'https://www.savings.com/popup/detail/coupon-{couponId}.html')

            except Exception as e:
                print(f'{R}Error scraping savings.com: {e}{E}')
                continue
        
        try:
            responses = await asyncio.gather(*[client.get_async(url, params=params, headers=headers) for url in urls])

            for response in responses:
                html2 = response.text
                soup2 = BeautifulSoup(html2, 'html.parser')
                coupon_elements2 = soup2.select('.code-wrapper input.code')
                for element2 in coupon_elements2:
                    coupon = element2.get('value')
                    if coupon:
                        coupons.append(coupon)
        except Exception as e:
            print(f'{R}Error scraping savings.com: {e}{E}')
                    
    except Exception as e:
        print(f'{R}Error scraping savings.com: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

async def dontPayFull(html):
    coupons = []

    try:
        urls = []
        soup = BeautifulSoup(html, 'html.parser')
        coupon_elements = soup.select('.card.obox.code[data-otype="code"]')

        for element in coupon_elements:
            idAttribute = element.get_attribute_list('data-id')[0]
            classAttribute = element.get_attribute_list('class')[0]
            if 'sponsored' not in classAttribute:
                urls.append(f'https://www.dontpayfull.com/coupons/getcoupon?id={idAttribute}')

        try:
            responses = await asyncio.gather(*[client.get_async(url, params=params, headers=headers) for url in urls])

            for response in responses:
                html2 = response.text
                soup2 = BeautifulSoup(html2, 'html.parser')

                coupon_elements2 = soup2.select('.code-box.code h2')
                for element2 in coupon_elements2:
                    code = element2.text.strip()
                    if code is not None:
                        coupons.append(code)
        except Exception as e:
            print(f'{R}Error scraping dontPayFull: {e}{E}')
                    
    except Exception as e:
        print(f'{R}Error scraping dontPayFull: {e}{E}')

    print(f'{list(set(coupons))}')
    return list(set(coupons))

urls = [
    #  f"https://usa.hotdeals.com/store/tommy-john-coupons/",
    # f"https://www.coupert.com/store/tommyjohn.com",
    # f"https://coupons.slickdeals.net/cozy-earth",
    # f"https://capitaloneshopping.com/s/tommyjohn.com/coupon",
    # f"https://www.retailmenot.com/view/nobullproject.com",
    # f"https://www.joinhoney.com/shop/tommy-john",
    # f"https://rebates.com/coupons/tommyjohn.com",
    # f"https://www.coupons.com/coupon-codes/nobull",
    # f"https://www.karmanow.com/api/v3/mixed_coupons?page=1&per_page=200&coupons_filter[retailers]=10018",
    # f"https://www.dealcatcher.com/coupons/cozy-earth",
    # f"https://www.dontpayfull.com/at/tommyjohn.com",
    # f"https://www.couponbirds.com/codes/tommyjohn.com",
    # f"https://www.offers.com/stores/tommy-john/",
    # f"https://dealspotr.com/promo-codes/tommyjohn.com",

    # f'https://www.rakuten.ca/cheapoair-ca', # Working
    # f'https://www.coupert.com/store/trycreate.co', # Working
     f'https://top.coupert.com/coupons/blackbrooks.co.uk', # Working
    #f'https://usa.hotdeals.com/store/cozy-earth-promo-codes', # Working
    # f'https://coupons.slickdeals.net/cozy-earth/', # Not Working
    #f'https://capitaloneshopping.com/s/currentbody.com/coupon', # Working
    #f'https://www.retailmenot.com/view/originalgrain.com', # Working
    # f'https://www.joinhoney.com/shop/cozy-earth/', # Working
    #f"https://www.joinhoney.com/shop/tommy-john",
    #f"https://rebates.com/coupons/cozyearth.com", # Working
    #f'https://www.coupons.com/coupon-codes/cozyearth', # Working
    #f'https://www.karmanow.com/api/v3/mixed_coupons?page=1&per_page=200&coupons_filter[retailers]=13903', # Working
    #f'https://www.dealcatcher.com/coupons/cozy-earth', # Working
    #f'https://www.dontpayfull.com/at/cozyearth.com', # Working
    #f'https://www.couponbirds.com/codes/twosvge.com', # Working
    #f'https://www.offers.com/stores/cozyearth/', # Working
    #f'https://www.savings.com/coupons/ashleystewart.com', # Working
]


async def main():
    responses = await asyncio.gather(*[client.get_async(url, params=params, headers=headers) for url in urls])
    codes = {}
    
    for response in responses:
        parsedUrl = urlparse(response.request.url)
        queryParams = parse_qs(parsedUrl.query)
        originalURL = queryParams['url'][0]

        print(originalURL)
        html = response.text
        # print(html)

        if('coupert.com' in originalURL):
            key = 'coupert.com'
            codes[key] = codes[key] + coupert(html) if key in codes else coupert(html)
        if('hotdeals.com' in originalURL):
            key = 'hotdeals.com'
            codes[key] = codes[key] + hotDeals(html) if key in codes else hotDeals(html)
        if('capitaloneshopping.com' in originalURL):
            key = 'capitaloneshopping.com'
            codes[key] = codes[key] + capitalone(html) if key in codes else capitalone(html)
        if('dealcatcher.com' in originalURL):
            key = 'dealcatcher.com'
            codes[key] = codes[key] + dealCatcher(html) if key in codes else dealCatcher(html)
        if('karmanow.com' in originalURL):
            key = 'karmanow.com'
            codes[key] = codes[key] + karmanow(html) if key in codes else karmanow(html)
        # if('coupons.com' in originalURL):
        #     key = 'coupons.com'
        #     codes[key] = codes[key] + couponsCom(html) if key in codes else couponsCom(html)
        if('joinhoney.com' in originalURL):
            key = 'joinhoney.com'
            codes[key] = codes[key] + honey(html) if key in codes else honey(html)

        if('rebates.com' in originalURL):
            key = 'rebates.com'
            codes[key] = codes[key] + rebates(html) if key in codes else rebates(html)

        if ('retailmenot.com' in originalURL):
            key = 'retailmenot.com'
            codes[key] = codes[key] + (await retailmenot(html)) if key in codes else (await retailmenot(html))

        if ('dontpayfull.com' in originalURL):
            key = 'dontpayfull.com'
            codes[key] = codes[key] + (await dontPayFull(html)) if key in codes else (await dontPayFull(html))  
        
        if ('couponbirds.com' in originalURL):
            key = 'couponbirds.com'
            codes[key] = codes[key] + (await couponBirds(html)) if key in codes else (await couponBirds(html))

        if ('offers.com' in originalURL):
            key = 'offers.com'
            codes[key] = codes[key] + (await offersCom(html, originalURL)) if key in codes else (await offersCom(html, originalURL))
        
        if ('savings.com' in originalURL):
            key = 'savings.com'
            codes[key] = codes[key] + (await savingsCom(html)) if key in codes else (await savingsCom(html))


        # writeToFile('html/coupert.html', response.text)
        # soup = BeautifulSoup(response.text, 'html.parser')
        # print(f'Soup Title: {soup.title.string}')
        # print({
        #     "response": response,
        #     "status_code": response.status_code,
        #     "request_url": originalURL,
        # })
    
   
    
asyncio.run(main())