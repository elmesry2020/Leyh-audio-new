# -*- coding: utf-8 -*-
"""طبقة تجهيز نص النطق (النص الأصلي لا يُمس). تحافظ على تشكيل المصدر ولا تُزيله.
الترتيب: رموز ← عبارات (ﷺ، رضي الله عنه) ← ابن ← لفظ الجلالة (بحسب السياق) ← الوقف."""
import json, os, re, unicodedata
HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, "config.json"), encoding="utf8"))
EXTRA = {}
for _e in json.load(open(os.path.join(HERE, "dictionary.json"), encoding="utf8")).get("words", []):
    EXTRA[re.sub("[\u064b-\u0652\u0670\u0640]", "", _e["match"]).replace("\u0671","ا")] = _e["say"]
MK = '\u064b-\u0652\u0670\u0640'
L = '\u0621-\u064a\u0671'
def bare(t): return re.sub('[' + MK + ']', '', t).replace('\u0671', 'ا')
def tok(w):  # حروف الكلمة بلا تشكيل
    return bare(w)

SALAT = 'صَلَّى اللَّهُ عَلَيْهِ وَسَلَّمَ'
RADI = {'عنه':'رَضِيَ اللَّهُ عَنْهُ','عنها':'رَضِيَ اللَّهُ عَنْهَا','عنهما':'رَضِيَ اللَّهُ عَنْهُمَا',
        'عنهم':'رَضِيَ اللَّهُ عَنْهُمْ','عنهن':'رَضِيَ اللَّهُ عَنْهُنَّ'}
# كلمات إذا سبقت «الله» غير المشكولة فهي مضاف إليه مجرور (قائمة مغلقة وآمنة)
GEN_BEFORE = {'رسول','سبيل','رضوان','عبد','رحمة','كتاب','دين','بيت','حق','ذكر','عند','خشية','وجه','طاعة','حب','محبة','كلمة','نصر','حدود'}

def base_clean(t):
    t = unicodedata.normalize('NFC', t)
    t = re.sub('[\u200e\u200f\u202a-\u202e\u2066-\u2069\ufeff]', '', t)
    t = re.sub(r'\s*«\s*\.\s*»?', '. ', t)            # «.» و «‏.‏» الزائدة → نقطة واحدة
    t = t.replace('«', ': ').replace('»', ' ')
    t = re.sub(r'\s*[،:]\s*:', ':', t)
    t = re.sub(r'\s*[،:]\s*\.', '.', t)
    t = re.sub(r'\.\s*[،:]\s*\.', '.', t)
    t = re.sub(r':\s*،', ':', t)
    t = re.sub(r'\.\s*:\s*\.?', '. ', t)
    t = re.sub(r':\s*\.', '.', t)
    t = re.sub(r'[{}*]', ' ', t)
    t = re.sub(r'\s*ـ\s*', ' ', t)                    # التطويل المعزول بين الأقواس
    return t

def fix_orthography(t):
    # قَالاَ ← قَالَا ، لاَ ← لَا ، إِلاَّ ← إِلَّا (الفتحة على الحرف لا على الألف)
    t = re.sub('([\u0621-\u0648\u064a])(?![\u064b-\u0652])\u0627(\u064e)(\u0651?)', lambda m: m.group(1) + '\u064e' + m.group(3) + 'ا', t)
    # أَىُّ ← أَيُّ ، شَىْءَ ← شَيْءَ  (ى في وسط الكلمة)
    t = re.sub('\u0649(?=[\u064b-\u0652]*[\u0621-\u064a]|[\u064c\u064d\u064f\u0650\u0651\u0652])', 'ي', t)
    return t

NAMES = {'المسيب': lambda p: p.replace('\u064a\u064e\u0651', '\u064a\u0651\u0650').replace('\u064a\u0651\u064e', '\u064a\u0651\u0650')}

SPEECH = re.compile(r'^[وف]?(قال|قالا|قالوا|قالت|قلت|قيل|سئل|يقول|تقول|سالت)$')
NEED_Q = re.compile(r'^[وف]?(قيل|سئل|قلت|سالت)$')
CONTENT = {'حدثنا','اخبرنا','اخبرني','حدثني','سمعت','سمعنا','انبانا','انباني','حدثتني','اخبرتني','عن','ان','نعم'}
INTERROG = {'اي','اين','ماذا','هل','كيف','متى','لماذا','كم'}
def _b(w): return bare(w).replace('أ','ا').replace('إ','ا').replace('آ','ا').replace('ئ','ء').replace('ؤ','ء') if False else bare(w)

