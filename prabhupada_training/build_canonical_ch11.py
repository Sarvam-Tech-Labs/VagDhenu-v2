import json
import re
from indic_transliteration import sanscript

def clean_iast(s):
    s = s.replace('śhrī', 'śrī').replace('śh', 'ś').replace('ṣh', 'ṣ')
    s = s.replace('ch', 'c').replace('chh', 'cch')
    s = s.replace('ṛi', 'ṛ').replace('’', "'")
    return s

def to_mms_words(s):
    if re.search(r'[\u0900-\u097F]', s):
        iast = sanscript.transliterate(s, sanscript.DEVANAGARI, sanscript.IAST)
    else:
        iast = s
    iast = clean_iast(iast)
    clean = (iast.replace('ā', 'a').replace('ī', 'i').replace('ū', 'u')
                 .replace('ṛ', 'r').replace('ṝ', 'r').replace('ḷ', 'l')
                 .replace('ṅ', 'n').replace('ñ', 'n').replace('ṇ', 'n').replace('ṃ', 'm').replace('ṁ', 'm')
                 .replace('ṭ', 't').replace('ḍ', 'd').replace('ś', 's').replace('ṣ', 's')
                 .replace('ḥ', 'h').replace("'", '').replace('-', ' '))
    words = re.sub(r'[^a-z\s]', '', clean.lower()).split()
    return ' '.join(words)

def count_syllables(s):
    clean = clean_iast(s).lower().replace('ai', 'E').replace('au', 'O')
    return sum(1 for ch in clean if ch in 'aāiīuūṛṝḷeoEO')

def split_hemistich(line_deva, line_iast):
    words_iast = line_iast.strip().split()
    words_deva = line_deva.strip().split()
    
    best_idx = len(words_iast) // 2
    min_diff = 999
    curr_s = 0
    for idx, w in enumerate(words_iast):
        curr_s += count_syllables(w)
        diff = abs(curr_s - 8)
        if diff < min_diff:
            min_diff = diff
            best_idx = idx + 1
        if curr_s >= 8:
            break
            
    p1_iast = ' '.join(words_iast[:best_idx])
    p2_iast = ' '.join(words_iast[best_idx:])
    
    if len(words_deva) == len(words_iast):
        p1_deva = ' '.join(words_deva[:best_idx])
        p2_deva = ' '.join(words_deva[best_idx:])
    else:
        p1_deva = sanscript.transliterate(p1_iast, sanscript.IAST, sanscript.DEVANAGARI).replace('ꣳ', 'ं')
        p2_deva = sanscript.transliterate(p2_iast, sanscript.IAST, sanscript.DEVANAGARI).replace('ꣳ', 'ं')
        
    p1_deva = re.sub(r'[।॥\d\.\s]+$', '', p1_deva).strip()
    p2_deva = re.sub(r'[।॥\d\.\s]+$', '', p2_deva).strip()
    return p1_deva, p2_deva, p1_iast, p2_iast

verses = [v for v in json.load(open('/home/ubuntu/vagdhenu/prabhupada_training/gita_verses.json')) if v['chapter_number'] == 11 and v['verse_number'] <= 27]
verses.sort(key=lambda x: x['verse_number'])

canonical_units = []

# Title
canonical_units.append({
    "fn": "bg_11_00_title.wav",
    "v": 0,
    "p": "title",
    "deva": "श्रीमद्भगवद्गीता - एकादशोऽध्यायः",
    "iast": "śrīmad-bhagavad-gītā - ekādaśo 'dhyāyaḥ",
    "words": "bhagavad gita ekadaso dhyayah"
})

