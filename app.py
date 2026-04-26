#!/usr/bin/env python3
"""Spring and Autumn Zuo Zhuan Web Query System - Flask Application"""

import json
import os
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)
DATA_DIR = os.path.dirname(os.path.abspath(__file__))

# Load data
with open(os.path.join(DATA_DIR, 'zuozhuan_data.json'), 'r', encoding='utf-8') as f:
    DATA = json.load(f)

RECORDS = DATA['records']
DUKES = DATA['dukes']
YEARS = DATA['years']
STATE_INDEX = DATA['state_index']
STATE_LIST = DATA['state_list']

# Load person aliases
ALIASES = {}
ALIAS_LOOKUP = {}  # reverse: any name -> canonical name
_alias_path = os.path.join(DATA_DIR, 'person_aliases.json')
if os.path.exists(_alias_path):
    with open(_alias_path, 'r', encoding='utf-8') as f:
        _raw_aliases = json.load(f)
    for canonical, alias_list in _raw_aliases.items():
        all_names = set(alias_list)
        all_names.add(canonical)
        for n in all_names:
            if n not in ALIAS_LOOKUP:
                ALIAS_LOOKUP[n] = canonical
        # Store full group
        ALIASES[canonical] = sorted(all_names)


def find_alias_groups(name):
    """Find all alias groups that match the given name (exact or substring)."""
    matched_groups = []
    seen_keys = set()
    # 1. Exact match
    canonical = ALIAS_LOOKUP.get(name)
    if canonical and canonical in ALIASES:
        key = '|'.join(sorted(ALIASES[canonical]))
        if key not in seen_keys:
            seen_keys.add(key)
            matched_groups.append(ALIASES[canonical])
    # 2. Substring match: name appears in any alias, or any alias contains name
    #    Skip single-char aliases to avoid false matches (e.g. '仲' matching 管仲)
    for canonical_name, group in ALIASES.items():
        for alias in group:
            if len(alias) < 2 and len(name) >= 2:
                continue
            if name in alias or (len(name) >= 2 and alias in name):
                key = '|'.join(sorted(group))
                if key not in seen_keys:
                    seen_keys.add(key)
                    matched_groups.append(group)
                break
    # If no match found, just search the name itself
    if not matched_groups:
        return [[name]]
    return matched_groups


def search_by_year(duke_name, year_num):
    """Search records by duke and year number."""
    results = []
    for r in RECORDS:
        if r['duke'] == duke_name and r['year_num'] == year_num:
            results.append(r)
    return results


def search_by_person(name):
    """Search records containing a person's name (including all aliases)."""
    groups = find_alias_groups(name)
    # Merge all names from all matched groups
    all_names = []
    seen = set()
    for group in groups:
        for n in group:
            if n not in seen:
                seen.add(n)
                all_names.append(n)
    results = []
    for r in RECORDS:
        for n in all_names:
            if n in r['text']:
                results.append(r)
                break  # Don't add same record twice
    return results, all_names


def search_by_state(state_name):
    """Search records mentioning a state."""
    results = []
    for r in RECORDS:
        if state_name in r['text']:
            results.append(r)
    return results


def fulltext_search(query):
    """Full-text search across all records."""
    results = []
    for r in RECORDS:
        if query in r['text']:
            results.append(r)
    return results


HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>春秋左传查询系统</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: "Noto Serif SC", "Source Han Serif SC", "SimSun", serif;
    background: #f5f0e8;
    color: #2c2416;
    line-height: 1.8;
}
.header {
    background: linear-gradient(135deg, #5c3a21, #8b6914);
    color: #f5f0e8;
    padding: 2rem 1rem;
    text-align: center;
}
.header h1 {
    font-size: 2rem;
    letter-spacing: 0.3em;
    margin-bottom: 0.5rem;
}
.header p {
    font-size: 0.9rem;
    opacity: 0.8;
}
.container {
    max-width: 1100px;
    margin: 0 auto;
    padding: 1.5rem;
}
.tabs {
    display: flex;
    gap: 0;
    border-bottom: 2px solid #8b6914;
    margin-bottom: 1.5rem;
}
.tab {
    padding: 0.8rem 1.5rem;
    cursor: pointer;
    background: #e8dcc8;
    border: 1px solid #c4b08a;
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    font-size: 1rem;
    transition: all 0.2s;
    user-select: none;
}
.tab:hover { background: #d4c4a0; }
.tab.active {
    background: #f5f0e8;
    border-bottom: 2px solid #f5f0e8;
    margin-bottom: -2px;
    font-weight: bold;
}
.panel { display: none; }
.panel.active { display: block; }
.search-box {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
    flex-wrap: wrap;
    align-items: center;
}
.search-box select, .search-box input {
    padding: 0.5rem 0.8rem;
    font-size: 1rem;
    border: 1px solid #c4b08a;
    border-radius: 4px;
    background: #fff;
    font-family: inherit;
}
.search-box button {
    padding: 0.5rem 1.2rem;
    background: #8b6914;
    color: #fff;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 1rem;
    transition: background 0.2s;
}
.search-box button:hover { background: #a07a18; }
.results {
    background: #fff;
    border: 1px solid #c4b08a;
    border-radius: 6px;
    padding: 1.5rem;
    min-height: 200px;
}
.results .count {
    color: #8b6914;
    font-size: 0.9rem;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px dashed #c4b08a;
}
.record {
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #e8dcc8;
}
.record:last-child { border-bottom: none; }
.record .meta {
    font-size: 0.85rem;
    color: #8b6914;
    margin-bottom: 0.3rem;
}
.record .meta span {
    margin-right: 1rem;
}
.record .text {
    text-indent: 2em;
    font-size: 1.05rem;
}
.record .text mark {
    background: #ffeaa7;
    padding: 0 2px;
    border-radius: 2px;
}
.tag-cloud {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-top: 0.5rem;
}
.tag {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    background: #e8dcc8;
    border-radius: 3px;
    font-size: 0.85rem;
    cursor: pointer;
    transition: background 0.2s;
}
.tag:hover { background: #d4c4a0; }
.tag .num { color: #8b6914; font-size: 0.75rem; margin-left: 0.2rem; }

.empty { color: #999; text-align: center; padding: 3rem; font-style: italic; }
@media (max-width: 600px) {
    .container { padding: 0.8rem; }
    .header h1 { font-size: 1.4rem; }
    .tab { padding: 0.5rem 0.8rem; font-size: 0.9rem; }

}
</style>
</head>
<body>

<div class="header">
    <h1>春秋左传</h1>
    <p>按年份浏览 · 人物检索 · 国名检索 · 全文搜索</p>
</div>

<div class="container">
    <div class="tabs">
        <div class="tab active" data-tab="year">年份浏览</div>
        <div class="tab" data-tab="person">人物检索</div>
        <div class="tab" data-tab="state">国名检索</div>
        <div class="tab" data-tab="search">全文搜索</div>
    </div>

    <!-- Year Panel -->
    <div class="panel active" id="panel-year">
        <div class="search-box">
            <select id="sel-duke">
                <option value="">选择公</option>
                {% for duke_name in duke_names %}
                <option value="{{ duke_name }}">{{ duke_name }}</option>
                {% endfor %}
            </select>
            <select id="sel-year">
                <option value="">选择年份</option>
            </select>
            <button onclick="queryByYear()">查询</button>
        </div>
        <div class="results" id="year-results">
            <div class="empty">选择年份查看春秋左传原文</div>
        </div>
    </div>

    <!-- Person Panel -->
    <div class="panel" id="panel-person">
        <div class="search-box">
            <input type="text" id="input-person" placeholder="输入人物名称，如：季武子、范宣子、子产" style="flex:1;min-width:200px;" autocomplete="off">
            <button onclick="queryByPerson()">检索</button>
        </div>
        <div id="alias-suggest" style="display:none;background:#fff;border:1px solid #c4b08a;border-radius:4px;padding:0.5rem;margin-bottom:1rem;font-size:0.85rem;"></div>
        <div class="results" id="person-results">
            <div class="empty">输入人物名称检索相关春秋左传原文</div>
        </div>
    </div>

    <!-- State Panel -->
    <div class="panel" id="panel-state">
        <div class="tag-cloud" id="state-tags">
            {% for state in state_list %}
            <span class="tag" onclick="queryByState('{{ state }}')">{{ state }}<span class="num">({{ state_index[state] }})</span></span>
            {% endfor %}
        </div>
        <div class="results" id="state-results">
            <div class="empty">点击国名查看相关春秋左传原文</div>
        </div>
    </div>

    <!-- Search Panel -->
    <div class="panel" id="panel-search">
        <div class="search-box">
            <input type="text" id="input-search" placeholder="输入关键词进行全文搜索" style="flex:1;min-width:200px;">
            <button onclick="fulltextSearch()">搜索</button>
        </div>
        <div class="results" id="search-results">
            <div class="empty">输入关键词搜索春秋左传全文</div>
        </div>
    </div>
</div>

<script>
const dukeYears = {{ duke_years_json|safe }};

// Tab switching
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById('panel-' + tab.dataset.tab).classList.add('active');
    });
});

// Duke-year dropdown
document.getElementById('sel-duke').addEventListener('change', function() {
    const duke = this.value;
    const sel = document.getElementById('sel-year');
    sel.innerHTML = '<option value="">选择年份</option>';
    if (duke && dukeYears[duke]) {
        dukeYears[duke].forEach(yr => {
            const opt = document.createElement('option');
            opt.value = yr;
            opt.textContent = yr + '年';
            sel.appendChild(opt);
        });
    }
});

function queryByYear() {
    const duke = document.getElementById('sel-duke').value;
    const year = document.getElementById('sel-year').value;
    if (!duke || !year) { alert('请选择公和年份'); return; }
    fetch('/api/query?type=year&duke=' + encodeURIComponent(duke) + '&year=' + year)
        .then(r => r.json()).then(renderResults.bind(null, 'year-results'));
}

function queryByPerson() {
    const name = document.getElementById('input-person').value.trim();
    if (!name) { alert('请输入人物名称'); return; }
    fetch('/api/query?type=person&name=' + encodeURIComponent(name))
        .then(r => r.json()).then(renderResults.bind(null, 'person-results'));
}

function queryByState(state) {
    fetch('/api/query?type=state&name=' + encodeURIComponent(state))
        .then(r => r.json()).then(renderResults.bind(null, 'state-results'));
}

function fulltextSearch() {
    const q = document.getElementById('input-search').value.trim();
    if (!q) { alert('请输入搜索关键词'); return; }
    fetch('/api/query?type=search&q=' + encodeURIComponent(q))
        .then(r => r.json()).then(renderResults.bind(null, 'search-results'));
}

function renderResults(containerId, data) {
    const container = document.getElementById(containerId);
    if (!data.results || data.results.length === 0) {
        container.innerHTML = '<div class="empty">未找到相关记录</div>';
        return;
    }
    let aliasInfo = '';
    if (data.keyword && data.keyword.includes('|')) {
        const names = data.keyword.split('|');
        aliasInfo = '<div style="color:#8b6914;font-size:0.9rem;margin-bottom:0.5rem;">关联别名：' + names.map(n => '<span style="background:#ffeaa7;padding:1px 4px;border-radius:2px;margin:0 2px;">' + n + '</span>').join('') + '</div>';
    }
    let html = aliasInfo + '<div class="count">共找到 ' + data.results.length + ' 条记录</div>';
    data.results.forEach(r => {
        let text = escapeHtml(r.text);
        // Highlight search keyword(s)
        if (data.keyword) {
            const kws = data.keyword.split('|');
            kws.forEach(kw => {
                const escaped = escapeHtml(kw);
                if (escaped) {
                    const re = new RegExp(escaped, 'g');
                    text = text.replace(re, '<mark>' + escaped + '</mark>');
                }
            });
        }
        const sectionLabel = r.section === 'jing' ? '经' : '传';
        html += '<div class="record">'
            + '<div class="meta">'
            + '<span>' + r.duke + (r.year_num > 0 ? r.year_num + '年' : '') + '</span>'
            + '<span>前' + r.year_bc + '年</span>'
            + '<span>' + sectionLabel + '</span>'
            + '</div>'
            + '<div class="text">' + text + '</div>'
            + '</div>';
    });
    container.innerHTML = html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Enter key support
document.getElementById('input-person').addEventListener('keydown', e => { if (e.key === 'Enter') queryByPerson(); });
// Alias autocomplete for person search
let aliasTimer = null;
document.getElementById('input-person').addEventListener('input', function() {
    clearTimeout(aliasTimer);
    const val = this.value.trim();
    const box = document.getElementById('alias-suggest');
    if (!val || val.length < 1) { box.style.display = 'none'; return; }
    aliasTimer = setTimeout(() => {
        fetch('/api/aliases?q=' + encodeURIComponent(val))
            .then(r => r.json())
            .then(data => {
                if (!data.suggestions.length) { box.style.display = 'none'; return; }
                box.style.display = 'block';
                box.innerHTML = data.suggestions.map(s => {
                    const div = document.createElement('div');
                    div.style.cssText = 'padding:0.3rem 0.5rem;cursor:pointer;border-bottom:1px solid #eee;';
                    div.innerHTML = '<b>' + escapeHtml(s.canonical) + '</b>'
                        + (s.aliases.length > 1 ? ' <span style="color:#8b6914;">（' + s.aliases.filter(a=>a!==s.canonical).map(escapeHtml).join('、') + '）</span>' : '');
                    div.addEventListener('click', () => selectPerson(s.canonical));
                    return div.outerHTML;
                }).join('');
            });
    }, 300);
});
function selectPerson(name) {
    document.getElementById('input-person').value = name;
    document.getElementById('alias-suggest').style.display = 'none';
    queryByPerson();
}
document.getElementById('input-search').addEventListener('keydown', e => { if (e.key === 'Enter') fulltextSearch(); });
</script>
</body>
</html>'''


@app.route('/')
def index():
    duke_names = list(DUKES.keys())
    duke_years = {d: DUKES[d]['years'] for d in duke_names}
    return render_template_string(
        HTML_TEMPLATE,
        duke_names=duke_names,
        dukes=DUKES,
        state_list=STATE_LIST[:50],  # Top 50 states
        state_index=STATE_INDEX,
        duke_years_json=json.dumps(duke_years, ensure_ascii=False),
    )


@app.route('/api/query')
def api_query():
    qtype = request.args.get('type', '')
    results = []
    keyword = ''
    
    if qtype == 'year':
        duke = request.args.get('duke', '')
        year = request.args.get('year', '0')
        try:
            year = int(year)
        except ValueError:
            year = 0
        results = search_by_year(duke, year)
        keyword = ''
    elif qtype == 'person':
        name = request.args.get('name', '')
        results, alias_names = search_by_person(name)
        keyword = '|'.join(alias_names)
    elif qtype == 'state':
        name = request.args.get('name', '')
        results = search_by_state(name)
        keyword = name
    elif qtype == 'search':
        q = request.args.get('q', '')
        results = fulltext_search(q)
        keyword = q
    
    # Limit results to prevent huge responses
    max_results = 500
    truncated = len(results) > max_results
    results = results[:max_results]
    
    return jsonify({
        'results': results,
        'keyword': keyword,
        'total': len(results),
        'truncated': truncated,
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=False)


@app.route('/api/aliases')
def api_aliases():
    """Return alias suggestions for a given name prefix."""
    q = request.args.get('q', '')
    if not q:
        return jsonify({'suggestions': []})
    suggestions = []
    seen = set()
    for name, canonical in ALIAS_LOOKUP.items():
        if q in name:
            group = ALIASES.get(canonical, [canonical])
            key = '|'.join(sorted(group))
            if key not in seen:
                seen.add(key)
                suggestions.append({
                    'name': name,
                    'canonical': canonical,
                    'aliases': group,
                })
    return jsonify({'suggestions': suggestions[:20]})
