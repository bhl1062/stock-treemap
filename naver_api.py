# -*- coding: utf-8 -*-
"""
naver_api.py
------------
네이버 금융(finance.naver.com)에서 국내 주식의 실시간(에 가까운) 시세를
가져오는 모듈입니다. 공식 API가 아니라 공개된 웹페이지를 파싱(스크래핑)하는
방식이므로, 네이버 페이지 구조가 바뀌면 동작하지 않을 수 있습니다.
그런 경우 아래 셀렉터(CSS class 이름)만 최신 구조에 맞게 고치면 됩니다.

동작 방식
1) 1차: https://finance.naver.com/item/main.naver?code=<종목코드> 페이지를
   BeautifulSoup으로 파싱해서 현재가/전일대비/등락률을 추출합니다.
2) 2차(백업): 1차가 실패하면 네이버의 일별시세 JSON(api.finance.naver.com)에서
   가장 최근 종가를 가져옵니다. (실시간은 아니고 "가장 최근 확정 종가"입니다.)
"""

import re
import time
import threading
from dataclasses import dataclass
from typing import Optional

import requests
from bs4 import BeautifulSoup

HEADERS = {
    # 네이버가 브라우저가 아닌 요청을 차단하는 경우가 있어 User-Agent를 지정합니다.
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

MAIN_URL = "https://finance.naver.com/item/main.naver?code={code}"
DAILY_JSON_URL = (
    "https://api.finance.naver.com/siseJson.naver"
    "?symbol={code}&requestType=1&startTime={start}&endTime={end}&timeframe=day"
)


class NaverFetchError(Exception):
    """시세 조회에 실패했을 때 발생시키는 예외."""


@dataclass
class Quote:
    code: str
    name: str
    price: float
    change: float          # 전일 대비 변동폭 (원). 상승이면 +, 하락이면 -
    change_rate: float     # 전일 대비 등락률 (%). 상승이면 +, 하락이면 -
    is_up: Optional[bool]  # True=상승(빨강), False=하락(파랑), None=보합


def _to_number(text: str) -> float:
    """'71,400' 같은 문자열을 71400.0 으로 변환."""
    if text is None:
        raise NaverFetchError("빈 값에서 숫자를 추출할 수 없습니다.")
    cleaned = re.sub(r"[^0-9.\-]", "", text)
    if cleaned in ("", "-", "."):
        raise NaverFetchError(f"숫자로 변환할 수 없는 값입니다: {text!r}")
    return float(cleaned)


def _fetch_from_main_page(code: str) -> Quote:
    url = MAIN_URL.format(code=code)
    resp = requests.get(url, headers=HEADERS, timeout=6)
    resp.raise_for_status()
    # 네이버 금융 구버전 페이지는 EUC-KR 인코딩을 사용합니다.
    resp.encoding = "euc-kr"
    soup = BeautifulSoup(resp.text, "html.parser")

    name_tag = soup.select_one("div.wrap_company h2 a")
    name = name_tag.get_text(strip=True) if name_tag else code

    price_tag = soup.select_one("p.no_today span.blind")
    if price_tag is None:
        raise NaverFetchError("현재가 요소를 찾지 못했습니다(no_today).")
    price = _to_number(price_tag.get_text())

    # 상승/하락/보합 판별 (em 태그의 class: no_up / no_down / no_same)
    is_up = None
    em_today = soup.select_one("p.no_today em")
    if em_today is not None:
        classes = em_today.get("class") or []
        if "no_up" in classes:
            is_up = True
        elif "no_down" in classes:
            is_up = False
        elif "no_same" in classes:
            is_up = None

    change = 0.0
    change_rate = 0.0
    exday_blinds = soup.select("p.no_exday span.blind")
    # 보통 [전일대비 금액, 등락률(%)] 순서로 두 개가 옵니다.
    if len(exday_blinds) >= 1:
        try:
            change = _to_number(exday_blinds[0].get_text())
        except NaverFetchError:
            change = 0.0
    if len(exday_blinds) >= 2:
        try:
            change_rate = _to_number(exday_blinds[1].get_text())
        except NaverFetchError:
            change_rate = 0.0

    if is_up is False:
        change = -abs(change)
        change_rate = -abs(change_rate)
    elif is_up is True:
        change = abs(change)
        change_rate = abs(change_rate)

    return Quote(code=code, name=name, price=price, change=change,
                 change_rate=change_rate, is_up=is_up)


def _fetch_from_daily_json(code: str) -> Quote:
    """1차 방식이 실패했을 때 쓰는 백업: 최근 종가만 가져옵니다(실시간 아님)."""
    today = time.strftime("%Y%m%d")
    start = time.strftime("%Y%m%d", time.localtime(time.time() - 14 * 86400))
    url = DAILY_JSON_URL.format(code=code, start=start, end=today)
    resp = requests.get(url, headers=HEADERS, timeout=6)
    resp.raise_for_status()
    text = resp.text.strip()
    # 응답이 JS 배열 리터럴 형태이므로 숫자만 뽑아 최근 두 개의 종가를 비교합니다.
    rows = re.findall(r"\[(.*?)\]", text)
    closes = []
    for row in rows[1:]:  # 첫 번째는 헤더
        cols = [c.strip(' "') for c in row.split(",")]
        if len(cols) >= 5:
            try:
                closes.append(float(cols[4]))
            except ValueError:
                continue
    if not closes:
        raise NaverFetchError(f"{code}: 백업 API에서도 데이터를 가져오지 못했습니다.")
    price = closes[-1]
    change = price - closes[-2] if len(closes) >= 2 else 0.0
    change_rate = (change / closes[-2] * 100) if len(closes) >= 2 and closes[-2] else 0.0
    is_up = True if change > 0 else (False if change < 0 else None)
    return Quote(code=code, name=code, price=price, change=change,
                 change_rate=change_rate, is_up=is_up)


def fetch_quote(code: str) -> Quote:
    """종목코드(6자리, 예: '005930')로 현재가 정보를 가져옵니다."""
    code = code.strip()
    try:
        return _fetch_from_main_page(code)
    except Exception:
        return _fetch_from_daily_json(code)


def fetch_quotes_async(codes, on_result, on_error=None, max_workers=6):
    """
    여러 종목을 백그라운드 스레드로 동시에 조회합니다.
    on_result(code, Quote) 는 각 종목 조회가 끝날 때마다 호출됩니다.
    (Kivy 앱에서는 on_result 안에서 Clock.schedule_once로 UI 갱신을 예약하세요.)
    """
    def worker(c):
        try:
            q = fetch_quote(c)
            on_result(c, q)
        except Exception as e:
            if on_error:
                on_error(c, e)

    threads = []
    for c in codes:
        t = threading.Thread(target=worker, args=(c,), daemon=True)
        t.start()
        threads.append(t)
    return threads
