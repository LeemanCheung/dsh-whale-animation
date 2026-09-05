"""Measure the shipped raster loops in Chrome without changing a DSH profile."""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / ".artifacts"
URL = (ROOT / "scripts/browser-smoke.html").as_uri()
ARTIFACTS.mkdir(exist_ok=True)

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel="chrome", headless=True)
    errors: list[str] = []
    page = browser.new_page(viewport={"width": 1000, "height": 700})
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.add_init_script("""
      window.playbackEvents = [];
      new MutationObserver(records => {
        for (const record of records) {
          if (record.attributeName !== 'data-dsh-whale-state') continue;
          if (record.target !== document.querySelector('[role="status"]')) continue;
          const state = record.target.dataset.dshWhaleState;
          if (window.playbackEvents.at(-1)?.state !== state)
            window.playbackEvents.push({state, at: performance.now()});
        }
      }).observe(document, {subtree: true, attributes: true, attributeFilter: ['data-dsh-whale-state']});
    """)
    page.goto(URL, wait_until="networkidle")
    statuses = page.locator('[role="status"]')
    assert statuses.count() == 2
    # Ask to switch while Dive is playing. The current cycle must finish first.
    statuses.first.evaluate("node => { node.textContent = 'Classic whale animation...'; }")
    assert statuses.first.get_attribute("data-dsh-whale-state") == "dive"
    page.wait_for_function("window.playbackEvents.length >= 2", timeout=5000)
    # Return to the automatic two-state playlist for the end of Classic.
    statuses.first.evaluate("node => { node.textContent = 'Deep diving...'; }")
    page.screenshot(path=str(ARTIFACTS / "playback-light.png"), full_page=True)
    page.wait_for_function("window.playbackEvents.length >= 3", timeout=14000)
    timeline = page.evaluate("window.playbackEvents.slice(0, 3)")
    assert [event["state"] for event in timeline] == ["dive", "classic", "dive"], timeline
    durations = [timeline[i + 1]["at"] - timeline[i]["at"] for i in range(2)]
    for measured, expected in zip(durations, [1980, 10506]):
        assert abs(measured - expected) < 150, (measured, expected)

    page.evaluate("document.documentElement.dataset.theme = 'dark'")
    assert statuses.first.evaluate("node => getComputedStyle(node, '::after').filter") == "invert(1)"
    page.screenshot(path=str(ARTIFACTS / "playback-dark.png"), full_page=True)
    page.emulate_media(color_scheme="dark")
    page.evaluate("document.documentElement.dataset.theme = 'light'")
    assert statuses.first.evaluate("node => getComputedStyle(node, '::after').filter") == "none"
    page.evaluate("document.documentElement.dataset.theme = 'dark'")
    page.set_viewport_size({"width": 390, "height": 844})
    assert statuses.first.evaluate("node => getComputedStyle(node, '::after').width") == "60px"
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.screenshot(path=str(ARTIFACTS / "playback-mobile.png"), full_page=True)
    page.emulate_media(reduced_motion="reduce")
    page.wait_for_timeout(50)
    assert statuses.first.evaluate("node => getComputedStyle(node, '::after').backgroundImage.startsWith('url(\"data:image/png;')")
    before = len(page.evaluate("window.playbackEvents"))
    page.wait_for_timeout(2200)
    assert len(page.evaluate("window.playbackEvents")) == before
    assert page.locator("svg").count() == 0
    page.evaluate("window.__disposeWhale()")
    assert page.locator('[data-dsh-whale-host="true"]').count() == 0
    assert page.locator('style[data-plugin="dsh-whale-animation"]').count() == 0
    assert not errors, errors
    browser.close()

result = {
    "ok": True,
    "states": ["dive", "classic"],
    "timeline": timeline,
    "measuredStateDurationMs": durations,
    "expectedStateDurationMs": [1980, 10506],
    "statusSwitchDeferred": True,
    "darkTheme": True,
    "explicitLightThemeOnDarkOs": True,
    "mobileWidth": 390,
    "reducedMotionPng": True,
    "svgCount": 0,
    "pageErrors": errors,
}
(ARTIFACTS / "playback-report.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result))
