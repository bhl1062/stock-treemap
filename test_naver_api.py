# -*- coding: utf-8 -*-
"""
test_naver_api.py
------------------
naver_api.py 가 실제로 동작하는지 커맨드라인에서 빠르게 확인하는 스크립트.
(이 개발 환경(샌드박스)에서는 보안 정책상 finance.naver.com 접속이 막혀 있어
 직접 테스트하지 못했습니다. 본인 PC나 휴대폰 환경에서 아래처럼 실행해서
 정상적으로 값이 나오는지 꼭 확인해 보세요.)

사용법:
    python test_naver_api.py 005930 000660
"""
import sys
from naver_api import fetch_quote

def main():
    codes = sys.argv[1:] or ["005930"]  # 기본값: 삼성전자
    for code in codes:
        try:
            q = fetch_quote(code)
            print(f"[{q.code}] {q.name}: {q.price:,.0f}원  "
                  f"(전일대비 {q.change:+,.0f}, {q.change_rate:+.2f}%)")
        except Exception as e:
            print(f"[{code}] 조회 실패: {e}")

if __name__ == "__main__":
    main()
