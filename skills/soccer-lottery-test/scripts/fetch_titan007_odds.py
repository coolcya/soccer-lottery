#!/usr/bin/env python3
"""Fetch soccer lottery odds and change history from Titan007 only."""

from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from html import unescape
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


SOURCE_HOST = "cp.titan007.com"
ODDS_SOURCE_URL = "https://cp.titan007.com/buy/JingCai.aspx"
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Referer": ODDS_SOURCE_URL,
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
}


def clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def parse_float(value: str | None) -> float | None:
    match = re.search(r"\d+(?:\.\d+)?", value or "")
    if not match:
        return None
    return float(match.group(0))


def parse_signed_handicap(value: str | None) -> int | None:
    match = re.search(r"([+-]?\d+)", value or "")
    if not match:
        return None
    return int(match.group(1))


def validate_date(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("Date must use YYYY-MM-DD format.") from exc
    return parsed.strftime("%Y-%m-%d")


def source_request_url(date: str | None) -> str:
    if date is None:
        return ODDS_SOURCE_URL
    page_date = datetime.strptime(date, "%Y-%m-%d").strftime("%Y-%m-%d")
    page_date = page_date.replace("-0", "-")
    return f"{ODDS_SOURCE_URL}?date={page_date}"


def ensure_titan_url(url: str) -> str:
    absolute = urljoin(ODDS_SOURCE_URL, unescape(url))
    parsed = urlparse(absolute)
    if parsed.scheme != "https" or parsed.hostname != SOURCE_HOST:
        raise ValueError(f"Rejected non-Titan007 URL: {absolute}")
    return absolute


def fetch_html(url: str, timeout: int) -> str:
    response = requests.get(
        url,
        headers=REQUEST_HEADERS,
        timeout=timeout,
        allow_redirects=False,
    )
    if 300 <= response.status_code < 400:
        raise RuntimeError(f"Rejected redirect from approved source: {response.status_code}")
    response.raise_for_status()
    if urlparse(response.url).hostname != SOURCE_HOST:
        raise RuntimeError(f"Rejected response from non-Titan007 host: {response.url}")
    response.encoding = "utf-8"
    return response.text


def parse_page_issue(soup: BeautifulSoup) -> str:
    match = re.search(r'IssueNum\s*=\s*"([^"]+)"', str(soup))
    return match.group(1).strip() if match else ""


def parse_group_date(value: str) -> str | None:
    match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", value)
    if not match:
        return None
    year, month, day = (int(part) for part in match.groups())
    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_title_time(value: str | None) -> str:
    text = clean_text(value)
    if "：" in text:
        return text.split("：", 1)[1].strip()
    if ":" in text:
        return text.split(":", 1)[1].strip()
    return text


def parse_market_odds(row: Any) -> dict[str, float | None]:
    odds: dict[str, float | None] = {}
    for key, title in (("home", "主胜"), ("draw", "平局"), ("away", "客胜")):
        cell = row.find("td", attrs={"title": title})
        span = cell.find("span") if cell is not None else None
        odds[key] = parse_float(clean_text(span.get_text(" ", strip=True))) if span else None
    return odds


def parse_history_url(row: Any) -> str | None:
    link = row.find("a", string=re.compile(r"变"))
    if link is None:
        return None
    onclick = link.get("onclick", "")
    match = re.search(r"ShowOddsWinow\(\s*['\"]([^'\"]+)['\"]", onclick)
    if not match:
        return None
    return ensure_titan_url(match.group(1))


def parse_history_records(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict[str, Any]] = []
    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 4:
            continue
        values = [clean_text(cell.get_text(" ", strip=True)) for cell in cells]
        odds = [parse_float(values[0]), parse_float(values[1]), parse_float(values[2])]
        if any(value is None for value in odds):
            continue
        if not re.match(r"\d{2}-\d{2}\s+\d{2}:\d{2}", values[3]):
            continue
        records.append(
            {
                "home": odds[0],
                "draw": odds[1],
                "away": odds[2],
                "change_time": values[3],
            }
        )

    # The endpoint returns newest first. Store records oldest-first for analysis.
    records.reverse()
    for index, record in enumerate(records, start=1):
        record["sequence"] = index
    return records


def movement(current: float | None, opening: float | None) -> str:
    if current is None or opening is None:
        return "unknown"
    delta = round(current - opening, 2)
    if delta > 0:
        return "up"
    if delta < 0:
        return "down"
    return "stable"


def summarize_market_changes(
    current: dict[str, float | None],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    if not records:
        return {
            "available": False,
            "record_count": 0,
            "opening": None,
            "latest_record": None,
            "current": current,
            "delta_current_vs_opening": {},
            "movement": {},
            "has_change": False,
        }

    opening = records[0]
    latest = records[-1]
    delta = {
        key: round(current[key] - opening[key], 2)
        if current.get(key) is not None and opening.get(key) is not None
        else None
        for key in ("home", "draw", "away")
    }
    return {
        "available": True,
        "record_count": len(records),
        "opening": opening,
        "latest_record": latest,
        "current": current,
        "delta_current_vs_opening": delta,
        "movement": {
            key: movement(current.get(key), opening.get(key))
            for key in ("home", "draw", "away")
        },
        "has_change": any(value not in (None, 0) for value in delta.values())
        or latest != opening,
    }


def handicap_settlement_rule(handicap: int | None) -> dict[str, Any]:
    if handicap is None:
        return {
            "available": False,
            "note": "让球数缺失，无法解释让球胜平负。",
        }

    if handicap < 0:
        goals = abs(handicap)
        return {
            "available": True,
            "type": "主队让球",
            "display": f"主队让{goals}球",
            "home_handicap": handicap,
            "formula": "home_goals - away_goals + handicap",
            "rules": {
                "胜": f"主队得分减去客队得分大于{goals}",
                "平": f"主队得分减去客队得分等于{goals}",
                "负": f"主队得分减去客队得分小于{goals}",
            },
        }

    if handicap > 0:
        goals = handicap
        return {
            "available": True,
            "type": "主队受让",
            "display": f"主队受让{goals}球",
            "home_handicap": handicap,
            "formula": "home_goals - away_goals + handicap",
            "rules": {
                "胜": f"客队得分减去主队得分小于{goals}",
                "平": f"客队得分减去主队得分等于{goals}",
                "负": f"客队得分减去主队得分大于{goals}",
            },
        }

    return {
        "available": True,
        "type": "平手",
        "display": "平手",
        "home_handicap": 0,
        "formula": "home_goals - away_goals",
        "rules": {
            "胜": "主队得分大于客队得分",
            "平": "主队得分等于客队得分",
            "负": "主队得分小于客队得分",
        },
    }


def settle_handicap_result(
    home_goals: int,
    away_goals: int,
    handicap: int,
) -> str:
    """Return 胜/平/负 for the home team under Jingcai handicap rules."""
    adjusted_home_score = home_goals - away_goals + handicap
    if adjusted_home_score > 0:
        return "胜"
    if adjusted_home_score == 0:
        return "平"
    return "负"


def parse_score(value: str) -> tuple[int, int] | None:
    match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", clean_text(value))
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def parse_match_row(row: Any, group_date: str | None) -> dict[str, Any] | None:
    row_id = row.get("id", "")
    lottery_id = row_id.removeprefix("row_")
    if not lottery_id.isdigit():
        return None

    spf_row = row.find("tr", id=f"spfTr_{lottery_id}")
    handicap_row = row.find("tr", id=f"rqTr_{lottery_id}")
    if spf_row is None or handicap_row is None:
        return None

    home_team_link = row.find("a", id=re.compile(r"^HomeTeam_"))
    away_team_link = row.find("a", id=re.compile(r"^GuestTeam_"))
    if home_team_link is None or away_team_link is None:
        return None

    spf = parse_market_odds(spf_row)
    handicap_spf = parse_market_odds(handicap_row)
    if any(value is None for value in spf.values()):
        return None
    if any(value is None for value in handicap_spf.values()):
        return None

    handicap_text = clean_text(handicap_row.find("td").get_text(" ", strip=True))
    handicap = parse_signed_handicap(handicap_text)
    if handicap is None:
        handicap = parse_signed_handicap(row.get("polygoal"))

    kickoff_cell = row.find("td", attrs={"title": re.compile(r"^开赛时间")})
    cutoff_cell = row.find("td", attrs={"title": re.compile(r"^截止时间")})
    match_number_text = clean_text(row.find("td").get_text(" ", strip=True))
    number_match = re.search(r"(\d{3,})", match_number_text)

    score_cell = row.find("span", class_=re.compile(r"\bscore\b"))
    score = clean_text(score_cell.get_text(" ", strip=True)) if score_cell else ""
    parsed_score = parse_score(score)
    result = None
    if parsed_score is not None and handicap is not None:
        result = settle_handicap_result(parsed_score[0], parsed_score[1], handicap)

    return {
        "lottery_id": lottery_id,
        "match_id": clean_text(row.get("matchid", "")),
        "match_number": number_match.group(1) if number_match else "",
        "group_date": group_date,
        "league": clean_text(row.find_all("td")[1].get_text(" ", strip=True))
        if len(row.find_all("td")) > 1
        else "",
        "kickoff_time": parse_title_time(kickoff_cell.get("title") if kickoff_cell else ""),
        "cutoff_time": parse_title_time(cutoff_cell.get("title") if cutoff_cell else ""),
        "home_team": clean_text(home_team_link.get_text(" ", strip=True)),
        "away_team": clean_text(away_team_link.get_text(" ", strip=True)),
        "score": score or None,
        "home_goals": parsed_score[0] if parsed_score else None,
        "away_goals": parsed_score[1] if parsed_score else None,
        "betting_open": row.get("cansale", "").lower() == "true",
        "spf": spf,
        "handicap": handicap_text,
        "handicap_value": handicap,
        "handicap_spf": handicap_spf,
        "handicap_settlement": handicap_settlement_rule(handicap),
        "settled_handicap_result": result,
        "spf_history_url": parse_history_url(spf_row),
        "handicap_history_url": parse_history_url(handicap_row),
    }


def parse_matches(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    matches: list[dict[str, Any]] = []
    group_date: str | None = None

    for row in soup.find_all("tr"):
        classes = set(row.get("class", []))
        if "niDate" in classes:
            group_date = parse_group_date(clean_text(row.get_text(" ", strip=True)))
        if not str(row.get("id", "")).startswith("row_"):
            continue
        match = parse_match_row(row, group_date)
        if match is not None:
            matches.append(match)

    return matches


def fetch_history(url: str | None, timeout: int) -> list[dict[str, Any]]:
    if not url:
        raise ValueError("Missing change-history URL.")
    safe_url = ensure_titan_url(url)
    html = fetch_html(safe_url, timeout=timeout)
    records = parse_history_records(html)
    if not records:
        raise RuntimeError("Change-history endpoint returned no records.")
    return records


def enrich_match_history(
    match: dict[str, Any],
    timeout: int,
) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    for key, field in (
        ("spf_history", "spf_history_url"),
        ("handicap_history", "handicap_history_url"),
    ):
        try:
            records = fetch_history(match.get(field), timeout=timeout)
            match[key] = records
        except Exception as exc:
            match[key] = []
            errors.append(f"{field}: {exc}")

    match["spf_changes"] = summarize_market_changes(
        match["spf"], match.get("spf_history", [])
    )
    match["handicap_changes"] = summarize_market_changes(
        match["handicap_spf"], match.get("handicap_history", [])
    )
    return match, errors


def fetch_odds(
    date: str | None = None,
    include_closed: bool = True,
    timeout: int = 25,
    history_timeout: int = 20,
    workers: int = 6,
) -> dict[str, Any]:
    date = validate_date(date)
    request_url = source_request_url(date)
    html = fetch_html(request_url, timeout=timeout)
    soup = BeautifulSoup(html, "html.parser")
    page_issue = parse_page_issue(soup)
    matches = parse_matches(html)
    if not matches:
        raise RuntimeError("Titan007 page loaded, but no match rows were found.")

    if not include_closed:
        matches = [match for match in matches if match["betting_open"]]

    history_errors: list[str] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {
            executor.submit(enrich_match_history, match, history_timeout): match
            for match in matches
        }
        for future in as_completed(futures):
            match, errors = future.result()
            label = f"{match.get('match_number')} {match.get('home_team')} vs {match.get('away_team')}"
            history_errors.extend(f"{label}: {error}" for error in errors)

    return {
        "source": ODDS_SOURCE_URL,
        "source_url": request_url,
        "source_only": True,
        "fallback_allowed": False,
        "source_host": SOURCE_HOST,
        "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "page_issue": page_issue,
        "date_filter": date,
        "count": len(matches),
        "history_complete": not history_errors,
        "history_errors": history_errors,
        "valid": not history_errors,
        "handicap_settlement_examples": {
            "主队让1球": {
                "handicap": -1,
                "胜": "主队得分 - 客队得分 > 1",
                "平": "主队得分 - 客队得分 = 1",
                "负": "主队得分 - 客队得分 < 1",
            },
            "主队受让3球": {
                "handicap": 3,
                "胜": "客队得分 - 主队得分 < 3",
                "平": "客队得分 - 主队得分 = 3",
                "负": "客队得分 - 主队得分 > 3",
            },
        },
        "matches": matches,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch Titan007 odds and change histories from the approved source only."
    )
    parser.add_argument("--date", help="Filter by kickoff date, for example 2026-09-29.")
    parser.add_argument(
        "--open-only",
        action="store_true",
        help="Return only matches whose betting window is still open.",
    )
    parser.add_argument("--timeout", type=int, default=25, help="Page HTTP timeout.")
    parser.add_argument(
        "--history-timeout",
        type=int,
        default=20,
        help="Change-history HTTP timeout.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=6,
        help="Parallel change-history requests.",
    )
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
            history_timeout=args.history_timeout,
            workers=args.workers,
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

    result["valid"] = bool(result["history_complete"])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
