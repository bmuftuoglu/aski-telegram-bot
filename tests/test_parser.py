from aski_checker.parser import find_matching_outages, normalize_text, parse_aski_outages


SAMPLE_HTML = """
<html>
  <body>
    <h4>ÇANKAYA</h4>
    <h4>Arıza Kaynaklı</h4>
    <p>Arıza Tarihi: 19.05.2026 09:20:00</p>
    <p>Tamir Tarihi: 19.05.2026 18:00:00</p>
    <p>Detay: Çiğdem mahallesi, İşçi Blokları mahallesi ve Karakusunlar.</p>
    <p>Etkilenen Yerler: Çiğdem mahallesi, İşçi Blokları mahallesi</p>

    <h4>ÇANKAYA</h4>
    <h4>Arıza Kaynaklı</h4>
    <p>Arıza Tarihi: 19.05.2026 14:30:00</p>
    <p>Tamir Tarihi: 19.05.2026 17:00:00</p>
    <p>Detay: Beytepe mahallesi 1674 sokak.</p>
    <p>Etkilenen Yerler: Beytepe mahallesi</p>
  </body>
</html>
"""


def test_parse_aski_outages_extracts_records() -> None:
    outages = parse_aski_outages(SAMPLE_HTML)

    assert len(outages) == 2
    assert outages[0].district == "ÇANKAYA"
    assert outages[0].repair_date == "19.05.2026 18:00:00"


def test_find_matching_outages_matches_target_neighborhood() -> None:
    matches = find_matching_outages(SAMPLE_HTML, "ÇANKAYA", "İşçi Blokları")

    assert len(matches) == 1
    assert "İşçi Blokları" in matches[0].affected_places


def test_find_matching_outages_ignores_other_neighborhoods() -> None:
    matches = find_matching_outages(SAMPLE_HTML, "ÇANKAYA", "Ayrancı")

    assert matches == []


def test_normalize_text_handles_turkish_case_and_diacritics() -> None:
    assert normalize_text("İŞÇİ BLOKLARI Mahallesi") == "isci bloklari mahallesi"

