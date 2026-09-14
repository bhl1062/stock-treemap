# -*- coding: utf-8 -*-
"""
treemap_widget.py
------------------
보유 종목을 트리맵(treemap)으로 그리는 Kivy 위젯.

- 사각형 크기  = 평가금액(현재가 x 수량) 비중
- 사각형 색상  = 매수가 대비 수익률(%)
    * 국내 주식 관례에 맞춰 상승(수익)은 빨강, 하락(손실)은 파랑으로 표시합니다.
- squarified treemap 알고리즘(Bruls, Huizing, van Wijk 1999)을 직접 구현해서
  외부 패키지(squarify 등) 없이도 동작하도록 했습니다. (Android 빌드 단순화 목적)
"""

from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, Line
from kivy.uix.label import Label
from kivy.core.text import Label as CoreLabel


def _layout_row(row, x, y, w, h, horizontal):
    """한 '행(row)'에 속한 아이템들을 실제 좌표 사각형으로 변환."""
    total = sum(item["value"] for item in row)
    rects = []
    if total <= 0:
        return rects
    offset = 0.0
    for item in row:
        frac = item["value"] / total
        if horizontal:
            rw = w
            rh = h * frac
            rects.append((item, x, y + offset, rw, rh))
            offset += rh
        else:
            rw = w * frac
            rh = h
            rects.append((item, x + offset, y, rw, rh))
            offset += rw
    return rects


def _worst_ratio(row, side):
    """한 행의 정사각형에 가까운 정도(작을수록 좋음)."""
    total = sum(item["value"] for item in row)
    if total <= 0 or side <= 0:
        return float("inf")
    max_v = max(item["value"] for item in row)
    min_v = min(item["value"] for item in row)
    side_sq = side * side
    return max(
        (side_sq * max_v) / (total * total),
        (total * total) / (side_sq * min_v) if min_v > 0 else float("inf"),
    )


def squarify(items, x, y, w, h):
    """
    items: [{"value": float, ...다른 키들...}] value 내림차순 정렬 권장.
    반환: [(item, rx, ry, rw, rh), ...]
    """
    items = [i for i in items if i.get("value", 0) > 0]
    if not items or w <= 0 or h <= 0:
        return []
    items = sorted(items, key=lambda i: i["value"], reverse=True)

    # squarify 알고리즘은 값의 합계가 사각형 넓이(w*h)와 같다고 가정합니다.
    # 실제 값(평가금액 등)은 스케일이 다르므로 넓이 기준으로 정규화한
    # 내부용 값을 별도로 만들어 레이아웃 계산에만 사용합니다.
    total_value = sum(i["value"] for i in items)
    scale = (w * h) / total_value if total_value > 0 else 0
    wrapped = [{"value": i["value"] * scale, "orig": i} for i in items]

    result = []
    remaining = wrapped[:]
    cx, cy, cw, ch = x, y, w, h

    while remaining:
        horizontal = cw >= ch
        side = ch if horizontal else cw
        row = [remaining[0]]
        remaining = remaining[1:]

        while remaining:
            test_row = row + [remaining[0]]
            if _worst_ratio(test_row, side) <= _worst_ratio(row, side):
                row = test_row
                remaining = remaining[1:]
            else:
                break

        row_total = sum(i["value"] for i in row)
        if horizontal:
            row_w = row_total / ch if ch > 0 else 0
            rects = _layout_row(row, cx, cy, row_w, ch, horizontal=True)
            result.extend(rects)
            cx += row_w
            cw -= row_w
        else:
            row_h = row_total / cw if cw > 0 else 0
            rects = _layout_row(row, cx, cy, cw, row_h, horizontal=False)
            result.extend(rects)
            cy += row_h
            ch -= row_h

    return [(w["orig"], rx, ry, rw, rh) for (w, rx, ry, rw, rh) in result]


def color_for_return(pct: float):
    """
    수익률(%)에 따른 색상.
    국내 증시 관례: 상승(+)=빨강 계열, 하락(-)=파랑 계열, 0%=회색.
    pct가 커질수록(절대값) 색이 진해지도록 강도를 조절합니다.
    """
    intensity = min(abs(pct) / 10.0, 1.0)  # ±10% 이상이면 최대 채도
    base = 0.35
    if pct > 0.05:
        r = base + intensity * (0.95 - base)
        g = base * (1 - intensity)
        b = base * (1 - intensity)
    elif pct < -0.05:
        r = base * (1 - intensity)
        g = base * (1 - intensity) + intensity * 0.15
        b = base + intensity * (0.95 - base)
    else:
        r = g = b = 0.55
    return (r, g, b, 1)


class TreemapWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data = []  # [{"label":..., "value":..., "pct":..., "sub":...}]
        self.bind(size=self._redraw, pos=self._redraw)

    def set_data(self, items):
        """items: [{'label': str, 'value': float, 'pct': float, 'sub': str}]"""
        self.data = items
        self._redraw()

    def _redraw(self, *args):
        self.canvas.clear()
        if not self.data or self.width <= 0 or self.height <= 0:
            return

        rects = squarify(self.data, self.x, self.y, self.width, self.height)

        with self.canvas:
            for item, rx, ry, rw, rh in rects:
                Color(*color_for_return(item.get("pct", 0.0)))
                Rectangle(pos=(rx, ry), size=(rw, rh))
                Color(0.08, 0.08, 0.08, 1)
                Line(rectangle=(rx, ry, rw, rh), width=1)

                if rw > 40 and rh > 24:
                    self._draw_label(item, rx, ry, rw, rh)

    def _draw_label(self, item, rx, ry, rw, rh):
        label_text = "{}\n{}\n{:+.2f}%".format(
            item.get("label", ""),
            item.get("sub", ""),
            item.get("pct", 0.0),
        )
        font_size = max(11, min(20, int(rw / 8)))
        core_label = CoreLabel(text=label_text, font_size=font_size,
                                halign="center", color=(1, 1, 1, 1))
        core_label.refresh()
        texture = core_label.texture
        tw, th = texture.size
        tw = min(tw, rw - 6)
        th = min(th, rh - 6)
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(
                texture=texture,
                pos=(rx + (rw - tw) / 2, ry + (rh - th) / 2),
                size=(tw, th),
            )
