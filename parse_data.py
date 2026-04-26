#!/usr/bin/env python3
"""Parse kanripo KR1e0001 zuozhuan text files into structured JSON."""

import os
import re
import json
from opencc import OpenCC

cc = OpenCC('t2s')

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(DATA_DIR, 'zuozhuan_data.json')

DUKES = ['隐公', '桓公', '庄公', '闵公', '僖公', '文公', '宣公', '成公', '襄公', '昭公', '定公', '哀公']

DUKE_START_BC = {
    '隐公': 722, '桓公': 711, '庄公': 693, '闵公': 661,
    '僖公': 659, '文公': 626, '宣公': 608, '成公': 590,
    '襄公': 572, '昭公': 541, '定公': 509, '哀公': 494,
}

# Chinese numeral to integer
CN_NUM = {
    '元': 1, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
    '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
    '十一': 11, '十二': 12, '十三': 13, '十四': 14, '十五': 15,
    '十六': 16, '十七': 17, '十八': 18, '十九': 19, '二十': 20,
    '二十一': 21, '二十二': 22, '二十三': 23, '二十四': 24, '二十五': 25,
    '二十六': 26, '二十七': 27, '二十八': 28, '二十九': 29, '三十': 30,
    '三十一': 31, '三十二': 32, '三十三': 33, '三十四': 34, '三十五': 35,
    '三十六': 36, '三十七': 37, '三十八': 38, '三十九': 39, '四十': 40,
}

# States for indexing
STATES = [
    '齐', '楚', '晋', '秦', '鲁', '郑', '宋', '卫', '陈', '蔡',
    '曹', '燕', '吴', '越', '许', '邾', '莒', '滕', '薛', '杞',
    '虞', '虢', '滑', '随', '黄', '江', '舒', '霍', '魏', '郜',
    '郕', '谭', '遂', '纪', '凡', '申', '吕', '邓', '鄫', '鄀',
    '巴', '绞', '罗', '巢', '桐', '肥', '鼓', '潞', '戎', '狄',
    '北戎', '山戎', '赤狄', '白狄', '长狄', '陆浑', '鲜虞', '蛮氏',
    '莒', '邿', '鄅', '郯', '任', '宿', '须句', '颛臾', '牟',
    '向', '极', '铸', '州', '淳于', '南燕', '鄣', '蒋', '茅',
    '胙', '邗', '焦', '耿', '密', '戴', '郐', '鄟', '钟离',
    '钟吾', '舒鸠', '舒龚', '舒龙', '舒鲍', '舒蓼', '蓼',
    '六', '皖', '英国', '宗', '贰', '轸', '郧', '卢戎',
    '缯', '弦', '鄀', '鄫', '无终', '令支', '孤竹',
    '甲氏', '留吁', '铎辰', '廧咎如', '郲', '偪', '逼',
    '倪', '小邾', '滥',
]


