from .shared import *


class ItemFinderShipMixin:
    def ship_group_key(self, item, category_filter):
        if self.is_ship_sale_item(item) and category_filter in {"All categories", SHIP_SALE_CATEGORY}:
            return (SHIP_SALE_CATEGORY, self.normalized_ship_name(item.name))
        if self.is_ship_rent_item(item) and category_filter in {"All categories", SHIP_RENT_CATEGORY}:
            return (SHIP_RENT_CATEGORY, self.normalized_ship_name(item.name))
        if item.category in {WIKELO_CATEGORY, SPECIAL_ACQUISITION_CATEGORY} and category_filter == item.category:
            return (item.category, self.normalized_ship_name(item.name))

        return None


    def merged_ship_item(self, items, category):
        base = items[0]
        locations = self.unique_item_locations(
            location
            for item in items
            for location in getattr(item, "locations", ())
        )
        return replace(
            base,
            item_id=f"{category}:{self.normalized_ship_name(base.name)}",
            category=category,
            sold=category not in {WIKELO_CATEGORY, SPECIAL_ACQUISITION_CATEGORY},
            availability=self.location_availability_text(locations),
            effect=self.ship_detail_summary_text(category, locations),
            locations=tuple(locations),
        )


    def unique_item_locations(self, locations):
        unique_locations = []
        seen = set()
        for location in locations:
            key = (
                str(location.location).strip().lower(),
                str(location.price).strip().lower(),
                str(location.verified).strip().lower(),
            )
            if key in seen:
                continue
            seen.add(key)
            unique_locations.append(location)

        return unique_locations


    def normalized_ship_name(self, name):
        return " ".join(str(name or "").lower().split())


    def is_ship_sale_item(self, item):
        return item.source == "SC Focus" and item.item_type == "Ship" and item.category in SHIP_SALE_SOURCE_CATEGORIES


    def is_ship_rent_item(self, item):
        return item.source == "SC Focus" and item.item_type == "Ship" and item.category == SHIP_RENT_CATEGORY


    def is_ship_item(self, item):
        return item.source == "SC Focus" and item.item_type == "Ship" and item.category in SHIP_CATEGORIES


    def item_summary_text(self, item, category_filter):
        if self.is_ship_item(item) and category_filter in {SHIP_SALE_CATEGORY, SHIP_RENT_CATEGORY}:
            return self.lowest_ship_price_text(item)

        return item.effect


    def item_sort_value(self, item, column, value, category_filter):
        if column == 4 and self.is_ship_item(item) and category_filter in {SHIP_SALE_CATEGORY, SHIP_RENT_CATEGORY}:
            price = self.lowest_ship_price_value(item)
            return price if price is not None else float("inf")
        if column == 3:
            locations = self.known_item_locations(item)
            if locations is not None:
                return len(locations)

        return value


    def lowest_ship_price_text(self, item):
        price = self.lowest_ship_price_value(item)
        if price is not None:
            return f"{price:,} aUEC"

        prices = {location.price for location in getattr(item, "locations", ()) if location.price}
        if WIKELO_CATEGORY in prices:
            return WIKELO_CATEGORY
        if "No aUEC price" in prices:
            return "No aUEC price"

        return "N/A"


    def lowest_ship_price_value(self, item):
        prices = [
            self.price_number(location.price)
            for location in getattr(item, "locations", ())
        ]
        prices = [price for price in prices if price is not None]
        return min(prices) if prices else None


    def price_number(self, value):
        digits = "".join(char for char in str(value or "") if char.isdigit())
        if not digits:
            return None

        try:
            return int(digits)
        except ValueError:
            return None


    def ship_detail_summary_text(self, category, locations):
        lowest_price = self.lowest_ship_price_text_for_locations(locations)
        if lowest_price == "N/A":
            return f"{category} | {self.location_count_text(len(locations))}"

        return f"{category} | Lowest {lowest_price}"


    def lowest_ship_price_text_for_locations(self, locations):
        prices = [
            self.price_number(location.price)
            for location in locations
        ]
        prices = [price for price in prices if price is not None]
        if prices:
            return f"{min(prices):,} aUEC"

        price_texts = {location.price for location in locations if location.price}
        if WIKELO_CATEGORY in price_texts:
            return WIKELO_CATEGORY
        if "No aUEC price" in price_texts:
            return "No aUEC price"

        return "N/A"


    def ship_metadata_text(self, item):
        metadata = ship_metadata_for(item.name)
        if not metadata:
            return "Crew: N/A | Cargo: N/A"

        crew = "N/A"
        if metadata.min_crew is not None and metadata.max_crew is not None:
            if metadata.min_crew == metadata.max_crew:
                crew = str(metadata.min_crew)
            else:
                crew = f"{metadata.min_crew}-{metadata.max_crew}"

        cargo = "N/A"
        if metadata.cargo_scu is not None:
            cargo = f"{metadata.cargo_scu:,} SCU"

        return f"Crew: {crew} | Cargo: {cargo}"

