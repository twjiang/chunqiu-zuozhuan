#!/usr/bin/env python3
"""Spring and Autumn Zuo Zhuan Web Query System - Flask Application"""

import json
import os
from flask import Flask, render_template_string, request, jsonify, redirect, url_for

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'))
DATA_DIR = os.path.dirname(os.path.abspath(__file__))

# Load data
with open(os.path.join(DATA_DIR, 'zuozhuan_data.json'), 'r', encoding='utf-8') as f:
    DATA = json.load(f)

RECORDS = DATA['records']
DUKES = DATA['dukes']
YEARS = DATA['years']
STATE_INDEX = DATA['state_index']
STATE_LIST = DATA['state_list']

# Build inverted index for fast substring search
# Maps each 2-char bigram to set of record indices
BIGRAM_INDEX = {}
for _i, _r in enumerate(RECORDS):
    _text = _r['text']
    for _j in range(len(_text) - 1):
        _bg = _text[_j:_j+2]
        if _bg not in BIGRAM_INDEX:
            BIGRAM_INDEX[_bg] = []
        BIGRAM_INDEX[_bg].append(_i)
# Also index single chars for short queries
CHAR_INDEX = {}
for _i, _r in enumerate(RECORDS):
    for _c in set(_r['text']):
        if _c not in CHAR_INDEX:
            CHAR_INDEX[_c] = []
        CHAR_INDEX[_c].append(_i)

# Build duke+year index for O(1) year lookups
YEAR_INDEX = {}
for _i, _r in enumerate(RECORDS):
    _key = (_r['duke'], _r['year_num'])
    if _key not in YEAR_INDEX:
        YEAR_INDEX[_key] = []
    YEAR_INDEX[_key].append(_i)

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


def save_aliases():
    """Save aliases to JSON file."""
    with open(_alias_path, 'w', encoding='utf-8') as f:
        json.dump(ALIASES, f, ensure_ascii=False, indent=2)


def load_aliases():
    """Reload aliases from JSON file."""
    global ALIASES, ALIAS_LOOKUP
    ALIASES = {}
    ALIAS_LOOKUP = {}
    if os.path.exists(_alias_path):
        with open(_alias_path, 'r', encoding='utf-8') as f:
            _raw = json.load(f)
        for _canonical, _aliases in _raw.items():
            _all = set(_aliases)
            _all.add(_canonical)
            ALIASES[_canonical] = sorted(_all)
            for _n in _all:
                if _n not in ALIAS_LOOKUP:
                    ALIAS_LOOKUP[_n] = _canonical


def find_alias_groups(name):
    """Find alias groups for the given name.
    
    Strategy:
    1. Exact match in ALIAS_LOOKUP (covers canonical names and full aliases)
    2. If no exact match, find groups where any alias STARTS WITH the input
       (e.g. '东门' matches '东门襄仲')
    But NEVER expand through short shared aliases (no multi-hop).
    """
    matched_groups = []
    seen_keys = set()
    
    # 1. Exact match
    canonical = ALIAS_LOOKUP.get(name)
    if canonical and canonical in ALIASES:
        key = '|'.join(sorted(ALIASES[canonical]))
        if key not in seen_keys:
            seen_keys.add(key)
            matched_groups.append(ALIASES[canonical])
    
    # 2. If no exact match, try prefix match on aliases
    if not matched_groups:
        for canonical_name, group in ALIASES.items():
            for alias in group:
                if alias.startswith(name) or name.startswith(alias):
                    key = '|'.join(sorted(group))
                    if key not in seen_keys:
                        seen_keys.add(key)
                        matched_groups.append(group)
                    break
    
    # If still no match, just search the name itself
    if not matched_groups:
        return [[name]]
    return matched_groups


def search_by_year(duke_name, year_num):
    """Search records by duke and year number using index."""
    indices = YEAR_INDEX.get((duke_name, year_num), [])
    return [RECORDS[i] for i in indices]


