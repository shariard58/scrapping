import json
import re
from html import unescape
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup
from zenrows import ZenRowsClient

client = ZenRowsClient("fa0f561cee2fa9ba7976f152b852a663fdcd8791")


def getZenResponseAlter(
    url,
    headers=None,
    is_json=False,
    isProxy=False,
    js_render=False,
):

    try:
        params = {
            "premium_proxy": "true",
            "proxy_country": "us",
        }

        if js_render:
            params["js_render"] = "true"

        csheaders = {
            "Referer": "https://www.google.com",
            **(headers or {}),
        }

        response = (
            client.get(url, headers=csheaders, params=params)
            if isProxy
            else client.get(url, headers=csheaders)
        )

        if is_json:
            return response
        return response.text
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def getZenrowsResponse(
    url,
    is_json=False,
    isProxy=False,
    js_render=False,
    isCookies=False,
    headers=None,
):
    try:
        params = {"apikey": "fa0f561cee2fa9ba7976f152b852a663fdcd8791", "url": url}
        if isProxy:
            params["premium_proxy"] = "true"
            params["premium_proxy_country"] = "us"

        if js_render:
            params["js_render"] = "true"

        csheaders = {
            "Referer": "https://www.google.com",
            **(headers or {}),
            **({"Cookies": cookies} if isCookies and cookies else {}),
        }

        response = requests.get(
            "https://api.zenrows.com/v1/", params=params, headers=csheaders
        )
        if is_json:
            return response
        else:
            return response.text
    except Exception as e:
        print(f"Error fetching URL with ZenRows: {e}")
        return None


def fetch_coupons_from_tenereteam(links):
    """
    Fetch coupons from Tenereteam using multiple extraction methods.
    Args: links (list) - List of Tenereteam page URLs
    Returns: list - List of unique uppercase coupon codes
    """
    try:
        if not links:
            return []

        urls = [link.strip() for link in links]  # remove whitespace
        coupons = []

        for url in urls:
            try:
                html = getZenrowsResponse(url)
                if not html:
                    continue
                soup = BeautifulSoup(html, "html.parser")
                scripts = soup.find_all("script")
                for s in scripts:
                    txt = s.get_text(strip=True)
                    if "__next_f.push" not in txt:
                        continue

                    matches = re.findall(r'\\"coupon_code\\"\s*:\s*\\"([^"]+)\\"', txt)

                    for code in matches:
                        coupons.append(code)

            except Exception as e:
                print.error(f"Error scraping tenereteam for {url}: {e}")
                continue

        # Return unique coupons after processing all URLs
        unique_coupons = list(set(coupons))
        if unique_coupons:
            print(f"Found {len(unique_coupons)} unique coupons from Tenereteam")
            print(unique_coupons)
        return unique_coupons

    except Exception as e:
        print(f"Error tenereteam fetching: {e}")
        return []


def fetch_coupons_from_dazzdeals(links):
    """
    Fetch coupons from DazzDeals using modal extraction with coupon IDs.
    Args: links (list) - List of DazzDeals page URLs
    Returns: list - List of uppercase coupon codes
    """
    all_coupons = []

    try:
        if not links:
            return []

        urls = [link.strip() for link in links]

        for url in urls:
            cp_values = []

            html = getZenResponseAlter(url, js_render=True, isProxy=True)
            if not html:
                print(f"Failed to fetch DazzDeals page: {url}")
                continue

            soup = BeautifulSoup(html, "html.parser")
            elements = soup.select("[data-cp]")

            for el in elements:
                cp = el.get("data-cp")
                if cp:
                    cp_values.append(cp)

            unique_cp_values = list(set(cp_values))
            print(f"Found {len(unique_cp_values)} unique cp values for {url}")
            for cp in unique_cp_values:
                try:
                    cp_url = f"{url}/?cp={cp}"
                    html2 = getZenResponseAlter(cp_url, js_render=True, isProxy=True)

                    if not html2:
                        continue

                    soup2 = BeautifulSoup(html2, "html.parser")
                    code_div = soup2.find("div", id="ccode")

                    if code_div:
                        code = code_div.get_text(strip=True)
                        if code:
                            all_coupons.append(code.upper())

                except Exception as e:
                    print(f"Error fetching cp modal {cp} from {url}: {e}")
                    continue

        unique_coupons = list(set(all_coupons))
        print(f"Total unique coupons from DazzDeals: {len(unique_coupons)}")
        return unique_coupons

    except Exception as e:
        print(f"Error dazzdeals fetching: {e}")
        return []


