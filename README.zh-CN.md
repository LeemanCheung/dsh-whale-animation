# dsh-whale-animation

DeepSeek Harness Web 鲸鱼插件现在只保留两套原始动画，不再包含任何新增美术状态。

| Refined Dive | Classic |
|---|---|
| <img src="assets/whale-dive.webp" alt="Refined Dive" width="180" /> | <img src="assets/whale-classic.webp" alt="Classic" width="180" /> |

## 范围

- **Refined Dive**：来自提交 `65e1205d1fbf4b01997e6dfc099103b0f9717e37`。
- **Classic**：来自首发提交 `95b06e3f0e6ea817d25858eb29f7064a233b3c65`。
- 两个 WebP 和两个减少动态效果 PNG 均校验 Git Blob SHA-1、SHA-256、帧数和时序。
- 动画导演每 11 秒按 `dive → classic` 轮换；“经典/原版”显式选择 Classic，“思考/推理/分析”显式选择 Dive。
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
