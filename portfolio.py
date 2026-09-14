# -*- coding: utf-8 -*-
"""
portfolio.py
------------
사용자가 입력한 보유 종목(종목코드, 매수단가, 매수수량)을
휴대폰 로컬 저장소(JSON 파일)에 저장/불러오기/수정/삭제하는 모듈.
"""

import json
import os
from typing import List, Dict


def default_storage_path() -> str:
    """
    Android(Kivy App 실행 중)에서는 App.user_data_dir 을,
    데스크톱에서 단독 테스트할 때는 현재 폴더의 holdings.json 을 사용합니다.
    """
    try:
        from kivy.app import App
        app = App.get_running_app()
        if app is not None:
            os.makedirs(app.user_data_dir, exist_ok=True)
            return os.path.join(app.user_data_dir, "holdings.json")
    except Exception:
        pass
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "holdings.json")


class Portfolio:
    def __init__(self, path: str = None):
        self.path = path or default_storage_path()
        self.holdings: List[Dict] = []
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.holdings = json.load(f)
            except Exception:
                self.holdings = []
        else:
            self.holdings = []
        return self.holdings

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.holdings, f, ensure_ascii=False, indent=2)

    def add(self, code: str, name: str, buy_price: float, qty: float):
        self.holdings.append({
            "code": code.strip(),
            "name": (name or code).strip(),
            "buy_price": float(buy_price),
            "qty": float(qty),
        })
        self.save()

    def update(self, index: int, **fields):
        if 0 <= index < len(self.holdings):
            self.holdings[index].update(fields)
            self.save()

    def delete(self, index: int):
        if 0 <= index < len(self.holdings):
            self.holdings.pop(index)
            self.save()

    def total_cost(self, holding: Dict) -> float:
        return holding["buy_price"] * holding["qty"]