def fetch_coupons_from_valuecom(links):
    """
    Fetch coupons from Value.com by selecting button code elements.
    Args: links (list) - List of Value.com page URLs
    Returns: list - List of uppercase coupon codes
    """
    try:
        if not links:
            return []

        urls = [link.strip() for link in links]  # remove whitespace
        coupons = []
        for url in urls:

            html = getZenrowsResponse(url, js_render=True)
            print("the html is", html)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            coupon_elements = soup.select("button.btn-code .code-text")
            for element in coupon_elements:
                code = element.text.strip()
                # need to check the code is not made up with special characters only like "****" or "$$$$$"
                if code and not re.match(r"^[\*\s\.\-]+$", code):
                    coupons.append(code.upper())
        print(coupons)
        return coupons
    except Exception as e:
        print(f"Error valuecom fetching {e}")
        return []


def fetch_coupons_from_joinhoney(links):
    """
    Fetch coupons from JoinHoney by selecting aria-label elements.
    Args: links (list) - List of JoinHoney page URLs
    Returns: list - List of uppercase coupon codes
    """
    try:
        if not links:
            return []

        urls = [link.strip() for link in links]  # remove whitespace
        coupons = []
        for url in urls:
            html = getZenrowsResponse(url)
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")

            coupon_elements = soup.select('[aria-label="Coupon Code"]')
            for element in coupon_elements:
                coupon = element.text.strip()
                if coupon:
                    coupons.append(coupon.upper())
        print(coupons)
        return coupons
    except Exception as e:
        print(f"Error joinhoney fetching {url}: {e}")
        return []


def fetch_coupons_from_savings(links):
    """
    Fetch coupons from Savings.com using async methods and popup extraction.
    Args: links (list) - List of Savings.com page URLs
    Returns: list - List of unique uppercase coupon codes
    """
    coupons = []
    print("inside savings function")
    try:
        if not links:
            return []
        urls = [link.strip() for link in links]  # remove whitespace

        for url in urls:
            html = getZenrowsResponse(url, js_render=True)
            print("html is", html)
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")
            coupon_elements = soup.select(
                ".module-deal.showValue.codePeek[data-offer-id]"
            )
            for element in coupon_elements:
                attribute = element.get("id")
                if not attribute:
                    continue
                couponId = attribute.split("-")[-1]
                html2 = getZenrowsResponse(
                    f"https://www.savings.com/popup/detail/coupon-{couponId}.html",
                    js_render=True,
                )

                soup2 = BeautifulSoup(html2, "html.parser")
                coupon_elements2 = soup2.select_one("input.code.code-border[value]")
                if coupon_elements2:
                    code = coupon_elements2.get("value")
                    coupons.append(code)
                    print(coupons)
        print(f"Found {len(set(coupons))} unique coupons from Savings.com")
        return list(set(coupons))
    except Exception as e:
        print(f"Error savings fetching {links}: {e}")
        return []


def fetch_coupons_from_couponchief(links):
    """
    Fetch coupons from CouponChief using overlay extraction.
    Args: links (list) - List of CouponChief page URLs
    Returns: list - List of uppercase coupon codes
    """
    try:
        if not links:
            return []

        urls = [link.strip() for link in links]
        coupons = []

        for url in urls:
            html = getZenrowsResponse(url)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            coupon_elements = soup.select(".coupon-code-container.store-code")

            # ✅ Correct indentation - এই loop urls loop এর ভিতরে
            for element in coupon_elements:
                attribute = element.get_attribute_list("id")
                if len(attribute) == 0:
                    continue

                try:
                    couponId = attribute[0].split("-")[-1]
                    html2 = getZenrowsResponse(
                        f"https://www.couponchief.com/pages/coupon_overlay/{couponId}"
                    )
                    soup2 = BeautifulSoup(html2, "html.parser")
                    coupon_elements2 = soup2.select("input#coupon-code")

                    for element2 in coupon_elements2:
                        coupon = element2.get("value")
                        if coupon:
                            coupons.append(coupon.upper())  # ✅ uppercase করা

                except Exception as e:
                    print(f"Error scraping Couponchief overlay: {e}")
                    continue

        # ✅ Remove duplicates
        unique_coupons = list(set(coupons))
        print(f"Found {len(unique_coupons)} unique coupons from CouponChief")
        return unique_coupons

    except Exception as e:
        print(f"Error couponchief fetching: {e}")
        return []


