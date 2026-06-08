#!/usr/bin/env python3
"""一休.com / Yahoo!トラベル（同一Nuxt+SSR基盤）の日付別・客室別価格スクレイパ。

価格はSSRでHTMLに入るが、(1)日付はURLの cid(YYYYMMDD)/lc(泊数)/ppc(人数)/rc(室数) で指定、
(2)既定はカジュアル数室＋他ホテル推薦のみ表示なので「部屋をすべてみる」を展開、
(3)朝食付フィルタを当てると各室の朝食付き最安が表示される。

使い方: python3 scrape_ota.py <base> <id1,id2,...>
  base: ikyu  → https://www.ikyu.com
        yahoo → https://travel.yahoo.co.jp
"""
import re
import sys
from playwright.sync_api import sync_playwright

BASES = {"ikyu": "https://www.ikyu.com", "yahoo": "https://travel.yahoo.co.jp"}
base = BASES[sys.argv[1]]
ids = sys.argv[2].split(",")
CID, LC, PPC, RC = "20260712", "2", "2", "1"
ROOM_HINT = re.compile(r"【禁煙】|【喫煙】|コーナー|デラックス|スーペリア|プレミア|ユニバーサル|"
                       r"エグゼクティブ|ラージ|ラグジュアリー|エコノミー|スタンダード|カジュアル|"
                       r"モデレート|コンセプト|グランド|ツイン|ダブル|キング|クイーン|スイート")
PRICE_LINE = re.compile(r"(朝食付|食事なし|夕朝食付|2食付).*?税込[\d,]+円|残りあと\d+室|プランをすべて|部屋をすべて")


def scrape(pg, hid):
    url = f"{base}/{hid}/?cid={CID}&lc={LC}&ppc={PPC}&rc={RC}&si=1&st=1&top=rooms"
    pg.goto(url, wait_until="domcontentloaded", timeout=50000)
    try:
        pg.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    pg.wait_for_timeout(2500)
    # 朝食付フィルタを当てる（あれば）
    for label in ("朝食付", "朝食あり"):
        try:
            loc = pg.get_by_text(label, exact=True)
            if loc.count():
                loc.first.click(timeout=3000)
                pg.wait_for_timeout(2000)
                break
        except Exception:
            pass
    # 全部屋展開
    for _ in range(4):
        try:
            loc = pg.get_by_text(re.compile("部屋をすべてみる"))
            if loc.count() == 0:
                break
            loc.first.scroll_into_view_if_needed(timeout=3000)
            loc.first.click(timeout=3000)
            pg.wait_for_timeout(1800)
        except Exception:
            break
    for _ in range(8):
        pg.mouse.wheel(0, 2200)
        pg.wait_for_timeout(500)
    pg.wait_for_timeout(1500)
    txt = pg.inner_text("body")
    cut = txt.find("この宿に泊まった人")
    if cut > 0:
        txt = txt[:cut]
    hdr = ""
    m = re.search(r"7月1[0-9]日.*?泊", txt)
    if m:
        hdr = m.group(0)
    print(f"\n===== {base}/{hid}  ({hdr}) =====")
    for ln in txt.splitlines():
        ln = ln.strip()
        if not ln or len(ln) > 120:
            continue
        if ("税込" in ln and "円" in ln) or "【禁煙】" in ln or "【喫煙】" in ln or "残りあと" in ln or "すべてみる" in ln:
            if ROOM_HINT.search(ln) or "税込" in ln or "残りあと" in ln or "すべて" in ln:
                print(ln)


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(locale="ja-JP",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        viewport={"width": 1366, "height": 2600})
    pg = ctx.new_page()
    for hid in ids:
        try:
            scrape(pg, hid)
        except Exception as e:
            print(f"\n===== {hid} ERROR: {str(e)[:100]}")
    b.close()
