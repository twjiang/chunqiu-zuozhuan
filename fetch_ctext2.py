#!/usr/bin/env python3
"""
Fetch Zuo Zhuan from ctext.org and merge into zuozhuan_data.json
- Uses web_fetch-style parsing (clean HTML -> text)
- Matches by (duke, year, section) and adds ctext_chinese + ctext_english
"""

import json
import time
import re
import os
from urllib.request import Request, urlopen
from html import unescape

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
BAK_FILE = os.path.join(DATA_DIR, 'zuozhuan_data.json')
OUTPUT = os.path.join(DATA_DIR, 'zuozhuan_data_ctext.json')

DUKE_SLUGS = {
    '隐公': 'yin-gong', '桓公': 'huan-gong', '庄公': 'zhuang-gong',
    '闵公': 'min-gong', '僖公': 'xi-gong', '文公': 'wen-gong',
    '宣公': 'xuan-gong', '成公': 'cheng-gong', '襄公': 'xiang-gong',
    '昭公': 'zhao-gong', '定公': 'ding-gong', '哀公': 'ai-gong',
}

CN_YEAR = {
    1:'yuan-nian', 2:'er-nian', 3:'san-nian', 4:'si-nian', 5:'wu-nian',
    6:'liu-nian', 7:'qi-nian', 8:'ba-nian', 9:'jiu-nian', 10:'shi-nian',
    11:'shi-yi', 12:'shi-er', 13:'shi-san', 14:'shi-si', 15:'shi-wu',
    16:'shi-liu', 17:'shi-qi', 18:'shi-ba', 19:'shi-jiu', 20:'er-shi',
    21:'er-shi-yi', 22:'er-shi-er', 23:'er-shi-san', 24:'er-shi-si',
    25:'er-shi-wu', 26:'er-shi-liu', 27:'er-shi-qi', 28:'er-shi-ba',
    29:'er-shi-jiu', 30:'san-shi', 31:'san-shi-yi', 32:'san-shi-er', 33:'san-shi-san',
}

def fetch_url(url):
    req = Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        'Accept': 'text/html',
    })
    try:
        with urlopen(req, timeout=20) as r:
            return r.read().decode('utf-8')
    except Exception as e:
        return None

def clean_html(html):
    """Remove HTML tags, keep text content."""
    # Remove script/style blocks
    html = re.sub(r'<script[^>]*>.*?</script>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
    # Remove HTML tags
    html = re.sub(r'<[^>]+>', ' ', html)
    # Decode entities
    html = unescape(html)
    # Collapse whitespace
    html = re.sub(r'\s+', ' ', html).strip()
    return html

def parse_ctext_page(html):
    """
    Parse ctext.org page.
    Format: [n](url) Title:\nChinese text\nEnglish text
    Returns: [{'num': n, 'chinese': ..., 'english': ...}, ...]
    """
    text = clean_html(html)
    # Pattern: find all [number](url) entries
    # Then grab text until next [number] or end
    pattern = r'\[(\d+)\]\([^)]+\)\s*([^\[]+)'
    matches = re.findall(pattern, text, re.DOTALL)
    
    entries = []
    for num_str, content in matches:
        content = content.strip()
        # Split into Chinese and English
        # Heuristic: English text has >50% ASCII chars
        chinese_parts = []
        english_parts = []
        
        # Split by sentences (Chinese ends with 。！？；)
        sentences = re.split(r'(?<=[。！？；])\s*', content)
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            ascii_ratio = sum(1 for c in sent if ord(c) < 128) / max(len(sent), 1)
            if ascii_ratio > 0.6:
                english_parts.append(sent)
            else:
                chinese_parts.append(sent)
        
        chinese = ' '.join(chinese_parts).strip()
        english = ' '.join(english_parts).strip()
        
        if chinese:  # Only add if we got Chinese text
            entries.append({
                'num': num_str,
                'chinese': chinese,
                'english': english,
            })
    
    return entries

def main():
    # Load existing data
    with open(BAK_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    records = data['records']
    print(f'Loaded {len(records)} records')
    
    # Group ctext data by (duke, year)
    ctext_by_year = {}  # (duke, year) -> [entries]
    
    base_url = 'https://ctext.org/chun-qiu-zuo-zhuan'
    
    for duke, slug in DUKE_SLUGS.items():
        print(f'Fetching {duke}...')
        max_year = max((r['year_num'] for r in records if r['duke'] == duke and r['year_num'] > 0), default=0)
        for year in range(1, max_year + 1):
            year_slug = CN_YEAR.get(year)
            if not year_slug:
                continue
            url = f'{base_url}/{slug}-{year_slug}'
            print(f'  Year {year}...', end=' ')
            html = fetch_url(url)
            if not html:
                print('FAILED')
                break
            entries = parse_ctext_page(html)
            if not entries:
                print('no entries, stopping')
                break
            ctext_by_year[(duke, year)] = entries
            print(f'{len(entries)} entries')
            time.sleep(0.5)
        time.sleep(1)
    
    print(f'\nFetched ctext data for {len(ctext_by_year)} year pages')
    
    # Now match and merge into records
    matched = 0
    for rec in records:
        if rec['year_num'] <= 0:
            continue
        key = (rec['duke'], rec['year_num'])
        if key not in ctext_by_year:
            continue
        entries = ctext_by_year[key]
        
        # Try to find matching entry by comparing text
        rec_text = rec['text'].strip()
        best_match = None
        best_score = 0
        
        for ent in entries:
            ct_text = ent['chinese'].strip()
            # Score: how much of rec_text is in ct_text or vice versa
            if rec_text in ct_text:
                score = len(rec_text)
            elif ct_text in rec_text:
                score = len(ct_text)
            else:
                # Count matching characters
                common = set(rec_text) & set(ct_text)
                score = len(common)
            
            if score > best_score:
                best_score = score
                best_match = ent
        
        if best_match:
            rec['ctext_chinese'] = best_match['chinese']
            rec['ctext_english'] = best_match['english']
            matched += 1
        elif entries:
            # Fallback: use first entry
            rec['ctext_chinese'] = entries[0]['chinese']
            rec['ctext_english'] = entries[0]['english']
            matched += 1
    
    print(f'Matched {matched} records with ctext data')
    
    # Save
    data['records'] = records
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'Saved to {OUTPUT}')
    print(f'Total records: {len(records)}')

if __name__ == '__main__':
    main()
