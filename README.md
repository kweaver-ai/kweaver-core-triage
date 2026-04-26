# kweaver-core-triage

每周扫描 [`kweaver-ai/kweaver-core`](https://github.com/kweaver-ai/kweaver-core) 开放 issue，输出分类、关联、严重度、响应缺口报告。

## 目标

- 给 issue 打标签（area/* + type/* + severity/*）
- 找出疑似重复或关联的 issue 簇
- 暴露高严重 + 零响应的 bug
- 标识 stale issue

**不自动关闭 issue**——所有关闭决策需人工审。

## 用法

每周本机跑一次：

```bash
cd ~/dev/github/kweaver-core-triage
make weekly        # 拉数据 + 生成报告（不动 git）
# ... 肉眼扫一遍 reports/{YYYY-WW}.md ...
make publish       # commit + push + 发 digest issue 到 kweaver-core
```

## 依赖

- `gh` CLI（已登录、有 kweaver-core 读写权限）
- `python3` (3.9+)
- `jq`（仅用于 fetch 后计数提示）

## 输出

```
reports/
├── 2026-W17.md     # 每周一份，git 永久保存
├── 2026-W18.md
└── ...
```

## 设计依据

参考 [`openclaw/clawsweeper`](https://github.com/openclaw/clawsweeper) 的整体思路，但根据 kweaver-core 的实际情况做了调整：

| 维度 | ClawSweeper（openclaw） | kweaver-core-triage |
|------|------------------------|---------------------|
| 规模 | 11k+ open issues | 51 open issues |
| 来源 | 公开社区为主 | 内部团队 100% |
| 主要任务 | 自动关闭垃圾/stale | 自动分类 + 找重复 + 响应提醒 |
| 并发架构 | 40 shard + checkpoint | 单脚本，几秒跑完 |
| 自动关闭 | 默认开 | **关闭**，仅给建议 |
| LLM 调用 | 每 issue 一次 Codex | 默认无 LLM；簇验证可手动调 |

## 后续可能的演进

- 当前 v1：纯规则，跑得快、零成本、足够覆盖 80% 场景
- v2 候选：簇验证用 LLM（验证"真重复 vs 误判"）
- v3 候选：implemented_on_main 自动检查（grep main 代码看 bug 是否已修）
- 迁 GitHub Actions：当本机跑变成负担时再做

## 历史报告

见 [`reports/`](./reports/) 目录。
