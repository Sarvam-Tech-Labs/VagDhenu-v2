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

verses = [v for v in json.load(open('/home/ubuntu/vagdhenu/prabhupada_training/gita_verses.json')) if v['chapter_number'] == 7]
verses.sort(key=lambda x: x['verse_number'])

canonical_units = []

# Unit 1: Speaker at 7.1
canonical_units.append({
    "fn": "bg_07_01_speaker.wav",
    "v": 1,
    "p": "speaker",
    "deva": "श्रीभगवानुवाच",
    "iast": "śrī-bhagavān uvāca",
    "words": "sribhagavan uvaca"
})

for v in verses:
    vn = v['verse_number']
    if vn == 3:
        # Note: Verse 7.3 was omitted on tape 2124 (Prabhupāda recited 7.2 and transitioned directly into 7.4)
        continue
        
    t_lines = [l.strip() for l in v['text'].split('\n') if l.strip() and 'वाच' not in l]
    tr_lines = [l.strip() for l in v['transliteration'].split('\n') if l.strip() and 'uvācha' not in l and 'uvaca' not in l]
    
    h1_deva = t_lines[0]
    h2_deva = t_lines[1]
    h1_iast = tr_lines[0]
    h2_iast = tr_lines[1]
    
    p1_d, p2_d, p1_i, p2_i = split_hemistich(h1_deva, h1_iast)
    p3_d, p4_d, p3_i, p4_i = split_hemistich(h2_deva, h2_iast)
    
    padas = [
        (1, p1_d, p1_i),
        (2, p2_d, p2_i),
        (3, p3_d, p3_i),
        (4, p4_d, p4_i)
    ]
    
    for p_idx, p_deva, p_iast in padas:
        w = to_mms_words(p_iast)
        canonical_units.append({
            "fn": f"bg_07_{vn:02d}_pada_{p_idx}.wav",
            "v": vn,
            "p": p_idx,
            "deva": p_deva,
            "iast": p_iast,
            "words": w
        })

# Colophon
canonical_units.append({
    "fn": "bg_07_31_colophon.wav",
    "v": 31,
    "p": "colophon",
    "deva": "ॐ तत्सदिति श्रीमद्भगवद्गीतासूपनिषत्सु ब्रह्मविद्यायां योगशास्त्रे श्रीकृष्णार्जुनसंवादे ज्ञानविज्ञानयोगो नाम सप्तमोऽध्यायः",
    "iast": "oṁ tat sad iti śrīmad-bhagavad-gītāsūpaniṣatsu brahma-vidyāyāṁ yoga-śāstre śrī-kṛṣṇārjuna-saṁvāde jñāna-vijñāna-yogo nāma saptamo 'dhyāyaḥ",
    "words": "om tat sad iti srimad bhagavad gitasupanisatsu brahma vidyayam yoga sastre sri krsnarjuna samvade jnana vijnana yogo nama saptamo dhyayah"
})

print(f"Generated {len(canonical_units)} canonical units for Chapter 7.")

out_py = '/home/ubuntu/vagdhenu/prabhupada_training/canonical_ch7_all.py'
with open(out_py, 'w', encoding='utf-8') as f:
    f.write("# Canonical pāda definitions for Bhagavad Gita Chapter 7 (Tape 2124)\n")
    f.write(f"# Total units: {len(canonical_units)} (1 speaker + 116 padas [29 verses] + 1 colophon)\n\n")
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
    f.write("    print(f'Chapter 7 canonical units: {len(canonical_units)}')\n")

print(f"Wrote {out_py} successfully.")