def _bigram_search(query):
    """Find record indices containing query using bigram index."""
    if len(query) >= 2:
        candidates = None
        for j in range(len(query) - 1):
            bg = query[j:j+2]
            idx = set(BIGRAM_INDEX.get(bg, []))
            candidates = idx if candidates is None else (candidates & idx)
            if not candidates:
                return set()
        return {i for i in candidates if query in RECORDS[i]['text']}
    elif len(query) == 1:
        return set(CHAR_INDEX.get(query, []))
    return set()


def search_by_person(name):
    """Search records containing a person's name (including all aliases)."""
    groups = find_alias_groups(name)
    all_names = []
    seen = set()
    for group in groups:
        for n in group:
            if n not in seen:
                seen.add(n)
                all_names.append(n)
    matched = set()
    for n in all_names:
        matched |= _bigram_search(n)
    results = [RECORDS[i] for i in sorted(matched)]
    return results, all_names


def search_by_state(state_name):
    """Search records mentioning a state using index."""
    indices = _bigram_search(state_name)
    return [RECORDS[i] for i in sorted(indices)]


def fulltext_search(query):
    """Full-text search using bigram index."""
    indices = _bigram_search(query)
    return [RECORDS[i] for i in sorted(indices)]


HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>春秋左传查询系统</title>
<link rel="icon" type="image/svg+xml" href="/static/logo.svg">
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
    padding: 1.5rem 1rem;
    text-align: center;
}
.header .title-group h1 {
    font-size: 2rem;
    letter-spacing: 0.3em;
    margin-bottom: 0.3rem;
}
.header .title-group p {
    font-size: 0.85rem;
    opacity: 0.75;
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
    <div class="title-group">
        <h1>春秋左传</h1>
        <p>按年份浏览 · 人物检索 · 国名检索 · 全文搜索 · 别名管理</p>
    </div>
</div>
<div class="container">
    <div class="tabs">
        <div class="tab active" data-tab="year">年份浏览</div>
        <div class="tab" data-tab="person">人物检索</div>
        <div class="tab" data-tab="state">国名检索</div>
        <div class="tab" data-tab="search">全文搜索</div>
        <div class="tab" data-tab="aliases">别名管理</div>
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
    <div class="panel" id="panel-aliases">
        <div class="search-box">
            <input type="text" id="alias-search-input" placeholder="搜索人物名称或别名...">
            <button onclick="searchAliasMgmt()">搜索</button>
            <button onclick="showAddAliasModal()">+ 添加别名</button>
        </div>
        <div class="results" id="alias-mgmt-list" style="max-height:600px;overflow-y:auto;"></div>
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
// Track current query params for pagination
let currentQuery = {type:'', params:{}};

function queryByYear(page) {
    const duke = document.getElementById('sel-duke').value;
    const year = document.getElementById('sel-year').value;
    if (!duke || !year) { alert('请选择公和年份'); return; }
    currentQuery = {type:'year', params:{duke, year}};
    fetch('/api/query?type=year&duke=' + encodeURIComponent(duke) + '&year=' + year + '&page=' + (page||1))
        .then(r => r.json()).then(renderResults.bind(null, 'year-results'));
}
function queryByPerson(page) {
    const name = document.getElementById('input-person').value.trim();
    if (!name) { alert('请输入人物名称'); return; }
    currentQuery = {type:'person', params:{name}};
    fetch('/api/query?type=person&name=' + encodeURIComponent(name) + '&page=' + (page||1))
        .then(r => r.json()).then(renderResults.bind(null, 'person-results'));
}
function queryByState(state, page) {
    currentQuery = {type:'state', params:{name:state}};
    fetch('/api/query?type=state&name=' + encodeURIComponent(state) + '&page=' + (page||1))
        .then(r => r.json()).then(renderResults.bind(null, 'state-results'));
}
function fulltextSearch(page) {
    const q = document.getElementById('input-search').value.trim();
    if (!q) { alert('请输入搜索关键词'); return; }
    currentQuery = {type:'search', params:{q}};
    fetch('/api/query?type=search&q=' + encodeURIComponent(q) + '&page=' + (page||1))
        .then(r => r.json()).then(renderResults.bind(null, 'search-results'));
}
function loadPage(containerId, page) {
    const q = currentQuery;
    const p = q.params;
    if (q.type === 'year') queryByYear(page);
    else if (q.type === 'person') queryByPerson(page);
    else if (q.type === 'state') queryByState(p.name, page);
    else if (q.type === 'search') fulltextSearch(page);
}
function renderResults(containerId, data) {
    const container = document.getElementById(containerId);
    if (!data.n || data.n === 0) {
        container.innerHTML = '<div class="empty">未找到相关记录</div>';
        return;
    }
    // Build alias info
    let aliasDiv = null;
    if (data.k && data.k.includes('|')) {
        aliasDiv = document.createElement('div');
        aliasDiv.style.cssText = 'color:#8b6914;font-size:0.9rem;margin-bottom:0.5rem;';
        const label = document.createElement('span');
        label.textContent = '关联别名：';
        aliasDiv.appendChild(label);
        const names = data.k.split('|');
        names.forEach(n => {
            const span = document.createElement('span');
            span.style.cssText = 'background:#ffeaa7;padding:1px 4px;border-radius:2px;margin:0 2px;cursor:pointer;';
            span.textContent = n;
            span.addEventListener('click', () => selectPerson(n));
            aliasDiv.appendChild(span);
        });
    }
    // Count div
    const countDiv = document.createElement('div');
    countDiv.className = 'count';
    countDiv.textContent = '共找到 ' + data.n + ' 条记录' + (data.m ? '（显示第 ' + ((data.p-1)*data.ps+1) + '-' + (data.p*data.ps) + ' 条）' : '');
    
    // Clear container and append
    container.innerHTML = '';
    if (aliasDiv) container.appendChild(aliasDiv);
    container.appendChild(countDiv);
    
    // Add records
    data.r.forEach(r => {
        const recDiv = document.createElement('div');
        recDiv.className = 'record';
        
        const metaDiv = document.createElement('div');
        metaDiv.className = 'meta';
        metaDiv.innerHTML = '<span>' + escapeHtml(r.d) + (r.y > 0 ? r.y + '年' : '') + '</span>'
            + '<span>前' + r.b + '年</span>'
            + '<span>' + (r.s === 'jing' ? '经' : '传') + '</span>';
        recDiv.appendChild(metaDiv);
        
        const textDiv = document.createElement('div');
        textDiv.className = 'text';
        let text = escapeHtml(r.t);
        if (data.k) {
            const kws = data.k.split('|');
            kws.forEach(kw => {
                const escaped = escapeHtml(kw);
                if (escaped) {
                    const re = new RegExp(escaped, 'g');
                    text = text.replace(re, '<mark>' + escaped + '</mark>');
                }
            });
        }
        textDiv.innerHTML = text;
        recDiv.appendChild(textDiv);
        container.appendChild(recDiv);
    });
    
    // Pager
    const pages = Math.ceil(data.n / data.ps);
    if (pages > 1) {
        const pager = document.createElement('div');
        pager.style.cssText = 'margin-top:1rem;text-align:center;';
        pager.className = 'pager-container';
        pager.dataset.ps = data.ps;
        for (let p = 1; p <= Math.min(pages, 10); p++) {
            const btn = document.createElement('button');
            btn.className = 'page-btn';
            btn.dataset.page = p;
            btn.textContent = p;
            btn.style.cssText = 'margin:0 2px;padding:0.3rem 0.7rem;background:' + (p === data.p ? '#8b6914' : '#e8dcc8') + ';color:' + (p === data.p ? '#fff' : '#2c2416') + ';border:none;border-radius:3px;cursor:pointer;';
            btn.addEventListener('click', () => loadPage(containerId, p));
            pager.appendChild(btn);
        }
        if (pages > 10) pager.appendChild(document.createTextNode(' ... ' + pages));
        container.appendChild(pager);
    }
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
                box.innerHTML = '';
                data.suggestions.forEach(s => {
                    const div = document.createElement('div');
                    div.style.cssText = 'padding:0.3rem 0.5rem;cursor:pointer;border-bottom:1px solid #eee;';
                    const bold = document.createElement('b');
                    bold.textContent = s.canonical;
                    div.appendChild(bold);
                    if (s.aliases.length > 1) {
                        const span = document.createElement('span');
                        span.style.color = '#8b6914';
                        span.textContent = '（' + s.aliases.filter(a => a !== s.canonical).join('、') + '）';
                        div.appendChild(span);
                    }
                    div.dataset.name = s.canonical;
                    box.appendChild(div);
                });
            });
    }, 300);
});
// Delegate click on alias-suggest
const aliasBox = document.getElementById('alias-suggest');
aliasBox.addEventListener('click', e => {
    const item = e.target.closest('div[data-name]');
    if (item) {
        selectPerson(item.dataset.name);
    }
});
function selectPerson(name) {
    document.getElementById('input-person').value = name;
    const box = document.getElementById('alias-suggest');
    box.style.display = 'none';
    box.innerHTML = '';
    queryByPerson(1);
}
document.getElementById('input-search').addEventListener('keydown', e => { if (e.key === 'Enter') fulltextSearch(); });
document.getElementById('alias-search-input').addEventListener('keydown', e => { if (e.key === 'Enter') searchAliasMgmt(); });

