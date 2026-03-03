#!/usr/bin/env python3
"""AIBox Image API client. Stdlib only."""

import argparse
import json
import os
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error
from pathlib import Path

_SSL_CTX = ssl.create_default_context()
_HEADERS_BASE = {"User-Agent": "OpenClaw-AIBox/1.0"}

API_BASE = "https://api.aiboxlab.us"
DEVICE_PARAMS = {
    "app_id": "openclaw",
    "country": "US",
    "lang": "en",
    "device_id": "openclaw-skill",
    "os_version": "1.0",
}


def load_dotenv():
    script_dir = Path(__file__).resolve().parent.parent
    for name in (".env", ".env.local"):
        env_file = script_dir / name
        if not env_file.exists():
            continue
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip("'\"")
            if name == ".env.local" or k not in os.environ:
                os.environ[k] = v


def get_api_key():
    load_dotenv()
    key = os.environ.get("AIBOX_API_KEY", "")
    if not key:
        print("Error: AIBOX_API_KEY not set. Add it to .env.local or export it.", file=sys.stderr)
        sys.exit(1)
    return key


def api_post_json(path, body, api_key):
    url = f"{API_BASE}{path}"
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            **_HEADERS_BASE,
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, context=_SSL_CTX) as resp:
        return json.loads(resp.read())


UNSUPPORTED_FORMATS = {".webp", ".avif", ".heic", ".heif"}


def ensure_jpeg(image_path):
    image_path = Path(image_path)
    if image_path.suffix.lower() not in UNSUPPORTED_FORMATS:
        return str(image_path), None

    tmp_dir = tempfile.mkdtemp(prefix="aibox_")
    out_path = Path(tmp_dir) / f"{image_path.stem}.jpg"

    if shutil.which("sips"):
        subprocess.run(
            ["sips", "-s", "format", "jpeg", str(image_path), "--out", str(out_path)],
            capture_output=True, check=True,
        )
    elif shutil.which("magick"):
        subprocess.run(["magick", str(image_path), str(out_path)], capture_output=True, check=True)
    elif shutil.which("convert"):
        subprocess.run(["convert", str(image_path), str(out_path)], capture_output=True, check=True)
    else:
        print(f"Cannot convert {image_path.suffix} — install ImageMagick or use jpg/png.", file=sys.stderr)
        sys.exit(1)

    print(f"Converted {image_path.suffix} → jpg")
    return str(out_path), tmp_dir


