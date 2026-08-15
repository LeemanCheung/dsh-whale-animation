<p align="center">
  <img src="docs/hero.png" alt="dsh-whale-animation — DeepSeek Harness 无缝鲸鱼深潜状态动画" width="100%" />
</p>

<p align="center">
  <a href="https://awesome.re"><img src="https://awesome.re/badge.svg" alt="Awesome" /></a>
  <a href="https://awesome-dsh-plugin.com"><img src="https://awesome-dsh-plugin.com/badge.svg" alt="Awesome DSH Plugin" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-2563eb.svg" alt="MIT license" /></a>
  <img src="https://img.shields.io/badge/DSH-Web-0f172a.svg" alt="DeepSeek Harness Web" />
  <img src="https://img.shields.io/badge/runtime-offline-0f766e.svg" alt="运行时离线" />
  <img src="https://img.shields.io/badge/motion-reduced--motion%20ready-7c3aed.svg" alt="支持减少动态效果" />
</p>

<p align="center">
  <strong>在 DeepSeek Harness 状态文字旁显示持久化黑色鲸鱼深潜动画。</strong><br />
  无缝闭环、运行时零网络请求，并为减少动态效果用户提供静态回退。
</p>

<p align="center">
  <a href="README.md">English</a> · 简体中文
</p>

## 动画预览

<p align="center">
  <img src="docs/preview.webp" alt="鲸鱼在 Deep diving 状态文字旁跃起和深潜的动画预览" width="900" />
</p>

> 预览完整保留 **60 张 image-2 原生画面**及其正式播放节奏；不会额外插入过渡帧。v0.3.0 统一了紧凑头型、上扬吻部、眼睛、嘴部和短尾鳍等身份特征，同时保持躯干与尾部逐帧弯曲。

## 截图

<table>
  <tr>
    <td width="33%"><img src="docs/screenshots/launch.png" alt="鲸鱼跃出水面的动作截图" /></td>
    <td width="33%"><img src="docs/screenshots/apex.png" alt="鲸鱼在跃起顶点卷曲身体的动作截图" /></td>
    <td width="33%"><img src="docs/screenshots/deep-dive.png" alt="鲸鱼重新潜入水下的动作截图" /></td>
  </tr>
  <tr>
    <td align="center"><strong>01 — 破水跃起</strong></td>
    <td align="center"><strong>02 — 跃起顶点</strong></td>
    <td align="center"><strong>03 — 入水深潜</strong></td>
  </tr>
</table>

所有截图均直接从仓库中的 `assets/whale-dive.webp` 渲染，因此展示的是用户实际安装后收到的动画帧，而不是单独绘制的概念图。

## 特性

| | 特性 | 说明 |
|---|---|---|
| 🌊 | **传播式水面** | 破水和入水会产生向外传播、回弹并逐步衰减的波峰，水线不再静止。 |
| 🐋 | **稳定的原创鲸鱼身份** | 紧凑头型、上扬吻部、眼神和短尾鳍保持一致，躯干则按头部带动、尾部滞后的规律弯曲。 |
| 📦 | **自包含 Bundle** | 动态 WebP 与静态 PNG 已嵌入客户端，无需运行时 URL 或原始帧目录。 |
| ♿ | **支持减少动态效果** | 检测到 `prefers-reduced-motion` 时自动切换为静态 PNG。 |
| 🎯 | **严格的纯视觉范围** | 只装饰 Web 回合状态区域；没有设置项、模型工具、持久化存储、工作区访问、网络请求或用户内容处理。 |
| ♻️ | **生命周期可清理** | 插件拥有的样式绑定到 Cordis Client fiber，停止或卸载时会被完整移除。 |
| 🔌 | **持久化 DSH 插件** | `dsh.bundle` manifest 与 `cordis.patch.yml` 会在 Web profile 中自动挂载客户端。 |

## 安装

从 GitHub 直接安装到 DSH Web profile：