// ===== Alias Management Panel =====
let aliasMgmtCurrentEdit = null;

function loadAliasMgmt(q) {
    const url = q ? '/api/aliases/list?q=' + encodeURIComponent(q) : '/api/aliases/list';
    fetch(url).then(r => r.json()).then(data => renderAliasMgmt(data.aliases));
}

function renderAliasMgmt(aliases) {
    const c = document.getElementById('alias-mgmt-list');
    if (!aliases || aliases.length === 0) {
        c.innerHTML = '<div class="empty">暂无别名数据</div>';
        return;
    }
    let html = '<div class="count">共 ' + aliases.length + ' 条别名</div>';
    aliases.forEach(item => {
        const tags = item.aliases.map(a => '<span class="tag">' + escapeHtml(a) + '</span>').join('');
        html += '<div class="record"><div class="meta"><span style="font-weight:bold;color:#8b6914;">' + escapeHtml(item.canonical) + '</span></div>'
            + '<div class="tag-cloud">' + tags + '</div>'
            + '<div style="margin-top:0.3rem;"><button class="alias-mgmt-edit" data-canonical="' + escapeHtml(item.canonical) + '" style="font-size:0.85rem;padding:0.2rem 0.6rem;margin-right:0.3rem;cursor:pointer;background:#e8dcc8;border:none;border-radius:3px;">编辑</button>'
            + '<button class="alias-mgmt-del" data-canonical="' + escapeHtml(item.canonical) + '" style="font-size:0.85rem;padding:0.2rem 0.6rem;cursor:pointer;background:#fadbd8;color:#c0392b;border:none;border-radius:3px;">删除</button></div></div>';
    });
    c.innerHTML = html;
    c.querySelectorAll('.alias-mgmt-edit').forEach(el => el.addEventListener('click', () => editAliasMgmt(el.dataset.canonical)));
    c.querySelectorAll('.alias-mgmt-del').forEach(el => el.addEventListener('click', () => deleteAliasMgmt(el.dataset.canonical)));
}

