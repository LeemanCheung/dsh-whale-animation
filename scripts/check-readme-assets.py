from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from urllib.parse import unquote

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
DOCS = ROOT / "docs"
EXPECTED_STATES = ("dive", "classic", "spout", "sonar", "work", "compose", "idle", "alert")
EXPECTED_PLAYLIST = ["dive", "classic", "spout", "sonar", "work", "compose", "idle"]
EXPECTED_DERIVED_FROM = {
    "work": ["whale-dive.webp"],
    "compose": ["whale-classic.webp"],
    "idle": ["whale-dive.webp"],
    "alert": ["whale-classic.webp"],
}
LEGACY_GIT_BLOBS = {
    "dive": {
        "animated": "5c2891f6aa8a8c318a987951138178195898076e",
        "static": "a04f807b546b2ec4f4310764c2bd7c0fa29bcd56",
        "canvas": (352, 352),
    },
    "classic": {
        "animated": "bf3d4efc4a0e38f285226722d9cf2f431b095a45",
        "static": "0a697352a92f25fb8c1794e485be7fa44efe0e78",
        "canvas": (184, 184),
    },
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    digest = hashlib.sha1()
    digest.update(f"blob {len(data)}\0".encode())
    digest.update(data)
    return digest.hexdigest()


def webp_durations(path: Path) -> list[int]:
    data = path.read_bytes()
    require(data[:4] == b"RIFF" and data[8:12] == b"WEBP", f"Invalid RIFF WebP: {path.relative_to(ROOT)}")
    durations: list[int] = []
    offset = 12
    while offset + 8 <= len(data):
        kind = data[offset:offset + 4]
        size = int.from_bytes(data[offset + 4:offset + 8], "little")
        payload = offset + 8
        if kind == b"ANMF":
            require(payload + 15 <= len(data), f"Truncated ANMF chunk: {path.relative_to(ROOT)}")
            durations.append(int.from_bytes(data[payload + 12:payload + 15], "little"))
        offset = payload + size + (size & 1)
    return durations


def image_profile(path: Path) -> tuple[tuple[int, int], int, list[int]]:
    require(path.is_file(), f"Missing image: {path.relative_to(ROOT)}")
    image = Image.open(path)
    frame_count = int(getattr(image, "n_frames", 1))
    durations = webp_durations(path) if path.suffix.lower() == ".webp" and frame_count > 1 else []
    return image.size, frame_count, durations


def rgba_frames(path: Path) -> list[bytes]:
    image = Image.open(path)
    frames: list[bytes] = []
    for index in range(int(getattr(image, "n_frames", 1))):
        image.seek(index)
        frames.append(image.convert("RGBA").tobytes())
    return frames


def local_references(markdown: str) -> set[str]:
    refs: set[str] = set()
    patterns = (
        r"!\[[^\]]*\]\(([^)\s]+)(?:\s+['\"][^'\"]*['\"])?\)",
        r"(?<!!)\[[^\]]+\]\(([^)\s]+)(?:\s+['\"][^'\"]*['\"])?\)",
        r"<(?:img|a)\b[^>]+(?:src|href)=[\"']([^\"']+)[\"']",
    )
    for pattern in patterns:
        refs.update(re.findall(pattern, markdown, flags=re.IGNORECASE))
    return refs


def validate_readme(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    require(text.count("```mermaid") == 1, f"{path.name} must contain exactly one Mermaid diagram")
    require("v0.6.0" in text, f"{path.name} does not document v0.6.0")
    require("spout" in text.lower() or "喷水" in text, f"{path.name} does not document the spout state")
    require("docs/preview.webp" in text, f"{path.name} does not reference the animated preview")
    require("docs/state-gallery.png" in text, f"{path.name} does not reference the state gallery")
    require("preserv" in text.lower() or "保留" in text, f"{path.name} does not explain legacy preservation")
    require("docs/screenshots/" not in text, f"{path.name} still references removed v0.3 screenshots")

    checked: list[str] = []
    for raw in sorted(local_references(text)):
        ref = unquote(raw.split("#", 1)[0].split("?", 1)[0]).strip()
        if not ref or ref.startswith(("http://", "https://", "mailto:", "#", "data:")):
            continue
        target = (path.parent / ref).resolve()
        require(ROOT == target or ROOT in target.parents, f"Reference escapes repository: {raw}")
        require(target.exists(), f"Broken local reference in {path.name}: {raw}")
        checked.append(ref)
    return {"file": path.name, "localReferences": checked}


def main() -> None:
    manifest = json.loads((ASSETS / "manifest.json").read_text(encoding="utf-8"))
    require(manifest.get("schemaVersion") == 1, "Unexpected manifest schema")
    require(manifest.get("canvas") == [352, 352], "Unexpected source canvas")
    require(manifest.get("canvasScope") == "generated-states", "Top-level canvas scope is ambiguous")
    require(manifest.get("defaultState") == "dive", "The refined legacy dive must remain the default")
    require(manifest.get("playlist") == EXPECTED_PLAYLIST, "Unexpected timed playlist")
    require(manifest.get("playlistIntervalMs") == 11000, "Unexpected playlist interval")
    require(tuple(manifest.get("states", {}).keys()) == EXPECTED_STATES, "Unexpected state ordering or membership")
    for state in EXPECTED_PLAYLIST:
        require(
            manifest["playlistIntervalMs"] >= manifest["states"][state]["loopDurationMs"],
            f"{state}: playlist interval truncates the animation",
        )

    allow_placeholder = os.environ.get("DSH_ALLOW_PLACEHOLDER_LEGACY") == "1"
    source_profiles: dict[str, dict[str, object]] = {}
    for state in EXPECTED_STATES:
        spec = manifest["states"][state]
        animated_path = ASSETS / spec["animated"]
        static_path = ASSETS / spec["static"]
        size, frames, durations = image_profile(animated_path)
        static_size, static_frames, _ = image_profile(static_path)
        manifest_canvas = tuple(spec.get("canvas", ()))
        require(manifest_canvas == size, f"{state}: manifest canvas {manifest_canvas} does not match WebP {size}")
        require(frames == spec["frames"], f"{state}: manifest frame count mismatch")
        require(set(durations) == {spec["frameDurationMs"]}, f"{state}: unexpected WebP timing {sorted(set(durations))}")
        require(sum(durations) == spec["loopDurationMs"], f"{state}: loop duration mismatch")
        require(static_size == size and static_frames == 1, f"{state}: invalid reduced-motion PNG")
        if state in LEGACY_GIT_BLOBS:
            require(spec["source"] == "legacy", f"{state}: legacy source marker missing")
            require(size == LEGACY_GIT_BLOBS[state]["canvas"], f"{state}: preserved native canvas changed")
            if not allow_placeholder:
                require(git_blob_sha(animated_path) == LEGACY_GIT_BLOBS[state]["animated"], f"{state}: legacy WebP bytes changed")
                require(git_blob_sha(static_path) == LEGACY_GIT_BLOBS[state]["static"], f"{state}: legacy PNG bytes changed")
        elif state == "spout":
            report_path = ROOT / spec["provenanceReport"]
            report = json.loads(report_path.read_text(encoding="utf-8"))
            source_sheets = sorted((ROOT / "artwork-sources" / "spout-imagegen-v1").glob("phase-*.png"))
            require(spec["source"] == "imagegen", "spout: source marker missing")
            require(size == (352, 352), "spout: canvas changed")
            require(spec["frames"] == 137 and spec["frameDurationMs"] == 33 and spec["loopDurationMs"] == 4521, "spout: runtime contract changed")
            require(spec.get("nativeImageGenCels") == 64 and spec.get("spoutSegmentFrames") == 77, "spout: provenance counts changed")
            require(spec.get("cycleSegments") == report["output"]["segments"], "spout: segment mapping changed")
            require(len(source_sheets) == 4, "spout: expected four Image Gen source sheets")
            for sheet in source_sheets:
                provenance = report["inputs"]["phaseSheets"][sheet.name]
                require(list(Image.open(sheet).size) == provenance["size"] == [1254, 1254], f"spout: source size mismatch for {sheet.name}")
                require(hashlib.sha256(sheet.read_bytes()).hexdigest() == provenance["sha256"], f"spout: source hash mismatch for {sheet.name}")
            dive_frames = rgba_frames(ASSETS / "whale-dive.webp")
            spout_frames = rgba_frames(animated_path)
            require(spout_frames[:60] == dive_frames, "spout: first 60 frames are not the preserved Dive loop")
            require(spout_frames[-1] == dive_frames[0], "spout: final frame does not close on Dive frame 1")
            require(report.get("checks", {}).get("allPassed") is True, "spout: deterministic build report failed")
        else:
            require(spec["source"] == "generated", f"{state}: generated source marker missing")
            require(size == (352, 352), f"{state}: generated canvas changed")
            require(spec["frames"] == 48, f"{state}: generated frame count changed")
            require(spec["frameDurationMs"] == 40, f"{state}: generated cadence changed")
            require(spec["loopDurationMs"] == 1920, f"{state}: generated duration changed")
            if state in EXPECTED_DERIVED_FROM:
                require(spec.get("derivedFrom") == EXPECTED_DERIVED_FROM[state], f"{state}: legacy identity lineage changed")
            else:
                require("derivedFrom" not in spec, f"{state}: unexpected legacy identity lineage")
        source_profiles[state] = {
            "source": spec["source"],
            "frames": frames,
            "durationMs": sum(durations),
            "animatedBytes": animated_path.stat().st_size,
            "staticBytes": static_path.stat().st_size,
        }

    hero_size, hero_frames, _ = image_profile(DOCS / "hero.png")
    gallery_size, gallery_frames, _ = image_profile(DOCS / "state-gallery.png")
    preview_size, preview_frames, preview_durations = image_profile(DOCS / "preview.webp")
    real_speed_size, real_speed_frames, real_speed_durations = image_profile(DOCS / "rebuilt-states-real-speed.webp")
    require(hero_size == (1200, 420) and hero_frames == 1, f"Unexpected hero profile: {hero_size}, {hero_frames}")
    require(gallery_size == (1200, 760) and gallery_frames == 1, f"Unexpected gallery profile: {gallery_size}, {gallery_frames}")
    require(preview_size == (1000, 360), f"Unexpected preview dimensions: {preview_size}")
    require(preview_frames == 56, f"Unexpected preview frame count: {preview_frames}")
    require(set(preview_durations) == {60}, f"Unexpected preview timing: {sorted(set(preview_durations))}")
    require((DOCS / "preview.webp").stat().st_size <= 1024 * 1024, "README preview exceeds 1 MiB budget")
    require(real_speed_size == (1000, 300), f"Unexpected real-speed preview dimensions: {real_speed_size}")
    require(real_speed_frames == 48, f"Unexpected real-speed preview frame count: {real_speed_frames}")
    require(set(real_speed_durations) == {40}, f"Unexpected real-speed preview timing: {sorted(set(real_speed_durations))}")
    require(sum(real_speed_durations) == 1920, "Real-speed preview loop duration changed")
    require((DOCS / "rebuilt-states-real-speed.webp").stat().st_size <= 1024 * 1024, "Real-speed preview exceeds 1 MiB budget")
    real_speed_report = json.loads((DOCS / "rebuilt-states-real-speed.json").read_text(encoding="utf-8"))
    require(real_speed_report.get("schemaVersion") == 1, "Unexpected real-speed preview report schema")
    require(real_speed_report.get("file") == "rebuilt-states-real-speed.webp", "Real-speed preview report filename changed")
    require(real_speed_report.get("size") == [1000, 300], "Real-speed preview report size changed")
    require(real_speed_report.get("frames") == 48, "Real-speed preview report frame count changed")
    require(real_speed_report.get("frameDurationMs") == 40, "Real-speed preview report cadence changed")
    require(real_speed_report.get("loopDurationMs") == 1920, "Real-speed preview report loop changed")
    require(
        real_speed_report.get("sha256") == hashlib.sha256((DOCS / "rebuilt-states-real-speed.webp").read_bytes()).hexdigest(),
        "Real-speed preview file does not match its locked SHA-256",
    )
    require(
        real_speed_report.get("states") == {
            state: manifest["states"][state]["animatedSha256"]
            for state in ("work", "compose", "idle", "alert")
        },
        "Real-speed preview was not rebuilt from the current four animated states",
    )

    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    require(package.get("version") == "0.6.0", "package.json version is not 0.6.0")
    require((ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines() == ["Pillow==12.1.1", "numpy==2.3.3"], "Image dependency locks changed")
    require("requirements.txt" in package.get("files", []), "Pillow lock is missing from package files")
    require("scripts/check-whale-style.py" in package.get("files", []), "Style identity gate is missing from package files")
    require(package.get("scripts", {}).get("check") == "node scripts/check-workflows.mjs && node scripts/check.mjs && python scripts/check-readme-assets.py && npm run audit:motion && npm run audit:style", "Package check script is incomplete")
    require(package.get("scripts", {}).get("build:spout") == "python scripts/build-whale-spout.py", "Spout build script is not wired")
    require(package.get("scripts", {}).get("verify") == "npm run build:assets && npm run build && npm run build:motion-audit && npm run build:style-audit && npm run check", "Package verify script is incomplete")

    readmes = [validate_readme(ROOT / "README.md"), validate_readme(ROOT / "README.zh-CN.md")]
    print(json.dumps({
        "ok": True,
        "states": list(EXPECTED_STATES),
        "playlist": EXPECTED_PLAYLIST,
        "sources": source_profiles,
        "hero": {"size": hero_size},
        "gallery": {"size": gallery_size},
        "preview": {
            "size": preview_size,
            "frames": preview_frames,
            "frameDurationMs": 60,
            "durationMs": sum(preview_durations),
            "bytes": (DOCS / "preview.webp").stat().st_size,
        },
        "realSpeedPreview": {
            "size": real_speed_size,
            "frames": real_speed_frames,
            "frameDurationMs": 40,
            "durationMs": sum(real_speed_durations),
            "bytes": (DOCS / "rebuilt-states-real-speed.webp").stat().st_size,
        },
        "readmes": readmes,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
