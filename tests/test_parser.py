from aski_parser import find_matching_outage, normalize, parse_outages


# Old format: values on the same line as labels
SAMPLE_HTML_OLD_FORMAT = """
<html>
  <body>
    <h4>ÇANKAYA</h4>
    <p>Arıza Tarihi: 19.05.2026 09:20:00</p>
    <p>Tamir Tarihi: 19.05.2026 18:00:00</p>
    <p>Detay: Çiğdem mahallesi, İşçi Blokları mahallesi ve Karakusunlar.</p>
    <p>Etkilenen Yerler: Çiğdem mahallesi, İşçi Blokları mahallesi</p>

    <h4>ÇANKAYA</h4>
    <p>Arıza Tarihi: 19.05.2026 14:30:00</p>
    <p>Tamir Tarihi: 19.05.2026 17:00:00</p>
    <p>Detay: Beytepe mahallesi 1674 sokak.</p>
    <p>Etkilenen Yerler: Beytepe mahallesi</p>
  </body>
</html>
"""

# New format: values on the next line after the label
SAMPLE_HTML_NEW_FORMAT = """
<html>
  <body>
    <h4>ÇANKAYA</h4>
    <p>Arıza Kaynaklı</p>
    <p>Arıza Tarihi:</p>
    <p>Tamir Tarihi:</p>
    <p>Detay:</p>
    <p>Çiğdem mahallesi, İşçi Blokları mahallesi ve Karakusunlar. 19.Mayıs.2026 saat-09:20</p>
    <p>Etkilenen Yerler:</p>
    <p>Çiğdem mahallesi, İşçi Blokları mahallesi</p>

    <h4>ÇANKAYA</h4>
    <p>Arıza Kaynaklı</p>
    <p>Arıza Tarihi:</p>
    <p>Tamir Tarihi:</p>
    <p>Detay:</p>
    <p>Beytepe mahallesi 1674 sokak.</p>
    <p>Etkilenen Yerler:</p>
    <p>Beytepe mahallesi</p>
  </body>
</html>
"""


def test_parse_outages_old_format() -> None:
    outages = parse_outages(SAMPLE_HTML_OLD_FORMAT)
    assert len(outages) == 2
    assert outages[0].district == "ÇANKAYA"
    assert outages[0].repair_date == "19.05.2026 18:00:00"


def test_parse_outages_new_format() -> None:
    outages = parse_outages(SAMPLE_HTML_NEW_FORMAT)
    assert len(outages) == 2
    assert outages[0].district == "ÇANKAYA"
    assert "İşçi Blokları" in outages[0].affected_places


def test_find_matching_outage_old_format() -> None:
    match = find_matching_outage(SAMPLE_HTML_OLD_FORMAT, "ÇANKAYA", "İşçi Blokları")
    assert match is not None
    assert "İşçi Blokları" in match.affected_places


def test_find_matching_outage_new_format() -> None:
    match = find_matching_outage(SAMPLE_HTML_NEW_FORMAT, "ÇANKAYA", "İşçi Blokları")
    assert match is not None
    assert "İşçi Blokları" in match.affected_places


def test_find_matching_outage_ignores_other_neighborhoods() -> None:
    assert find_matching_outage(SAMPLE_HTML_NEW_FORMAT, "ÇANKAYA", "Ayrancı") is None


def test_normalize_handles_turkish() -> None:
    assert normalize("İŞÇİ BLOKLARI Mahallesi") == "isci bloklari mahallesi"
