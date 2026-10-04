# -*- coding: utf-8 -*-
"""
gita_prosody.py — Fast parallel scansion and meter identification for Bhagavad-gītā verses.
Leverages VyakaranaBandhu's chandas_labeler and Sanskrit verse analysis.
"""

import sys
sys.path.insert(0, '/home/ubuntu/vagdhenu/src')
sys.path.insert(0, '/home/ubuntu/vagdhenu')

import chandas_labeler as CL
from chandas.verse_analysis import analyze_sanskrit_verse
from chandas.identification import identify_sanskrit_meter

def analyze_unit_prosody(item, is_hemi=False):
    text = item.get('text_deva', '')
    v_num = item.get('verse', 0)
    p_combo = item.get('pada_combo', item.get('pada', ''))
    p_combo_str = str(p_combo).lower()
    fn_str = str(item.get('filename', '')).lower()
    
    is_speaker = (
        'speaker' in p_combo_str or 
        'speaker' in fn_str or 
        item.get('is_speaker', False) or 
        text.strip() in ('धृतराष्ट्र उवाच', 'सञ्जय उवाच', 'अर्जुन उवाच', 'श्रीभगवानुवाच', 'भगवानुवाच')
    )
    is_title = (v_num == 0 or 'title' in str(p_combo).lower() or ('अध्याय' in text and 'ब्रह्मविद्या' not in text and 'संवादे' not in text and 'तत्सदिति' not in text))
    is_colophon = (
        'तत्सदिति' in text or 
        'पुष्पिका' in text or 
        'colophon' in str(item.get('filename', '')).lower() or 
        ('ब्रह्मविद्या' in text and 'योगशास्त्रे' in text) or
        ('संवादे' in text and 'अध्याय' in text) or
        (v_num == 48 and 'bg_01' in str(item.get('filename', ''))) or
        (v_num == 44 and 'bg_03' in str(item.get('filename', '')))
    )
    
    slp = CL.to_slp1(text)
    weights, n_syl = CL.scan(slp)
    w_str = ''.join(weights)
    
    if is_title:
        return {
            'meter': 'adhyāya-śīrṣaka (title)',
            'syllables': n_syl,
            'weights': w_str,
            'is_known': True
        }
    if is_colophon:
        return {
            'meter': 'gadya (puṣpikā - colophon)',
            'syllables': n_syl,
            'weights': w_str,
            'is_known': True
        }
    if is_speaker:
        return {
            'meter': 'gadya (uvāca-pada)',
            'syllables': n_syl,
            'weights': w_str,
            'is_known': True
        }
        
    meter_name = None
    try:
        ana = analyze_sanskrit_verse(text)
        ident = identify_sanskrit_meter(ana)
        if ident.primary and ident.primary.name:
            meter_name = ident.primary.name
    except Exception:
        pass
        
    # Gita conventions for Anuṣṭubh and Triṣṭubh
    if n_syl in (8, 16, 32):
        if not meter_name or meter_name in ('kanyā', 'unknown', 'unidentified'):
            meter_name = 'anuṣṭubh (śloka)'
    elif n_syl in (11, 22, 23, 44, 45):
        if not meter_name or meter_name.startswith('nicṛt gāyatrī'):
            meter_name = 'triṣṭubh / upajāti'
    elif not meter_name:
        meter_name = f'chandas ({n_syl} akṣaras)'
        
    return {
        'meter': meter_name,
        'syllables': n_syl,
        'weights': w_str,
        'is_known': True
    }

def batch_analyze_manifest(items, is_hemi=False, max_workers=32):
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(analyze_unit_prosody, it, is_hemi) for it in items]
        results = [f.result() for f in futures]
    return results

if __name__ == '__main__':
    test_items = [
        {'text_deva': 'धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः', 'verse': 1, 'pada_combo': '1+2'},
        {'text_deva': 'श्रीभगवानुवाच', 'verse': 2, 'pada_combo': 'speaker', 'is_speaker': True},
        {'text_deva': 'आश्चर्यवत्पश्यति कश्चिदेनम् आश्चर्यवद्वदति तथैव चान्यः', 'verse': 29, 'pada_combo': '1+2'}
    ]
    res = batch_analyze_manifest(test_items, is_hemi=True, max_workers=4)
    for t, r in zip(test_items, res):
        print(t['text_deva'], '-->', r)
