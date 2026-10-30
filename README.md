# DSX-01 *ISV Kairos Horizon* — Deep Space Exploration Ship · 深空探索船 3D 建模工作台

A complete, original, **procedurally generated** 3D modelling project for a
deep-space exploration vessel: seven glTF-binary assets, a native Blender
original, an offline Three.js workbench, a software preview renderer, a test
suite and full design documentation. Everything regenerates from source with
only NumPy (Blender and the vendored Three.js are the only optional/external
pieces).

一套完整、原创、**全程序化生成**的深空探索船 3D 建模项目：七个 glTF 二进制模型、
Blender 原始模型、离线 Three.js 交互查看器、软件预览渲染器、测试套件与完整设计文档。
全部资产均可仅依赖 NumPy 从源码重新生成（Blender 与内置 Three.js 为可选/外部组件）。

## What's inside · 内容一览

| Path | Content · 内容 |
|---|---|
| `models/glb/` | 7 glTF 2.0 binary assets + `manifest.json` · 七个 GLB 模型与清单 |
| `models/blend/` | Native Blender original (full ship) · Blender 原始模型 |
| `geometry/` | NumPy mesh kernel + from-scratch glTF writer/reader · 几何内核与 glTF 读写器 |
| `shipspec/` | Design spec + procedural builders (hull, decks, interiors, propulsion) · 设计规范与程序化建模器 |
| `blender/` | Headless Blender bridge → `.blend` / cross-check `.glb` · Blender 桥接脚本 |
| `viewer/` | Offline Three.js workbench (vendored three r160) · 离线 Three.js 查看器 |
| `scripts/` | build / render / test / validate / serve / publish helpers · 各类工具脚本 |
| `assets/preview/` | 14 software-rendered stills · 14 张软件渲染预览图 |
| `docs/` | design spec, modelling guide, asset contract, viewer guide, acceptance criteria · 设计/建模/资产/查看器/验收文档 |
| `tests/`, `reports/` | dependency-free test suite + validation & acceptance reports · 测试与验收报告 |

## The vessel · 飞船概览

- **ISV Kairos Horizon (DSX-01)**, Kairos-class, 492 m overall, 84 crew, 12-year
  outer-system survey mission.
- Four decks (Command / Operations / Habitat / Engineering), eleven isolation
  systems, centrifuge gravity ring, four thermal radiator wings, spine truss
  with five propellant tanks, three fusion torch drives, 15 m high-gain array.
- 262 056 triangles across the seven assets; 35-material PBR library.

See `docs/design-specification.md` for the full frozen dimension set.

## Quick start · 快速开始

```bash
# 1. Regenerate every model (NumPy only) · 重新生成全部模型
python3 scripts/build_models.py --report reports/model-validation.json

# 2. Run the test suite · 运行测试
python3 scripts/run_tests.py

# 3. Open the interactive viewer · 打开交互查看器
./scripts/serve.sh            # then open http://localhost:8000/viewer/

# Optional · 可选
./blender/build_all.sh        # native .blend originals
python3 scripts/render_preview.py --all   # preview stills
```

## Repository layout & workflow · 仓库与工作流

- All modelling source lives at the repository root; there is no separate
  scratch project.
- Development happens on `feat/spaceship-3d-workbench`; `main` keeps only the
  initial skeleton. Each milestone is its own commit with an English message.
- `scripts/publish.sh <owner>` pushes the branch and prints ready-to-use PR
  text (see `docs/PULL_REQUEST.md`).

## Validation · 校验

- `scripts/run_tests.py` — 33 dependency-free tests (kernel, shipped assets,
  spec coherence).
- `reports/model-validation.json` — per-asset counts, bounds and GLB
  round-trip parity.
- `reports/blender-validation.json` — Blender vs Python exporter parity
  (triangle/mesh counts match for all seven assets).
- `reports/acceptance-report.md` — measured acceptance results.

## Licence & provenance · 版权与来源

Original design and code. Three.js (MIT) is vendored under `viewer/vendor/`
unmodified. No third-party model assets are used; every triangle is generated
by this repository's own kernel.
