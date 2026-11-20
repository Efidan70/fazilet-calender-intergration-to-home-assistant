"""Run: python3 -I tests/test_parser.py"""
import importlib.util
import pathlib
import sys
import unittest
from datetime import date

_p = pathlib.Path(__file__).parent.parent / "custom_components/fazilet_takvimi/parser.py"
_spec = importlib.util.spec_from_file_location("fz_parser", _p)
fz = importlib.util.module_from_spec(_spec)
sys.modules["fz_parser"] = fz
_spec.loader.exec_module(fz)

# Layout mirrors a sample city page of 20 Nov 2026 (label + time as separate elements).
SAMPLE_HTML = """
<html><head><title>Sample City Namaz Vakitleri – Country | Fazilet Takvimi</title>
<script>var x = {"imsak":"99:99"};</script></head><body>
<h1>Sample City Namaz Vakitleri</h1><p>20 Kasım 2026 Cuma</p><p>7 Cemaziyelahir 1448</p>
<ol>
<li><span>İmsak</span><span>05:52</span></li>
<li><span>Güneş</span><span>07:58</span></li>
<li><span>Öğle</span><span>12:28</span></li>
<li><span>İkindi</span><span>14:25</span></li>
<li><span>Akşam</span><span>16:48</span></li>
<li><span>Yatsı</span><span>18:37</span></li>
</ol><p>Sabah 06:12</p>
<table>
<tr><th>Vakit</th><th>19 Kasım (Dün)</th><th>20 Kasım (Bugün)</th><th>21 Kasım (Yarın)</th></tr>
<tr><td>İmsak</td><td>05:50</td><td>05:52</td><td>05:53</td></tr>
<tr><td>Sabah</td><td>06:10</td><td>06:12</td><td>06:13</td></tr>
<tr><td>Güneş</td><td>07:56</td><td>07:58</td><td>07:59</td></tr>
<tr><td>Öğle</td><td>12:28</td><td>12:28</td><td>12:28</td></tr>
<tr><td>İkindi</td><td>14:26</td><td>14:25</td><td>14:24</td></tr>
<tr><td>Akşam</td><td>16:49</td><td>16:48</td><td>16:46</td></tr>
<tr><td>Yatsı</td><td>18:38</td><td>18:37</td><td>18:36</td></tr>
</table>
<a href="/country">Country: all cities →</a>
<a href="https://namaz-vakitleri.fazilettakvimi.com/country/city">Sample City</a>
<a href="/en">English</a><a href="/api/og/tr/country/city.jpg">img</a>
</body></html>
"""

# Same page with the table flattened to text and no tags between words.
SAMPLE_TEXT = (
    "20 Kasım 2026 Cuma İmsak05:52 Güneş07:58 Öğle12:28 İkindi14:25 Akşam16:48 Yatsı18:37 "
    "Vakit 19 Kasım (Dün) 20 Kasım (Bugün) 21 Kasım (Yarın) | İmsak | 05:50 | 05:52 | 05:53 | "
    "Sabah | 06:10 | 06:12 | 06:13 | Güneş | 07:56 | 07:58 | 07:59 | Öğle | 12:28 | 12:28 | 12:28 | "
    "İkindi | 14:26 | 14:25 | 14:24 | Akşam | 16:49 | 16:48 | 16:46 | Yatsı | 18:38 | 18:37 | 18:36 |"
)


class ParserTests(unittest.TestCase):
    def check(self, page):
        self.assertEqual(sorted(page.days), [date(2026, 11, 19), date(2026, 11, 20), date(2026, 11, 21)])
        today = page.days[date(2026, 11, 20)]
        self.assertEqual(
            today,
            {"imsak": "05:52", "sabah": "06:12", "gunes": "07:58", "ogle": "12:28",
             "ikindi": "14:25", "aksam": "16:48", "yatsi": "18:37"},
        )
        self.assertEqual(page.days[date(2026, 11, 21)]["aksam"], "16:46")
        self.assertEqual(page.days[date(2026, 11, 19)]["imsak"], "05:50")
        self.assertEqual(page.warnings, [])

    def test_html(self):
        page = fz.parse_page(SAMPLE_HTML)
        self.check(page)
        self.assertTrue(page.title.startswith("Sample City"))

    def test_flat_text(self):
        self.check(fz.parse_page(SAMPLE_TEXT))

    def test_year_rollover(self):
        text = SAMPLE_TEXT.replace("20 Kasım 2026", "1 Ocak 2027").replace("19 Kasım", "31 Aralık").replace(
            "20 Kasım", "1 Ocak").replace("21 Kasım", "2 Ocak")
        page = fz.parse_page(text)
        self.assertIn(date(2026, 12, 31), page.days)
        self.assertIn(date(2027, 1, 2), page.days)

    def test_list_only(self):
        page = fz.parse_page("20 Kasım 2026 İmsak 05:52 Güneş 07:58 Öğle 12:28 İkindi 14:25 Akşam 16:48 Yatsı 18:37")
        self.assertEqual(list(page.days), [date(2026, 11, 20)])

    def test_conflict_warns(self):
        page = fz.parse_page(SAMPLE_TEXT.replace("İmsak05:52", "İmsak05:55"))
        self.assertTrue(page.warnings)

    def test_bad_order_rejected(self):
        with self.assertRaises(fz.ParseError):
            fz.parse_page("20 Kasım 2026 İmsak 12:00 Güneş 07:58 Öğle 12:28 İkindi 14:25 Akşam 16:48 Yatsı 18:37")

    def test_no_times(self):
        with self.assertRaises(fz.ParseError):
            fz.parse_page("<html>Vakitler hazırlanıyor</html>")

    def test_midnight_wrap_ok(self):
        fz.validate_day({"imsak": "01:10", "gunes": "04:30", "ogle": "13:40", "ikindi": "18:20",
                         "aksam": "22:50", "yatsi": "00:35"})

    def test_links(self):
        links = dict(fz.extract_links(SAMPLE_HTML, "namaz-vakitleri.fazilettakvimi.com"))
        self.assertEqual(links, {"country": "Country: all cities →", "country/city": "Sample City"})


if __name__ == "__main__":
    unittest.main()
