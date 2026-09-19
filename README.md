# Claude 桌面版一键汉化 · Claude-zh-CN

> 给 **Claude Desktop（Windows / MSIX）** 做简体中文汉化，并支持把它接到 **DeepSeek** 等第三方推理网关。
> 作者：**睡醒的夜猫子** · 仓库：<https://github.com/QingYu327/Claude-zh-CN>

[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-0078D4)](#环境要求)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## 它能做什么

| 功能 | 说明 |
|---|---|
| **界面汉化** | 桌面壳 + 前端 i18n + 硬编码文案 + 主聊天视图，四层覆盖，语言包覆盖约 **98%**（28855/29442 键） |
| **一键重建** | 双击入口即可重新解包官方安装包 → 打补丁 → 打包签名 → 安装（约 2~4 分钟） |
| **DeepSeek 接入** | 内置本地中继，把 DeepSeek 接成 Claude 的第三方推理网关，模型选择器里可选 |
| **随时还原** | 一键装回官方原版 / 一键删除第三方网关策略 |

## 快速开始

1. 安装 **Python 3.10+**（勾选 Add to PATH）
2. 双击 **`Claude一键汉化.cmd`**
3. 选 **[4] 一键全装** → 完成后重启 Claude

```text
[1] 汉化 Claude（重建 + 安装）
[2] 配置 DeepSeek 网关（写注册表）
[3] 启动 DeepSeek 中继（127.0.0.1:17871）
[4] 一键全装（1 + 2 + 3）        ← 推荐
[5] 状态检查
[6] 还原官方版（英文）
[7] 还原 DeepSeek（删策略）
```

## 环境要求

| 项 | 要求 |
|---|---|
| 系统 | Windows 10 / 11 x64（Claude Desktop 为 MSIX 包） |
| Claude | 已通过官方安装器正常安装过（`%LOCALAPPDATA%\ClaudeInstaller\cache\*.msix` 会留下基础安装包） |
| Python | 3.10+（脚本仅用标准库） |
| 打包工具 | Windows SDK 的 `MakeAppx.exe` / `signtool.exe`（装 SDK 或 VS 时勾选） |
| 签名证书 | 本机当前用户证书库需有一个 Subject 含 `Anthropic` 的代码签名证书（见下） |

### 首次使用：准备签名证书（只需一次）

MSIX 替换包必须重新签名。应用包发布者含 `Anthropic`，所以证书 Subject 要与之一致：

```powershell
$c = New-SelfSignedCertificate -Type CodeSigningCert `
     -Subject 'CN="Anthropic, PBC", O="Anthropic, PBC", C=US' `
     -CertStoreLocation Cert:\CurrentUser\My
certutil -addstore -f TrustedPeople $c.Thumbprint      # 需管理员；信任该证书
```

> 只影响本机应用包信任，不修改系统根证书链。

## 汉化原理（四层，缺一不可）

| 层 | 位置 | 做法 |
|---|---|---|
| ① 桌面壳 | `app/resources/zh-CN.json` | 语言包（705 键）+ 同时覆盖 `en-US.json` 双保险 |
| ② 前端 i18n | `app/resources/ion-dist/i18n/` | `zh-Hans.json` 与 `zh-CN.json` **双命名**，并删除遮蔽翻译的 overrides |
| ③ 硬编码文案 | `ion-dist/index.html` | 注入 `zh-hans-patch.js`（530 条运行时替换 + MutationObserver） |
| ④ 主聊天视图 | `app.asar` 内 `.vite/build/mainView.js` | preload 里注入运行时替换（约 700 条对照表） |

另外：前端 JS 里的**语言白名单** `Am` 需加入 `zh-Hans` / `zh-CN`，否则协商结果会被丢弃。

### 三个必须知道的坑（都已在脚本里处理）

1. **asar 完整性熔丝**：`claude.exe` 里 `EnableEmbeddedAsarIntegrityValidation` 开着时，改过 `app.asar` 会导致应用**打不开**。管线会自动把该熔丝字节翻成关闭。
2. **语言包必须双命名**：网关（3P）模式下桌面壳协商出的是 `zh-CN`，前端就会去取 `/i18n/zh-CN.json`；只放 `zh-Hans.json` 会 404 → 界面回落英文。
3. **版本号必须递增**：同版本不同内容会被 MSIX 拒绝（`0x80073CFB`）。管线自动取「已装版本 +0.0.0.1」。

## DeepSeek 接入为什么需要本地中继

Claude Desktop 要求网关的**模型列表**与**对话**共用一个 base URL：

```
/v1/models    （模型发现）      /v1/messages  （对话）
```

而 DeepSeek 的模型列表在 `https://api.deepseek.com/v1/models`，
对话端点在 `https://api.deepseek.com/anthropic/v1/messages`
—— 前缀不同，单个 base URL 无法同时满足。

此外应用对**模型名有硬性校验**（必须像 Anthropic 模型），否则日志报
`Gateway /v1/models returned 0 usable models` → 配置被判 `invalid_config`
→ Claude 顶部弹「管理员配置无法使用」，模型选择器为空。

`scripts/deepseek-3p-proxy.py`（监听 `127.0.0.1:17871`）因此做两件事：

1. `/v1/models` 由它自己应答（返回 Anthropic 风格路由名）
2. 其它 `/v1/*` 原样转发到 `https://api.deepseek.com/anthropic/v1/*`，
   并在转发前把路由名改写回 DeepSeek 真名：

| 选择器显示 | 对外路由名 | 实际模型 |
|---|---|---|
| DeepSeek V4 Pro | `claude-sonnet-4-5` | `deepseek-v4-pro` |
| DeepSeek V4 Flash | `claude-haiku-4-5` | `deepseek-v4-flash` |

> 映射可改：同时编辑 `scripts/deepseek_setup.py` 与 `scripts/deepseek-3p-proxy.py` 顶部的 `ALIAS`。

**注意**：
- 中继只监听 127.0.0.1，不对外暴露；不运行中继时 Claude 会请求失败。
- API Key 存放在 `.workbuddy/deepseek.key`（已 gitignore），请勿外传。
- Claude 启动时会对网关做一次健康探测（少量 token 消耗），属正常行为。

### 手动配置（可选，不用工具箱时）

菜单 `[2]` 会原生写入注册表；若想手工写，把下面内容存成 `.reg`（编码选 **UTF-16 LE 或 ANSI**，
不要用 UTF-8——regedit 读不了），替换 Key 后导入：

```reg
Windows Registry Editor Version 5.00

[HKEY_CURRENT_USER\SOFTWARE\Policies\Claude]
"inferenceProvider"="gateway"
"inferenceGatewayBaseUrl"="http://127.0.0.1:17871"
"inferenceGatewayApiKey"="PASTE-YOUR-DEEPSEEK-API-KEY-HERE"
"inferenceGatewayAuthScheme"="bearer"
"modelDiscoveryEnabled"="true"
"inferenceModels"="[{\"name\":\"claude-sonnet-4-5\",\"labelOverride\":\"DeepSeek V4 Pro\"},{\"name\":\"claude-haiku-4-5\",\"labelOverride\":\"DeepSeek V4 Flash\"}]"
```

还原：删除 `HKCU\SOFTWARE\Policies\Claude` 即可（工具箱 `[7]`）。

## 目录结构

```
Claude一键汉化/
├── Claude一键汉化.cmd        主入口（工具箱菜单）
├── 启动DeepSeek代理.cmd      快捷方式：启动本地中继
├── 还原官方版.cmd            快捷方式：装回官方英文版
├── scripts/
│   ├── claude-toolbox.py     工具箱（菜单与流程编排）
│   ├── build_and_install.py  汉化主管线（解包→关熔丝→注入→打包→签名→安装）
│   ├── patch_asar.py         自定义 asar 重打包器（含完整性校验）
│   ├── patch_frontend.py     前端四层补丁（语言包/白名单/DOM 脚本）
│   ├── claude-zh-preload.js  主视图运行时汉化脚本（对照表）
│   ├── deepseek_setup.py     DeepSeek 3P 策略（apply / remove / status）
│   ├── deepseek-3p-proxy.py  本地中继
│   └── translate_i18n.py     i18n 缺词批量机翻（可选，维护用）
├── 语言包/                   中文语言包与对照表（payload）
└── 一键配置/                 签名证书 + 手动配置说明（不含密钥）
```

运行数据（断点、日志、密钥）落在 `.workbuddy/`，已被 `.gitignore` 排除。

## 应用升级后

Claude 自动/商店更新会换新版本目录，**补丁全部丢失**（应用本身仍干净可用）。
重新双击入口 → `[1]`（或 `[4]`）即可。若新版本新增了词条，可先跑 `translate_i18n.py`
补译再打包（默认走免费模型，切换通道前请确认是否计费）。

## 常见问题

| 现象 | 原因 / 处理 |
|---|---|
| 双击后提示找不到 makeappx/signtool | 未安装 Windows SDK |
| 安装报 `0x800B0109` | 签名证书未装入「本地计算机 → 受信任的人」 |
| 安装报 `0x80073CFB` | 包版本未递增（脚本已自动处理） |
| 应用打不开 / 秒退 | asar 完整性熔丝未关闭（脚本已自动处理，勿手工改 exe） |
| 界面仍是英文 | 语言包命名不全（需 zh-Hans + zh-CN 双命名）或补丁未生效，跑 `[5] 状态检查` 看证据 |
| 模型选择器为空 / 提示管理员配置不可用 | 中继未启动，或模型名不是 Anthropic 风格 |
| Claude 提示「不可用你所在地区」 | 账号/出口 IP 的区域限制，与本工具无关 |

## 免责声明

- 本项目仅修改**本机安装包副本**（官方安装器缓存）并重新签名安装，不篡改官方下载源。
- 汉化为**界面文本替换**，不改动模型输出与账号数据。
- 请自行确认所在地区/账号的相关使用条款；使用第三方推理网关产生的费用与合规责任由使用者承担。

## License

MIT © 睡醒的夜猫子（QingYu327）