function searchAliasMgmt() {
    const q = document.getElementById('alias-search-input').value.trim();
    loadAliasMgmt(q);
}

function showAddAliasModal() {
    aliasMgmtCurrentEdit = null;
    document.getElementById('alias-modal-title').textContent = '添加别名';
    document.getElementById('alias-modal-canonical').value = '';
    document.getElementById('alias-modal-aliases').value = '';
    document.getElementById('alias-modal').style.display = 'flex';
}

function editAliasMgmt(canonical) {
    aliasMgmtCurrentEdit = canonical;
    document.getElementById('alias-modal-title').textContent = '编辑别名';
    document.getElementById('alias-modal-canonical').value = canonical;
    fetch('/api/aliases/list?q=' + encodeURIComponent(canonical))
        .then(r => r.json()).then(data => {
            const item = data.aliases.find(a => a.canonical === canonical);
            if (item) document.getElementById('alias-modal-aliases').value = item.aliases.filter(a => a !== canonical).join(', ');
        });
    document.getElementById('alias-modal').style.display = 'flex';
}

function closeAliasModal() {
    document.getElementById('alias-modal').style.display = 'none';
}

function saveAliasMgmt() {
    const canonical = document.getElementById('alias-modal-canonical').value.trim();
    const aliasesStr = document.getElementById('alias-modal-aliases').value.trim();
    if (!canonical) { alert('请输入标准名称'); return; }
    const aliases = aliasesStr.split(/[,，\s]+/).filter(a => a.trim());
    const url = aliasMgmtCurrentEdit ? '/api/aliases/update' : '/api/aliases/add';
    const body = { canonical, aliases };
    if (aliasMgmtCurrentEdit) body.old_canonical = aliasMgmtCurrentEdit;
    fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
        .then(r => r.json()).then(data => {
            if (data.success) { closeAliasModal(); loadAliasMgmt(); }
            else alert(data.message || '保存失败');
        });
}

