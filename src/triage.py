#!/usr/bin/env python3
"""kweaver-core-triage rule-based weekly triage v1.

Input : /tmp/kweaver-issues.json (produced by Makefile via gh CLI)
Output: reports/{YYYY-WW}.md
"""
import json, re, datetime, os
from collections import Counter
from difflib import SequenceMatcher

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT = '/tmp/kweaver-issues.json'

with open(INPUT) as f:
    issues = json.load(f)

now = datetime.datetime.now(datetime.timezone.utc)

# ---------- module whitelist ----------
MODULE_ALIASES = {
    'vega': ['vega'],
    'bkn': ['bkn'],
    'sandbox': ['sandbox'],
    'deploy': ['deploy', 'oss-gateway / deploy', 'oss-gateway/deploy'],
    'context-loader': ['context-loader', 'contextloader'],
    'model-factory': ['model-factory', 'infra/model-factory', 'modelfactory'],
    'model-management': ['model-management', 'modelmanagement'],
    'decision-agent': ['decision-agent', 'decision agent', 'decisionagent'],
    'execution-factory': ['execution-factory', 'executionfactory'],
    'core': ['core', 'kweaver core', 'kweaver-core'],
    'trace-ai': ['trace-ai', 'traceai'],
    'infra': ['infra'],
    'studio': ['studio'],
    'dataflow': ['dataflow'],
    'agent-executer': ['agent-executer', 'agentexecuter'],
}
ALIAS_TO_CANON = {a.lower(): canon for canon, aliases in MODULE_ALIASES.items() for a in aliases}
NON_MODULE_TOKENS = {'bug', 'fix', 'feat', 'feature', 'chore', 'docs', 'test'}

PREFIX_RE = re.compile(r'^[【\[]([^】\]]+)[】\]]')

def parse_module(title):
    m = PREFIX_RE.match(title)
    if not m: return None
    raw = m.group(1).strip()
    raw_l = raw.lower()
    if raw_l in ALIAS_TO_CANON: return ALIAS_TO_CANON[raw_l]
    for p in re.split(r'[\s/,]+', raw_l):
        if p in ALIAS_TO_CANON: return ALIAS_TO_CANON[p]
    if raw_l in NON_MODULE_TOKENS: return None
    if not raw.isascii(): return None
    return f"_unknown:{raw_l}"

def detect_type(issue):
    existing = [l['name'] for l in issue['labels']]
    for t in ('bug','feature','enhancement'):
        if t in existing: return t
    body = issue['body'].lower()
    title = issue['title'].lower()
    pref = PREFIX_RE.match(issue['title'])
    pref_l = pref.group(1).lower() if pref else ''
    if pref_l == 'bug' or 'fix:' in title or 'fix(' in title: return 'bug'
    if 'feat:' in title or 'feat(' in title: return 'feature'
    if any(k in title or k in body for k in ['复现','报错','500','白屏','undefined','panic','crash','静默失败','沉默失败']):
        return 'bug'
    if any(k in title for k in ['支持','新增','增强','优化']):
        return 'enhancement'
    return None

SEV_HIGH = ['白屏','crash','panic','无法启动','服务不可用','静默','沉默','data loss','丢失','安全','泄漏','permission','authentication','必然','所有','全部','都会']
SEV_MED = ['500','404','报错','timeout','超时','卡住','失败']

def detect_severity(issue):
    if detect_type(issue) != 'bug': return None
    text = (issue['title'] + ' ' + issue['body']).lower()
    if any(k in text for k in SEV_HIGH): return 'high'
    if any(k in text for k in SEV_MED): return 'medium'
    return 'low'

for i in issues:
    upd = datetime.datetime.fromisoformat(i['updatedAt'].replace('Z','+00:00'))
    crt = datetime.datetime.fromisoformat(i['createdAt'].replace('Z','+00:00'))
    i['_age_upd'] = (now - upd).days
    i['_age_crt'] = (now - crt).days
    i['_module'] = parse_module(i['title'])
    i['_type'] = detect_type(i)
    i['_severity'] = detect_severity(i)
    i['_existing_labels'] = [l['name'] for l in i['labels']]

def normalize(s):
    s = re.sub(r'^[【\[][^】\]]+[】\]]\s*','',s)
    s = re.sub(r'[^\w一-鿿]+',' ', s.lower())
    return s.strip()

def is_known_module(m):
    return m and not m.startswith('_unknown:')

clusters = []
seen = set()
for i, a in enumerate(issues):
    if a['number'] in seen: continue
    group = [a]
    na = normalize(a['title'])
    for b in issues[i+1:]:
        if b['number'] in seen: continue
        nb = normalize(b['title'])
        ratio = SequenceMatcher(None, na, nb).ratio()
        same_module = is_known_module(a['_module']) and a['_module'] == b['_module']
        same_author = a['author']['login'] == b['author']['login']
        if ratio > 0.55 or (same_module and same_author and ratio > 0.30):
            group.append(b)
    if len(group) > 1:
        clusters.append(group)
        for g in group: seen.add(g['number'])

for c in clusters:
    mods = set(g['_module'] for g in c if is_known_module(g['_module']))
    cm = {'cross_module': len(mods) > 1, 'modules': sorted(mods)}
    for g in c: g['_cluster_meta'] = cm

# ---------- render ----------
out = []
out.append(f"# 📊 kweaver-core Triage Report — {now.strftime('%Y-W%V')} ({now.date()})\n")
out.append(f"_Rule-based v1 (whitelist modules + heuristics). Scanned {len(issues)} open issues._\n")

