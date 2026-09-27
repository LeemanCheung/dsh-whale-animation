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
    regression_page = browser.new_page()
    regression_page.on("pageerror", lambda error: errors.append(str(error)))
    regression_page.goto(URL, wait_until="networkidle")
    unrelated_status = regression_page.evaluate("""async () => {
      const [independent, previous] = document.querySelectorAll('[role="status"]');
      const previousParent = previous.parentElement;
      const oldState = previous.dataset.dshWhaleState;
      const oldImage = previous.style.getPropertyValue('--dsh-whale-current-image');
      const nextParent = document.createElement('article');
      const next = document.createElement('div');
      next.className = 'regression_turnStatus';
      next.setAttribute('role', 'status');
      next.textContent = 'Deep diving...';
      nextParent.appendChild(next);
      window.unrelatedStatusEvents = [];
      new MutationObserver(() => {
        const state = next.dataset.dshWhaleState;
        if (window.unrelatedStatusEvents.at(-1)?.state !== state)
          window.unrelatedStatusEvents.push({state, at: performance.now()});
      }).observe(next, {attributes: true, attributeFilter: ['data-dsh-whale-state']});
      const batches = [];
      const recorder = new MutationObserver(records => batches.push(records));
      recorder.observe(document.documentElement, {childList: true, subtree: true});
      previous.remove();
      independent.parentElement.appendChild(nextParent);
      await new Promise(resolve => queueMicrotask(() => queueMicrotask(resolve)));
      recorder.disconnect();
      const records = batches.flat();
      return {
        oldState,
        newState: next.dataset.dshWhaleState,
        freshImage: next.style.getPropertyValue('--dsh-whale-current-image') !== oldImage,
        singleObserverBatch: batches.length === 1,
        differentContainers: previousParent !== next.parentElement,
        separateRemovalAndInsertion: records.some(record => record.target === previousParent && record.removedNodes[0] === previous && record.addedNodes.length === 0)
          && records.some(record => record.target === independent.parentElement && record.addedNodes[0] === nextParent && record.removedNodes.length === 0),
      };
    }""")
    assert unrelated_status["oldState"] == "classic", unrelated_status
    assert unrelated_status["newState"] == "dive", unrelated_status
    assert all(unrelated_status[key] for key in ["freshImage", "singleObserverBatch", "differentContainers", "separateRemovalAndInsertion"]), unrelated_status
    regression_page.wait_for_function("window.unrelatedStatusEvents.length >= 2", timeout=5000)
    unrelated_timeline = regression_page.evaluate("window.unrelatedStatusEvents.slice(0, 2)")
    assert [event["state"] for event in unrelated_timeline] == ["dive", "classic"], unrelated_timeline
    unrelated_duration = unrelated_timeline[1]["at"] - unrelated_timeline[0]["at"]
    assert abs(unrelated_duration - 1980) < 150, unrelated_duration
    regression_page.close()
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
    def replace_status(*, subtree: bool = False) -> None:
        continuity = statuses.first.evaluate("""async (node, subtree) => {
          const image = node.style.getPropertyValue('--dsh-whale-current-image');
          const state = node.dataset.dshWhaleState;
          const independent = document.querySelectorAll('[role="status"]')[1];
          const independentImage = independent.style.getPropertyValue('--dsh-whale-current-image');
          const previous = subtree ? node.parentElement : node;
          const replacement = previous.cloneNode(true);
          const status = subtree ? replacement.querySelector('[role="status"]') : replacement;
          status.removeAttribute('data-dsh-whale-host');
          status.removeAttribute('data-dsh-whale-state');
          status.style.removeProperty('--dsh-whale-current-image');
          previous.replaceWith(replacement);
          // Allow MutationObserver and its queued scan to finish, without
          // crossing a timer deadline between separate browser round trips.
          await new Promise(resolve => queueMicrotask(() => queueMicrotask(resolve)));
          return {
            imagePreserved: status.style.getPropertyValue('--dsh-whale-current-image') === image,
            statePreserved: status.dataset.dshWhaleState === state,
            independentUnchanged: independent.style.getPropertyValue('--dsh-whale-current-image') === independentImage,
          };
        }""", subtree)
        assert all(continuity.values()), continuity

    for _ in range(3):
        page.wait_for_timeout(250)
        replace_status()
    page.wait_for_function("window.playbackEvents.length >= 2", timeout=5000)
    # Return to the automatic two-state playlist for the end of Classic.
    statuses.first.evaluate("node => { node.textContent = 'Deep diving...'; }")
    page.screenshot(path=str(ARTIFACTS / "playback-light.png"), full_page=True)
    replace_status(subtree=True)
    assert statuses.first.get_attribute("data-dsh-whale-state") == "classic"
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
    "statusReplacementPreservesLoop": True,
    "subtreeReplacementPreservesLoop": True,
    "independentStatusUnchanged": True,
    "unrelatedStatus": unrelated_status,
    "unrelatedStatusFirstLoopMs": unrelated_duration,
    "darkTheme": True,
    "explicitLightThemeOnDarkOs": True,
    "mobileWidth": 390,
    "reducedMotionPng": True,
    "svgCount": 0,
    "pageErrors": errors,
}
(ARTIFACTS / "playback-report.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result))
