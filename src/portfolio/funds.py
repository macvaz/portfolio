"""
Morningstar fund search using Playwright.

This is a server-friendly alternative to the Selenium implementation.
Playwright automatically downloads and manages browser binaries, making it
ideal for server environments where Chrome/Chromium is not pre-installed.

Works on: Linux servers, Docker containers, cloud platforms (AWS, GCP, Azure)
No system-level browser installation required.
"""

import json
import re
import asyncio
from typing import Dict, Optional
from playwright.async_api import async_playwright

DOMAIN = "https://global.morningstar.com"


async def search_isin(isin: str) -> Optional[Dict]:
    """
    Search for a fund by ISIN using Morningstar's API with Playwright.
    
    Args:
        isin: The ISIN code to search for
        
    Returns:
        The API response JSON as a dict, or None if the search fails
    """
    
    # Build the search URL
    query = f'((isin+~%3D+%22{isin}%22))'
    url = f"{DOMAIN}/api/v1/es/legacy-search/securities?fields=isin&query={query}&sort=_score"
    
    async with async_playwright() as p:
        print(f"[*] Launching headless browser (Playwright)...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,
        )
        
        # Add headers to context
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
        """)
        
        page = await context.new_page()
        
        # Set extra headers
        await page.set_extra_http_headers({
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://global.morningstar.com/",
            "Origin": "https://global.morningstar.com",
        })
        
        try:
            # Establish session with domain
            print(f"[*] Visiting domain: {DOMAIN}")
            await page.goto(DOMAIN, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)  # Wait for JS
            
            # Fetch the search results
            print(f"[*] Searching for ISIN: {isin}")
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(1000)
            
            # Extract page content
            page_content = await page.content()
            
            # Try to parse JSON
            try:
                # First try direct JSON parse
                data = json.loads(page_content)
                print(f"[+] Successfully retrieved search results for {isin}")
                return data
            except json.JSONDecodeError:
                # Try extracting from <pre> tag or stripping HTML
                match = re.search(r'<pre[^>]*>({.*})</pre>', page_content, re.DOTALL)
                if match:
                    json_str = match.group(1)
                    data = json.loads(json_str)
                    print(f"[+] Successfully retrieved search results for {isin}")
                    return data
                
                # Also try just looking for JSON object at page level
                json_match = re.search(r'({.*})', page_content, re.DOTALL)
                if json_match:
                    try:
                        json_str = json_match.group(1)
                        data = json.loads(json_str)
                        print(f"[+] Successfully retrieved search results for {isin}")
                        return data
                    except:
                        pass
                
                print(f"[-] Could not extract search results for {isin}")
                return None
            
        except Exception as e:
            print(f"[-] Error searching for ISIN {isin}: {e}")
            return None
            
        finally:
            await context.close()
            await browser.close()


def search_isin_sync(isin: str) -> Optional[Dict]:
    """
    Synchronous wrapper for search_isin().
    Use this if you're not in an async context.
    
    Args:
        isin: The ISIN code to search for
        
    Returns:
        The API response JSON as a dict, or None if the search fails
    """
    return asyncio.run(search_isin(isin))


if __name__ == "__main__":
    # Test with the example ISIN
    result = search_isin_sync("IE00BFMXXD54")
    if result:
        print("\nSearch Results:")
        print(json.dumps(result, indent=2)[:1500])
