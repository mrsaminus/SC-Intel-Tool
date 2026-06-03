import re
import time
from functools import lru_cache
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup


class RSILookupError(Exception):
    pass


BASE_URL = "https://robertsspaceindustries.com"
TIMEOUT_SECONDS = 15

HEADERS = {
    "User-Agent": "Mozilla/5.0 SC-Intel-Tool",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.7",
}

_SESSION = requests.Session()
_SESSION.headers.update(HEADERS)

_RE_REDACTED = re.compile(
    r"(This information has been redacted|\bREDACTED\b)",
    re.IGNORECASE,
)
_RE_NO_MAIN_ORG = re.compile(r"NO MAIN ORG FOUND IN PUBLIC RECORDS", re.IGNORECASE)
_RE_MAIN_ORG = re.compile(r"Main organization", re.IGNORECASE)
_RE_SPECTRUM_ID = re.compile(r"Spectrum Identification", re.IGNORECASE)
_RE_ORG_RANK = re.compile(r"Organization rank", re.IGNORECASE)
_RE_ORG_LINK = re.compile(r"/orgs/([A-Za-z0-9_-]+)")

_ORG_TYPE_VALUES = {"Organization", "Syndicate", "Corporation", "PMC", "Club", "Faith"}
_COMMITMENT_VALUES = {"Casual", "Regular", "Hardcore"}
_EXCLUSIVITY_VALUES = {"Exclusive", "Affiliate"}
_EMPTY_ORG_VALUES = {"", "n/a", "not found", "none", "redacted", "no main org"}
_REDACTED_ORG_NAME = "REDACTED"


@lru_cache(maxsize=200)
def lookup_player(handle: str) -> dict:
    handle = handle.strip()

    if not handle:
        raise RSILookupError("No handle provided.")

    response, profile_url = fetch_profile_page(handle)
    soup = BeautifulSoup(response.text, "lxml")

    profile_org = extract_main_org(soup)
    organizations_data = fetch_player_organizations(handle)
    organizations = organizations_data["organizations"]
    organizations_redacted = organizations_data["redacted"]

    main_org = next(
        (org for org in organizations if org["relationship"] == "Main organization"),
        None,
    )
    if not main_org:
        if profile_org.get("redacted") or organizations_redacted:
            main_org = redacted_org_result("Main organization")
        else:
            main_org = {
                **profile_org,
                "relationship": "Main organization",
                "member_count": "N/A",
            }

    main_org = enrich_organization(main_org)
    affiliations = [
        enrich_organization(org)
        for org in organizations
        if org["relationship"] == "Affiliation"
    ]
    main_org_redacted = bool(main_org.get("redacted"))
    affiliations_redacted = bool(organizations_redacted and not affiliations)
    main_org_piracy = False if main_org_redacted else main_org["piracy"]
    affiliation_piracy = False if affiliations_redacted else any(org["piracy"] for org in affiliations)
    any_org_piracy = main_org_piracy or affiliation_piracy

    return {
        "handle": handle,
        "display_name": extract_display_name(soup),
        "avatar": extract_avatar(soup),
        "citizen_record": extract_label_value(soup, "UEE Citizen Record"),
        "enlisted": extract_label_value(soup, "Enlisted"),
        "location": extract_label_value(soup, "Location"),
        "fluency": extract_label_value(soup, "Fluency"),
        "main_org": main_org["name"],
        "org_sid": main_org["sid"],
        "org_rank": main_org["rank"],
        "org_type": main_org["type"],
        "org_commitment": main_org["commitment"],
        "org_exclusivity": main_org["exclusivity"],
        "org_member_count": main_org["member_count"],
        "org_piracy": main_org["piracy"],
        "any_org_piracy": any_org_piracy,
        "org_url": main_org["url"],
        "org_logo": main_org["logo_url"],
        "affiliations": affiliations,
        "main_org_redacted": main_org_redacted,
        "affiliations_redacted": affiliations_redacted,
        "organizations_redacted": organizations_redacted,
        "organizations_url": f"{BASE_URL}/en/citizens/{quote(handle, safe='')}/organizations",
        "profile_url": profile_url,
    }