function deleteAliasMgmt(canonical) {
    if (!confirm('确定删除「' + canonical + '」的别名？')) return;
    fetch('/api/aliases/delete', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ canonical }) })
        .then(r => r.json()).then(data => {
            if (data.success) loadAliasMgmt();
            else alert(data.message || '删除失败');
        });
}

// Load alias data when switching to the tab
const origTabHandler = document.querySelectorAll('.tab');
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        if (tab.dataset.tab === 'aliases') loadAliasMgmt();
    });
});
</script>

<!-- Alias Edit Modal -->
<div id="alias-modal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:1000;justify-content:center;align-items:center;">
  <div style="background:#fff;border-radius:8px;padding:1.5rem;width:90%;max-width:480px;">
    <div id="alias-modal-title" style="font-size:1.2rem;font-weight:bold;color:#8b6914;margin-bottom:1rem;">添加别名</div>
    <label style="display:block;font-weight:bold;margin-bottom:0.3rem;">标准名称（正名）</label>
    <input id="alias-modal-canonical" type="text" placeholder="如：季孙宿" style="width:100%;padding:0.5rem;border:1px solid #c4b08a;border-radius:4px;font-size:1rem;margin-bottom:1rem;">
    <label style="display:block;font-weight:bold;margin-bottom:0.3rem;">别名列表（逗号分隔）</label>
    <input id="alias-modal-aliases" type="text" placeholder="如：季武子, 季武子宿" style="width:100%;padding:0.5rem;border:1px solid #c4b08a;border-radius:4px;font-size:1rem;margin-bottom:1rem;">
    <div style="display:flex;gap:0.5rem;justify-content:flex-end;">
      <button onclick="closeAliasModal()" style="padding:0.5rem 1rem;background:#e8dcc8;border:none;border-radius:4px;cursor:pointer;">取消</button>
      <button onclick="saveAliasMgmt()" style="padding:0.5rem 1rem;background:#8b6914;color:#fff;border:none;border-radius:4px;cursor:pointer;">保存</button>
    </div>
  </div>
