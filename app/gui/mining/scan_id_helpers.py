def parse_scan_query(text, parse_int):
    numeric_ranges = []
    resource_terms = []
    for raw_token in str(text or "").split(","):
        token = raw_token.strip()
        compact = token.replace(" ", "")
        if not compact:
            continue

        if compact.startswith("~"):
            center = parse_int(compact[1:])
            if center is None:
                resource_terms.append(token.lower())
                continue
            numeric_ranges.append((int(center * 0.9), int(center * 1.1)))
            continue

        if "-" in compact:
            left, right = compact.split("-", 1)
            low = parse_int(left)
            high = parse_int(right)
            if low is not None and high is not None:
                numeric_ranges.append((min(low, high), max(low, high)))
                continue

        value = parse_int(compact)
        if value is not None:
            numeric_ranges.append((value, value))
        else:
            resource_terms.append(token.lower())

    return {
        "numeric_ranges": tuple(numeric_ranges),
        "resource_terms": tuple(dict.fromkeys(resource_terms)),
    }


def match_scan_values(values, numeric_ranges):
    if not numeric_ranges:
        return []

    matches = []
    seen = set()
    for value in values:
        for low, high in numeric_ranges:
            if low <= value <= high and value not in seen:
                matches.append(value)
                seen.add(value)
                break

    return matches


def resource_matches(resource, resource_terms):
    if not resource_terms:
        return False

    resource_text = str(resource or "").lower()
    return any(term in resource_text for term in resource_terms)


def scan_signature_matches(signature, query):
    numeric_matches = match_scan_values(signature.values, query["numeric_ranges"])
    name_match = resource_matches(signature.resource, query["resource_terms"])
    return name_match, numeric_matches


def query_has_filters(query):
    return bool(query["numeric_ranges"] or query["resource_terms"])


def format_scan_match_summary(name_match, numeric_matches, format_values):
    parts = []
    if name_match:
        parts.append("Resource match")
    if numeric_matches:
        parts.append(format_values(numeric_matches))
    return " | ".join(parts)
