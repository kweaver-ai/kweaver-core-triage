# kweaver-core-triage

Weekly scan of open issues in [`kweaver-ai/kweaver-core`](https://github.com/kweaver-ai/kweaver-core), producing categorization, clustering, severity, and response-gap reports.

[中文版 →](./README.zh.md)

## Goals

- Suggest labels for each issue (`area/*` + `type/*` + `severity/*`)
- Detect clusters of likely-duplicate or related issues
- Surface high-severity bugs with zero response
- Flag stale issues

**Does not auto-close issues** — every close decision requires human review.

## Usage

Run weekly on your local machine:

```bash
cd ~/dev/github/kweaver-core-triage
make weekly        # fetch + generate report (no git changes)
# ... eyeball reports/{YYYY-WW}.md ...
make publish       # commit + push + post digest issue to kweaver-core
```

## Requirements

- `gh` CLI (logged in, with read/write access to `kweaver-core`)
- `python3` (3.9+)
- `jq` (only for the post-fetch count line)

## Output

```
reports/
├── 2026-W17.md     # one per week, kept in git permanently
├── 2026-W18.md
└── ...
```

## Design Rationale

Inspired by [`openclaw/clawsweeper`](https://github.com/openclaw/clawsweeper), but adapted to kweaver-core's actual situation:

| Dimension | ClawSweeper (openclaw) | kweaver-core-triage |
|-----------|------------------------|---------------------|
| Scale | 11k+ open issues | ~50 open issues |
| Source | Mostly public community | 100% internal team |
| Primary task | Auto-close stale/spam | Auto-categorize + find duplicates + response reminders |
| Concurrency | 40 shards + checkpoint | Single script, runs in seconds |
| Auto-close | Enabled by default | **Disabled** — suggestions only |
| LLM calls | Codex per issue | None by default; cluster verification optional manual step |

## Roadmap

- **v1 (current)**: pure rules — fast, zero cost, covers ~80% of value
- **v2 candidate**: LLM-based cluster verification (true-duplicate vs false-positive)
- **v3 candidate**: automated `implemented_on_main` check (grep main to see if a bug was already fixed)
- **GitHub Actions migration**: when running locally becomes a chore

## History

See [`reports/`](./reports/).
