#!/usr/bin/env python3
"""探索用: ページをレンダリングしつつ、価格を含むJSON/XHR応答もキャプチャする。

使い方: python3 explore.py <url> [wait_ms]
出力: 最終URL/タイトル、価格を含むJSON応答のURL一覧、本文テキスト先頭、
      キャプチャしたJSONは /tmp/captured.json に保存。
"""
import json
import sys
from playwright.sync_api import sync_playwright

URL = sys.argv[1]
WAIT = int(sys.argv[2]) if len(sys.argv) > 2 else 9000
PRICE_HINT = ("price", "Price", "料金", "金額", "amount", "Amount", "total",
              "plan", "Plan", "rate", "Rate", "円", "tax", "stay")
captured = []


def on_response(resp):
    try:
        ct = resp.headers.get("content-type", "")
        if "json" not in ct and "javascript" not in ct:
            return
        u = resp.url
        body = resp.text()
        if len(body) > 8 and any(k in body for k in PRICE_HINT):
            captured.append({"url": u, "ct": ct, "len": len(body), "body": body})
    except Exception:
        pass


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(
        locale="ja-JP",
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
        viewport={"width": 1280, "height": 2200},
    )
    pg = ctx.new_page()
    pg.on("response", on_response)
    pg.goto(URL, timeout=50000, wait_until="domcontentloaded")
    try:
        pg.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    for _ in range(8):
        pg.mouse.wheel(0, 3000)
        pg.wait_for_timeout(700)
    pg.wait_for_timeout(WAIT)
    print("FINAL_URL:", pg.url)
    print("TITLE:", pg.title())
    print("=== CAPTURED price-ish JSON/JS responses:", len(captured))
    for c in captured:
        print(f"  [{c['len']:>7}] {c['url'][:150]}")
    print("=== BODY TEXT (first 5000 chars) ===")
    print(pg.inner_text("body")[:5000])
    b.close()

with open("/tmp/captured.json", "w") as f:
    json.dump(captured, f, ensure_ascii=False)
print("=== saved", len(captured), "responses to /tmp/captured.json")