```powershell
dsh plugin --profile web add github:LeemanCheung/dsh-whale-animation
```

安装后请硬刷新 DSH Web 页面。如果当前 profile 已缓存客户端 Bundle，请重启 DSH。

如需固定当前版本，可使用 `#v0.3.0`：

```powershell
dsh plugin --profile web add github:LeemanCheung/dsh-whale-animation#v0.3.0
```

### 卸载

```powershell
dsh plugin --profile web remove dsh-whale-animation
```

## 动画规格

| 属性 | 数值 |
|---|---:|
| 画布 | 352 × 352 px（CSS 显示为 84 × 84 px） |
| 原始帧数 | 60 张唯一原生画面 |
| 单帧时长 | 33 ms |
| 循环时长 | 1.980 秒 |
| 编码 | 带 Alpha 的无损动画 WebP |
| 减少动态效果资源 | 透明 PNG |
| 运行时资源请求 | 无 |

项目会对最终编码后的 WebP 进行实际解码验证，而不只是检查源帧。成品包含 60 张唯一画面，每帧 33 ms；当前闭环接缝的 Alpha 差异为 `0.00306`，质心步长为 `0.27 px`。鲸鱼主体面积全程不低于中位数的 98.7%，入水和深潜阶段都不会消失。

水面使用闭环行进波与两组阻尼波包：完整循环包含 59 个连续变化的独立水面轮廓，末帧与首帧精确闭合；最大峰谷差为 `23.45 px`，相邻水面轮廓的最大平均变化为 `1.90 px`，因此既能看见波动，也不会闪跳。

## 工作原理

```mermaid
flowchart LR
  A[动画 WebP + 静态 PNG] --> B[scripts/build-client.mjs]
  B --> C[嵌入式 data URL]
  C --> D[DSH 客户端 Bundle]
  D --> E[状态文字 ::after 元素]
  F[prefers-reduced-motion] --> D
```

客户端向 DSH 状态文字元素添加一个归属于插件生命周期的样式表。两个资源都以内嵌 data URL 形式写入 `lib/client.js`，因此安装后运行时不依赖仓库检出目录。

## 开发

要求：**Node.js 20+**。只有重新生成 README 配图时才需要 Python 与 Pillow。

```powershell
node scripts/build-client.mjs
node scripts/check.mjs
python scripts/build-readme-assets.py
python scripts/check-readme-assets.py
```

### 仓库结构

```text
assets/
  whale-dive.webp        完整无损动画
  whale-static.png       减少动态效果静态回退
docs/
  hero.png               README 头图
  preview.webp           README 轻量动画预览
  screenshots/           破水、顶点与深潜动作截图
lib/
  client.js              预构建 DSH 浏览器客户端
scripts/
  build-client.mjs       将源资源嵌入客户端
  build-readme-assets.py 使用真实动画重新生成仓库配图
  check-readme-assets.py 验证配图时序、尺寸与 README 链接
  check.mjs              验证注册、生命周期与嵌入资源
cordis.patch.yml         持久化 DSH Bundle 组合补丁
```

`lib/client.js` 会有意提交到仓库，确保 GitHub 安装无需执行构建或下载外部资源。

## 兼容性

- 目标平台为 **DeepSeek Harness Web UI**。
- 需要兼容 `@deepseek-ai/dsh-client-runtime ^0.1.0-rc.6` 的 DSH 版本。
- 当前依赖 DSH 状态文字的 CSS 类名模式；未来 DSH Shell 若重新设计，可能需要更新选择器。

## 声明

本项目为独立项目，与 DeepSeek 无关联，也未获得其背书。动画是为呼应 DeepSeek Harness 鲸鱼主题状态体验而制作的原创 UI 插图。视觉设计与商标说明请参阅 [NOTICE.md](NOTICE.md)。

## 许可证

以 [MIT License](LICENSE) 发布。
