from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from bs4 import BeautifulSoup


TURKISH_CHAR_MAP = str.maketrans(
    {
        "ç": "c",
        "Ç": "c",
        "ğ": "g",
        "Ğ": "g",
        "ı": "i",
        "I": "i",
        "İ": "i",
        "ö": "o",
        "Ö": "o",
        "ş": "s",
        "Ş": "s",
        "ü": "u",
        "Ü": "u",
    }
)


@dataclass(frozen=True)
class Outage:
    district: str
    outage_type: str = ""
    fault_date: str = ""
    repair_date: str = ""
    detail: str = ""
    affected_places: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def normalize_text(value: str) -> str:
    normalized = value.translate(TURKISH_CHAR_MAP).casefold()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def parse_aski_outages(html: str) -> list[Outage]:
    soup = BeautifulSoup(html, "html.parser")
    lines = [
        line.strip()
        for line in soup.get_text("\n").splitlines()
        if line.strip()
    ]

    outages: list[Outage] = []
    current: dict[str, str] | None = None

    for line in lines:
        if _is_probable_district(line):
            _append_if_complete(outages, current)
            current = {"district": line}
            continue

        if current is None:
            continue

        normalized = normalize_text(line)
        if normalized == "ariza kaynakli":
            current["outage_type"] = line
        elif line.startswith("Arıza Tarihi:"):
            current["fault_date"] = _field_value(line)
        elif line.startswith("Tamir Tarihi:"):
            current["repair_date"] = _field_value(line)
        elif line.startswith("Detay:"):
            current["detail"] = _field_value(line)
        elif line.startswith("Etkilenen Yerler:"):
            current["affected_places"] = _field_value(line)

    _append_if_complete(outages, current)
    return outages


def find_matching_outages(
    html: str,
    target_district: str,
    target_neighborhood: str,
) -> list[Outage]:
    district_key = normalize_text(target_district)
    neighborhood_key = normalize_text(target_neighborhood)

    matches: list[Outage] = []
    for outage in parse_aski_outages(html):
        if normalize_text(outage.district) != district_key:
            continue

        searchable = normalize_text(
            " ".join([outage.detail, outage.affected_places])
        )
        if neighborhood_key in searchable:
            matches.append(outage)

    return matches


def _append_if_complete(
    outages: list[Outage],
    current: dict[str, str] | None,
) -> None:
    if not current:
        return

    has_outage_fields = any(
        current.get(key)
        for key in ("fault_date", "repair_date", "detail", "affected_places")
    )
    if not has_outage_fields:
        return

    outages.append(
        Outage(
            district=current.get("district", ""),
            outage_type=current.get("outage_type", ""),
            fault_date=current.get("fault_date", ""),
            repair_date=current.get("repair_date", ""),
            detail=current.get("detail", ""),
            affected_places=current.get("affected_places", ""),
        )
    )


def _field_value(line: str) -> str:
    return line.split(":", 1)[1].strip()


def _is_probable_district(line: str) -> bool:
    if ":" in line or len(line) > 40:
        return False

    normalized = normalize_text(line)
    if normalized in {
        "ariza kaynakli",
        "icerik",
        "anasayfa",
        "kurumsal",
        "iletisim",
    }:
        return False

    letters = [char for char in line if char.isalpha()]
    return bool(letters) and line.upper() == line

