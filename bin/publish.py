#!/usr/bin/env python3
"""Publish a language's phone build to Netlify, the host your site already uses.

    python bin/publish.py --lang de
    python bin/publish.py --lang de --site my-site-name
    python bin/publish.py --lang fr --dry-run          show what would be sent

Needs your Netlify access token in the NETLIFY_AUTH_TOKEN environment variable
(on Colab: the key icon on the left, a secret named NETLIFY_AUTH_TOKEN).
Create one at app.netlify.com -> User settings -> Applications -> Personal
access tokens.

Only changed files are uploaded: Netlify compares fingerprints and asks for
what it does not already have, so a republish after a small change is quick.
If the site name does not exist yet, it is created in your account.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote

import requests

from language import PROFILE as P
from paths import LANG_ROOT

API = os.environ.get("NETLIFY_API", "https://api.netlify.com/api/v1").rstrip("/")
SKIP = {".DS_Store", "Thumbs.db"}


def sha1(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fingerprints(folder: Path) -> dict[str, str]:
    files = {}
    for p in sorted(folder.rglob("*")):
        if p.is_file() and p.name not in SKIP and not p.name.endswith(".command"):
            files["/" + p.relative_to(folder).as_posix()] = sha1(p)
    return files


class Netlify:
    def __init__(self, token: str):
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {token}"

    def call(self, method, path, **kw):
        for attempt in range(5):
            try:
                r = self.s.request(method, f"{API}{path}", timeout=kw.pop("timeout", 120), **kw)
            except requests.RequestException as e:
                if attempt == 4:
                    raise SystemExit(f"cannot reach Netlify: {e}")
                time.sleep(2 * (attempt + 1))
                continue
            if r.status_code in (429, 500, 502, 503, 504) and attempt < 4:
                time.sleep(int(r.headers.get("Retry-After", 2 * (attempt + 1))))
                continue
            return r
        return r

    def site(self, name: str) -> dict:
        r = self.call("GET", f"/sites/{name}.netlify.app")
        if r.status_code == 200:
            return r.json()
        if r.status_code == 401:
            raise SystemExit("Netlify refused the token. Check NETLIFY_AUTH_TOKEN.")
        print(f"  site {name} not found in your account; creating it")
        r = self.call("POST", "/sites", json={"name": name})
        if r.status_code in (200, 201):
            return r.json()
        raise SystemExit(f"could not create site {name}: {r.status_code} {r.text[:200]}\n"
                         "The name may be taken. Choose another with --site.")


def publish(folder: Path, site_name: str, token: str, workers: int = 8) -> str:
    files = fingerprints(folder)
    by_hash: dict[str, list[str]] = {}
    for path, digest in files.items():
        by_hash.setdefault(digest, []).append(path)
    print(f"  {len(files)} files, {sum((folder / p[1:]).stat().st_size for p in files) / 1e6:.0f} MB")

    nf = Netlify(token)
    site = nf.site(site_name)
    r = nf.call("POST", f"/sites/{site['id']}/deploys", json={"files": files, "async": True})
    if r.status_code not in (200, 201):
        raise SystemExit(f"Netlify refused the deploy: {r.status_code} {r.text[:300]}")
    deploy = r.json()
    for _ in range(120):                                   # wait until Netlify has compared
        if deploy.get("state") not in ("preparing", "new", None) or deploy.get("required") is not None:
            break
        time.sleep(2)
        deploy = nf.call("GET", f"/deploys/{deploy['id']}").json()
    if deploy.get("state") == "error":
        raise SystemExit(f"Netlify reported an error: {deploy.get('error_message')}")

    required = deploy.get("required") or []
    uploads = [by_hash[h][0] for h in required if h in by_hash]
    print(f"  Netlify already has {len(files) - len(uploads)}; uploading {len(uploads)}")

    done = 0

    def put(path: str):
        nonlocal done
        data = (folder / path[1:]).read_bytes()
        r = nf.call("PUT", f"/deploys/{deploy['id']}/files/{quote(path[1:])}", data=data,
                    headers={"Content-Type": "application/octet-stream"}, timeout=600)
        if r.status_code not in (200, 201):
            raise SystemExit(f"upload failed for {path}: {r.status_code} {r.text[:200]}")
        done += 1
        if done % 50 == 0 or done == len(uploads):
            print(f"  uploaded {done}/{len(uploads)}", flush=True)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(put, uploads))

    for _ in range(180):
        deploy = nf.call("GET", f"/deploys/{deploy['id']}").json()
        if deploy.get("state") in ("ready", "error"):
            break
        time.sleep(2)
    if deploy.get("state") != "ready":
        raise SystemExit(f"deploy ended in state {deploy.get('state')}: {deploy.get('error_message', '')}")
    return deploy.get("ssl_url") or site.get("ssl_url") or f"https://{site_name}.netlify.app"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default=P.data.get("deploy", {}).get("site", ""))
    ap.add_argument("--folder", default=str(LANG_ROOT / "builds" / "phone_build"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    folder = Path(a.folder).expanduser()
    if not (folder / "index.html").exists():
        raise SystemExit(f"no build at {folder}. Run the builds stage first.")
    if not a.site:
        raise SystemExit("no site name. Give one with --site, or set deploy.site in the profile.")
    print(f"[publish] {P.name}: {folder} -> {a.site}.netlify.app")
    if a.dry_run:
        f = fingerprints(folder)
        print(f"  would send {len(f)} files; nothing uploaded (dry run)")
        return
    token = os.environ.get("NETLIFY_AUTH_TOKEN", "").strip()
    if not token:
        raise SystemExit("NETLIFY_AUTH_TOKEN is not set. See the top of bin/publish.py.")
    url = publish(folder, a.site, token)
    print(f"  live at {url}")


if __name__ == "__main__":
    sys.exit(main())
