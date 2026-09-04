#!/usr/bin/env python3
"""
意大利语单词随身背 · 端到端冒烟测试
用法：python tools/smoke_test.py [--url http://localhost:8099/index.html] [--headless]
"""
import argparse
import glob
import os
import sys
import time

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8099/index.html")
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--out", default="_shots")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    results = []
    console_errors = []
    request_failures = []
    mp3_status = {}

    def shot(name):
        path = os.path.join(args.out, f"smoke_{name}.png")
        page.screenshot(path=path)
        return path

    def log(kind, msg, ok=True):
        results.append((kind, msg, ok))
        print(("[PASS] " if ok else "[FAIL] ") + f"{kind}: {msg}")

    # 音频文件完整性预检
    bad = []
    sizes = []
    for d in ("it", "zh"):
        for fp in glob.glob(os.path.join("audio", d, "*.mp3")):
            sz = os.path.getsize(fp)
            sizes.append(sz)
            if sz < 300:
                bad.append((fp, f"too small {sz}"))
                continue
            with open(fp, "rb") as f:
                head = f.read(4)
            ok = head[:3] == b"ID3" or (head[0] == 0xFF and (head[1] & 0xE0) == 0xE0 and head[1] != 0xFF)
            if not ok:
                bad.append((fp, f"bad header {head!r}"))
    sz_min = min(sizes) if sizes else 0
    sz_max = max(sizes) if sizes else 0
    sz_avg = sum(sizes) // len(sizes) if sizes else 0
    log("audio", f"{len(sizes)} mp3, {sz_min / 1024:.1f}/{sz_avg / 1024:.1f}/{sz_max / 1024:.1f} KB, invalid={len(bad)}", ok=not bad)
    for fp, reason in bad[:10]:
        print(f"  BAD {fp}: {reason}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="msedge",
            headless=args.headless,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = browser.new_page(viewport={"width": 1080, "height": 1920})

        page.on("console", lambda m: console_errors.append((m.type, m.text)) if m.type == "error" else None)
        page.on("requestfailed", lambda r: request_failures.append((r.url, str(r.failure))))

        def track_mp3(resp):
            if resp.url.endswith(".mp3"):
                mp3_status[resp.url] = resp.status

        page.on("response", track_mp3)

        # 1. 加载首页并等待内容渲染
        page.goto(args.url, wait_until="networkidle")
        page.wait_for_selector("#content .row", timeout=15000)
        shot("01_home")
        log("load", "首页加载，内容渲染完成")

        # 2. 主题切换
        theme_before = page.evaluate("() => document.documentElement.getAttribute('data-theme') || 'light'")
        page.click("#themeBtn")
        page.wait_for_timeout(300)
        theme_after = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        shot("02_theme")
        log("theme", f"{theme_before} -> {theme_after}", ok=theme_before != theme_after)
        page.click("#themeBtn")  # 切回来
        page.wait_for_timeout(300)

        # 3. 搜索
        page.fill("#search", "lunedì")
        page.wait_for_selector("#searchResults:not(.hidden) .sr-item", timeout=3000)
        sr_count = page.locator("#searchResults .sr-item").count()
        shot("03_search")
        log("search", f"关键词 lunedì，结果项 {sr_count} 条", ok=sr_count > 0)
        page.click("#searchClear")
        page.wait_for_timeout(300)

        # 4. 点读按钮
        mp3_before = set(mp3_status.keys())
        with page.expect_response(lambda r: r.url.endswith(".mp3"), timeout=5000) as resp_info:
            page.locator(".spk").first.click()
        mp3_resp = resp_info.value
        page.wait_for_timeout(200)
        new_mp3 = {u: mp3_status[u] for u in mp3_status if u not in mp3_before}
        statuses = [mp3_resp.status] + [st for st in new_mp3.values()]
        shot("04_spk")
        spk_ok = any(st in (200, 206) for st in statuses)
        log("spk", f"mp3 响应状态 {statuses}，OK {spk_ok}", ok=len(request_failures) == 0 and spk_ok)

        # 5. 全盘播放
        page.click("#playBtn")
        page.wait_for_timeout(1200)
        playing = page.locator("#playBtn.playing").count() > 0
        label = page.text_content("#plLabel") or ""
        player_started = playing or label != "未播放"
        shot("05_player")
        log("player", f"播放器状态: {label}", ok=player_started)
        page.click("#playBtn")  # 暂停
        page.wait_for_timeout(300)

        # 6. 学习模式：闪卡 + 测验
        page.click("#studyBtn")
        page.wait_for_selector("#studyBody .card-face", timeout=10000)
        shot("06_flashcard")
        log("flashcard", "闪卡正面渲染", ok=page.locator("#studyBody .card-face").count() > 0)
        page.click("#sFlip")
        page.wait_for_selector("#studyBody .card-face.back", timeout=5000)
        shot("07_flashcard_back")
        log("flashcard_back", "闪卡背面（中文+拼音）渲染", ok=page.locator("#studyBody .card-face.back").count() > 0)
        page.click('.stab[data-smode="quiz"]')
        page.wait_for_selector("#studyBody .quiz-opts", timeout=10000)
        shot("08_quiz")
        qopts = page.locator("#studyBody .qopt").count()
        log("quiz", f"测验四选一渲染，选项 {qopts} 个", ok=qopts == 4)
        page.click("#studyClose")
        page.wait_for_timeout(300)

        # 7. 标记学完
        done_before = page.text_content("#doneBtn") or ""
        page.click("#doneBtn")
        page.wait_for_timeout(300)
        done_after = page.text_content("#doneBtn") or ""
        ls_done = page.evaluate("() => localStorage.getItem('sv15000_done') || '{}'")
        shot("09_done")
        log("done", f"学完按钮: {done_before} -> {done_after}", ok=done_after == "✓ 已学完")

        browser.close()

    # 汇总
    print("\n=== 冒烟测试汇总 ===")
    ok = sum(1 for _, _, ok in results if ok)
    print(f"通过 {ok}/{len(results)}")
    if console_errors:
        print(f"控制台错误: {len(console_errors)} 条")
        for t, m in console_errors[:10]:
            print(f"  {t}: {m}")
    if request_failures:
        print(f"请求失败: {len(request_failures)} 条")
        for u, e in request_failures[:10]:
            print(f"  {u} -> {e}")
    all_ok = all(ok for _, _, ok in results) and not console_errors and not request_failures
    print("整体:", "PASS" if all_ok else "FAIL")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
