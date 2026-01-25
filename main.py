import asyncio
import os
import random
import string
import aiohttp
from playwright.async_api import async_playwright

BASE_URL = "https://guns.lol/{}"

available_list = []
banned_list = []
taken_list = []

CHARS = string.ascii_lowercase + string.digits
RATE_LIMIT_TEXT = ["too many requests"]
RATE_RETRY_DELAY = 120

WEBHOOK_AVAILABLE = os.getenv("WEBHOOK_AVAILABLE")
WEBHOOK_TAKEN = os.getenv("WEBHOOK_TAKEN")
WEBHOOK_BANNED = os.getenv("WEBHOOK_BANNED")

ROLE_TAKEN = "1465095412791771318"
ROLE_BANNED = "1465095383259549818"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# ---------------- CHECK FUNCTION ---------------- #
async def check_username(page, username):
    try:
        response = await page.goto(
            BASE_URL.format(username),
            timeout=30000,
            wait_until="domcontentloaded"
        )

        content = (await page.content()).lower()

        if response and response.status == 429 or any(x in content for x in RATE_LIMIT_TEXT):
            print("[RATE LIMITED] Sleeping...")
            await asyncio.sleep(RATE_RETRY_DELAY)
            return "retry"

        h1 = page.locator("h1")
        text = (await h1.inner_text()).lower() if await h1.count() else ""

        if "username not found" in text:
            print(f"[AVAILABLE] {username}")
            available_list.append(username)
        elif "has been banned" in text:
            print(f"[BANNED] {username}")
            banned_list.append(username)
        else:
            print(f"[TAKEN] {username}")
            taken_list.append(username)

    except Exception as e:
        print(f"[ERROR] {username}: {e}")
        taken_list.append(username)

    return "ok"

# ---------------- WEBHOOK ---------------- #
async def send_webhook(url, title, names, color, content, roles=None):
    if not url:
        return

    if not names:
        names = ["None"]

    payload = {
        "content": content,
        "embeds": [{
            "title": title,
            "description": "```\n" + "\n".join(names[:50]) + "\n```",
            "color": color
        }],
        "allowed_mentions": {
            "parse": [],
            "roles": roles or []
        }
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as r:
            print(f"{title} webhook: {r.status}")

# ---------------- MAIN ---------------- #
async def main():
    mode = os.getenv("MODE", "2c")
    amount = int(os.getenv("AMOUNT", "50"))

    if mode == "2c":
        usernames = ["".join(random.choice(CHARS) for _ in range(2)) for _ in range(amount)]
    elif mode == "3c":
        usernames = ["".join(random.choice(CHARS) for _ in range(3)) for _ in range(amount)]
    else:
        print("Invalid MODE")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )

        page = await browser.new_page(
            user_agent=USER_AGENT
        )

        for user in usernames:
            await check_username(page, user)

        await browser.close()

    await send_webhook(
        WEBHOOK_AVAILABLE,
        "✅ Available Names",
        available_list,
        0x57F287,
        "@everyone"
    )

    await send_webhook(
        WEBHOOK_TAKEN,
        "❌ Taken Names",
        taken_list,
        0xED4245,
        f"<@&{ROLE_TAKEN}>",
        roles=[ROLE_TAKEN]
    )

    await send_webhook(
        WEBHOOK_BANNED,
        "⚠️ Banned Names",
        banned_list,
        0xFEE75C,
        f"<@&{ROLE_BANNED}>",
        roles=[ROLE_BANNED]
    )

    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
