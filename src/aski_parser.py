from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup


_TURKISH_MAP = str.maketrans(
    {
        "ç": "c", "Ç": "c",
        "ğ": "g", "Ğ": "g",
        "ı": "i", "I": "i", "İ": "i",
        "ö": "o", "Ö": "o",
        "ş": "s", "Ş": "s",
        "ü": "u", "Ü": "u",
    }
)


@dataclass(frozen=True)
class Outage:
    district: str
    fault_date: str = ""
    repair_date: str = ""
    detail: str = ""
    affected_places: str = ""

    def to_api_dict(self) -> dict[str, str]:
        return {
            "district": self.district,
            "faultDate": self.fault_date,
            "repairDate": self.repair_date,
            "detail": self.detail,
            "affectedPlaces": self.affected_places,
        }


def normalize(value: str) -> str:
    normalized = value.translate(_TURKISH_MAP).casefold()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def parse_outages(html: str) -> list[Outage]:
    soup = BeautifulSoup(html, "html.parser")
    lines = [l.strip() for l in soup.get_text("\n").splitlines() if l.strip()]

    outages: list[Outage] = []
    current: dict[str, str] | None = None

    for line in lines:
        if _is_district(line):
            _flush(outages, current)
            current = {"district": line}
            continue

        if current is None:
            continue

        if line.startswith("Arıza Tarihi:"):
            current["fault_date"] = _value(line)
        elif line.startswith("Tamir Tarihi:"):
            current["repair_date"] = _value(line)
        elif line.startswith("Detay:"):
            current["detail"] = _value(line)
        elif line.startswith("Etkilenen Yerler:"):
            current["affected_places"] = _value(line)

    _flush(outages, current)
    return outages


def find_matching_outage(
    html: str,
    target_district: str,
    target_neighborhood: str,
) -> Outage | None:
    district_key = normalize(target_district)
    neighborhood_key = normalize(target_neighborhood)

    for outage in parse_outages(html):
        if normalize(outage.district) != district_key:
            continue
        searchable = normalize(f"{outage.detail} {outage.affected_places}")
        if neighborhood_key in searchable:
            return outage

    return None


def outage_hash(outage: Outage | None) -> str:
    if outage is None:
        return ""
    return normalize(
        f"{outage.district}|{outage.fault_date}|{outage.repair_date}"
        f"|{outage.affected_places}|{outage.detail}"
    )


def _flush(outages: list[Outage], current: dict[str, str] | None) -> None:
    if not current:
        return
    if not any(current.get(k) for k in ("fault_date", "repair_date", "detail", "affected_places")):
        return
    outages.append(
        Outage(
            district=current.get("district", ""),
            fault_date=current.get("fault_date", ""),
            repair_date=current.get("repair_date", ""),
            detail=current.get("detail", ""),
            affected_places=current.get("affected_places", ""),
        )
    )


def _value(line: str) -> str:
    return line.split(":", 1)[1].strip()


def _is_district(line: str) -> bool:
    if ":" in line or len(line) > 40:
        return False
    if normalize(line) in {"ariza kaynakli", "icerik", "anasayfa", "kurumsal", "iletisim"}:
        return False
    letters = [c for c in line if c.isalpha()]
    return bool(letters) and line.upper() == line
