# 任务包 · 政治冲刺题库 GitHub 热更新（交棒给另一个 AI）

> 生成时间：2026-11-14
> 工作目录：`D:\27考研ai产出\政治`（Git Bash 路径 `/d/27考研ai产出/政治`）
> 本文件 + `_sync/` 下的三个脚本 = 完整可执行交接，不需要读别的文档也能干完。

---

## 0. 本次更新（2026-11-14 · v2）

| | 变化 |
|---|---|
| 题量 | 1353 → **1617**（新增 27肖八选择题 8 套 264 题） |
| 套数 | 41 → **49** |
| `d.json.gz` | 811 KB → **936 KB** |
| 离线包 | 1.08 MB → **1.27 MB** |
| 肖八解析 | **264/264 全部就绪**（答案 264/264，解析 262/264 完整；906003/903024/907024 三题 OCR 截断待补） |
| 肖八考点 | **209 题挂确定考点，55 题挂 `571 暂无考点`**（等苍盾官方更新后替换，`_xiaoba/kd_status.json` 存了全部候选） |

**要推的就是新的 `d.json.gz` + `version.json`（已 git commit）**，流程见第 3 节，不用重新生成数据。

## 0.1 一句话任务

把已经生成好的 `_sync/`（`version.json` + `d.json.gz`，共 936 KB）推到一个 GitHub 仓库，
让 `冲刺刷题3.html` 启动时能通过 jsDelivr 检查并拉取新版题库。

**唯一卡点：需要一个人类在浏览器上点一次 Authorize（AI 拿不到账号身份，这一步无法代劳）。**

---

## 1. 先看你在哪一步

| 步骤 | 状态 | 说明 |
|---|---|---|
| 题库 / 页面 / 离线包 | ✅ 已完成 | **1617 题 / 49 套**（含 27肖八 264 题），v3 工作台，离线包 1.2 MB 可双击 |
| `_sync/` 两个数据文件 | ✅ 已生成 | `version.json` 163 B，`d.json.gz` 936 KB（1617 题，肖八 264 题全解析） |
| `_sync/` git 仓库 | ✅ 已 init | 唯一提交 `0e98420 sync: v2026-11-14`，分支已改名 `main`（原始是 master，必须 main，页面里 `SYNC.branch='main'`） |
| SSH key 文件 | ✅ 存在 | `~/.ssh/id_ed25519_github` + `.pub`，`~/.ssh/config` 已配 `ssh.github.com:443` |
| SSH key 加到 GitHub 账号 | ❌ **没加** | 实测 `ssh -T git@github.com` → `Permission denied (publickey)` |
| GitHub 仓库 | ❌ **没建** | `SYNC.repo` 还是空字符串 |
| 网络可达性 | ✅ 已验证 | `api.github.com` 200 / `github.com` 200 / `cdn.jsdelivr.net` 200（HTTP 层实测，不是只测 TLS） |

**结论：本地一切就绪，只差「授权 + 建库 + push + 填配置」。**

---

## 2. 授权这一步（为什么必须人类做，以及怎么做）

我（上一个 AI）已经写好 `_sync/gh_auth.py`，走 GitHub 官方 **Device Flow**：
用户不需要给密码、不需要粘贴 token，只需要在浏览器输一个 8 位码点 Authorize。
scope 只要 `repo`。

> 我上一次已经生成过一个码（`1E9A-4447`，15 分钟有效），**大概率已过期**。
> `_sync/.ghdevice.json` 里是它的临时 device_code，过期就没用，可以直接删。

让用户执行：

```bash
cd /d/27考研ai产出/政治/_sync
python gh_auth.py start      # 打印 URL + 8 位码（中文在 GBK 控制台可能乱码，看码就行）
```

然后告诉用户：
1. 打开 `https://github.com/login/device`
2. 输入打印出来的码，如 `XXXX-XXXX`
3. 点 **Authorize**

用户点完后，AI 执行：

```bash
python gh_auth.py wait       # 轮询，成功后写 _sync/.ghtoken（权限 600，不打印明文）
```

`wait` 成功会打印 `OK 已拿到 token（xxxx…xxxx, len=40）`。
**任何时候都不要把 token 明文写进日志、回答、提交的文件。**需要比对时只保留前后各 4 位。

如果用户的 GitHub 账号还没注册 / 不想用 GitHub，直接跳到第 6 节「B 计划」。

---

## 3. 拿到 token 后：一条命令干完（推荐）

```bash
cd /d/27考研ai产出/政治/_sync
python gh_setup.py --repo n27-sync --dry-run    # 先看计划，不动手
python gh_setup.py --repo n27-sync              # 真跑
```

`gh_setup.py` 会依次做（全部幂等，失败可重跑）：

