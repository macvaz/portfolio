#!/usr/bin/env python3
"""Capture a Morningstar SAL ``access_token`` with Playwright.

Opens a public Morningstar fund page, waits for the site to call
``api-global.morningstar.com`` with an ``access_token`` query param (or an
``Authorization: Bearer …`` header), and prints the raw token to stdout.

Examples::

  docker build -f docker/playwright/Dockerfile -t portfolio-playwright docker/playwright
  docker run --rm --ipc=host portfolio-playwright
  docker run --rm --ipc=host portfolio-playwright --url \\
    'https://global.morningstar.com/es/inversiones/fondos/0P0000TJ7F/cotizacion'

Exit codes:
  0 — token printed to stdout
  1 — timed out / failed
"""

from __future__ import annotations

import argparse
import re
import sys
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

DEFAULT_URL = (
    "https://global.morningstar.com/es/inversiones/fondos/0P0000TJ7F/cotizacion"
)

# JWT-shaped token (header.payload.signature)
JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")


def token_from_url(url: str) -> str | None:
    """Extract ``access_token`` from a request URL if present."""
    parsed = urlparse(url)
    values = parse_qs(parsed.query).get("access_token") or []
    if values and values[0].strip():
        return values[0].strip()
    # Sometimes token is embedded elsewhere in the URL.
    match = JWT_RE.search(url)
    return match.group(0) if match else None


def token_from_authorization(header_value: str | None) -> str | None:
    if not header_value:
        return None
    value = header_value.strip()
    if value.lower().startswith("bearer "):
        token = value[7:].strip()
        return token or None
    match = JWT_RE.search(value)
    return match.group(0) if match else None


def token_from_storage(page) -> str | None:
    """Best-effort scrape of local/session storage for a JWT."""
    return page.evaluate(
        """() => {
          const buckets = [window.localStorage, window.sessionStorage];
          const jwt = /eyJ[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+/;
          for (const store of buckets) {
            for (let i = 0; i < store.length; i++) {
              const key = store.key(i);
              const val = store.getItem(key) || '';
              if (/access[_-]?token/i.test(key) && jwt.test(val)) {
                const m = val.match(jwt);
                if (m) return m[0];
              }
              if (jwt.test(val) && /token|auth|ms|morningstar/i.test(key)) {
                const m = val.match(jwt);
                if (m) return m[0];
              }
            }
          }
          return null;
        }"""
    )


def fetch_morningstar_access_token(
    *,
    url: str = DEFAULT_URL,
    timeout_ms: int = 60_000,
    headed: bool = False,
) -> str:
    """
    Drive Chromium against Morningstar and return the SAL access token.

    Raises ``RuntimeError`` if no token is observed before ``timeout_ms``.
    """
    found: dict[str, str | None] = {"token": None}

    def on_request(request) -> None:
        if found["token"]:
            return
        token = token_from_url(request.url)
        if not token:
            token = token_from_authorization(request.headers.get("authorization"))
        if token:
            found["token"] = token

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=not headed,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            locale="es-ES",
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1400, "height": 900},
        )
        page = context.new_page()
        page.on("request", on_request)

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            # Chart / SAL calls often fire after hydration.
            page.wait_for_timeout(3_000)
            # Click common performance / chart tabs if present (best-effort).
            for label in ("Rentabilidad", "Performance", "Chart", "Gráfico"):
                try:
                    locator = page.get_by_role("tab", name=re.compile(label, re.I))
                    if locator.count() > 0:
                        locator.first.click(timeout=2_000)
                        page.wait_for_timeout(2_000)
                        break
                except Exception:
                    continue

            deadline = timeout_ms
            elapsed = 0
            step = 500
            while elapsed < deadline and not found["token"]:
                stored = token_from_storage(page)
                if stored:
                    found["token"] = stored
                    break
                page.wait_for_timeout(step)
                elapsed += step
        except PlaywrightTimeoutError as exc:
            browser.close()
            raise RuntimeError(f"Timed out loading Morningstar page: {exc}") from exc

        browser.close()

    if not found["token"]:
        raise RuntimeError(
            "No Morningstar access_token observed. "
            "The page may require login, block headless browsers, or use a "
            "different auth flow."
        )
    return found["token"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture Morningstar SAL access_token via Playwright"
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help="Morningstar fund page that triggers SAL chart calls",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=60_000,
        help="Max wait for a token-bearing request (default: 60000)",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run with a visible browser (needs a display / VNC)",
    )
    args = parser.parse_args(argv)

    try:
        token = fetch_morningstar_access_token(
            url=args.url,
            timeout_ms=args.timeout_ms,
            headed=args.headed,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    # Token only on stdout so it can be captured: TOKEN=$(docker run …)
    print(token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