</div>
</body>
</html>'''


ALIAS_MANAGE_TEMPLATE = ""


@app.route('/')
def index():
    duke_names = list(DUKES.keys())
    duke_years = {d: DUKES[d]['years'] for d in duke_names}
    return render_template_string(
        HTML_TEMPLATE,
        duke_names=duke_names,
        dukes=DUKES,
        state_list=STATE_LIST[:50],
        state_index=STATE_INDEX,
        duke_years_json=json.dumps(duke_years, ensure_ascii=False),
    )


@app.route('/api/query')
def api_query():
    qtype = request.args.get('type', '')
    page = max(1, int(request.args.get('page', '1')))
    page_size = min(100, max(10, int(request.args.get('size', '50'))))
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

    total = len(results)
    start = (page - 1) * page_size
    end = start + page_size
    page_results = results[start:end]
    has_more = end < total

    # Slim down response: only send needed fields
    slim = [{
        'd': r['duke'],
        'y': r['year_num'],
        'b': r['year_bc'],
        's': r['section'],
        't': r['text']
    } for r in page_results]

    return jsonify({
        'r': slim,
        'k': keyword,
        'n': total,
        'p': page,
        'ps': page_size,
        'm': has_more,
    })


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


# Alias Management Routes
@app.route('/admin/aliases')
def admin_aliases():
    """Redirect to main page with aliases tab."""
    return redirect('/#aliases')


@app.route('/api/aliases/list')
def api_aliases_list():
    """Get all aliases, optionally filtered by search query."""
    q = request.args.get('q', '').strip().lower()
    result = []
    for canonical, aliases in ALIASES.items():
        if q:
            # Search in canonical name or any alias
            if q not in canonical.lower() and not any(q in a.lower() for a in aliases):
                continue
        result.append({
            'canonical': canonical,
            'aliases': aliases
        })
    # Sort by canonical name
    result.sort(key=lambda x: x['canonical'])
    return jsonify({'aliases': result})


@app.route('/api/aliases/add', methods=['POST'])
def api_aliases_add():
    """Add a new alias group."""
    data = request.get_json()
    canonical = data.get('canonical', '').strip()
    aliases = data.get('aliases', [])
    
    if not canonical:
        return jsonify({'success': False, 'message': '标准名称不能为空'})
    
    if canonical in ALIASES:
        return jsonify({'success': False, 'message': '该标准名称已存在'})
    
    # Add canonical to aliases list
    all_names = set(aliases)
    all_names.add(canonical)
    ALIASES[canonical] = sorted(all_names)
    
    # Update lookup
    for name in all_names:
        if name not in ALIAS_LOOKUP:
            ALIAS_LOOKUP[name] = canonical
    
    save_aliases()
    return jsonify({'success': True})


@app.route('/api/aliases/update', methods=['POST'])
def api_aliases_update():
    """Update an existing alias group."""
    data = request.get_json()
    old_canonical = data.get('old_canonical', '').strip()
    canonical = data.get('canonical', '').strip()
    aliases = data.get('aliases', [])
    
    if not canonical:
        return jsonify({'success': False, 'message': '标准名称不能为空'})
    
    if old_canonical not in ALIASES:
        return jsonify({'success': False, 'message': '原标准名称不存在'})
    
    # Remove old lookup entries
    old_aliases = ALIASES[old_canonical]
    for name in old_aliases:
        if name in ALIAS_LOOKUP and ALIAS_LOOKUP[name] == old_canonical:
            del ALIAS_LOOKUP[name]
    
    # Remove old entry
    del ALIASES[old_canonical]
    
    # Add new entry
    all_names = set(aliases)
    all_names.add(canonical)
    ALIASES[canonical] = sorted(all_names)
    
    # Update lookup
    for name in all_names:
        if name not in ALIAS_LOOKUP:
            ALIAS_LOOKUP[name] = canonical
    
    save_aliases()
    return jsonify({'success': True})


@app.route('/api/aliases/delete', methods=['POST'])
def api_aliases_delete():
    """Delete an alias group."""
    data = request.get_json()
    canonical = data.get('canonical', '').strip()
    
    if canonical not in ALIASES:
        return jsonify({'success': False, 'message': '标准名称不存在'})
    
    # Remove lookup entries
    for name in ALIASES[canonical]:
        if name in ALIAS_LOOKUP and ALIAS_LOOKUP[name] == canonical:
            del ALIAS_LOOKUP[name]
    
    # Remove entry
    del ALIASES[canonical]
    
    save_aliases()
    return jsonify({'success': True})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=False)