| 步 | 动作 | 接口/命令 |
|---|---|---|
| 1 | 校验 token，取用户名 | `GET /user` |
| 2 | 建空仓库（已存在则跳过） | `POST /user/repos` |
| 3 | 上传 SSH 公钥（已存在则跳过） | `GET/POST /user/keys` |
| 4 | 配 remote 并 push | `git remote add origin git@github.com:<user>/<repo>.git`；`git push -u origin main` |
| 5 | **清 jsDelivr 缓存** | `https://purge.jsdelivr.net/gh/<user>/<repo>@main/<file>` |
| 6 | 写 `冲刺刷题3.html` 的 `SYNC.repo` | 正则替换第 268 行 |
| 7 | 重打包 + 真实 CDN 拉取验证 | `python 更新题库.py --rebuild-only` → 下载 `version.json` / `d.json.gz` 并解析 |

### 参数

```bash
--repo <名字>      默认 n27-sync
--private          建私有库（注意：jsDelivr 免费版只服务公开库，私有库走 B 计划）
--dry-run          只打印计划
--skip-push        跳过 push（调试用）
--skip-rebuild     跳过重打包
```

### 手动等效命令（如果 `gh_setup.py` 不可用）

```bash
cd /d/27考研ai产出/政治/_sync
git remote add origin git@github.com:<用户名>/n27-sync.git
git push -u origin main
# 清缓存
curl -s "https://purge.jsdelivr.net/gh/<用户名>/n27-sync@main/version.json"
curl -s "https://purge.jsdelivr.net/gh/<用户名>/n27-sync@main/d.json.gz"
# 改 冲刺刷题3.html 第 268 行
#   const SYNC = { repo:'', branch:'main', baseUrl:'' };
# → const SYNC = { repo:'<用户名>/n27-sync', branch:'main', baseUrl:'' };
cd /d/27考研ai产出/政治
python 更新题库.py --rebuild-only
```

---

## 4. 验收标准（必须全绿才算完成）

1. `git push` 成功，`https://github.com/<user>/n27-sync` 能看到 `version.json` + `d.json.gz`
2. `curl https://cdn.jsdelivr.net/gh/<user>/n27-sync@main/version.json` 返回
   `{"version":"2026-11-14","total":1617,"sets":49,"mantra":543,...}`
3. `d.json.gz` 能下载、gunzip 后是合法 JSON，`questions` 有 1617 个键
4. `冲刺刷题3.html` 第 268 行 `SYNC.repo` 已填 `<user>/n27-sync`
5. 本地起 http 服务打开页面，控制台无 `[sync] 检查更新失败`：
   ```bash
   cd /d/27考研ai产出/政治
   python -m http.server 8899 --bind 127.0.0.1
   # 浏览器开 http://127.0.0.1:8899/冲刺刷题3.html
   ```
   验证技巧：`?synctest=<url>` 可以临时覆盖 `syncBase()`（第 395 行），
   用它指向一个假 server 打印请求，可确认逻辑真跑了。
6. 假更新验证（推荐）：把 `version.json` 的 `version` 改成 `2026-11-15` 推上去，
   清缓存，刷新页面 → 顶部应弹出蓝色「题库已更新到 2026-11-15」。验完改回来。

---

## 5. 已知坑（都踩过，别再踩）

| 坑 | 真相 |
|---|---|
| **jsDelivr 缓存 12 小时** | 分支引用（`@main`）缓存 **12h**，tag/commit 才是永久。**每次 push 后必须打 purge 接口**，否则页面拉到的还是旧文件。`?t=时间戳` 对 jsDelivr **无效**（query 不参与缓存 key）。 |
| 分支名 | 页面里 `SYNC.branch='main'`，但 `git init` 默认 `master`。已改名为 `main`。若重建仓库务必 `git branch -M main`。 |
| HTTPS git 被 reset | 本机对 `github.com` 的 git-over-HTTPS 会断，**push 必须走 SSH**；`~/.ssh/config` 已把 `github.com` 指到 `ssh.github.com:443`。API（`api.github.com`）走 HTTPS 没问题。 |
| SSH key 没注册 | 上文已述，`gh_setup.py` 会用 token 自动上传 `/user/keys`。 |
| `.gz` 的 Content-Type | jsDelivr 返回 `application/octet-stream`，页面用 `fetch(...).arrayBuffer()` 读，不要 `.json()`。 |
| 空仓库 push | 空仓库没有 `main`，直接 `git push -u origin main` 即可；仓库加了 README（`auto_init:true`）反而会冲突，**建库必须 auto_init=false**。 |
| 中文乱码 | Windows 控制台 GBK，脚本里 `sys.stdout.reconfigure(encoding='utf-8')`；`gh_auth.py start` 没做这个 reconfigure，所以中文乱码，但**码本身是 ASCII，能看**。 |
| 文件版权 | 见第 7 节。 |

---

## 6. B 计划：不上 GitHub 的三条路

如果用户不想授权、或 GitHub 不可用：

1. **放弃热更新，手动换代**（0 成本，最稳）
   `冲刺模考_离线版.html` 1.08 MB，直接传微信/QQ 给平板，双击即用。
   每次更新题库就重发一次文件。缺点：旧文件不会自动更新。