def upload_image(image_path, api_key):
    boundary = "----OpenClawBoundary"
    image_path = Path(image_path)
    filename = image_path.name
    image_data = image_path.read_bytes()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + image_data + b"\r\n"

    for k, v in DEVICE_PARAMS.items():
        body += (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{k}"\r\n\r\n'
            f"{v}\r\n"
        ).encode()

    body += f"--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        f"{API_BASE}/v1/image/upload",
        data=body,
        headers={
            **_HEADERS_BASE,
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    with urllib.request.urlopen(req, context=_SSL_CTX) as resp:
        result = json.loads(resp.read())

    if not result.get("success"):
        print(f"Upload failed: {result.get('msg', 'unknown error')}", file=sys.stderr)
        sys.exit(1)

    location = result["data"]["location"]
    print(f"Uploaded: {location}")
    return location


def list_presets(api_key):
    result = api_post_json("/v1/image/preset/list", DEVICE_PARAMS, api_key)
    if not result.get("success"):
        print(f"Failed to list presets: {result.get('msg')}", file=sys.stderr)
        sys.exit(1)
    presets = result["data"]["presets"]
    print(f"{'ID':<6} {'Name':<20} {'Cost'}")
    print("-" * 35)
    for p in presets:
        print(f"{p['preset_id']:<6} {p['preset_name']:<20} {p['preset_cost']}")
    return presets


def resolve_preset(name, api_key):
    result = api_post_json("/v1/image/preset/list", DEVICE_PARAMS, api_key)
    if not result.get("success"):
        print(f"Failed to fetch presets: {result.get('msg')}", file=sys.stderr)
        sys.exit(1)
    for p in result["data"]["presets"]:
        if p["preset_name"].lower() == name.lower():
            return p["preset_id"]
    names = [p["preset_name"] for p in result["data"]["presets"]]
    print(f"Unknown preset '{name}'. Available: {', '.join(names)}", file=sys.stderr)
    sys.exit(1)


def generate(img_url, preset_id, api_key, prompt=None, retries=10, retry_delay=5):
    body = {**DEVICE_PARAMS, "img_url": img_url, "preset_id": str(preset_id),
            "user_id": "openclaw", "isVip": True}
    if prompt:
        body["prompt"] = prompt
    for attempt in range(retries):
        result = api_post_json("/v1/image/generate", body, api_key)
        if result.get("success"):
            flow_id = result["data"]["flow_id"]
            print(f"Generation started: flow={flow_id}")
            return flow_id
        msg = result.get("msg", "unknown")
        if msg in ("system busy", "service is unavailable") and attempt < retries - 1:
            print(f"  {msg}, retrying in {retry_delay}s ({attempt + 1}/{retries})...")
            time.sleep(retry_delay)
            continue
        print(f"Generate failed: {msg}", file=sys.stderr)
        sys.exit(1)


def poll_flow(flow_id, api_key, interval=3, timeout=120):
    # flow_status: 9 = done, other values = in progress/failed
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = api_post_json("/v1/image/flow/get", {"flow_ids": [flow_id]}, api_key)
        if not result.get("success"):
            print(f"Poll error: {result.get('msg')}", file=sys.stderr)
            time.sleep(interval)
            continue

        flows = result["data"]["flows"]
        flow = next((f for f in flows if f["flow_id"] == flow_id), None)
        if not flow:
            time.sleep(interval)
            continue

        status = flow.get("flow_status", "")
        if status == "9":
            duration = flow.get("flow_duration", "?")
            print(f"  Done in {duration}s")
            return flow
        if status in ("-1", "error"):
            print(f"Generation failed: {flow}", file=sys.stderr)
            sys.exit(1)

        print(f"  status: {status} (processing)...", end="\r")
        time.sleep(interval)

    print(f"\nTimeout after {timeout}s", file=sys.stderr)
    sys.exit(1)


def download_result(flow_result, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    images = flow_result.get("generated_images", [])
    if not images:
        print(f"No images in result: {json.dumps(flow_result, indent=2)}", file=sys.stderr)
        return None

    paths = []
    for i, img_url in enumerate(images):
        ext = Path(img_url.split("?")[0]).suffix or ".jpg"
        out_path = out_dir / f"aibox_{flow_result['flow_id']}_{i}{ext}"
        urllib.request.urlretrieve(img_url, str(out_path))
        print(f"Saved: {out_path}")
        paths.append(str(out_path))
    return paths


def main():
    parser = argparse.ArgumentParser(description="AIBox Image API")
    parser.add_argument("--image", help="Source image path")
    parser.add_argument("--preset", help="Preset name (e.g. HD, street, wedding)")
    parser.add_argument("--preset-id", help="Preset ID number")
    parser.add_argument("--prompt", help="Optional prompt text")
    parser.add_argument("--list-presets", action="store_true", help="Show available presets")
    parser.add_argument("--out-dir", default=".", help="Output directory")
    parser.add_argument("--poll-interval", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    api_key = get_api_key()

    if args.list_presets:
        list_presets(api_key)
        return

    if not args.image:
        parser.error("--image is required for generation")

    if not Path(args.image).exists():
        print(f"File not found: {args.image}", file=sys.stderr)
        sys.exit(1)

    preset_id = args.preset_id
    if not preset_id:
        if not args.preset:
            parser.error("--preset or --preset-id is required")
        preset_id = resolve_preset(args.preset, api_key)

    image_path, tmp_dir = ensure_jpeg(args.image)
    try:
        img_url = upload_image(image_path, api_key)
        flow_id = generate(img_url, preset_id, api_key, prompt=args.prompt)
        flow_result = poll_flow(flow_id, api_key, args.poll_interval, args.timeout)
        download_result(flow_result, args.out_dir)
    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
