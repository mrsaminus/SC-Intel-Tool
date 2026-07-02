import hashlib
import re
from dataclasses import dataclass, field, replace

from .models import HaulingContract


PICKUP_LABELS = ("pick up", "pickup", "collect from", "from", "origin")
DELIVERY_LABELS = ("deliver to", "delivery to", "delivery", "drop off", "destination", "to")
COMMODITY_LABELS = ("commodity", "cargo", "item", "goods")
QUANTITY_LABELS = ("quantity", "qty", "amount", "scu")
REWARD_LABELS = ("reward", "payout", "payment")
CONTRACT_LABELS = ("contract", "contract name", "name")


@dataclass(frozen=True)
class HaulingParseResult:
    contracts: tuple[HaulingContract, ...] = field(default_factory=tuple)
    source_text: str = ""
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def confidence(self):
        if not self.contracts:
            return 0.0
        return sum(contract.confidence for contract in self.contracts) / len(self.contracts)


class HaulingContractParser:
    def parse(self, text):
        text = str(text or "")
        blocks = split_contract_blocks(text)
        contracts = []
        warnings = []
        for block in blocks:
            contract = parse_contract_block(block)
            if contract:
                contracts.append(contract)

        if not contracts and text.strip():
            warnings.append("No hauling contract fields detected.")
        if not text.strip():
            warnings.append("No hauling contract text provided.")

        return HaulingParseResult(
            contracts=unique_contract_ids(contracts),
            source_text=text,
            warnings=tuple(warnings),
        )


def parse_hauling_contracts(text):
    return HaulingContractParser().parse(text).contracts


def unique_contract_ids(contracts):
    seen = {}
    unique = []
    for index, contract in enumerate(contracts or ()):
        base_id = contract.id or f"contract-{index + 1}"
        seen[base_id] = seen.get(base_id, 0) + 1
        contract_id = base_id if seen[base_id] == 1 else f"{base_id}-{seen[base_id]}"
        if contract.id == contract_id:
            unique.append(contract)
            continue
        unique.append(replace(contract, id=contract_id))
    return tuple(unique)


def split_contract_blocks(text):
    lines = meaningful_lines(text)
    if not lines:
        return []

    blocks = []
    current = []
    for line in lines:
        if current and starts_contract_block(line):
            blocks.append("\n".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append("\n".join(current))
    return blocks


def parse_contract_block(block):
    lines = meaningful_lines(block)
    if not lines:
        return None

    pickup = value_after_label(lines, PICKUP_LABELS)
    delivery = value_after_label(lines, DELIVERY_LABELS)
    commodity = value_after_label(lines, COMMODITY_LABELS)
    scu = parse_scu(lines)
    reward = parse_reward(lines)
    contract_name = value_after_label(lines, CONTRACT_LABELS)

    if not any((pickup, delivery, commodity, scu)):
        return None

    warnings = []
    confidence = 1.0
    for field_name, value, penalty in (
        ("pickup", pickup, 0.20),
        ("delivery", delivery, 0.20),
        ("commodity", commodity, 0.20),
        ("SCU", scu, 0.25),
    ):
        missing = value is None if field_name == "SCU" else not value
        if missing:
            warnings.append(f"Missing {field_name}.")
            confidence -= penalty

    confidence = max(0.0, round(confidence, 2))
    status = "parsed" if not warnings else "needs_review"

    return HaulingContract(
        id=contract_id(block),
        pickup=pickup,
        delivery=delivery,
        commodity=commodity,
        scu=float(scu or 0.0),
        reward=reward,
        contract_name=contract_name,
        source_text=block,
        confidence=confidence,
        status=status,
        warnings=tuple(warnings),
    )


def starts_contract_block(line):
    normalized = normalize_label_text(line)
    if re.match(r"^contract\s*#?\s*\d+", normalized):
        return True
    return any(label_matches(normalized, label) for label in ("pick up", "pickup"))


def value_after_label(lines, labels):
    for index, line in enumerate(lines):
        label, value = split_labeled_line(line)
        if label and any(labels_equal(label, candidate) for candidate in labels):
            cleaned = clean_field_value(value)
            if cleaned:
                return cleaned
            next_value = next_non_label_line(lines, index + 1)
            if next_value:
                return next_value
    compact = value_after_compact_label("\n".join(lines), labels)
    if compact:
        return compact
    return ""


def value_after_compact_label(text, labels):
    label_pattern = "|".join(re.escape(label) for label in sorted(labels, key=len, reverse=True))
    stop_labels = (
        list(PICKUP_LABELS)
        + list(DELIVERY_LABELS)
        + list(COMMODITY_LABELS)
        + list(QUANTITY_LABELS)
        + list(REWARD_LABELS)
        + list(CONTRACT_LABELS)
    )
    stop_pattern = "|".join(re.escape(label) for label in sorted(set(stop_labels), key=len, reverse=True))
    pattern = re.compile(
        rf"(?is)\b(?:{label_pattern})\b\s*:?\s*(.+?)(?=\b(?:{stop_pattern})\b\s*:|\n|$)"
    )
    match = pattern.search(text)
    if not match:
        return ""
    return clean_value(match.group(1))


def parse_scu(lines):
    for index, line in enumerate(lines):
        label, value = split_labeled_line(line)
        if label and any(labels_equal(label, candidate) for candidate in QUANTITY_LABELS):
            parsed = parse_scu_value(value, allow_bare=True)
            if parsed is not None:
                return parsed
            if index + 1 < len(lines):
                parsed = parse_scu_value(lines[index + 1], allow_bare=True)
                if parsed is not None:
                    return parsed

    for line in lines:
        parsed = parse_scu_value(line)
        if parsed is not None:
            return parsed
    return None


def parse_reward(lines):
    for index, line in enumerate(lines):
        label, value = split_labeled_line(line)
        if label and any(labels_equal(label, candidate) for candidate in REWARD_LABELS):
            parsed = parse_number(value)
            if parsed is not None:
                return parsed
            if index + 1 < len(lines):
                return parse_number(lines[index + 1])
    return None


def parse_scu_value(value, allow_bare=False):
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:s\.?\s*c\.?\s*u\.?|scu)\b", str(value or ""), re.IGNORECASE)
    if not match and allow_bare:
        match = re.fullmatch(r"\s*(\d+(?:[.,]\d+)?)\s*", str(value or ""))
    if not match:
        return None
    return float(match.group(1).replace(",", "."))