for v in verses:
    vn = v['verse_number']
    
    # Speakers
    if vn == 1:
        canonical_units.append({
            "fn": "bg_11_01_speaker.wav",
            "v": 1,
            "p": "speaker",
            "deva": "अर्जुन उवाच",
            "iast": "arjuna uvāca",
            "words": "arjuna uvaca"
        })
    elif vn == 5:
        canonical_units.append({
            "fn": "bg_11_05_speaker.wav",
            "v": 5,
            "p": "speaker",
            "deva": "श्रीभगवानुवाच",
            "iast": "śrī-bhagavān uvāca",
            "words": "sribhagavan uvaca"
        })
    elif vn == 9:
        canonical_units.append({
            "fn": "bg_11_09_speaker.wav",
            "v": 9,
            "p": "speaker",
            "deva": "सञ्जय उवाच",
            "iast": "sañjaya uvāca",
            "words": "sanjaya uvaca"
        })
    elif vn == 15:
        canonical_units.append({
            "fn": "bg_11_15_speaker.wav",
            "v": 15,
            "p": "speaker",
            "deva": "अर्जुन उवाच",
            "iast": "arjuna uvāca",
            "words": "arjuna uvaca"
        })
        
    t_lines = [l.strip() for l in v['text'].split('\n') if l.strip() and 'वाच' not in l]
    tr_lines = [l.strip() for l in v['transliteration'].split('\n') if l.strip() and 'uvācha' not in l and 'uvaca' not in l and not re.search(r'[\u0900-\u097F]', l)]
    
    if vn == 19:
        t_lines = [
            'अनादिमध्यान्तमनन्तवीर्यम्',
            'अनन्तबाहुं शशिसूर्यनेत्रम्',
            'पश्यामि त्वां दीप्तहुताशवक्त्रम्',
            'स्वतेजसा विश्वमिदं तपन्तम्'
        ]
        tr_lines = [
            'anādi-madhyāntam ananta-vīryam',
            'ananta-bāhuṁ śaśi-sūrya-netram',
            'paśyāmi tvāṁ dīpta-hutāśa-vaktraṁ',
            'sva-tejasā viśvam idaṁ tapantam'
        ]
    elif vn == 26:
        tr_lines = tr_lines[:4]
    elif vn == 27:
        tr_lines = [
            'vaktrāṇi te tvaramāṇā viśanti',
            'daṁṣṭrā-karālāni bhayānakāni',
            'kecid vilagnā daśanāntareṣu',
            'sandṛśyante cūrṇitair uttamāṅgaiḥ'
        ]
        
    if len(t_lines) == 4 and len(tr_lines) == 4:
        padas = [
            (1, re.sub(r'[।॥\d\.\s]+$', '', t_lines[0]), tr_lines[0]),
            (2, re.sub(r'[।॥\d\.\s]+$', '', t_lines[1]), tr_lines[1]),
            (3, re.sub(r'[।॥\d\.\s]+$', '', t_lines[2]), tr_lines[2]),
            (4, re.sub(r'[।॥\d\.\s]+$', '', t_lines[3]), tr_lines[3])
        ]
    else:
        p1_d, p2_d, p1_i, p2_i = split_hemistich(t_lines[0], tr_lines[0])
        p3_d, p4_d, p3_i, p4_i = split_hemistich(t_lines[1], tr_lines[1])
        padas = [
            (1, p1_d, p1_i),
            (2, p2_d, p2_i),
            (3, p3_d, p3_i),
            (4, p4_d, p4_i)
        ]
        
    for p_idx, p_deva, p_iast in padas:
        w = to_mms_words(p_iast)
        canonical_units.append({
            "fn": f"bg_11_{vn:02d}_pada_{p_idx}.wav",
            "v": vn,
            "p": p_idx,
            "deva": p_deva,
            "iast": p_iast,
            "words": w
        })

print(f"Generated {len(canonical_units)} canonical units for Chapter 11 (Part 1, verses 1-27).")

out_py = '/home/ubuntu/vagdhenu/prabhupada_training/canonical_ch11_all.py'
with open(out_py, 'w', encoding='utf-8') as f:
    f.write("# Canonical pāda definitions for Bhagavad Gita Chapter 11 (Tape 2128, Verses 1-27)\n")
    f.write(f"# Total units: {len(canonical_units)} (1 title + 4 speakers + 108 padas [27 verses])\n\n")
    f.write("canonical_units = [\n")
    for u in canonical_units:
        f.write("    {\n")
        f.write(f"        \"fn\": \"{u['fn']}\",\n")
        f.write(f"        \"v\": {u['v']},\n")
        p_val = f"\"{u['p']}\"" if isinstance(u['p'], str) else str(u['p'])
        f.write(f"        \"p\": {p_val},\n")
        f.write(f"        \"deva\": \"{u['deva']}\",\n")
        f.write(f"        \"iast\": \"{u['iast']}\",\n")
        f.write(f"        \"words\": \"{u['words']}\"\n")
        f.write("    },\n")
    f.write("]\n\n")
    f.write("if __name__ == '__main__':\n")
    f.write("    print(f'Chapter 11 canonical units: {len(canonical_units)}')\n")

print(f"Wrote {out_py} successfully.")