def punctuate(t):
    parts = words(t)
    W = [i for i, p in enumerate(parts) if re.match('[' + L + ']', p)]
    key = lambda i: bare(parts[i]).replace('أ','ا').replace('إ','ا')
    def sep_after(k):  # الفاصل بعد الكلمة رقم k في W
        j = W[k] + 1
        return j if j < len(parts) and not re.match('[' + L + ']', parts[j]) else None
    def sep_plain(k):
        j = sep_after(k)
        return j is not None and parts[j].strip() == ''
    # «:» بعد أفعال القول
    for k, i in enumerate(W[:-1]):
        w = key(i); nxt = key(W[k+1])
        if SPEECH.match(w) and sep_plain(k):
            ok = nxt in CONTENT or (NEED_Q.match(w) and ((nxt in INTERROG and '\u0652' not in parts[W[k+1]]) or nxt == 'ثم'))
            if ok: parts[sep_after(k)] = ': '
    # «؟» لسؤال يلي سئل/قيل/قلت
    for k, i in enumerate(W):
        w = key(i)
        if not NEED_Q.match(w): continue
        q = None
        for d in (1, 2, 3):
            if k + d < len(W) and key(W[k+d]) in INTERROG and '\u0652' not in parts[W[k+d]]: q = k + d; break
            if k + d < len(W) and key(W[k+d]) != 'ثم' and d > 1: break
        if q is None: continue
        for e in range(q + 1, min(q + 14, len(W))):
            if SPEECH.match(key(W[e])):
                j = sep_after(e - 1)
                if j is not None:
                    sp = parts[j]
                    if sp.strip() == '': parts[j] = '؟ '
                    elif sp.lstrip().startswith('،'): parts[j] = '؟ '
                break
            j = sep_after(e)
            if j is not None and re.search('[.:؟!]', parts[j]): break
    return ''.join(parts)

def words(t):
    return re.findall('[' + L + MK + ']+|[^' + L + MK + ']+', t)

def prepare(t):
    t = fix_orthography(base_clean(t))
    t = t.replace('ﷺ', ' ' + SALAT + ' ')
    parts = words(t)
    out, i = [], 0
    while i < len(parts):
        p = parts[i]; b = bare(p)
        # صلى الله عليه وسلم (مشكولة أو لا) → صيغة واحدة مضبوطة
        if b == 'صلى' and i + 6 < len(parts):
            seq = [bare(parts[j]) for j in (i+2, i+4, i+6)]
            if seq == ['الله', 'عليه', 'وسلم'] and all(not parts[j].strip() or not re.search('[' + L + ']', parts[j]) for j in (i+1, i+3, i+5)):
                out.append(SALAT); i += 7; continue
        # رضي الله عنه/ها/هما/هم
        if b in ('رضي', 'رضى') and i + 4 < len(parts) and bare(parts[i+2]) == 'الله' and bare(parts[i+4]) in RADI:
            out.append(RADI[bare(parts[i+4])]); i += 5; continue
        # بن → ابن مع بقاء حركة الإعراب نفسها
        if b == 'بن':
            m = re.search('[\u064b-\u0650]', p[1:]) if False else None
            vowel = ''.join(c for c in p if c in '\u064b\u064c\u064d\u064e\u064f\u0650')
            out.append('ابْ' + 'ن' + vowel[-1:] if vowel else 'ابن'); i += 1; continue
        # لفظ الجلالة غير المشكول: يُضبط فقط حين يسبقه مضاف معروف
        if b == 'الله' and p == 'الله':
            prev = next((bare(x) for x in reversed(out) if re.search('[' + L + ']', x)), '')
            out.append('اللَّهِ' if prev in GEN_BEFORE else p); i += 1; continue
        if b in EXTRA: out.append(EXTRA[b]); i += 1; continue
        if b in NAMES: p = NAMES[b](p)
        out.append(p); i += 1
    t = punctuate(''.join(out))
    t = re.sub(r'\s*،(\s*،)+', '،', t); t = re.sub(r'\s+([،.؟!:؛])', r'\1', t)
    t = re.sub(r'([.،؟!:؛])(?=[' + L + '])', r'\1 ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    t = re.sub(r'[\s:،]+$', '', t)
    return t if t[-1:] in '.؟!' else t + '.'


def status(original, tts):
    """Heuristic label only; it is NOT a certification of grammatical or hadith accuracy.
    processed: mostly vocalized input; review: weak/uncertain vocalization; plain: mostly unvocalized.
    """
    letters = len(re.findall('[\u0621-\u064a]', original)) or 1
    ratio = len(re.findall('[\u064b-\u0652]', original)) / letters
    if ratio < 0.05: return 'plain'
    if ratio < 0.5 or re.search('(?<![' + L + '])الله(?![' + L + '])', tts): return 'review'
    return 'processed'
