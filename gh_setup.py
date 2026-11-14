#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GitHub 热更新一键配置（在拿到 .ghtoken 之后运行）

前置：
  1) python gh_auth.py start   → 浏览器输码授权
  2) python gh_auth.py wait    → 生成 _sync/.ghtoken

用法：
  python gh_setup.py --repo n27-sync            # 建公开库
  python gh_setup.py --repo n27-sync --private  # 建私有库
  python gh_setup.py --repo n27-sync --dry-run  # 只打印计划，不动手

做的事（幂等，可重复跑）：
  /user                    取登录名
  /user/repos              仓库不存在则创建
  /user/keys               上传 ~/.ssh/id_ed25519_github.pub（已存在则跳过）
  git remote + push        _sync/ → origin main
  purge.jsdelivr.net       清 CDN 缓存（jsDelivr 对分支缓存 12 小时，不清就是旧数据）
  冲刺刷题3.html           写 SYNC.repo
  python 更新题库.py --rebuild-only
  jsDelivr 拉取验证

安全：token 从 .ghtoken 读，绝不打印明文。
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOKFILE = os.path.join(HERE, ".ghtoken")
HTML = os.path.join(ROOT, "冲刺刷题3.html")
PUBKEY = os.path.expanduser("~/.ssh/id_ed25519_github.pub")
API = "https://api.github.com"


def token():
    if not os.path.exists(TOKFILE):
        sys.exit("缺少 _sync/.ghtoken —— 先跑 gh_auth.py start / wait")
    return open(TOKFILE).read().strip()


def call(method, path, body=None, tok=None, ok=(200, 201, 204)):
    url = path if path.startswith("http") else API + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "pi-agent")
    req.add_header("Authorization", "Bearer " + (tok or token()))
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw.strip() else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw


def sh(cmd, cwd=None, check=True):
    print("    $", cmd)
    p = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    out = out.strip()
    if out:
        print("      " + out.replace("\n", "\n      "))
    if check and p.returncode != 0:
        sys.exit(f"命令失败（{p.returncode}）：{cmd}")
    return p.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="n27-sync")
    ap.add_argument("--private", action="store_true")
    ap.add_argument("--description", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-push", action="store_true")
    ap.add_argument("--skip-rebuild", action="store_true")
    a = ap.parse_args()
    tok = token()

    print("\n[1/7] 校验 token / 取登录名")
    st, me = call("GET", "/user", tok=tok)
    if st == 401:
        sys.exit("token 无效或已撤销，重新跑 gh_auth.py start / wait")
    if st != 200:
        sys.exit(f"/user 失败 {st}: {me}")
    login = me["login"]
    print(f"    OK  user={login}  scope 允许建库={me.get('public_repos') is not None}")

    full = f"{login}/{a.repo}"
    print(f"\n[2/7] 仓库 {full}（private={a.private}）")
    st, repo = call("GET", f"/repos/{full}", tok=tok)
    if st == 200:
        print("    已存在，跳过创建")
        if repo.get("private") != a.private:
            print(f"    !! 注意：现有仓库 private={repo.get('private')}，与请求 {a.private} 不一致")
    elif st == 404:
        if a.dry_run:
            print("    [dry-run] 将创建")
        else:
            st, repo = call("POST", "/user/repos", {
                "name": a.repo,
                "private": a.private,
                "description": a.description,
                "auto_init": False,
                "has_issues": False,
                "has_wiki": False,
                "has_projects": False,
            }, tok=tok)
            if st not in (200, 201):
                sys.exit(f"建库失败 {st}: {repo}")
            print("    OK 已创建")
            time.sleep(2)
    else:
        sys.exit(f"查询仓库失败 {st}: {repo}")

    print("\n[3/7] 上传 SSH 公钥（供 git push 走 ssh.github.com:443）")
    if not os.path.exists(PUBKEY):
        print(f"    !! 找不到 {PUBKEY}，跳过（push 会失败，需手动处理）")
    else:
        key = open(PUBKEY).read().strip()
        st, keys = call("GET", "/user/keys", tok=tok)
        have = {k.get("key", "").strip() for k in (keys or [])} if st == 200 else set()
        if key in have:
            print("    已存在，跳过")
        elif a.dry_run:
            print("    [dry-run] 将上传")
        else:
            st, r = call("POST", "/user/keys",
                         {"title": "pi-agent-" + os.uname().nodename if hasattr(os, "uname") else "pi-agent",
                          "key": key}, tok=tok)
            print("    OK 已上传" if st in (200, 201) else f"    !! 上传失败 {st}: {r}")

    print("\n[4/7] git remote + push")
    remote = f"git@github.com:{full}.git"
    if a.skip_push:
        print("    跳过（--skip-push）")
    elif a.dry_run:
        print(f"    [dry-run] remote={remote} && git push -u origin main")
    else:
        st, _ = call("GET", f"/repos/{full}/git/ref/heads/main", tok=tok)
        if st == 404:
            # 空仓库：直接 push 建立 main
            pass
        sh(f'git remote remove origin', cwd=HERE, check=False)
        sh(f'git remote add origin {remote}', cwd=HERE)
        sh('git remote -v', cwd=HERE)
        sh('git push -u origin main', cwd=HERE)

    print("\n[5/7] jsDelivr 缓存清理（关键：分支缓存 12 小时，不清就是旧数据）")
    for f in ("version.json", "d.json.gz"):
        url = f"https://purge.jsdelivr.net/gh/{full}@main/{f}"
        if a.dry_run:
            print("    [dry-run]", url)
            continue
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "pi-agent"}),
                                        timeout=30) as r:
                print(f"    {f}: {r.status} {r.read()[:120].decode('utf8', 'replace')}")
        except Exception as e:
            print(f"    {f}: purge 失败 {type(e).__name__}: {e}")

    print(f"\n[6/7] 写入 冲刺刷题3.html 的 SYNC.repo = '{full}'")
    html = open(HTML, encoding="utf-8").read()
    import re
    m = re.search(r"const SYNC = \{ repo:'[^']*'", html)
    if not m:
        print("    !! 没找到 SYNC 常量，手动检查第 268 行")
    else:
        new = re.sub(r"const SYNC = \{ repo:'[^']*'", f"const SYNC = {{ repo:'{full}'", html, count=1)
        if new != html:
            if a.dry_run:
                print("    [dry-run] 将改写")
            else:
                open(HTML, "w", encoding="utf-8").write(new)
                print("    OK 已改写")
        else:
            print("    已经是目标值，跳过")

    print("\n[7/7] 重打包 + 真实 CDN 验证")
    if not a.skip_rebuild and not a.dry_run:
        sh("python 更新题库.py --rebuild-only", cwd=ROOT)
        # 重新生成后 _sync 内容变了，需要再推一次
        sh("git add -A && git commit -m 'sync: rebuild' || true", cwd=HERE)
        sh("git push origin main", cwd=HERE)
        for f in ("version.json",):
            try:
                with urllib.request.urlopen(urllib.request.Request(
                        f"https://purge.jsdelivr.net/gh/{full}@main/{f}",
                        headers={"User-Agent": "pi-agent"}), timeout=30) as r:
                    r.read()
            except Exception:
                pass
        time.sleep(5)

    okall = True
    for path, ck in (("version.json", "json"), ("d.json.gz", "gz")):
        url = f"https://cdn.jsdelivr.net/gh/{full}@main/{path}"
        try:
            with urllib.request.urlopen(urllib.request.Request(
                    url + f"?t={int(time.time())}", headers={"User-Agent": "pi-agent"}), timeout=40) as r:
                b = r.read()
            if ck == "json":
                v = json.loads(b)
                print(f"    OK {path}  {r.status}  version={v.get('version')} total={v.get('total')}")
            else:
                import gzip as _gz
                d = _gz.decompress(b)
                j = json.loads(d)
                print(f"    OK {path}  {r.status}  {len(b)}B → {len(d)}B  questions={len(j.get('questions', {}))}")
        except Exception as e:
            okall = False
            print(f"    !! {path} 拉取失败 {type(e).__name__}: {e}")

    print("\n" + "=" * 55)
    print("完成" if okall else "部分失败，看上面 !!")
    print(f"  页面：冲刺刷题3.html（SYNC.repo={full}）")
    print(f"  离线包：冲刺模考_离线版.html")
    print("  撤销授权：python _sync/gh_auth.py logout（删本地 token）")
    print("=" * 55)


if __name__ == "__main__":
    main()
