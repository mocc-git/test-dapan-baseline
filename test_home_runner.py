#!/usr/bin/env python3
"""CSQAQ 首页采集测试运行器

测试 scrape_home.py 的 dataZoom 滑动加载功能（23个指数全部滑动加载完整历史）。
记录耗时和每个指数的1day数据条数。
"""
import json
import time
import sys
import os
import importlib.util


def load_module(filepath, module_name):
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    from playwright.sync_api import sync_playwright

    print(f"{'=' * 60}", flush=True)
    print(f"  CSQAQ 首页采集测试 (dataZoom 全指数)", flush=True)
    print(f"  时间: {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"{'=' * 60}", flush=True)

    home_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scrape_home.py")
    if not os.path.exists(home_path):
        print(f"  ✗ scrape_home.py 不存在: {home_path}", flush=True)
        sys.exit(1)

    print(f"\n[加载] scrape_home.py...", flush=True)
    mod = load_module(home_path, "scrape_home")

    index_ids = mod.DEFAULT_INDEX_IDS
    periods = mod.DEFAULT_PERIODS
    kline_periods = mod.DEFAULT_KLINE_PERIODS

    print(f"  指数数量: {len(index_ids)}", flush=True)
    print(f"  sub_data 周期: {periods}", flush=True)
    print(f"  sub_kline 周期: {kline_periods}", flush=True)

    t_start = time.time()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="zh-CN",
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = context.new_page()

        result = mod.scrape_home(page, index_ids, periods, kline_periods)
        browser.close()

    t_end = time.time()
    elapsed = t_end - t_start

    sub_kline = result.get("sub_kline", {})
    index_stats = {}
    total_klines = 0
    for idx_id, info in sub_kline.items():
        periods_data = info.get("periods", {})
        stats = {
            "name": info.get("name", ""),
            "1day": len(periods_data.get("1day", [])),
            "1hour": len(periods_data.get("1hour", [])),
            "7day": len(periods_data.get("7day", [])),
        }
        index_stats[idx_id] = stats
        for cnt in [stats["1day"], stats["1hour"], stats["7day"]]:
            total_klines += cnt

    indices_with_full_history = sum(1 for s in index_stats.values() if s["1day"] >= 200)
    indices_with_data = sum(1 for s in index_stats.values() if s["1day"] > 0)

    steamdt = result.get("steamdt_kline", {})
    steamdt_total = 0
    steamdt_blocks = 0
    for sid, sinfo in steamdt.items():
        if sid != "broad":
            steamdt_blocks += 1
        for pk, pdata in sinfo.get("periods", {}).items():
            steamdt_total += len(pdata)

    test_result = {
        "test_type": "home_datazoom_all",
        "elapsed_seconds": round(elapsed, 1),
        "elapsed_str": f"{int(elapsed // 60)}m{elapsed % 60:.0f}s",
        "scrape_ok": result.get("scrape_ok", False),
        "scrape_fail": result.get("scrape_fail", ""),
        "index_count": len(sub_kline),
        "indices_with_data": indices_with_data,
        "indices_with_full_history": indices_with_full_history,
        "total_klines": total_klines,
        "steamdt_blocks": steamdt_blocks,
        "steamdt_total_klines": steamdt_total,
        "index_stats": index_stats,
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
    }

    print(f"\n{'=' * 60}", flush=True)
    print(f"  测试结果", flush=True)
    print(f"{'=' * 60}", flush=True)
    print(f"  耗时: {test_result['elapsed_str']} ({elapsed:.1f}s)", flush=True)
    print(f"  采集状态: {'✓ 成功' if test_result['scrape_ok'] else '✗ 失败'}", flush=True)
    print(f"  CSQAQ 指数数量: {test_result['index_count']}", flush=True)
    print(f"  CSQAQ 有数据指数: {indices_with_data}/{test_result['index_count']}", flush=True)
    print(f"  CSQAQ 1day完整历史(≥200条): {indices_with_full_history}/{test_result['index_count']}", flush=True)
    print(f"  CSQAQ 总K线条数: {total_klines}", flush=True)
    print(f"  SteamDT 板块数: {steamdt_blocks}", flush=True)
    print(f"  SteamDT 总K线条数: {steamdt_total}", flush=True)

    print(f"\n  各指数1day数据条数:", flush=True)
    for idx_id, stats in sorted(index_stats.items(), key=lambda x: int(x[0]) if str(x[0]).isdigit() else 999):
        marker = "✓" if stats["1day"] >= 200 else ("⚠" if stats["1day"] > 0 else "✗")
        print(f"    {marker} {stats['name']}({idx_id}): 1day={stats['1day']}, 1hour={stats['1hour']}, 7day={stats['7day']}", flush=True)

    result_file = "home_test_result.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(test_result, f, ensure_ascii=False, indent=2)
    print(f"\n  结果已保存: {result_file}", flush=True)

    with open("home_raw_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return test_result


if __name__ == "__main__":
    main()
