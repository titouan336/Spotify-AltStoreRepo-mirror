#!/usr/bin/env python3
import subprocess
import os

REPO_PATH = "."

def run(cmd):
    print("▶", " ".join(cmd))
    subprocess.run(cmd, check=True)

def main():
    os.chdir(REPO_PATH)

    # Local Git config (visible only on this machine, not stored in the repo)
    run(["git", "config", "user.name", "SpotifyAutoBot"])
    run(["git", "config", "user.email", "bot@example.com"])  # only for Git, not stored in the GitLab repo

    # Add ipas + source.json
    run(["git", "add", "ipas", "source.json"])

    # Commit (if there are no changes, this fails → we ignore it)
    try:
        run(["git", "commit", "-m", "Auto update from Telegram"])
    except subprocess.CalledProcessError:
        print("ℹ️ No changes to commit")
        return

    # Push to GitLab
    run(["git", "push", "origin", "main"])
    print("✅ Pushed to GitLab!")

if __name__ == "__main__":
    main()
