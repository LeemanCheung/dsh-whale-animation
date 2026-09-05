# dsh-whale-animation

DeepSeek Harness Web 鲸鱼插件现在只保留两套原始动画，不再包含任何新增美术状态。

v0.7.1 已适配 DSH 0.1.2-rc.1：移除了新版已不再提供、插件本身也未使用的旧 client-runtime 依赖。后台标签页暂停页面扫描，恢复可见时立即更新。Windows 与 Linux 构建现在使用相同的 LF 输出，并由双平台 CI 检查。

| Refined Dive | Classic |
|---|---|
| <img src="assets/whale-dive.webp" alt="Refined Dive" width="180" /> | <img src="assets/whale-classic.webp" alt="Classic" width="180" /> |

## 范围

- **Refined Dive**：来自提交 `65e1205d1fbf4b01997e6dfc099103b0f9717e37`。
- **Classic**：来自首发提交 `95b06e3f0e6ea817d25858eb29f7064a233b3c65`。
- 两个 WebP 和两个减少动态效果 PNG 均校验 Git Blob SHA-1、SHA-256、帧数和时序。
- 按 `dive → classic` 播放完整循环：Dive 1.980 秒，Classic 10.506 秒。状态文字要求切换时，也先播完当前循环。
- 保留深色主题、84/72/60 px 响应式尺寸、减少动态效果、离线内嵌与完整生命周期清理。

v0.7.0 已删除：Spout、Sonar、Tool Run、Stream、Calm、Retry、全部生成美术源图及其构建链。

## 安装

```powershell
dsh plugin --profile web add github:LeemanCheung/dsh-whale-animation
```

升级后请重启 DSH，或对 DSH Web 强制刷新。

## 验证

```powershell
npm run verify
npm run check:browser
npm pack --dry-run
```

`npm run verify` 只重建 `assets/manifest.json` 与 `lib/client.js`，绝不会重新生成或重新编码两套原始动画。

安装了 Python Playwright 和 Chrome 的开发机还可运行 `npm run check:playback`，实测完整轮换时长、后台恢复、主题和减少动态效果。详细记录见 [2026-09-05 兼容与播放验收](docs/compatibility-20260905.md)。

## 运行时合约

| 项目 | Refined Dive | Classic |
|---|---:|---:|
| 画布 | 352 × 352 | 184 × 184 |
| 帧数 | 60 | 618 |
| 单帧时长 | 33 ms | 17 ms |
| 循环时长 | 1.980 秒 | 10.506 秒 |
| 来源 | 逐字节保留 | 逐字节保留 |

本项目独立开发，与 DeepSeek 不存在隶属或官方背书关系。详见 [NOTICE.md](NOTICE.md)。

[English](README.md) · 简体中文