def parse_files():
    """Parse all 12 zuozhuan text files into structured data."""
    records = []
    
    for file_idx in range(1, 13):
        filename = f'KR1e0001_{file_idx:03d}.txt'
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.exists(filepath):
            continue
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        current_duke = ''
        current_year_num = 0
        current_year_bc = 0
        current_section = 'zhuan'
        current_paragraph = ''
        paragraph_id = ''
        
        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if not line or line.startswith('#') or line.startswith('<pb:'):
                i += 1
                continue
            
            # Detect duke heading: ** N 隱公
            duke_match = re.match(r'^\*\*\s+\d+\s+(.+)$', line)
            if duke_match:
                duke_name = cc.convert(duke_match.group(1).strip())
                if duke_name in DUKES:
                    current_duke = duke_name
                    current_year_num = 0
                    current_year_bc = DUKE_START_BC.get(duke_name, 0)
                i += 1
                continue
            
            # Detect year heading: A1.1《隱公元年經》 or B1.1《隱公元年傳》
            # Pattern: [AB]N.N《DUKE_NAME YEAR_NUM年[經傳]》
            year_match = re.match(r'^([AB])\d+\.\d+\u300a(.+?)\u300b$', line)
            if year_match:
                ab = year_match.group(1)
                inner = cc.convert(year_match.group(2))
                # Parse: 隐公元年经
                ym = re.match(r'^(.+?)(元|一|二|三|四|五|六|七|八|九|十|十一|十二|十三|十四|十五|十六|十七|十八|十九|二十|二十一|二十二|二十三|二十四|二十五|二十六|二十七|二十八|二十九|三十|三十一|三十二|三十三|三十四|三十五|三十六|三十七|三十八|三十九|四十)年([经传])$', inner)
                if ym:
                    # Save previous paragraph
                    if current_paragraph.strip():
                        records.append(make_record(
                            current_duke, current_year_num, current_year_bc,
                            current_section, paragraph_id, current_paragraph
                        ))
                        current_paragraph = ''
                    
                    duke_in_heading = ym.group(1)
                    year_cn = ym.group(2)
                    section_type = ym.group(3)
                    
                    current_duke = duke_in_heading
                    current_year_num = CN_NUM.get(year_cn, 0)
                    current_section = 'jing' if section_type == '经' else 'zhuan'
                    if current_duke in DUKE_START_BC:
                        current_year_bc = DUKE_START_BC[current_duke] - current_year_num + 1
                    paragraph_id = inner
                    
                i += 1
                continue
            
            # Detect sub-entry heading: A1.1.1 or B1.1.1
            sub_match = re.match(r'^([AB])(\d+\.\d+\.\d+)(.*)', line)
            if sub_match:
                # Save previous paragraph
                if current_paragraph.strip():
                    records.append(make_record(
                        current_duke, current_year_num, current_year_bc,
                        current_section, paragraph_id, current_paragraph
                    ))
                    current_paragraph = ''
                
                rest = sub_match.group(3)
                paragraph_id = sub_match.group(2)
                current_section = 'jing' if sub_match.group(1) == 'A' else 'zhuan'
                
                text = re.sub(r'[¶]', '', rest).strip()
                text = cc.convert(text)
                if text and not text.startswith('\u300a'):
                    current_paragraph = text
                i += 1
                continue
            
            # Also detect standalone B《傳》 marker (prologue before year 1)
            if re.match(r'^B\u300a?傳\u300b?$', line) or re.match(r'^B《传》$', cc.convert(line)):
                if current_paragraph.strip():
                    records.append(make_record(
                        current_duke, current_year_num, current_year_bc,
                        current_section, paragraph_id, current_paragraph
                    ))
                    current_paragraph = ''
                current_section = 'zhuan'
                paragraph_id = f'{current_duke}序传'
                i += 1
                continue
            
            # Regular text line
            text = re.sub(r'[¶]', '', line).strip()
            text = cc.convert(text)
            if text:
                if current_paragraph:
                    current_paragraph += text
                else:
                    current_paragraph = text
            
            i += 1
        
        # Save last paragraph
        if current_paragraph.strip():
            records.append(make_record(
                current_duke, current_year_num, current_year_bc,
                current_section, paragraph_id, current_paragraph
            ))
    
    return records


def make_record(duke, year_num, year_bc, section, para_id, text):
    return {
        'duke': duke,
        'year_num': year_num,
        'year_bc': year_bc,
        'section': section,
        'para_id': para_id,
        'text': text,
    }


def main():
    print("Parsing zuozhuan text files...")
    records = parse_files()
    print(f"Parsed {len(records)} paragraphs")
    
    # Build year index
    years = {}
    for r in records:
        if r['year_num'] == 0:
            continue
        key = f"{r['duke']}{r['year_num']}年"
        bc = r['year_bc']
        if key not in years:
            years[key] = {
                'duke': r['duke'],
                'year_num': r['year_num'],
                'year_bc': bc,
                'label': f"{r['duke']}{r['year_num']}年(前{bc}年)",
            }
    
    # Build duke index with year list
    dukes = {}
    for d in DUKES:
        duke_records = [r for r in records if r['duke'] == d and r['year_num'] > 0]
        if duke_records:
            duke_years = sorted(set(r['year_num'] for r in duke_records))
            dukes[d] = {
                'name': d,
                'years': duke_years,
                'start_bc': DUKE_START_BC.get(d, 0),
            }
    
    # Build state index
    state_index = {}
    for state in STATES:
        state_recs = [r for r in records if state in r['text']]
        if state_recs:
            state_index[state] = len(state_recs)
    
    output = {
        'records': records,
        'dukes': dukes,
        'years': years,
        'state_index': state_index,
        'state_list': sorted(state_index.keys(), key=lambda s: state_index[s], reverse=True),
    }
    
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"Saved to {OUTPUT}")
    print(f"Dukes: {len(dukes)}, Years: {len(years)}, States with data: {len(state_index)}")
    print(f"Total text length: {sum(len(r['text']) for r in records)} chars")
    
    # Quick sample
    for d in DUKES[:3]:
        if d in dukes:
            print(f"  {d}: years {dukes[d]['years'][:5]}...")


if __name__ == '__main__':
    main()