2. **本机 http + 局域网**：`python -m http.server 8899 --bind 0.0.0.0`，
   平板连同一 WiFi 开 `http://<内网IP>:8899/冲刺模考_离线版.html`。只在家/宿舍有效。
3. **Cloudflare Worker 代理私有库**（要 CF 账号授权）
   私有库 + Worker 持 PAT 代理 `raw.githubusercontent.com`，页面请求 Worker。
   优点：内容不公开；缺点：多一层依赖 + 又一个账号授权。**成本比 GitHub 公开库高。**

---

## 7. 版权红线（每次都要说）

题目来自徐涛 / 腿姐 / 米鹏 / 余峰 / 杨攀 / 苏一的**付费押题卷**，解析来自苍盾平台，
口诀来自评论区用户。**上传公开仓库 = 二次分发。**

- 仓库名**不要**带「政治 / 题库 / 考研 / 冲刺」等字样，建议就用 `n27-sync`
- **不要**写 README 说明内容
- **不要**开 Issues / Wiki（已默认关）
- 用户已被明确告知风险两次，权限归用户；**AI 只执行，不替用户决定公开与否**

### 如果用户选「公开库」但介意明文 → 方案 A：AES 加密后再推（约 20 分钟，推荐折中）

本机 `cryptography 48.0.1` 已装，可直接用。改造点：

**生成端**（`更新题库.py` 的 `build_sync()`，第 160 行）：
```python
import os, gzip, json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
KEY = bytes.fromhex(open("_sync/.aeskey").read().strip())   # 32 字节 = 64 位 hex
nonce = os.urandom(12)
ct = AESGCM(KEY).encrypt(nonce, raw, None)
open("_sync/d.json.bin","wb").write(nonce + ct)             # 12B nonce || 密文
```
`version.json` 里加 `"file":"d.json.bin"`。

**页面端**（`冲刺刷题3.html` 的 `gunzipBuf`，第 303 行附近）：
```js
async function decryptBuf(buf){
  const key = await crypto.subtle.importKey('raw',
    Uint8Array.from(SYNC.key.match(/../g), h=>parseInt(h,16)),
    'AES-GCM', false, ['decrypt']);
  const iv = buf.slice(0,12);
  return await crypto.subtle.decrypt({name:'AES-GCM', iv}, key, buf.slice(12));
}
// checkUpdate 里：
// const buf = await dr.arrayBuffer();
// const plain = SYNC.key ? await decryptBuf(buf) : buf;
// const txt = await gunzipBuf(plain);
```
`SYNC` 常量加 `key:'<64 位 hex>'`。密钥只存在本地 HTML，不公开，CDN 上只有密文。

⚠️ 代价：页面 HTML 一旦被分享出去，密钥跟着泄露。**页面本身同样不能公开分发。**

---

## 8. 文件清单（本次交接产物）

| 文件 | 作用 |
|---|---|
| `_sync/TASK_接力_GH热更新.md` | 本文件 |
| `_sync/gh_auth.py` | Device Flow 授权：`start` / `wait` / `logout` |
| `_sync/gh_setup.py` | 建库 + 传公钥 + push + 清缓存 + 填 SYNC + 重打包 + 验证，一条命令 |
| `_sync/version.json` / `d.json.gz` | 待推送的数据（已 git 提交） |
| `_sync/.ghtoken` | **运行后生成**，token，权限 600，用完 `python gh_auth.py logout` 删 |
| `_sync/.ghdevice.json` | **临时**，授权的中间状态，已过期可删 |

---

## 9. 不要做的事（已发生过 / 极易搞错）

- ❌ 不要重新生成题库数据（`python 更新题库.py` 全流程）——会联网拉评论/判口诀，**消耗号池积分且有风控风险**。这里只需要 `--rebuild-only`。
- ❌ 不要 `git push --force` 到已有仓库（会丢历史）。
- ❌ 不要把 `冲刺刷题3.html` 和离线包传到同一个公开仓库（页面里有密钥/全量数据），只推 `_sync/` 里的两个数据文件。
- ❌ 不要在对话里贴 token，也不要写进本文件。
- ❌ 不要并发批量打号池（与本任务无关，但如果顺手做了别的更新，记得单并发 ≤1–2、间隔 ≥10s）。
- ❌ 不要改 `_sync/` 之外的历史版本文件（`冲刺刷题.html` / `冲刺刷题2.html` 可删，但不属于本任务）。

---

## 10. 交接回执模板（做完后填）

```
仓库       github.com/<user>/n27-sync  (public/private)
push       ✅ <commit sha>
CDN        ✅ version.json 200, total=1617
d.json.gz  ✅ 936 KB → 解压后 3.01 MB, questions=1617
SYNC.repo  ✅ 冲刺刷题3.html:268
离线包     ✅ 冲刺模考_离线版.html 1.08 MB 重新生成
token      已 logout / 保留（删了 _sync/.ghtoken）
遗留       <无 / 说明>
```