zero_comment = [i for i in issues if len(i['comments'])==0]
stale = sorted([i for i in issues if i['_age_upd'] >= 60], key=lambda i: -i['_age_upd'])
high_sev = [i for i in issues if i['_severity']=='high']
unlabeled = [i for i in issues if not i['_existing_labels']]
unknown_module = [i for i in issues if i['_module'] and i['_module'].startswith('_unknown:')]
no_module = [i for i in issues if not i['_module']]

out.append("## 概览\n")
out.append(f"- 开放 issue: **{len(issues)}**")
out.append(f"- 本周新建（≤7d）: **{sum(1 for i in issues if i['_age_crt']<=7)}**")
out.append(f"- 零评论: **{len(zero_comment)}** ({len(zero_comment)*100//len(issues)}%)")
out.append(f"- 无标签: **{len(unlabeled)}** ({len(unlabeled)*100//len(issues)}%)")
out.append(f"- Stale (>60d): **{len(stale)}**")
out.append(f"- 高严重 bug: **{len(high_sev)}**")
out.append(f"- 关联/重复簇: **{len(clusters)}** 簇 / 涉及 {sum(len(c) for c in clusters)} 项")
out.append(f"- 未识别模块前缀: **{len(unknown_module)}** · 无前缀: **{len(no_module)}**\n")

mod_count = Counter(i['_module'] for i in issues if is_known_module(i['_module']))
out.append("### 模块分布（已知）\n")
out.append("| 模块 | 数量 |")
out.append("|------|------|")
for m, c in mod_count.most_common():
    out.append(f"| `area/{m}` | {c} |")
out.append("")

if unknown_module:
    out.append("### ⚠️ 未识别的模块前缀（需扩白名单）\n")
    for i in unknown_module:
        raw = i['_module'].split(':',1)[1]
        out.append(f"- #{i['number']}: `{raw}` — {i['title']}")
    out.append("")

if no_module:
    out.append("### 🚫 无模块前缀\n")
    for i in no_module:
        out.append(f"- #{i['number']} @{i['author']['login']}: {i['title']}")
    out.append("")

type_count = Counter(i['_type'] for i in issues)
out.append("### 类型分布\n")
out.append("| 类型 | 数量 |")
out.append("|------|------|")
for t, c in type_count.most_common():
    out.append(f"| {t or '_未识别_'} | {c} |")
out.append("")

high_zero = [i for i in high_sev if len(i['comments'])==0]
out.append(f"## 🚨 高严重 + 零响应 — {len(high_zero)} 项\n")
for i in sorted(high_zero, key=lambda x: -x['_age_crt']):
    mod = f"`area/{i['_module']}`" if is_known_module(i['_module']) else ''
    out.append(f"- **#{i['number']}** ({i['_age_crt']}d) {mod} @{i['author']['login']}: {i['title']}")
out.append("")

out.append(f"## ⏰ Stale (>60d) — {len(stale)} 项\n")
for i in stale:
    state = "**零评论**" if len(i['comments'])==0 else f"{len(i['comments'])} comments"
    out.append(f"- **#{i['number']}** ({i['_age_upd']}d 无动) {state} @{i['author']['login']}: {i['title']}")
out.append("")

out.append(f"## 🔗 关联/重复簇 — {len(clusters)} 簇\n")
for idx, group in enumerate(clusters, 1):
    cm = group[0]['_cluster_meta']
    tag = '⚠️ 跨模块（同主题）' if cm['cross_module'] else f"`{cm['modules'][0] if cm['modules'] else 'no-module'}`"
    out.append(f"### Cluster {idx} — {tag}\n")
    for g in group:
        mod_tag = f"[{g['_module']}]" if is_known_module(g['_module']) else ''
        out.append(f"  - #{g['number']} {mod_tag} @{g['author']['login']}: {g['title']}")
    out.append("")

out.append("## 📌 自动标签建议（全量）\n")
out.append("| # | 现有 | 建议新增 | 标题 |")
out.append("|---|------|---------|------|")
for i in sorted(issues, key=lambda x: -x['number']):
    suggested = []
    if is_known_module(i['_module']): suggested.append(f"area/{i['_module']}")
    if i['_type'] and i['_type'] not in i['_existing_labels']: suggested.append(f"type/{i['_type']}")
    if i['_severity']: suggested.append(f"severity/{i['_severity']}")
    if not suggested: continue
    existing = ','.join(i['_existing_labels']) or '-'
    title = i['title'][:60].replace('|','\\|')
    out.append(f"| #{i['number']} | {existing} | {', '.join(suggested)} | {title} |")
out.append("")

backlog = sorted([i for i in zero_comment if i['_severity'] in ('high','medium')], key=lambda x: (x['_severity']!='high', -x['_age_crt']))
out.append(f"## 📥 响应缺口 — 零评论 + 中高严重 bug ({len(backlog)} 项)\n")
for i in backlog:
    out.append(f"- [{i['_severity']}] **#{i['number']}** ({i['_age_crt']}d) @{i['author']['login']}: {i['title']}")
out.append("")

out.append("## ✂️ 建议关闭\n")
out.append("_规则版无法判断，需人工或 LLM 验证（参考 W17 报告中的「LLM 增量发现」章节）_\n")

out.append("---")
out.append(f"🤖 _kweaver-core-triage v1 · {now.isoformat()}_")

report = '\n'.join(out)
report_dir = os.path.join(ROOT, 'reports')
os.makedirs(report_dir, exist_ok=True)
report_path = os.path.join(report_dir, f"{now.strftime('%Y-W%V')}.md")
with open(report_path,'w') as f: f.write(report)
print(f"✅ wrote {report_path}")
print(f"   {len(report.splitlines())} lines, {len(report)} chars")
