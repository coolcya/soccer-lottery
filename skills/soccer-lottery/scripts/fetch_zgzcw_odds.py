#!/usr/bin/env python3
"""Fetch soccer lottery odds from the single approved ZGZCW source."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any

import requests
from bs4 import BeautifulSoup


ODDS_SOURCE_URL = (
    "https://cp.zgzcw.com/lottery/jchtplayvsForJsp.action"
    "?lotteryId=47&type=jcmini"
)
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Referer": "https://cp.zgzcw.com/",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
}


def clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def parse_float(value: str) -> float | None:
    match = re.search(r"\d+(?:\.\d+)?", value or "")
    if not match:
        return None
    return float(match.group(0))


def parse_odds(container: Any) -> list[float]:
    odds: list[float] = []
    for anchor in container.select("a"):
        number = parse_float(clean_text(anchor.get_text(" ", strip=True)))
        if number is not None:
            odds.append(number)
    return odds


def parse_sp_values(row: Any) -> tuple[list[float], list[float]]:
    hidden = row.select_one("input.spArr")
    if hidden is None:
        return [], []

    groups = clean_text(hidden.get("value", "")).split("|")
    parsed: list[list[float]] = []
    for group in groups:
        values: list[float] = []
        for token in group.split():
            number = parse_float(token)
            if number is not None:
                values.append(number)
        parsed.append(values)

    if len(parsed) < 2:
        return [], []

    return parsed[0][:3], parsed[1][:3]


def find_rows(soup: BeautifulSoup) -> list[Any]:
    table = soup.find("table", id="hide_box_1")
    if table is not None:
        rows = table.find_all("tr", id=re.compile(r"^tr_\d+$"))
        if rows:
            return rows

    return [
        row
        for row in soup.find_all("tr", id=re.compile(r"^tr_\d+$"))
        if row.select_one("td.wh-4") is not None
    ]


def first_text(node: Any, selector: str) -> str:
    match = node.select_one(selector)
    return clean_text(match.get_text(" ", strip=True)) if match else ""


def parse_issue(soup: BeautifulSoup) -> str:
    node = soup.find("textarea", id="responseJson")
    if node is None:
        return ""
    match = re.search(r'issue\s*:\s*"([^"]+)"', node.get_text())
    return match.group(1).strip() if match else ""


def title_value(row: Any, prefix: str) -> str:
    match = row.select_one(f'td.wh-3 span[title^="{prefix}:"]')
    if match is None:
        return ""
    return clean_text(match.get("title", "")).split(":", 1)[-1].strip()


def parse_match_row(row: Any) -> dict[str, Any] | None:
    row_id = row.get("id", "")
    match_id = row_id.removeprefix("tr_")
    if not match_id.isdigit():
        return None

    home_node = row.select_one("td.wh-4")
    away_node = row.select_one("td.wh-6")
    if home_node is None or away_node is None:
        return None

    home_team = clean_text(home_node.select_one("a").get_text(" ", strip=True)) if home_node.select_one("a") else ""
    away_team = clean_text(away_node.select_one("a").get_text(" ", strip=True)) if away_node.select_one("a") else ""
    if not home_team or not away_team:
        return None

    spf_container = row.select_one("div.tz-area.frq")
    rqq_container = row.select_one("div.tz-area.rqq")
    spf = parse_odds(spf_container) if spf_container is not None else []
    rqq = parse_odds(rqq_container) if rqq_container is not None else []

    if len(spf) != 3 or len(rqq) != 3:
        fallback_spf, fallback_rqq = parse_sp_values(row)
        if len(spf) != 3:
            spf = fallback_spf
        if len(rqq) != 3:
            rqq = fallback_rqq

    handicap_node = row.select_one("div.rqq em.rq")
    handicap = clean_text(handicap_node.get_text(" ", strip=True)) if handicap_node else row.get("rq", "")

    score_node = row.select_one("td.wh-5")
    score = clean_text(score_node.get_text(" ", strip=True)) if score_node else ""
    if not score or score == "VS":
        score = None

    classes = set(row.get("class", []))
    home_rank = first_text(home_node, "em.oneDat")
    away_rank = first_text(away_node, "em.oneDat")
    match_time = title_value(row, "比赛时间")
    cutoff_time = title_value(row, "截期时间")

    return {
        "match_id": match_id,
        "match_number": clean_text(row.get("mN") or row.get("mn") or ""),
        "weekday": clean_text(row.get("d", "")),
        "league": clean_text(row.get("m", "")) or first_text(row, "td.wh-2"),
        "kickoff_time": match_time or clean_text(row.get("t", "")),
        "cutoff_time": cutoff_time,
        "home_team": home_team,
        "away_team": away_team,
        "home_rank": home_rank,
        "away_rank": away_rank,
        "score": score,
        "betting_open": "endBet" not in classes,
        "listed_hidden": "hide" in classes,
        "handicap": handicap,
        "spf": {
            "home": spf[0] if len(spf) == 3 else None,
            "draw": spf[1] if len(spf) == 3 else None,
            "away": spf[2] if len(spf) == 3 else None,
        },
        "handicap_spf": {
            "home": rqq[0] if len(rqq) == 3 else None,
            "draw": rqq[1] if len(rqq) == 3 else None,
            "away": rqq[2] if len(rqq) == 3 else None,
        },
    }


def fetch_html(timeout: int = 25) -> str:
    response = requests.get(
        ODDS_SOURCE_URL,
        headers=REQUEST_HEADERS,
        timeout=timeout,
    )
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    return response.text


def fetch_odds(
    date: str | None = None,
    include_closed: bool = True,
    timeout: int = 25,
) -> dict[str, Any]:
    html = fetch_html(timeout=timeout)
    soup = BeautifulSoup(html, "html.parser")
    issue = parse_issue(soup)
    rows = find_rows(soup)
    if not rows:
        raise RuntimeError("Odds page loaded, but no match rows were found.")

    matches: list[dict[str, Any]] = []
    for row in rows:
        match = parse_match_row(row)
        if match is None:
            continue
        if date and date != issue and not match["kickoff_time"].startswith(date):
            continue
        if not include_closed and not match["betting_open"]:
            continue
        matches.append(match)

    return {
        "source": ODDS_SOURCE_URL,
        "source_only": True,
        "fallback_allowed": False,
        "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "lottery_issue": issue,
        "date_filter": date,
        "count": len(matches),
        "matches": matches,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch odds from the approved ZGZCW source only."
    )
    parser.add_argument("--date", help="Filter by kickoff date, for example 2026-09-27.")
    parser.add_argument(
        "--open-only",
        action="store_true",
        help="Return only matches whose betting window is still open.",
    )
    parser.add_argument("--timeout", type=int, default=25, help="HTTP timeout in seconds.")
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    args = build_parser().parse_args()
    try:
        result = fetch_odds(
            date=args.date,
            include_closed=not args.open_only,
            timeout=args.timeout,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "source": ODDS_SOURCE_URL,
                    "source_only": True,
                    "fallback_allowed": False,
                    "valid": False,
                    "error": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    result["valid"] = True
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