def fetch_profile_page(handle):
    encoded_handle = quote(handle, safe="")
    urls = [
        f"{BASE_URL}/en/citizens/{encoded_handle}",
        f"{BASE_URL}/citizens/{encoded_handle}",
    ]

    errors = []
    for url in urls:
        response = request_with_retry(url)

        if response.status_code == 404:
            continue

        if response.status_code == 200:
            return response, url

        errors.append(f"{response.status_code} from {url}")

    if errors:
        raise RSILookupError("RSI lookup failed: " + "; ".join(errors))

    raise RSILookupError("Player not found.")


def request_with_retry(url):
    last_error = None

    for attempt in range(2):
        try:
            response = _SESSION.get(url, timeout=TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(1)
            continue

        if response.status_code in (429, 503) and attempt == 0:
            time.sleep(3)
            continue

        return response

    raise RSILookupError(f"Connection error: {last_error}")


def extract_display_name(soup):
    selectors = [
        ".profile-content .nickname",
        ".profile .entry strong",
        ".entry.nickname strong",
        ".citizen-record .value",
        "h1"
    ]

    for selector in selectors:
        element = soup.select_one(selector)
        text = clean_text(element)
        if text and "citizen dossier" not in text.lower():
            return text

    return "Unknown"


def extract_avatar(soup):
    selectors = [
        "img.thumb",
        ".profile-image img",
        ".avatar img",
        ".citizen-profile img",
        ".profile-content img",
        "img",
    ]

    for selector in selectors:
        img = soup.select_one(selector)
        if not img or not img.get("src"):
            continue

        src = img["src"]
        if "/orgs/" in src.lower():
            continue

        return absolute_url(src)

    return None


def extract_label_value(soup, label, default="Unknown"):
    text = soup.get_text("\n", strip=True)
    label_lower = label.lower()

    lines = [
        line.strip()
        for line in text.split("\n")
        if line.strip()
    ]

    for i, line in enumerate(lines):
        line_lower = line.lower()

        if line_lower == label_lower and i + 1 < len(lines):
            return lines[i + 1]

        if line_lower.startswith(label_lower):
            value = line[len(label):].strip(" :-")
            if value and not value.startswith("("):
                return value

            if i + 1 < len(lines):
                return lines[i + 1]

        if label_lower in line_lower:
            if i + 1 < len(lines):
                return lines[i + 1]

    label_node = soup.find(string=re.compile(re.escape(label), re.IGNORECASE))
    if label_node:
        node = getattr(label_node, "parent", None)
        if node:
            for candidate in node.find_all_next():
                value = clean_text(candidate)
                if value and label_lower not in value.lower():
                    return value

    return default


def extract_main_org(soup):
    result = {
        "name": "None",
        "sid": "N/A",
        "rank": "N/A",
    }

    org_section = soup.find("div", class_="org-mini-block")
    if org_section:
        result["name"] = clean_text(org_section.find("div", class_="name")) or result["name"]
        result["sid"] = clean_text(org_section.find("div", class_="sid")) or result["sid"]
        result["rank"] = clean_text(org_section.find("div", class_="rank")) or result["rank"]
        return normalize_org_result(result)

    if soup.find(string=_RE_NO_MAIN_ORG):
        return {"name": "No Main Org", "sid": "N/A", "rank": "N/A"}

    if soup.find(string=_RE_REDACTED):
        return redacted_org_result("Main organization")

    main_org = extract_label_value(soup, "Main organization", default="")
    if main_org:
        result["name"] = main_org

    sid = extract_label_value(soup, "Spectrum Identification", default="")
    if sid:
        result["sid"] = sid

    rank = extract_label_value(soup, "Organization rank", default="")
    if rank:
        result["rank"] = rank

    return normalize_org_result(result)


def fetch_player_organizations(handle):
    url = f"{BASE_URL}/en/citizens/{quote(handle, safe='')}/organizations"

    try:
        response = request_with_retry(url)
    except RSILookupError:
        return {"organizations": [], "redacted": False}

    if response.status_code != 200:
        return {"organizations": [], "redacted": False}

    soup = BeautifulSoup(response.text, "lxml")
    redacted = bool(soup.find(string=_RE_REDACTED))
    cards = soup.select("div.box-content.org")
    if cards:
        organizations = [
            org
            for org in (extract_organization_card(card) for card in cards)
            if org["name"] != "None" or org["sid"] != "N/A"
        ]
        return {"organizations": organizations, "redacted": redacted}

    return {"organizations": extract_organizations_from_lines(soup), "redacted": redacted}


def extract_organization_card(card):
    classes = set(card.get("class", []))
    relationship = "Affiliation" if "affiliation" in classes else "Main organization"

    name = ""
    for link in card.find_all("a", href=True):
        if "/orgs/" not in link["href"]:
            continue

        link_text = clean_text(link)
        if link_text:
            name = link_text
            break

    sid = extract_label_value(card, "Spectrum Identification", default="")
    if not sid:
        sid = extract_org_sid_from_links(card)

    result = {
        "relationship": relationship,
        "name": name,
        "sid": sid,
        "rank": extract_label_value(card, "Organization rank", default="N/A"),
        "member_count": extract_member_count(card),
        "logo_url": extract_image_url(card),
    }
    return normalize_org_result(result)


def extract_organizations_from_lines(soup):
    lines = [
        line.strip()
        for line in soup.get_text("\n", strip=True).split("\n")
        if line.strip()
    ]
    organizations = []
    i = 0

    while i < len(lines):
        if lines[i] not in ("Main organization", "Affiliation"):
            i += 1
            continue

        relationship = lines[i]
        member_count = "N/A"
        name = "None"
        sid = "N/A"
        rank = "N/A"

        if i + 1 < len(lines) and "member" in lines[i + 1].lower():
            member_count = extract_member_count_from_text(lines[i + 1])
        if i + 2 < len(lines):
            name = lines[i + 2]

        j = i + 3
        while j < len(lines) and lines[j] not in ("Main organization", "Affiliation"):
            if "Spectrum Identification" in lines[j] and j + 1 < len(lines):
                sid = lines[j + 1]
                j += 2
                continue
            if lines[j] == "Organization rank" and j + 1 < len(lines):
                rank = lines[j + 1]
                j += 2
                continue
            j += 1

        organizations.append(normalize_org_result({
            "relationship": relationship,
            "name": name,
            "sid": sid,
            "rank": rank,
            "member_count": member_count,
            "logo_url": None,
        }))
        i = j

    return organizations


def enrich_organization(org):
    enriched = {
        "relationship": org.get("relationship", "Affiliation"),
        "name": org.get("name", "None"),
        "sid": org.get("sid", "N/A"),
        "rank": org.get("rank", "N/A"),
        "member_count": org.get("member_count", "N/A"),
        "type": "N/A",
        "commitment": "N/A",
        "exclusivity": "N/A",
        "piracy": False,
        "url": None,
        "logo_url": org.get("logo_url"),
        "redacted": bool(org.get("redacted")),
    }

    if enriched["redacted"]:
        enriched.update({
            "name": _REDACTED_ORG_NAME,
            "sid": "N/A",
            "rank": "Hidden organization affiliation",
            "member_count": "N/A",
            "type": "REDACTED",
            "commitment": "REDACTED",
            "exclusivity": "REDACTED",
            "piracy": False,
            "url": None,
            "logo_url": None,
        })
        return enriched

    details = fetch_org_details(enriched["sid"])
    for key in ("type", "commitment", "exclusivity", "member_count", "url", "logo_url"):
        if enriched.get(key) in (None, "", "N/A"):
            enriched[key] = details[key]

    enriched["piracy"] = details["piracy"]
    return enriched


@lru_cache(maxsize=200)
def fetch_org_details(sid):
    result = {
        "type": "N/A",
        "commitment": "N/A",
        "exclusivity": "N/A",
        "member_count": "N/A",
        "piracy": False,
        "url": None,
        "logo_url": None,
    }

    if not sid or sid.strip().lower() in _EMPTY_ORG_VALUES:
        return result

    sid = sid.strip().upper()
    url = f"{BASE_URL}/en/orgs/{quote(sid, safe='')}"
    result["url"] = url

    try:
        response = request_with_retry(url)
    except RSILookupError:
        return result

    if response.status_code != 200:
        return result

    soup = BeautifulSoup(response.text, "lxml")
    result["type"] = extract_known_value(soup, _ORG_TYPE_VALUES)
    result["commitment"] = extract_known_value(soup, _COMMITMENT_VALUES)
    result["exclusivity"] = extract_known_value(soup, _EXCLUSIVITY_VALUES)
    result["member_count"] = extract_member_count(soup)
    result["piracy"] = has_piracy_activity(soup)
    result["logo_url"] = extract_org_logo(soup)
    return result


def extract_known_value(soup, allowed_values):
    for item in soup.find_all(["li", "span", "div"]):
        text = clean_text(item)
        if text in allowed_values:
            return text

    return "N/A"


def extract_member_count(soup):
    text = soup.get_text(" ", strip=True)
    return extract_member_count_from_text(text)


def extract_member_count_from_text(text):
    match = re.search(r"\b(\d[\d,.\s]*)\s+members?\b", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return "N/A"


def has_piracy_activity(soup):
    for img in soup.find_all("img"):
        if img.get("alt", "").strip().lower() == "piracy":
            return True

    return False


def normalize_org_result(result):
    result["name"] = strip_known_label(result["name"], _RE_MAIN_ORG)
    result["sid"] = strip_known_label(result["sid"], _RE_SPECTRUM_ID).upper()
    result["rank"] = strip_known_label(result["rank"], _RE_ORG_RANK)
    result["member_count"] = result.get("member_count", "N/A") or "N/A"
    result["relationship"] = result.get("relationship", "Affiliation")
    result["logo_url"] = result.get("logo_url")
    result["redacted"] = bool(result.get("redacted"))

    if not result["name"] or result["name"].lower() in {"unknown", "none"}:
        result["name"] = "None"

    if not result["sid"] or result["sid"].lower() in _EMPTY_ORG_VALUES:
        result["sid"] = "N/A"

    if not result["rank"] or result["rank"].lower() in _EMPTY_ORG_VALUES:
        result["rank"] = "N/A"

    return result


def redacted_org_result(relationship):
    return {
        "relationship": relationship,
        "name": _REDACTED_ORG_NAME,
        "sid": "N/A",
        "rank": "Hidden organization affiliation",
        "member_count": "N/A",
        "logo_url": None,
        "redacted": True,
    }


def extract_org_sid_from_links(element):
    for link in element.find_all("a", href=True):
        match = _RE_ORG_LINK.search(link["href"])
        if match:
            return match.group(1)

    return ""


def extract_image_url(element):
    img = element.find("img")
    if img and img.get("src"):
        return absolute_url(img["src"])

    return None


def extract_org_logo(soup):
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if "/logo/" in src or "Logo" in src:
            return absolute_url(src)

    return extract_image_url(soup)


def strip_known_label(value, label_pattern):
    value = value or ""
    return label_pattern.sub("", value).strip(" :-\n\t")


def clean_text(element):
    if not element:
        return ""

    return element.get_text(" ", strip=True)


def absolute_url(url):
    if not url:
        return None

    return urljoin(BASE_URL, url)
