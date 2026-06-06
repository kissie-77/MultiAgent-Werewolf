"""Quick ARK / Doubao OpenAI-compatible API connectivity check."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

from llm_werewolf.game_runtime.support.env import load_project_dotenv


def main() -> int:
    load_project_dotenv()
    api_key = os.getenv("ARK_API_KEY", "").strip()
    endpoint = os.getenv("ARK_EP", "").strip()
    base_url = "https://ark.cn-beijing.volces.com/api/v3"

    print("=== ARK API Connectivity Test ===")
    print(f"ARK_API_KEY: {'set (' + str(len(api_key)) + ' chars)' if api_key else 'MISSING'}")
    print(f"ARK_EP: {endpoint or 'MISSING'}")

    if not api_key or not endpoint:
        return 2

    payload = {
        "model": endpoint,
        "messages": [{"role": "user", "content": "Reply with exactly: pong"}],
        "max_tokens": 16,
        "temperature": 0,
    }
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            elapsed = time.perf_counter() - start
            data = json.loads(body)
            content = data["choices"][0]["message"].get("content", "")
            usage = data.get("usage", {})
            print(f"STATUS: OK ({resp.status}) in {elapsed:.2f}s")
            print(f"REPLY: {content!r}")
            print(f"USAGE: {usage}")
            return 0
    except urllib.error.HTTPError as exc:
        elapsed = time.perf_counter() - start
        err = exc.read().decode("utf-8", errors="replace")
        print(f"STATUS: HTTP {exc.code} in {elapsed:.2f}s")
        print("ERROR BODY:", err[:800])
        return 1
    except Exception as exc:
        elapsed = time.perf_counter() - start
        print(f"STATUS: FAILED in {elapsed:.2f}s")
        print("ERROR:", type(exc).__name__, str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
