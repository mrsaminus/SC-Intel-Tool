import requests
from bs4 import BeautifulSoup
from functools import lru_cache


class RSILookupError(Exception):
    pass


HEADERS = {
    "User-Agent": "Mozilla/5.0 SC-Intel-Tool"
}


@lru_cache(maxsize=200)
def lookup_player(handle: str) -> dict:
    handle = handle.strip()

    if not handle:
        raise RSILookupError("No handle provided.")

    url = f"https://robertsspaceindustries.com/citizens/{handle}"

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=20
    )

    if response.status_code == 404:
        raise RSILookupError("Player not found.")

    if response.status_code != 200:
        raise RSILookupError(
            f"RSI returned status code {response.status_code}"
        )

    soup = BeautifulSoup(response.text, "lxml")

    avatar = extract_avatar(soup)
    display_name = extract_display_name(soup)

    return {
        "handle": handle,
        "display_name": display_name,
        "avatar": avatar,
        "citizen_record": extract_label_value(
            soup,
            "UEE Citizen Record"
        ),
        "enlisted": extract_label_value(
            soup,
            "Enlisted"
        ),
        "location": extract_label_value(
            soup,
            "Location"
        ),
        "fluency": extract_label_value(
            soup,
            "Fluency"
        ),
        "main_org": extract_main_org(soup),
        "profile_url": url,
    }


def extract_display_name(soup):
    selectors = [
        ".profile .entry strong",
        ".entry.nickname strong",
        ".citizen-record .value"
    ]

    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            return element.get_text(strip=True)

    return "Unknown"


def extract_avatar(soup):
    img = soup.select_one("img.thumb")

    if img and img.get("src"):
        return img["src"]

    return None


def extract_label_value(soup, label):
    text = soup.get_text("\n", strip=True)

    lines = [
        line.strip()
        for line in text.split("\n")
        if line.strip()
    ]

    for i, line in enumerate(lines):
        if label.lower() in line.lower():
            if i + 1 < len(lines):
                return lines[i + 1]

    return "Unknown"


def extract_main_org(soup):
    text = soup.get_text("\n", strip=True)

    lines = [
        line.strip()
        for line in text.split("\n")
        if line.strip()
    ]

    for i, line in enumerate(lines):
        if "Main organization" in line:
            if i + 1 < len(lines):
                return lines[i + 1]

    return "None"