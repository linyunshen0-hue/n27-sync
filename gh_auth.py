"""GitHub Device Flow 授权（不需要密码、不需要粘贴 token）

用法：
  python gh_auth.py start   # 打印 verification URL + 8 位码
  python gh_auth.py wait    # 你去浏览器点 Authorize 后跑这条，轮询拿 token

token 只写到本目录 .ghtoken（权限 600），不打印明文。
用完可 python gh_auth.py logout 删除。
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

CLIENT = "178c6fc778ccc68e1d6a"  # GitHub CLI 的公开 OAuth client_id（标准设备码流程）
SCOPE = "repo"
BASE = os.path.dirname(os.path.abspath(__file__))
DEV = os.path.join(BASE, ".ghdevice.json")
TOK = os.path.join(BASE, ".ghtoken")


def _post(url, data):
    req = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(data).encode(),
        headers={"Accept": "application/json", "User-Agent": "pi-agent"},
    )
    return json.load(urllib.request.urlopen(req, timeout=25))


def start():
    r = _post(
        "https://github.com/login/device/code",
        {"client_id": CLIENT, "scope": SCOPE},
    )
    if "user_code" not in r:
        print("FAIL", r)
        return 1
    json.dump(r, open(DEV, "w"))
    print("=" * 52)
    print("  打开 :", r["verification_uri"])
    print("  输入码:", r["user_code"])
    print("  scope:", SCOPE, " 有效期", r["expires_in"], "秒")
    print("=" * 52)
    return 0


def wait():
    if not os.path.exists(DEV):
        print("先跑 start")
        return 1
    r = json.load(open(DEV))
    deadline = time.time() + r["expires_in"]
    interval = r.get("interval", 5)
    print("轮询中…（去浏览器确认后会自己完成）", flush=True)
    while time.time() < deadline:
        time.sleep(interval)
        try:
            t = _post(
                "https://github.com/login/oauth/access_token",
                {
                    "client_id": CLIENT,
                    "device_code": r["device_code"],
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
            )
        except Exception as e:
            print("  网络重试:", type(e).__name__)
            continue
        if t.get("access_token"):
            with open(TOK, "w") as f:
                f.write(t["access_token"])
            try:
                os.chmod(TOK, 0o600)
            except OSError:
                pass
            os.remove(DEV)
            tok = t["access_token"]
            print(f"OK 已拿到 token（{tok[:4]}…{tok[-4:]}, len={len(tok)}）")
            print("scope:", t.get("scope"))
            return 0
        err = t.get("error")
        if err == "authorization_pending":
            continue
        if err == "slow_down":
            interval += 5
            continue
        print("FAIL", t)
        return 1
    print("超时，重新跑 start")
    return 1


def logout():
    for p in (TOK, DEV):
        if os.path.exists(p):
            os.remove(p)
    print("已删除本地 token")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.exit({"start": start, "wait": wait, "logout": logout}.get(cmd, lambda: print(__doc__) or 1)())
