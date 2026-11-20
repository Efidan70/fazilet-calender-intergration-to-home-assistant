"""Pure-Python parser for namaz-vakitleri.fazilettakvimi.com pages.

No Home Assistant imports here so it can be unit-tested on its own.
A page shows today's times plus a yesterday/today/tomorrow table.
Every day is keyed by its real date, so a stale or shifted page is never
mistaken for today.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from html.parser import HTMLParser

PRAYER_KEYS = ("imsak", "sabah", "gunes", "ogle", "ikindi", "aksam", "yatsi")
REQUIRED = ("imsak", "gunes", "ogle", "ikindi", "aksam", "yatsi")

MONTHS = {
    "ocak": 1, "subat": 2, "mart": 3, "nisan": 4, "mayis": 5, "haziran": 6,
    "temmuz": 7, "agustos": 8, "eylul": 9, "ekim": 10, "kasim": 11, "aralik": 12,
}
_MONTH_RX = "|".join(MONTHS)
_TR = str.maketrans("İIıŞşĞğÖöÜüÇç", "iiissggoouucc")
_T = r"(?:[01]?\d|2[0-3]):[0-5]\d"
LANG_CODES = {"en", "de", "nl", "fr", "ar", "tr"}


class ParseError(Exception):
    """Raised when a page does not contain usable prayer times."""


@dataclass
class ParsedPage:
    """Result of parsing one page."""

    title: str | None
    days: dict[date, dict[str, str]]
    warnings: list[str] = field(default_factory=list)


def norm(text: str) -> str:
    """Lowercase and strip Turkish diacritics."""
    return text.translate(_TR).lower()


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):  # noqa: D401
        if tag in ("script", "style"):
            self._skip += 1
        self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1
        self.parts.append(" ")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    """Return visible text with a space between elements."""
    parser = _TextExtractor()
    parser.feed(html)
    return "".join(parser.parts)


def _series(text: str, label: str) -> list[list[str]]:
    rx = re.compile(
        rf"(?<![a-z]){label}(?![a-z])[\s|:\-–]*((?:{_T}[\s|]*){{1,3}})"
    )
    out = []
    for m in rx.finditer(text):
        out.append([t.zfill(5) for t in re.findall(_T, m.group(1))])
    return out


def _to_minutes(value: str) -> int:
    h, m = value.split(":")
    return int(h) * 60 + int(m)


def validate_day(times: dict[str, str]) -> None:
    """Check completeness and order (one midnight wrap allowed)."""
    missing = [k for k in REQUIRED if k not in times]
    if missing:
        raise ParseError(f"missing times: {', '.join(missing)}")
    prev = -1
    offset = 0
    wraps = 0
    first = None
    for key in PRAYER_KEYS:
        if key not in times:
            continue
        minutes = _to_minutes(times[key]) + offset
        if minutes <= prev:
            offset += 1440
            minutes += 1440
            wraps += 1
        if wraps > 1:
            raise ParseError(f"times not in order at {key}")
        if first is None:
            first = minutes
        elif minutes - first >= 1440:
            raise ParseError("times span more than 24h")
        prev = minutes


def _shift_year(month: int, base_month: int, base_year: int) -> int:
    if base_month == 1 and month == 12:
        return base_year - 1
    if base_month == 12 and month == 1:
        return base_year + 1
    return base_year


def parse_page(html: str) -> ParsedPage:
    """Parse a Fazilet prayer-times page into {date: {key: 'HH:MM'}}."""
    title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    title = re.sub(r"\s+", " ", title_m.group(1)).strip() if title_m else None

    text = norm(html_to_text(html))
    if not any(_series(text, k) for k in REQUIRED):
        # Fallback: times only present inside script payloads.
        text = norm(re.sub(r"<[^>]+>", " ", html))

    warnings: list[str] = []
    series = {k: _series(text, k) for k in PRAYER_KEYS}
    triples = {k: next((s for s in v if len(s) == 3), None) for k, v in series.items()}
    singles = {k: next((s[0] for s in v if len(s) == 1), None) for k, v in series.items()}

    long_m = re.search(
        rf"(?<!\d)(\d{{1,2}})\s+({_MONTH_RX})\s+(\d{{4}})", text
    )
    head_m = re.search(
        rf"vakit\s+(\d{{1,2}})\s+({_MONTH_RX})[^\d]*?(\d{{1,2}})\s+({_MONTH_RX})"
        rf"[^\d]*?(\d{{1,2}})\s+({_MONTH_RX})",
        text,
    )

    have_triple = all(triples[k] for k in REQUIRED)
    days: dict[date, dict[str, str]] = {}

    if have_triple:
        if head_m and long_m:
            by, bm = int(long_m.group(3)), MONTHS[long_m.group(2)]
            dates = []
            for i in (1, 3, 5):
                d, mo = int(head_m.group(i)), MONTHS[head_m.group(i + 1)]
                dates.append(date(_shift_year(mo, bm, by), mo, d))
        elif long_m:
            from datetime import timedelta

            today = date(int(long_m.group(3)), MONTHS[long_m.group(2)], int(long_m.group(1)))
            dates = [today - timedelta(days=1), today, today + timedelta(days=1)]
            warnings.append("table header not found; assumed yesterday/today/tomorrow")
        else:
            raise ParseError("no date found on page")
        for idx, day in enumerate(dates):
            days[day] = {k: triples[k][idx] for k in PRAYER_KEYS if triples[k]}
        today_key = dates[1]
        for k in REQUIRED:
            if singles[k] and singles[k] != days[today_key].get(k):
                warnings.append(
                    f"{k}: list says {singles[k]}, table says {days[today_key].get(k)}"
                )
    else:
        if not long_m:
            raise ParseError("no date found on page")
        today = date(int(long_m.group(3)), MONTHS[long_m.group(2)], int(long_m.group(1)))
        days[today] = {k: singles[k] for k in PRAYER_KEYS if singles[k]}

    for day, times in days.items():
        try:
            validate_day(times)
        except ParseError as err:
            raise ParseError(f"{day}: {err}") from err
    return ParsedPage(title=title, days=days, warnings=warnings)


# ---- link extraction for the config flow ---------------------------------

class _LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._buf = []

    def handle_data(self, data):
        if self._href is not None:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join("".join(self._buf).split())))
            self._href = None


def extract_links(html: str, base_host: str) -> list[tuple[str, str]]:
    """Return unique internal (path, label) pairs, e.g. ('country/city', 'City')."""
    parser = _LinkExtractor()
    parser.feed(html)
    out: dict[str, str] = {}
    for href, label in parser.links:
        if not href:
            continue
        if href.startswith("http"):
            if base_host not in href:
                continue
            href = "/" + href.split(base_host, 1)[1].lstrip("/")
        if not href.startswith("/"):
            continue
        path = href.split("?")[0].split("#")[0].strip("/")
        if not path or any(c in path for c in ".:_") or path.startswith("api"):
            continue
        if path.split("/")[0] in LANG_CODES and "/" not in path:
            continue
        if label and path not in out:
            out[path] = label
    return sorted(out.items(), key=lambda kv: norm(kv[1]))
