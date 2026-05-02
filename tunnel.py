"""
Cloudflare Quick Tunnel 起動 & URL表示スクリプト
cloudflared の出力からURLを抽出してコンソールに大きく表示する
"""
import subprocess
import re
import sys

def main():
    print("Cloudflare Tunnel を起動中...")
    import os
    cloudflared = os.path.expandvars(
        r"%LOCALAPPDATA%\Microsoft\WinGet\Packages"
        r"\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe"
    )
    proc = subprocess.Popen(
        [cloudflared, "tunnel", "--url", "http://localhost:8501"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    url = None
    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        if url is None:
            m = re.search(r"https://[a-z0-9\-]+\.trycloudflare\.com", line)
            if m:
                url = m.group(0)
                print("\n" + "=" * 60)
                print("  外出先からのアクセスURL:")
                print(f"  {url}")
                print("=" * 60 + "\n")

    proc.wait()

if __name__ == "__main__":
    main()
