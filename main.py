# -*- coding: utf-8 -*-
"""
main.py
-------
안드로이드용 "내 주식 포트폴리오 트리맵" 앱 (Kivy)

기능
- 화면1(보유종목): 종목코드/매수단가/매수수량을 입력해서 보유 종목을 등록·삭제
- 화면2(트리맵): 네이버 금융에서 실시간(요청 시점 기준) 시세를 가져와
  평가금액 비중 = 사각형 크기, 매수가 대비 수익률 = 색상(빨강=수익, 파랑=손실)
  으로 트리맵을 그림. 새로고침 / 자동새로고침(30초) 지원.

실행(데스크톱 테스트): python main.py
안드로이드 APK 빌드: README.md 참고 (buildozer 사용)
"""

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.label import Label

import naver_api
from portfolio import Portfolio
from treemap_widget import TreemapWidget

AUTO_REFRESH_SECONDS = 30


class HoldingRow(BoxLayout):
    def __init__(self, index, holding, on_delete, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, height=44,
                          spacing=6, **kwargs)
        text = "{code}  |  매수단가 {buy:,.0f}  |  수량 {qty:g}".format(
            code=holding["code"], buy=holding["buy_price"], qty=holding["qty"]
        )
        self.add_widget(Label(text=text, halign="left", valign="middle"))
        del_btn = Button(text="삭제", size_hint_x=None, width=70)
        del_btn.bind(on_release=lambda *_: on_delete(index))
        self.add_widget(del_btn)


class HoldingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=10, spacing=8)

        root.add_widget(Label(text="[b]보유 종목 관리[/b]", markup=True,
                               size_hint_y=None, height=30))
        root.add_widget(Label(
            text="종목코드는 네이버 금융 6자리 코드입니다 (예: 삼성전자 005930)",
            size_hint_y=None, height=24, font_size=12, color=(0.6, 0.6, 0.6, 1)))

        form = BoxLayout(orientation="horizontal", size_hint_y=None, height=44, spacing=6)
        self.code_input = TextInput(hint_text="종목코드(예:005930)", multiline=False)
        self.price_input = TextInput(hint_text="매수단가", multiline=False,
                                      input_filter="float")
        self.qty_input = TextInput(hint_text="매수수량", multiline=False,
                                    input_filter="float")
        add_btn = Button(text="추가", size_hint_x=None, width=70)
        add_btn.bind(on_release=self.add_holding)
        form.add_widget(self.code_input)
        form.add_widget(self.price_input)
        form.add_widget(self.qty_input)
        form.add_widget(add_btn)
        root.add_widget(form)

        self.status_label = Label(text="", size_hint_y=None, height=20,
                                   font_size=12, color=(0.8, 0.2, 0.2, 1))
        root.add_widget(self.status_label)

        self.list_grid = GridLayout(cols=1, size_hint_y=None, spacing=4)
        self.list_grid.bind(minimum_height=self.list_grid.setter("height"))
        scroll = ScrollView()
        scroll.add_widget(self.list_grid)
        root.add_widget(scroll)

        goto_btn = Button(text="트리맵 보기 ▶", size_hint_y=None, height=48)
        goto_btn.bind(on_release=self.goto_treemap)
        root.add_widget(goto_btn)

        self.add_widget(root)

    def on_pre_enter(self):
        self.refresh_list()

    def refresh_list(self):
        app = App.get_running_app()
        self.list_grid.clear_widgets()
        for i, h in enumerate(app.portfolio.holdings):
            self.list_grid.add_widget(
                HoldingRow(i, h, on_delete=self.delete_holding)
            )

    def add_holding(self, *_):
        app = App.get_running_app()
        code = self.code_input.text.strip()
        price_text = self.price_input.text.strip()
        qty_text = self.qty_input.text.strip()
        if not code or not price_text or not qty_text:
            self.status_label.text = "종목코드/매수단가/매수수량을 모두 입력하세요."
            return
        try:
            buy_price = float(price_text)
            qty = float(qty_text)
        except ValueError:
            self.status_label.text = "매수단가/매수수량은 숫자로 입력하세요."
            return
        app.portfolio.add(code=code, name=code, buy_price=buy_price, qty=qty)
        self.code_input.text = ""
        self.price_input.text = ""
        self.qty_input.text = ""
        self.status_label.text = ""
        self.refresh_list()

    def delete_holding(self, index):
        App.get_running_app().portfolio.delete(index)
        self.refresh_list()

    def goto_treemap(self, *_):
        self.manager.current = "treemap"


class TreemapScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=6, spacing=6)

        top_bar = BoxLayout(orientation="horizontal", size_hint_y=None, height=44, spacing=6)
        back_btn = Button(text="◀ 종목관리", size_hint_x=None, width=100)
        back_btn.bind(on_release=lambda *_: setattr(self.manager, "current", "holdings"))
        refresh_btn = Button(text="새로고침", size_hint_x=None, width=90)
        refresh_btn.bind(on_release=lambda *_: App.get_running_app().refresh_prices())
        self.auto_btn = ToggleButton(text="자동새로고침 OFF", size_hint_x=None, width=140)
        self.auto_btn.bind(on_release=self.toggle_auto)
        top_bar.add_widget(back_btn)
        top_bar.add_widget(refresh_btn)
        top_bar.add_widget(self.auto_btn)
        root.add_widget(top_bar)

        self.summary_label = Label(text="", size_hint_y=None, height=50, font_size=15)
        root.add_widget(self.summary_label)

        self.treemap = TreemapWidget()
        root.add_widget(self.treemap)

        self.add_widget(root)

    def on_enter(self):
        App.get_running_app().refresh_prices()

    def toggle_auto(self, *_):
        App.get_running_app().toggle_auto_refresh(self.auto_btn.state == "down")
        self.auto_btn.text = "자동새로고침 ON" if self.auto_btn.state == "down" else "자동새로고침 OFF"

    def update_totals(self, total_value, total_cost):
        pnl = total_value - total_cost
        pnl_pct = (pnl / total_cost * 100) if total_cost else 0.0
        sign = "+" if pnl >= 0 else ""
        self.summary_label.text = (
            "평가금액 {tv:,.0f}원   |   매수금액 {tc:,.0f}원   |   "
            "평가손익 {sign}{pnl:,.0f}원 ({sign}{pct:.2f}%)"
        ).format(tv=total_value, tc=total_cost, sign=sign, pnl=pnl, pct=pnl_pct)


class StockTreemapApp(App):
    title = "내 주식 트리맵"

    def build(self):
        self.portfolio = Portfolio()
        self.quotes = {}
        self._auto_event = None

        sm = ScreenManager()
        self.holdings_screen = HoldingsScreen(name="holdings")
        self.treemap_screen = TreemapScreen(name="treemap")
        sm.add_widget(self.holdings_screen)
        sm.add_widget(self.treemap_screen)
        return sm

    def refresh_prices(self):
        codes = [h["code"] for h in self.portfolio.holdings]
        if not codes:
            self.treemap_screen.treemap.set_data([])
            self.treemap_screen.update_totals(0, 0)
            return
        naver_api.fetch_quotes_async(
            codes, on_result=self._on_quote_result, on_error=self._on_quote_error
        )

    def _on_quote_result(self, code, quote):
        Clock.schedule_once(lambda dt: self._apply_quote(code, quote))

    def _on_quote_error(self, code, err):
        print("[naver_api] {} 조회 실패: {}".format(code, err))

    def _apply_quote(self, code, quote):
        self.quotes[code] = quote
        self._rebuild_treemap()

    def _rebuild_treemap(self):
        items = []
        total_value = 0.0
        total_cost = 0.0
        for h in self.portfolio.holdings:
            code = h["code"]
            qty = h["qty"]
            buy_price = h["buy_price"]
            q = self.quotes.get(code)
            current_price = q.price if q else buy_price
            value = current_price * qty
            cost = buy_price * qty
            pct = ((current_price - buy_price) / buy_price * 100) if buy_price else 0.0
            label = q.name if q else h.get("name", code)
            items.append({
                "label": label,
                "value": value,
                "pct": pct,
                "sub": "{:,.0f}원".format(current_price),
            })
            total_value += value
            total_cost += cost
        self.treemap_screen.treemap.set_data(items)
        self.treemap_screen.update_totals(total_value, total_cost)

    def toggle_auto_refresh(self, active):
        if active:
            if self._auto_event is None:
                self._auto_event = Clock.schedule_interval(
                    lambda dt: self.refresh_prices(), AUTO_REFRESH_SECONDS
                )
        else:
            if self._auto_event is not None:
                self._auto_event.cancel()
                self._auto_event = None


if __name__ == "__main__":
    StockTreemapApp().run()
