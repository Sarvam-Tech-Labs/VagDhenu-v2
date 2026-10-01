"""
Sanskrit Script Normalizer
Handles transliteration and normalization between Devanagari and IAST (International Alphabet of Sanskrit Transliteration).
"""

import re
import unicodedata

# Mapping between Devanagari and IAST
DEV_TO_IAST_VOWELS = {
    'अ': 'a', 'आ': 'ā', 'इ': 'i', 'ई': 'ī', 'उ': 'u', 'ऊ': 'ū',
    'ऋ': 'ṛ', 'ॠ': 'ṝ', 'ऌ': 'ḷ', 'ॡ': 'ḹ', 'ए': 'e', 'ऐ': 'ai',
    'ओ': 'o', 'औ': 'au'
}

DEV_MATRAS = {
    'ा': 'ā', 'ि': 'i', 'ी': 'ī', 'ु': 'u', 'ू': 'ū',
    'ृ': 'ṛ', 'ॄ': 'ṝ', 'ॢ': 'ḷ', 'ॣ': 'ḹ', 'े': 'e', 'ै': 'ai',
    'ो': 'o', 'ौ': 'au'
}

DEV_TO_IAST_CONSONANTS = {
    'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ṅ',
    'च': 'c', 'छ': 'ch', 'ज': 'j', 'झ': 'jh', 'ञ': 'ñ',
    'ट': 'ṭ', 'ठ': 'ṭh', 'ड': 'ḍ', 'ढ': 'ḍh', 'ण': 'ṇ',
    'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
    'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
    'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v',
    'श': 'ś', 'ष': 'ṣ', 'स': 's', 'ह': 'h'
}

DEV_SPECIAL = {
    'ं': 'ṃ', 'ँ': 'm̐', 'ः': 'ḥ', '्': '', 'ऽ': "'"
}

IAST_TO_DEV_VOWELS = {v: k for k, v in DEV_TO_IAST_VOWELS.items()}
IAST_TO_DEV_MATRAS = {v: k for k, v in DEV_MATRAS.items()}
IAST_TO_DEV_CONSONANTS = {v: k for k, v in DEV_TO_IAST_CONSONANTS.items()}


def is_devanagari(text: str) -> bool:
    """Check if the text contains Devanagari characters."""
    return any('\u0900' <= char <= '\u097F' for char in text)


def devanagari_to_iast(dev_text: str) -> str:
    """Convert Devanagari text to IAST."""
    result = []
    i = 0
    chars = list(dev_text)
    n = len(chars)

    while i < n:
        c = chars[i]
        
        # Consonant handling
        if c in DEV_TO_IAST_CONSONANTS:
            cons = DEV_TO_IAST_CONSONANTS[c]
            # Check next character
            if i + 1 < n:
                next_c = chars[i + 1]
                if next_c == '्':  # Virama / Halant
                    result.append(cons)
                    i += 2
                    continue
                elif next_c in DEV_MATRAS:  # Vowel sign
                    result.append(cons + DEV_MATRAS[next_c])
                    i += 2
                    continue
                elif next_c in DEV_SPECIAL and next_c != '्':
                    result.append(cons + 'a')
                    result.append(DEV_SPECIAL[next_c])
                    i += 2
                    continue
            # Default inherent 'a'
            result.append(cons + 'a')
            i += 1
        elif c in DEV_TO_IAST_VOWELS:
            result.append(DEV_TO_IAST_VOWELS[c])
            i += 1
        elif c in DEV_SPECIAL:
            result.append(DEV_SPECIAL[c])
            i += 1
        elif c == '।':
            result.append('.')
            i += 1
        elif c == '॥':
            result.append('..')
            i += 1
        else:
            result.append(c)
            i += 1

    return "".join(result)


def iast_to_devanagari(iast_text: str) -> str:
    """Convert IAST text to Devanagari."""
    text = normalize_iast(iast_text)
    
    # Sort consonant keys by length descending to match 'kh' before 'k'
    consonants = sorted(IAST_TO_DEV_CONSONANTS.keys(), key=len, reverse=True)
    vowels = sorted(IAST_TO_DEV_VOWELS.keys(), key=len, reverse=True)
    
    res = []
    i = 0
    n = len(text)
    
    at_word_start = True
    
    while i < n:
        # Check space or punctuation
        if text[i].isspace() or text[i] in '.,-;:!?()[]{}':
            res.append(text[i])
            at_word_start = True
            i += 1
            continue
            
        if text[i] == "'":
            res.append('ऽ')
            i += 1
            continue
        if text[i] == 'ṃ':
            res.append('ं')
            i += 1
            continue
        if text[i] == 'ḥ':
            res.append('ः')
            i += 1
            continue

        # Try match consonant
        matched_cons = None
        for cons in consonants:
            if text.startswith(cons, i):
                matched_cons = cons
                break
                
        if matched_cons:
            dev_cons = IAST_TO_DEV_CONSONANTS[matched_cons]
            i += len(matched_cons)
            
            # Check following vowel
            matched_vowel = None
            for vow in vowels:
                if text.startswith(vow, i):
                    matched_vowel = vow
                    break
                    
            if matched_vowel:
                i += len(matched_vowel)
                if matched_vowel == 'a':
                    res.append(dev_cons)
                else:
                    res.append(dev_cons + IAST_TO_DEV_MATRAS[matched_vowel])
            else:
                # No vowel follows -> add virama
                res.append(dev_cons + '्')
            at_word_start = False
            continue

        # Try match independent vowel
        matched_vowel = None
        for vow in vowels:
            if text.startswith(vow, i):
                matched_vowel = vow
                break
                
        if matched_vowel:
            res.append(IAST_TO_DEV_VOWELS[matched_vowel])
            i += len(matched_vowel)
            at_word_start = False
            continue

        # Other character
        res.append(text[i])
        i += 1

    return "".join(res)


def normalize_iast(text: str) -> str:
    """Normalize IAST string: lowercased, Unicode NFC normalized, standard accents."""
    if not text:
        return ""
    
    # If input is in Devanagari, convert to IAST first
    if is_devanagari(text):
        text = devanagari_to_iast(text)

    text = unicodedata.normalize('NFC', text.strip().lower())
    
    # Normalize common alternate representations
    replacements = {
        'aa': 'ā', 'ii': 'ī', 'uu': 'ū', 'ri': 'ṛ', 'ree': 'ṝ',
        'sh': 'ś', 'shh': 'ṣ', 'm.': 'ṃ', 'h.': 'ḥ',
        '~m': 'ṃ', 'M': 'ṃ', 'H': 'ḥ',
        'ch': 'c', 'chh': 'ch'  # standardize to IAST where c = च, ch = छ
    }
    
    # Replace avagraha variations
    text = text.replace('’', "'").replace('`', "'")
    
    return text


def clean_text(text: str) -> str:
    """Standard clean for NLP classification."""
    norm = normalize_iast(text)
    # Strip verse numbers and daṇḍas
    cleaned = re.sub(r'[\d०-९।॥|]+', ' ', norm)
    # Remove unwanted punctuation keeping letters, spaces, hyphens and avagraha
    cleaned = re.sub(r"[^\w\s\-'āīūṛṝḷḹṃḥṅñṭḍṇśṣ]", " ", cleaned)
    return re.sub(r'\s+', ' ', cleaned).strip()
