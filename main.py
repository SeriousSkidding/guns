import asyncio
import os
import random
import string
import time
import requests
from playwright.async_api import async_playwright

BASE_URL = "https://guns.lol/{}"

available_list = []
banned_list = []
taken_list = []

CHARS = string.ascii_lowercase + string.digits
RATE_LIMIT_TEXT = ["too many requests"]
RATE_RETRY_DELAY = 120  # seconds

# Script by the big GPT and revised by SeriousSkidding
WEBHOOK_AVAILABLE = os.getenv("WEBHOOK_AVAILABLE")
WEBHOOK_TAKEN = os.getenv("WEBHOOK_TAKEN")
WEBHOOK_BANNED = os.getenv("WEBHOOK_BANNED")

ROLE_TAKEN = "1465095412791771318"
ROLE_BANNED = "1465095383259549818"

# ---------------- CHECK FUNCTION ---------------- #
async def check_username(page, username):
    url = BASE_URL.format(username)

    try:
        response = await page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page_text = (await page.content()).lower()

        if (response and response.status == 429) or any(t in page_text for t in RATE_LIMIT_TEXT):
            print("[RATE LIMITED] Sleeping...")
            time.sleep(RATE_RETRY_DELAY)
            return "retry"

        try:
            h1_text = (await page.locator("h1").inner_text()).lower().strip()
        except:
            h1_text = ""

        if "username not found" in h1_text:
            print(f"[AVAILABLE] {username}")
            available_list.append(username)
        elif "has been banned" in h1_text:
            print(f"[BANNED] {username}")
            banned_list.append(username)
        else:
            print(f"[TAKEN] {username}")
            taken_list.append(username)

    except Exception as e:
        print(f"[ERROR] {username} - {e}")
        taken_list.append(username)

    return "ok"

# ---------------- FILE SAVE ---------------- #
def save_results():
    with open("available.txt", "w") as f:
        f.write("\n".join(available_list) or "None")
    with open("banned.txt", "w") as f:
        f.write("\n".join(banned_list) or "None")
    with open("taken.txt", "w") as f:
        f.write("\n".join(taken_list) or "None")

# ---------------- DISCORD WEBHOOK ---------------- #
def send_webhook(url, title, names, color, content, allow_everyone=False, allow_roles=None):
    if not url or not names:
        return

    payload = {
        "content": content,
        "embeds": [{
            "title": title,
            "description": "```\n" + "\n".join(names[:50]) + "\n```",
            "color": color
        }],
        "allowed_mentions": {
            "parse": [],
            "roles": []
        }
    }

    if allow_everyone:
        payload["allowed_mentions"]["parse"].append("everyone")

    if allow_roles:
        payload["allowed_mentions"]["roles"].extend(allow_roles)

    r = requests.post(url, json=payload)
    print(f"{title} webhook sent: {r.status_code}")

# ---------------- RANDOM GENERATOR ---------------- #
def generate_random_usernames(length, amount):
    return ["".join(random.choice(CHARS) for _ in range(length)) for _ in range(amount)]

# ---------------- MAIN ---------------- #
async def main():
    mode = os.getenv("MODE", "2c")
    amount = int(os.getenv("AMOUNT", "50"))
    wordlist = os.getenv("WORDLIST", "")

    if mode == "2c":
        usernames = generate_random_usernames(2, amount)
    elif mode == "3c":
        usernames = generate_random_usernames(3, amount)
    elif mode == "wordlist":
        with open(wordlist, "r", encoding="utf-8") as f:
            usernames = [u.strip() for u in f if u.strip()]
    else:
        print("Invalid MODE")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for user in usernames:
            result = await check_username(page, user)
            if result == "retry":
                continue

        await browser.close()

    save_results()

    # Send Discord notifications
    send_webhook(
        WEBHOOK_AVAILABLE,
        "✅ Available Names",
        available_list,
        0x57F287,
        "@everyone",
        allow_everyone=True
    )

    send_webhook(
        WEBHOOK_TAKEN,
        "❌ Taken Names",
        taken_list,
        0xED4245,
        f"<@&{ROLE_TAKEN}>",
        allow_roles=[ROLE_TAKEN]
    )

    send_webhook(
        WEBHOOK_BANNED,
        "⚠️ Banned Names",
        banned_list,
        0xFEE75C,
        f"<@&{ROLE_BANNED}>",
        allow_roles=[ROLE_BANNED]
    )

    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