def parse_number(value):
    text = str(value or "")
    match = re.search(r"(\d[\d\s,._]*)", text)
    if not match:
        return None
    digits = re.sub(r"[^\d.]", "", match.group(1).replace(",", ""))
    if not digits:
        return None
    try:
        return float(digits)
    except ValueError:
        return None


def split_labeled_line(line):
    text = str(line or "").strip()
    if ":" in text:
        label, value = text.split(":", 1)
        return normalize_label_text(label), value.strip()

    for label in all_labels():
        pattern = re.compile(rf"(?i)^\s*{re.escape(label)}\b\s*(.*)$")
        match = pattern.match(text)
        if match:
            return normalize_label_text(label), match.group(1).strip(" -")
    return "", text


def labels_equal(left, right):
    return normalize_label_text(left) == normalize_label_text(right)


def label_matches(line, label):
    return line.startswith(normalize_label_text(label))


def next_non_label_line(lines, start_index):
    for line in lines[start_index:]:
        label, value = split_labeled_line(line)
        if label:
            return clean_value(value) if value else ""
        return clean_value(line)
    return ""


def clean_value(value):
    text = str(value or "").strip()
    text = re.sub(r"^[\-\u2013\u2014: ]+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_field_value(value):
    text = clean_value(value)
    if not text:
        return ""
    stop_pattern = "|".join(re.escape(label) for label in all_labels())
    match = re.match(rf"(?is)(.+?)(?=\b(?:{stop_pattern})\b\s*:|$)", text)
    return clean_value(match.group(1) if match else text)


def meaningful_lines(text):
    lines = []
    for line in str(text or "").replace("\r", "\n").split("\n"):
        cleaned = clean_value(line)
        if cleaned:
            lines.append(cleaned)
    return lines


def normalize_label_text(value):
    text = str(value or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def all_labels():
    return tuple(
        sorted(
            set(
                PICKUP_LABELS
                + DELIVERY_LABELS
                + COMMODITY_LABELS
                + QUANTITY_LABELS
                + REWARD_LABELS
                + CONTRACT_LABELS
            ),
            key=len,
            reverse=True,
        )
    )


def contract_id(text):
    digest = hashlib.sha1(str(text or "").encode("utf-8")).hexdigest()
    return digest[:12]
