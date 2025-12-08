#!/usr/bin/env python3
import asyncio
import os
import json
import hashlib
from datetime import datetime
from telegram import Bot

# CONFIG
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")  # environnement variable
CHANNEL_USERNAME = "@SpotilifeIPAs"
SOURCE_JSON = "source.json"
REPO_RAW_BASE = "https://gitlab.com/titouan336/Spotify-AltStoreRepo/-/raw/main"


# ---------- Text helpers ----------

def extract_description(message_text: str) -> str:
    """
    Copy the entire message up to 2 lignes above @SpotilifeIPAs.
    """
    if not message_text:
        return ""
    lines = message_text.splitlines()

    idx_spoti = None
    for i, line in enumerate(lines):
        if "@SpotilifeIPAs" in line:
            idx_spoti = i
            break

    if idx_spoti is None:
        return message_text.strip()

    end_idx = max(0, idx_spoti - 2)
    kept_lines = lines[:end_idx]
    return "\n".join(kept_lines).strip()


def extract_version_from_text(message_text: str) -> str:
    """
    Find line like :
    - updated spotify to v9.0.96
    and returns 9.0.96
    """
    if not message_text:
        return "unknown"
    for line in message_text.splitlines():
        line_lower = line.lower().strip()
        if line_lower.startswith("- updated spotify to v"):
            part = line_lower.split("to v", 1)[-1]
            version = part.split()[0]  # cut at space in case
            return version
    return "unknown"


# ---------- Read / write JSON ----------

def load_source_json():
    if not os.path.exists(SOURCE_JSON):
        return {"apps": []}
    with open(SOURCE_JSON, "r") as f:
        return json.load(f)


def save_source_json(data):
    with open(SOURCE_JSON, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_next_build_version(app):
    """
    Increment buildVersion +1.
    """
    if "versions" not in app or not app["versions"]:
        return "1"
    last = app["versions"][0]
    try:
        bv = int(last.get("buildVersion", "0"))
    except ValueError:
        bv = 0
    return str(bv + 1)


def find_or_create_app(data, bundle_id, name, subtitle, localized_desc_base):
    """
    Find or create objet app in source.json.
    """
    for app in data["apps"]:
        if app.get("bundleIdentifier") == bundle_id:
            return app

    app = {
        "name": name,
        "bundleIdentifier": bundle_id,
        "marketplaceID": "",
        "developerName": "whoeevee",
        "subtitle": subtitle,
        "localizedDescription": localized_desc_base,
        "iconURL": "https://i.imgur.com/j51OrKn.png",
        "tintColor": "#1cd464",
        "category": "other",
        "screenshots": [],
        "versions": [],
        "appPermissions": {"entitlements": [], "privacy": {}},
        "patreon": {}
    }

    data["apps"].append(app)
    return app


# ---------- Telegram processing ----------

async def main():
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN non defined into environnement variables")

    bot = Bot(token=BOT_TOKEN)
    print("🚀 Scan Telegram → update source.json")

    os.makedirs("ipas/classic", exist_ok=True)
    os.makedirs("ipas/patched", exist_ok=True)

    data = load_source_json()

    offset = 0
    while True:
        updates = await bot.get_updates(offset=offset, limit=20)
        if not updates:
            break

        for update in updates:
            offset = update.update_id + 1

            msg = update.channel_post
            if not msg or not msg.document:
                continue

            doc = msg.document
            filename = doc.file_name
            if not filename.lower().endswith(".ipa"):
                continue

            print(f"\n📥 New IPA Message: {filename}")

            # Local downloading
            folder = "patched" if "patched" in filename.lower() else "classic"
            local_path = f"ipas/{folder}/{filename}"
            file = await bot.get_file(doc.file_id)
            await file.download_to_drive(local_path)

            # File size
            size = os.path.getsize(local_path)

            # Text message
            caption = msg.caption or ""

            # Version since "updated spotify to v9.x.x"
            version = extract_version_from_text(caption)

            # Description 2 lines before @SpotilifeIPA
            loc_desc = extract_description(caption)

            # Date (YYYY-MM-DD)
            date_str = msg.date.strftime("%Y-%m-%d")

            # URL downloading GitLab
            download_url = f"{REPO_RAW_BASE}/ipas/{folder}/{filename}"

            # Bundle + app
            if folder == "patched":
                bundle_id = "com.titouan336.spotify.patched"
                app_name = "Spotify (Patched)"
                subtitle = "Patched for paid certs"
            else:
                bundle_id = "com.titouan336.spotify.classic"
                app_name = "Spotify"
                subtitle = "Latest eevee release"

            app = find_or_create_app(
                data,
                bundle_id=bundle_id,
                name=app_name,
                subtitle=subtitle,
                localized_desc_base=loc_desc
            )

            # buildVersion + adding version at the beginning
            build_version = get_next_build_version(app)
            new_version = {
                "version": version,
                "date": date_str,
                "localizedDescription": loc_desc,
                "downloadURL": download_url,
                "size": size,
                "buildVersion": build_version,
                "minOSVersion": app["versions"][0]["minOSVersion"] if app["versions"] else "15.0"
            }

            app["versions"].insert(0, new_version)

            print(f"  ✅ v{version} | {size:,} octets | build {build_version}")
            print(f"  📝 Desc (beginning): {loc_desc.splitlines()[0] if loc_desc else '—'}")

        await asyncio.sleep(1)

    save_source_json(data)
    print("\n✅ source.json updated, ready to be pushed on GitLab")


if __name__ == "__main__":
    asyncio.run(main())
