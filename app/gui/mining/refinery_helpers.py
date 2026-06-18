def parse_refinery_duration_seconds(value, parse_float):
    text = str(value or "").strip()
    if not text:
        return 0

    if ":" in text:
        parts = [part.strip() for part in text.split(":")]
        if len(parts) not in (2, 3):
            return 0
        try:
            numbers = [int(part) for part in parts]
        except ValueError:
            return 0

        if len(numbers) == 2:
            minutes, seconds = numbers
            return max(0, minutes * 60 + seconds)

        hours, minutes, seconds = numbers
        return max(0, hours * 3600 + minutes * 60 + seconds)

    return max(0, int(parse_float(text) * 60))


def format_refinery_duration(seconds):
    seconds = max(0, int(seconds or 0))
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"


def refinery_material_code(material, material_choices):
    for code, candidate in material_choices:
        if candidate == material:
            return code

    return str(material or "")[:4].upper()


def canonical_refinery_material(material):
    aliases = {
        "Quantanium": "Quantainium",
    }
    return aliases.get(material, material)


def refinery_option_key(value):
    return " ".join(str(value or "").lower().replace(":", " ").replace("-", " ").split())


def is_material_in_choices(material, choices):
    return any(candidate == material for _code, candidate in choices)


def refinery_material_value_from_price(quantity_cscu, price_sell, parse_float):
    return (parse_float(quantity_cscu) / 100) * parse_float(price_sell)


def calculate_refinery_yield_value(qty_cscu, method_yield, station_bonus=0.0, salvage_multiplier=1.0):
    qty = float(qty_cscu or 0)
    if qty <= 0 or method_yield <= 0:
        return 0.0

    return max(0.0, float(round(qty * method_yield * (1 + station_bonus) * salvage_multiplier)))


def format_scu_from_cscu(cscu, parse_float, format_number):
    return format_number(parse_float(cscu) / 100)


def format_cscu_and_scu(cscu, parse_float, format_number):
    return f"{format_number(cscu)} cSCU / {format_scu_from_cscu(cscu, parse_float, format_number)} SCU"
