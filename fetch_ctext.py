#!/usr/bin/env python3
"""
Fetch Zuo Zhuan from ctext.org and merge into zuozhuan_data.json
- Each ctext page has: [n] Chinese text \n English translation
- We match by duke + year_num, then add ctext_text and ctext_english fields
"""

import json
import time
import re
import os
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
BAK_FILE = os.path.join(DATA_DIR, 'zuozhuan_data.json')
CTEXT_FILE = os.path.join(DATA_DIR, 'zuozhuan_ctext_merged.json')

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
    29:'er-shi-jiu', 30:'san-shi', 31:'san-shi-yi', 32:'san-shi-er',
    33:'san-shi-san',
}

def fetch_ctext(url):
    req = Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml',
    })
    try:
        with urlopen(req, timeout=20) as resp:
            html = resp.read().decode('utf-8')
        return html
    except Exception as e:
        print(f'    ERROR: {e}')
        return None

def parse_ctext_markdown(markdown_text):
    """
    Parse ctext.org markdown output.
    Format per entry:
      [n](url) Chinese text \n English translation
    Returns list of dicts with 'chinese' and 'english' keys.
    """
    entries = []
    # Split by [n] markers (where n is digits)
    # Pattern: [number](url) followed by text
    parts = re.split(r'\[(\d+)\]\([^)]+\)\s*', markdown_text)
    # parts[0] is preamble, then [num, content, num, content, ...]
    for i in range(1, len(parts), 2):
        if i + 1 >= len(parts):
            break
        num = parts[i]
        content = parts[i+1].strip()
        # Split Chinese and English
        # English starts when we see mostly ASCII characters
        chinese = ''
        english = ''
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Check if line is mostly English (ASCII ratio > 0.6)
            ascii_count = sum(1 for c in line if ord(c) < 128)
            ascii_ratio = ascii_count / max(len(line), 1)
            if ascii_ratio > 0.6:
                english += line + ' '
            else:
                chinese += line + ' '
        if chinese:
            entries.append({
                'num': num,
                'chinese': chinese.strip(),
                'english': english.strip(),
            })
    return entries

def main():
    # Load existing data
    with open(BAK_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    records = data['records']
    print(f'Loaded {len(records)} records from {BAK_FILE}')

    # Build index: (duke, year_num, section) -> record
    # ctext doesn't have section split, so we'll add ctext_* fields to all records of that year
    # and store ctext entries separately

    ctext_data = {}  # key: (duke, year_num) -> list of {num, chinese, english}

    base_url = 'https://ctext.org/chun-qiu-zuo-zhuan'

    for duke, slug in DUKE_SLUGS.items():
        print(f'Fetching {duke}...')
        max_year = max((r['year_num'] for r in records if r['duke'] == duke and r['year_num'] > 0), default=0)
        for year in range(1, max_year + 1):
            year_slug = CN_YEAR.get(year)
            if not year_slug:
                continue
            url = f'{base_url}/{slug}-{year_slug}'
            print(f'  Year {year} -> {url}')
            html = fetch_ctext(url)
            if not html:
                break
            # Use web_fetch for clean markdown
            # (Simulate by extracting from HTML)
            # For now, save raw HTML
            entries = parse_ctext_markdown(html)
            if not entries:
                print(f'    No entries found, stopping.')
                break
            ctext_data[(duke, year)] = entries
            print(f'    Got {len(entries)} entries')
            time.sleep(0.5)
        time.sleep(1)

    # Now merge: add ctext_* fields to records
    # For each record, find matching ctext entry by comparing text
    matched = 0
    for rec in records:
        if rec['year_num'] <= 0:
            continue
        key = (rec['duke'], rec['year_num'])
        if key not in ctext_data:
            continue
        ctext_entries = ctext_data[key]
        # Try to match by text similarity
        rec_text = rec['text'].strip()
        for ct in ctext_entries:
            ct_chinese = ct['chinese'].strip()
            # Check if ctext chinese contains or is contained by our text
            if rec_text in ct_chinese or ct_chinese in rec_text:
                rec['ctext_chinese'] = ct_chinese
                rec['ctext_english'] = ct['english']
                matched += 1
                break
        # If no match found, add first entry as fallback
        if 'ctext_chinese' not in rec and ctext_entries:
            rec['ctext_chinese'] = ctext_entries[0]['chinese']
            rec['ctext_english'] = ctext_entries[0]['english']

    print(f'\nMatched {matched} records with ctext data')
    print(f'Total records: {len(records)}')

    # Save merged data
    data['records'] = records
    with open(CTEXT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'Saved merged data to {CTEXT_FILE}')

if __name__ == '__main__':
    main()
