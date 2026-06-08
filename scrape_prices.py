#!/usr/bin/env python3
"""仙台ホテル価格スクレイパ（JS描画対応 / Playwright）。

WebFetch では取れない、JavaScript で描画される予約サイトの日付別料金を
ヘッドレスChromiumで実際にレンダリングして抽出する。

使い方:
    python3 scrape_prices.py <url> [wait_ms]
レンダリング後の body テキストから、客室名・プラン名・料金(円)を含む行だけ出力する。
"""
import re
import sys
from playwright.sync_api import sync_playwright

KEYWORDS = re.compile(
    r"円|泊|朝食|食事なし|素泊|コーナー|ダブル|ツイン|デラックス|スタンダード|"
    r"スーペリア|プレミア|ユニバーサル|エグゼクティブ|ラージ|エコノミー|合計|"
    r"残\s*\d|空室|予約"
)


def scrape(url: str, wait_ms: int = 6000) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            locale="ja-JP",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 2000},
        )
        page = ctx.new_page()
        page.goto(url, timeout=45000, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        # lazy-load 対策: 下までスクロール
        for _ in range(6):
            page.mouse.wheel(0, 2400)
            page.wait_for_timeout(700)
        page.wait_for_timeout(wait_ms)
        print("TITLE:", page.title())
        print("URL:", page.url)
        print("=" * 70)
        text = page.inner_text("body")
        seen = set()
        for raw in text.splitlines():
            line = raw.strip()
            if not line or len(line) > 120:
                continue
            if KEYWORDS.search(line) and line not in seen:
                seen.add(line)
                print(line)
        browser.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: scrape_prices.py <url> [wait_ms]")
        sys.exit(1)
    scrape(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 6000)