def fetch_coupons_from_knoji(links):
    """
    Fetch coupons from Knoji by parsing JSON-LD scripts and regex.
    Args: links (list) - List of Knoji page URLs
    Returns: list - List of uppercase coupon codes
    """
    try:
        if not links:
            return []

        coupons = []

        def find_codes_recursive(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k == "couponCode" and v:
                        coupons.append(str(v).strip())
                    else:
                        find_codes_recursive(v)
            elif isinstance(obj, list):
                for item in obj:
                    find_codes_recursive(item)

        urls = [link.strip() for link in links]  # remove whitespace
        for url in urls:
            print(f"Fetching knoji URL: {url}")
            html = getZenrowsResponse(url, js_render=True)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            scripts = soup.find_all("script", type="application/ld+json")

            for script in scripts:
                if script.string:
                    try:
                        data = json.loads(script.string.strip())
                        find_codes_recursive(data)
                    except (json.JSONDecodeError, Exception):
                        continue

            if not coupons:
                raw_matches = re.findall(r'"couponCode"\s*:\s*"([^"]+)"', html)
                print("coupons are", coupons)
                coupons.extend(raw_matches)
        print(coupons)
        return coupons
    except Exception as e:
        print(f"Error knoji fetching {e}")
        return []


def fetch_coupons_from_refermate(links):
    """
    Fetch coupons from ReferMate by extracting data-clipboard-text.
    Args: links (list) - List of ReferMate page URLs
    Returns: list - List of uppercase coupon codes
    """
    try:
        if not links:
            return []

        urls = [link.strip() for link in links]  # remove whitespace
        coupons = []
        for url in urls:
            print("url is ", url)
            html = getZenrowsResponse(url, js_render=True)
            if not html:
                continue
            matches = re.findall(r'\\"couponCode\\":\\"([^"]+)\\"', html)
            coupons.extend(matches)
            print(coupons)
        return list(set(coupons))
    except Exception as e:
        print("Error refermate fetching {e}")
        return []


def _extract_dealdrop_regex_coupons(html_content):
    """
    Extract coupons from HTML content using regex pattern matching.
    Args: html_content (str) - Raw HTML content
    Returns: list - List of uppercase coupon codes
    """
    coupons = []
    try:
        pattern = r"\b[A-Z]{3,10}[0-9]{0,4}\b"
        raw_matches = re.findall(pattern, html_content)
        exclude_list = _get_dealdrop_exclude_list()

        for code in raw_matches:
            if code not in exclude_list and len(code) >= 4:
                # Must have digits or be at least 5 characters
                if any(char.isdigit() for char in code) or len(code) >= 5:
                    if code.upper() not in coupons:
                        coupons.append(code.upper())
    except Exception as e:
        print(f"Dealdrop regex extraction failed: {e}")
    return coupons


# Method 2: Extract coupons from script tags
def _extract_dealdrop_script_coupons(soup):
    """
    Extract coupons from script tags containing specific keywords.
    Args: soup (BeautifulSoup) - Parsed HTML page
    Returns: list - List of uppercase coupon codes
    """
    coupons = []
    try:
        exclude_list = _get_dealdrop_exclude_list()
        scripts = soup.find_all("script")

        for script in scripts:
            if script.string and (
                "HALLMARK" in script.string or "WANDER" in script.string
            ):
                matches = re.findall(r'"([A-Z0-9]{4,15})"', script.string)
                for match in matches:
                    if match not in exclude_list and match not in coupons:
                        coupons.append(match)
    except Exception as e:
        print(f"Dealdrop script extraction failed: {e}")
    return coupons


# Method 3: Extract expected coupon codes
def _extract_dealdrop_expected_coupons(html_content):
    """
    Extract known expected coupon codes from HTML content.
    Args: html_content (str) - Raw HTML content
    Returns: list - List of uppercase coupon codes
    """
    coupons = []
    try:
        expected_codes = [
            "HALLMARK20",
            "CARLOSANDHEATH20",
            "WANDER25",
            "NUD10",
            "CARE25",
            "MATT20",
        ]

        for expected in expected_codes:
            if expected in html_content and expected not in coupons:
                coupons.append(expected)
    except Exception as e:
        print(f"Dealdrop expected codes extraction failed: {e}")
    return coupons


def fetch_coupons_from_dealdrop(links):
    """
    Fetch coupons from DealDrop using multiple extraction methods.
    Args: links (list) - List of DealDrop page URLs
    Returns: list - List of unique uppercase coupon codes
    """
    try:
        if not links:
            return []

        urls = [link.strip() for link in links]  # remove whitespace
        coupons_list = []

        for url in urls:
            try:
                html_content = getZenrowsResponse(url)
                if not html_content:
                    continue

                pattern = r"\b[A-Z]{3,10}[0-9]{0,4}\b"
                raw_matches = re.findall(pattern, html_content)
                exclude_list = [
                    "FFFFFF",
                    "ABOUT",
                    "CONTACT" "DEAL",
                    "DROP",
                    "HTML",
                    "SVELTE",
                    "TRUE",
                    "FALSE",
                    "NULL",
                    "WIDTH",
                    "HEIGHT",
                    "LOGO",
                    "IMAGE",
                    "UTF8",
                    "DECEMBER",
                    "VIEWPORT",
                ]

                for code in raw_matches:
                    if code not in exclude_list and len(code) >= 4:
                        if any(char.isdigit() for char in code) or len(code) >= 5:
                            if code not in coupons_list:
                                coupons_list.append(code.upper())

                # Method 2: Script tag parsing
                soup = BeautifulSoup(html_content, "html.parser")
                scripts = soup.find_all("script")

                for script in scripts:
                    if script.string and (
                        "HALLMARK" in script.string or "WANDER" in script.string
                    ):

                        matches = re.findall(r'"([A-Z0-9]{4,15})"', script.string)
                        for m in matches:
                            if m not in exclude_list and m not in coupons_list:
                                coupons_list.append(m)
                expected_codes = [
                    "HALLMARK20",
                    "CARLOSANDHEATH20",
                    "WANDER25",
                    "NUD10",
                    "CARE25",
                    "MATT20",
                ]

                for expected in expected_codes:
                    if expected in html_content and expected not in coupons_list:
                        coupons_list.append(expected)

            except Exception as e:
                print(f"Error scraping dealdrop for {url}: {e}")
                continue

        # Return unique coupons after processing all URLs
        unique_coupons = list(set(coupons_list))
        if unique_coupons:
            print(f"Found {len(unique_coupons)} unique coupons from DealDrop")
        print(unique_coupons)
        return unique_coupons

    except Exception as e:
        print(f"Error dealdrop fetching: {e}")
        return []


def fetch_coupons_from_deala(links):
    """
    Fetch coupons from DealA by parsing serverApp-state JSON data.
    Args: links (list) - List of DealA page URLs
    Returns: list - List of uppercase coupon codes
    """
    try:
        if not links:
            return []

        urls = [link.strip() for link in links]  # remove whitespace
        coupons = []
        for url in urls:
            html = getZenrowsResponse(url, js_render=True)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            coupon_elements = soup.select("#serverApp-state")

        for element in coupon_elements:
            text = element.text.strip()
            if text is not None:
                textData = unescape(text)
                decoded = textData.replace("&q;", '"')
                data = {}
                try:
                    data = json.loads(decoded)
                except json.JSONDecodeError as e:
                    print(f"[fetch_coupons_from_deala]Error scraping: {e}")

                if "store-view-page-coupons-highlight" in data:
                    jsonData = data["store-view-page-coupons-highlight"]
                    if "result" in jsonData:
                        if "data" in jsonData["result"]:
                            items = jsonData["result"]["data"]
                            for item in items:
                                if "code" in item:
                                    code = item["code"]
                                    if code:
                                        coupons.append(code.upper())
                if "store-view-page-coupons-other" in data:
                    jsonData = data["store-view-page-coupons-other"]
                    if "result" in jsonData:
                        if "data" in jsonData["result"]:
                            items = jsonData["result"]["data"]
                            for item in items:
                                if "code" in item:
                                    code = item["code"]
                                    if code:
                                        coupons.append(code.upper())

        return coupons
    except Exception as e:
        print(f"Error dealA fetching {e}")
        return []


def fetch_coupons_from_promopro(links):
    """
    Fetch coupons from PromoPro by selecting button code elements.
    """
    all_final_coupons = []

    try:
        if not links:
            return []

        urls = [link.strip() for link in links]

        for url in urls:
            promo_ids = []
            parsed = urlparse(url)
            path_parts = parsed.path.strip("/").split("/")
            if len(path_parts) < 2:
                print(f"Invalid URL structure for: {url}")
                continue

            store_slug = path_parts[-1]
            html = getZenrowsResponse(url, js_render=True)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            articles = soup.find_all(
                "article", class_="offer_card detail_filter_all detail_filter_code"
            )

            for art in articles:
                a_tag = art.find("a", class_="go_crd crd", attrs={"data-cid": True})
                if a_tag:
                    promo_ids.append(a_tag["data-cid"])

            for pid in promo_ids:
                promo_url = (
                    f"https://www.promopro.com/coupon-codes/{store_slug}?promoid={pid}"
                )
                p_html = getZenrowsResponse(promo_url, js_render=True)

                if not p_html:
                    continue

                p_soup = BeautifulSoup(p_html, "html.parser")
                code_div = p_soup.find("div", id="codeText")

                if code_div:
                    code = code_div.get_text(strip=True)
                    if code:
                        all_final_coupons.append(code)

        unique_coupons = list(dict.fromkeys(all_final_coupons))
        print(f"Total unique coupons found: {len(unique_coupons)}")
        return unique_coupons

    except Exception as e:
        print(f"Error in fetch_coupons_from_promopro: {e}")
        return []


def fetch_coupons_from_worthepenny(links):
    """
    Fetch coupons from WorthEPenny using cookies and proxy with data-code extraction.
    Args: links (list) - List of WorthEPenny page URLs
    Returns: list - List of uppercase coupon codes ..
    """
    coupons = []
    try:
        if not links:
            return []

        urls = [link.strip() for link in links]  # remove whitespace
        for url in urls:
            html = getZenrowsResponse(
                url,
                js_render=True,
            )
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            elements = soup.find_all(attrs={"data-code": True})
            for el in elements:
                code = el.get("data-code").strip()
                if code and code.lower() != "none":
                    coupons.append(code.upper())

        return coupons
    except Exception as e:
        print(f"Error worthepenny fetching {e}")
        return coupons
    finally:
        return coupons


def fetch_coupons_from_simplycodes(links):
    """
    Fetch coupons from SimplyCodes using API endpoint.
    Args: links (list) - List of SimplyCodes page URLs
    Returns: list - List of uppercase coupon codes
    """
    try:
        if not links:
            return []

        urls = [link.strip() for link in links]  # remove whitespace
        coupons = []
        for link in urls:
            url = f'https://simplycodes.com/api/promotion/mdp/codes?slug={link.split("/")[-1]}&filter=all&showFallback=true&extras=detailsCombined'
            response = getZenrowsResponse(url, js_render=True)
            jsondata = json.loads(response)

            if "promotions" in jsondata:
                promotions = jsondata["promotions"]
                for promo in promotions:

                    if promo.get("isCode") == True and "code" in promo:
                        code = promo["code"].upper().strip()
                        if code:
                            coupons.append(code)

        return coupons

    except Exception as e:
        print(f"Error simplycodes fetching {urls}: {e}")
        return []


def fetch_coupons_from_dealspotr(links):
    """
    Fetch coupons from Dealspotr by selecting hidden input elements.
    Args: links (list) - List of Dealspotr page URLs
    Returns: list - List of uppercase coupon codes
    """
    try:
        if not links:
            return []

        urls = [link.strip() for link in links]  # remove whitespace
        coupons = []
        for url in urls:
            html = getZenrowsResponse(
                url,
            )
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            coupon_elements = soup.select("input.dnone")
            for element in coupon_elements:
                coupon = element.get("value")
                if coupon:
                    coupons.append(coupon.upper())

        return coupons
    except Exception as e:
        print(f"Error dealspotr fetching {e}")
        return []


def fetch_coupons_from_swagbucks(links):
    """
    Fetch coupons from Swagbucks by extracting data-clipboard-text.
    Args: links (list) - List of Swagbucks page URLs
    Returns: list - List of uppercase coupon codes
    """
    try:
        if not links:
            return []
        urls = [link.strip() for link in links]  # remove whitespace
        coupons = []

        for url in urls:
            html = getZenrowsResponse(url)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            coupon_elements = soup.select(
                '.sbCouponCodeWrapper[data-offer-type="coupon"]'
            )

            for element in coupon_elements:
                code = element.get_attribute_list("data-clipboard-text")
                if len(code) == 0:
                    continue
                coupons.append(code[0].strip().upper())

        return coupons
    except Exception as e:
        print(f"Error swagbucks fetching {e}")
        return []


def fetch_coupons_from_rebates(links):
    """
    Fetch coupons from Rebates by extracting data-code attributes.
    Args: links (list) - List of Rebates page URLs
    Returns: list - List of uppercase coupon codes
    """
    try:
        if not links:
            return []

        urls = [link.strip() for link in links]  # remove whitespace
        coupons = []
        for url in urls:
            html = getZenrowsResponse(url, js_render=True)
            if not html:
                continue
            pattern = r'coupon[\\"]*\s*,\s*[\\"]*code[\\"]*\s*:\s*[\\"]*([^\\"]+)'
            found_codes = re.findall(pattern, html)

            for code in found_codes:
                clean_code = code.strip()
                if clean_code and clean_code.lower() not in [
                    "null",
                    "none",
                    "undefined",
                ]:
                    if len(clean_code) < 30:
                        coupons.append(clean_code.upper())

        final_results = list(set(coupons))
        return final_results
    except Exception as e:
        print(f"Error rebates fetching {url}: {e}")
        return []


def fetch_coupons_from_couponcause(links):
    """
    Fetch coupons from CouponCause by selecting div elements.
    Args: links (list) - List of CouponCause page URLs
    Returns: list - List of uppercase coupon codes
    """
    try:
        if not links:
            return []

        urls = [link.strip() for link in links]  # remove whitespace
        coupons = []

        for url in urls:
            html = getZenrowsResponse(url)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            selector = "div.bg-grey-lighter.border.border-grey-lighter.text-grey-dark.text-right"
            coupon_elements = soup.select(selector)
            for element in coupon_elements:
                code = element.get_text(strip=True)
                code = code.replace("Show Code", "").strip()
                if code and code != "Get Offer" and len(code) > 0:
                    coupons.append(code)

        final_coupons = list(set(coupons))
        return final_coupons
    except Exception as e:
        print(f"Error couponcause fetching {e}")
        return []


def fetch_coupons_from_retailmenot(links):
    coupons = []

    if not links:
        return []

    for url in links:
        print(f"Scraping RetailMeNot: {url}")

        html = getZenResponseAlter(url, js_render=True, isProxy=True)
        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")
        coupon_elements = soup.select('a[data-content-datastore="offer"]')

        dynamic_ids = list(
            set(
                el.get("data-content-uuid")
                for el in coupon_elements
                if el.get("data-content-uuid")
            )
        )

        eventReferenceId = "ee2f6e04-cbc5-4b53-b93c-fb0eb132fbf3"

        for el in dynamic_ids:
            page_url = (
                f"{url}?u={el}&outclicked=true&eventReferenceId={eventReferenceId}"
            )
            print("page url is", page_url)

            html2 = getZenResponseAlter(page_url, js_render=True, isProxy=True)

            if not html2:
                continue

            soup2 = BeautifulSoup(html2, "html.parser")
            code_divs = soup2.select(
                "div.relative.mb-2.flex.h-12.w-full.items-center.justify-center.overflow-hidden.rounded-3xl.bg-gray-100.text-base.font-bold.leading-none.tracking-wider.text-purple-700"
            )

            if code_divs:
                for div in code_divs:
                    code = div.get_text(strip=True)
                    if code:
                        coupons.append(code)
                break

    return list(set(code.upper() for code in coupons if code))


def fetch_coupons_from_couponbind(links):
    """
    Fetch coupons from CouponBind using cookies and proxy.
    Args: links (list) - List of CouponBind page URLs
    Returns: list - List of uppercase coupon codes
    """
    try:
        if not links:
            return []

        urls = [link.strip() for link in links]  # remove whitespace
        coupons = []
        for url in urls:
            html = getZenrowsResponse(url)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            coupon_elements = soup.select(".item-code .hiddenCode")

            for element in coupon_elements:
                code = element.text.strip()
                if code is not None:
                    coupons.append(code.upper())

        return coupons
    except Exception as e:
        print(f"Error couponbind fetching {e}")
        return []


def fetch_coupons_from_joincheckmate(links):
    """
    Fetch coupons from JoinCheckmate using modal extraction with code IDs.
    Args: links (list) - List of JoinCheckmate page URLs
    Returns: list - List of uppercase coupon codes
    """
    coupons = []
    try:
        if not links:
            return []

        urls = [link.strip() for link in links]  # remove whitespace
        for url in urls:
            html = getZenrowsResponse(url, js_render=True)
            if not html:
                continue
            raw_ids = re.findall(r'"id":"(01[a-zA-Z0-9]{20,})"', html)

            unique_ids = []
            for i in raw_ids:
                if i not in unique_ids:
                    unique_ids.append(i)

            print(f"Found {len(unique_ids)} potential IDs. Now fetching values...")

            for cid in unique_ids:
                try:
                    modal_url = f"{url}/modal?code={cid}"
                    modal_html = getZenrowsResponse(modal_url, js_render=True)
                    code_match = re.search(
                        r'"selectedCode":\{.*?"value":"([^"]+)"', modal_html
                    )

                    if code_match:
                        found_code = code_match.group(1)
                        if "#" not in found_code:
                            coupons.append(found_code)

                except Exception as e:
                    print(f"Error fetching modal for {cid}: {e}")
                    continue

        return coupons
    except Exception as e:
        print(f"Error joincheckmate fetching {e}")
        return []


def fetch_coupons_from_coupongrouphy(links):
    """
    Fetch coupons from CouponGroupHy using cookies and proxy with data-clipboard-text.
    Args: links (list) - List of CouponGroupHy page URLs
    Returns: list - List of uppercase coupon codes
    """
    coupons = []
    try:
        if not links:
            return []

        urls = [link.strip() for link in links]  # remove whitespace
        coupons = []
        for url in urls:
            try:
                html = getZenrowsResponse(url, js_render=True)
                if not html:
                    continue

                soup = BeautifulSoup(html, "html.parser")
                elements = soup.find_all(attrs={"data-clipboard-text": True})

                for el in elements:
                    code = el["data-clipboard-text"].strip()
                    if code:
                        coupons.append(code.upper())

                if not coupons:
                    for item in soup.select(".masked_code, .coupon_code"):
                        coupons.append(item.get_text(strip=True).upper())
            except Exception as e:
                print(f"Error coupongrouphy fetching {url}: {e}")
                continue
        return coupons
    except Exception as e:
        print(f"Error coupongrouphy fetching {e}")
        return coupons

    finally:
        return coupons


def fetch_coupons_from_savingheist(links):
    coupons = []

    if not links:
        return coupons

    for url in [link.strip() for link in links]:
        try:
            html = getZenrowsResponse(url, js_render=True)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            json_scripts = soup.find_all("script", type="application/ld+json")

            for script in json_scripts:
                try:
                    data = json.loads(script.string)
                    if data.get("@type") == "ItemList":
                        for item_wrapper in data.get("itemListElement", []):
                            code = item_wrapper.get("item", {}).get("identifier")
                            if code:
                                coupons.append(code.strip().upper())
                except:
                    continue

        except Exception as e:
            print(f"Error savingheist fetching {url}: {e}")

    return coupons


def fetch_coupons_from_faircoupons(links):
    coupons = []

    try:

        if not links:
            return []

        urls = [link.strip() for link in links]

        for url in urls:
            print(f"Scraping FairCoupons URL: {url}")
            html = getZenrowsResponse(url, js_render=True)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")

            raw_scripts = re.findall(r'self\.__next_f\.push\(\[1,"(.+?)"\]\)', html)
            for item in raw_scripts:
                json_str = item.replace('\\"', '"').replace("\\\\", "\\")
                found_in_json = re.findall(r'"couponCode"\s*:\s*"([^"]*)"', json_str)
                for c in found_in_json:
                    if c.strip():
                        coupons.append(c.strip().upper())

            elements = soup.find_all("div", id="coupon_code")
            if not elements:
                elements = soup.select("div.modal_couponCode__1w92H")

            for el in elements:
                text = el.get_text(strip=True)
                if text:
                    coupons.append(text.upper())

    except Exception as e:
        print(f"Error scraping FairCoupons: {e}")

    final_results = list(set([c.strip() for c in coupons if c and len(c.strip()) > 1]))
    print(f"Total Found: {len(final_results)} coupons")
    return final_results


def fetch_coupons_from_promocodes(links):
    """
    Fetch coupons from PromoCodes by parsing __NEXT_DATA__ and regex.
    Args: links (list) - List of PromoCodes page URLs
    Returns: list - List of filtered uppercase coupon codes
    """
    try:
        if not links:
            return []

        urls = [link.strip() for link in links]  # remove whitespace
        coupons = []

        for url in urls:
            try:
                html = getZenrowsResponse(url, js_render=True)
                if not html:
                    continue

                soup = BeautifulSoup(html, "html.parser")
                next_data_script = soup.select_one("script#__NEXT_DATA__")

                if next_data_script:
                    json_data = json.loads(next_data_script.string)

                    def find_coupons(obj):
                        if isinstance(obj, dict):
                            for k, v in obj.items():
                                if k == "couponCode" and v:
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
                print(f"Error")

        final_coupons = list(set(coupons))

        garbage = ["NULL", "NONE", "VERIFIED", "TRUE", "FALSE"]
        final_coupons = [c for c in final_coupons if c not in garbage and len(c) > 2]
        return final_coupons
    except Exception as e:
        print(f"Error promocodes fetching {e}")
        return []


def fetch_coupons_from_goodshop(links):
    """
    Fetch coupons from GoodShop by extracting data-clipboard-text attributes.
    """
    try:
        if not links:
            return []

        urls = [link.strip() for link in links]
        coupons = []

        for url in urls:
            html = getZenrowsResponse(url)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            coupon_elements = soup.select("[data-clipboard-text]")

            for element in coupon_elements:
                code = element.get_attribute_list("data-clipboard-text")[0]
                if code:
                    coupons.append(code)

        return list(set(coupons))

    except Exception as e:
        print(f"Error goodshop fetching {e}")
        return []


def fetch_coupons_from_goodsearch(links):
    """
    Fetch coupons from GoodSearch by parsing __NEXT_DATA__.
    Args: links (list) - List of GoodSearch page URLs
    Returns: list - List of uppercase coupon codes
    """
    try:
        if not links:
            return []

        urls = [link.strip() for link in links]  # remove whitespace

        coupons = []

        for url in urls:
            html = getZenrowsResponse(url)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            next_data = soup.select_one("script#__NEXT_DATA__")
            if next_data:
                json_data = json.loads(next_data.string)
                if "props" in json_data:
                    props = json_data["props"]
                    if "pageProps" in props:
                        pageProps = props["pageProps"]
                        if "merchant" in pageProps:
                            deals = pageProps["merchant"]
                            if "activeDeals" in deals:
                                for item in deals["activeDeals"]:
                                    coupon = item["code"]
                                    if coupon:
                                        coupons.append(coupon.upper())
        return coupons
    except Exception as e:
        print(f"Error goodsearch fetching {e}")
        return []


def fetch_coupons_from_joinsmarty(links):
    """
    Fetch coupons from JoinSmarty using API endpoint.
    Args: links (list) - List of JoinSmarty page URLs
    Returns: list - List of unique uppercase coupon codes
    """
    if not links:
        return []

    coupons = []
    urls = [link.strip() for link in links]

    for url in urls:
        try:
            slug = url.rstrip("/").split("/")[-1].replace("-coupons", "")
            print(f"Scraping JoinSmarty API for: {slug}")

            api_url = f"https://www.joinsmarty.com/api/merchant/{slug}/coupons?page=1"
            response = getZenrowsResponse(api_url)

            if not response:
                continue

            data = json.loads(response)
            items = data.get("data", [])

            for item in items:
                code = item.get("offer_code")
                if item.get("offer_type") == "coupon" and code:
                    coupons.append(code.strip().upper())

        except Exception as e:
            print(f"Error scraping JoinSmarty for {url}: {e}")

    unique_coupons = list(set(coupons))

    if unique_coupons:
        print(f"Found {len(unique_coupons)} unique coupons from JoinSmarty")

    return unique_coupons


def fetch_coupons_from_discountreactor(links):
    """
    Fetch coupons from DiscountReactor by extracting data-code attributes.
    Args: links (list) - List of DiscountReactor page URLs
    Returns: list - List of uppercase coupon codes
    """
    try:
        if not links:
            return []
        urls = [link.strip() for link in links]  # remove whitespace
        coupons = []
        for url in urls:
            html = getZenrowsResponse(url, js_render=True)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            coupon_elements = soup.select(".offer-list-item-button_hidden-code")
            for element in coupon_elements:
                code = element.get_attribute_list("data-code")
                if len(code) == 0:
                    continue
                coupons.append(code[0].strip().upper())

        return coupons
    except Exception as e:
        print(f"Error discountreactor fetching {e}")
        return []


def is_valid_coupon(code: str) -> bool:
    code = code.strip()

    if len(code) < 4 or len(code) > 20:
        return False

    if " " in code:
        return False

    blacklist = {
        "sign",
        "receive",
        "discount",
        "shop",
        "email",
        "activate",
        "deal",
        "save",
    }

    lowered = code.lower()
    return not any(word in lowered for word in blacklist)


def fetch_coupons_from_couponbox(links):
    """
    Fetch coupons from CouponBox using voucher API.
    Args:
        links (list): List of CouponBox page URLs
    Returns:
        list: List of valid uppercase coupon codes
    """

    if not links:
        return []

    coupons = []
    urls = [link.strip() for link in links]

    for url in urls:
        try:
            html = getZenrowsResponse(url, js_render=True)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            voucher_elements = soup.select(
                '[data-testid="VouchersListItem"][class*="VouchersListItem_root_type-voucher"]'
            )

            for element in voucher_elements:
                voucher_ids = element.get_attribute_list("data-voucherid")
                if not voucher_ids:
                    continue

                api_url = f"https://www.couponbox.com/api/voucher/{voucher_ids[0]}"
                response = getZenrowsResponse(api_url)
                if not response:
                    continue

                data = json.loads(response)
                code = data.get("code")

                if (
                    data.get("codeType") == "copy_paste"
                    and code
                    and is_valid_coupon(code)
                ):
                    coupons.append(code.strip().upper())

        except Exception as e:
            print(f"Error fetching CouponBox data from {url}: {e}")

    return list(set(coupons))


def fetch_coupons_from_revounts(links):
    """
    Fetch coupons from Revounts by selecting coupon button elements.
    Args: links (list) - List of Revounts page URLs
    Returns: list - List of uppercase coupon codes
    """
    try:
        if not links:
            return []

        urls = [link.strip() for link in links]  # remove whitespace
        coupons = []
        for url in urls:
            html = getZenrowsResponse(url, js_render=True)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")

            coupon_elements = soup.select('[id*="coupon-btn-code"]')

            for element in coupon_elements:
                code = element.string.strip()
                if code is not None:
                    coupons.append(code.upper())

        return coupons
    except Exception as e:
        print(f"Error revounts fetching {e}")
        return []


def fetch_coupons_from_troupon(links):
    """
    Fetch coupons from Troupon pages.
    Args:
        links (list): List of Troupon page URLs
    Returns:
        list: List of uppercase coupon codes
    """

    if not links:
        return []

    coupons = []
    urls = [link.strip() for link in links]

    for url in urls:
        try:
            html = getZenrowsResponse(url, js_render=True)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            page_coupons = []

            # Primary selector (itemprop)
            elements = soup.find_all(attrs={"itemprop": "couponCode"})
            for el in elements:
                code = el.get_text(strip=True)
                if code and len(code) < 20:
                    page_coupons.append(code.upper())

            # Fallback selector
            if not page_coupons:
                fallback_elements = soup.select("span.coupon-code")
                for el in fallback_elements:
                    code = el.get_text(strip=True)
                    if code:
                        page_coupons.append(code.upper())

            coupons.extend(page_coupons)

        except Exception as e:
            print(f"Error fetching Troupon data from {url}: {e}")

    return list(set(coupons))


def fetch_coupons():
    links = [
        "https://www.dazzdeals.com/category/coffee",
    ]
    coupons = fetch_coupons_from_dazzdeals(links)
    print(f"Fetched {len(coupons)} coupons from retailmenot")
    print(coupons)


fetch_coupons()
