# -*- coding: utf-8 -*-
# تشغيل من جذر المشروع: python test_clean.py   (أي قاعدة جديدة لا يجوز أن تكسر هذه الحالات)
import sys, os, unicodedata
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tts'))
from clean import prepare
N = lambda x: unicodedata.normalize('NFC', x)
CASES = [(
"حَدَّثَنَا أَحْمَدُ بْنُ يُونُسَ، وَمُوسَى بْنُ إِسْمَاعِيلَ، قَالاَ حَدَّثَنَا إِبْرَاهِيمُ بْنُ سَعْدٍ، قَالَ حَدَّثَنَا ابْنُ شِهَابٍ، عَنْ سَعِيدِ بْنِ الْمُسَيَّبِ، عَنْ أَبِي هُرَيْرَةَ، أَنَّ رَسُولَ اللَّهِ صلى الله عليه وسلم سُئِلَ أَىُّ الْعَمَلِ أَفْضَلُ فَقَالَ « إِيمَانٌ بِاللَّهِ وَرَسُولِهِ «‏.‏ قِيلَ ثُمَّ مَاذَا قَالَ « الْجِهَادُ فِي سَبِيلِ اللَّهِ «‏.‏ قِيلَ ثُمَّ مَاذَا قَالَ « حَجٌّ مَبْرُورٌ «‏.‏»",
"حَدَّثَنَا أَحْمَدُ ابْنُ يُونُسَ، وَمُوسَى ابْنُ إِسْمَاعِيلَ، قَالَا: حَدَّثَنَا إِبْرَاهِيمُ ابْنُ سَعْدٍ، قَالَ: حَدَّثَنَا ابْنُ شِهَابٍ، عَنْ سَعِيدِ ابْنِ الْمُسَيِّبِ، عَنْ أَبِي هُرَيْرَةَ، أَنَّ رَسُولَ اللَّهِ صَلَّى اللَّهُ عَلَيْهِ وَسَلَّمَ سُئِلَ: أَيُّ الْعَمَلِ أَفْضَلُ؟ فَقَالَ: إِيمَانٌ بِاللَّهِ وَرَسُولِهِ. قِيلَ: ثُمَّ مَاذَا؟ قَالَ: الْجِهَادُ فِي سَبِيلِ اللَّهِ. قِيلَ: ثُمَّ مَاذَا؟ قَالَ: حَجٌّ مَبْرُورٌ.")]
bad = 0
for src, want in CASES:
    ok = N(prepare(src)) == N(want); bad += (not ok); print('OK ' if ok else 'FAIL', src[:30])
# Regression cases: preserve uncertain forms, expand only requested devotional symbols,
# keep the source untouched (the caller owns original_text), and handle empty input.
EXTRA_CASES = [
    ('ﷺ', 'صَلَّى اللَّهُ عَلَيْهِ وَسَلَّمَ.'),
    ('رَضِيَ اللَّهُ عَنْهُ', 'رَضِيَ اللَّهُ عَنْهُ.'),
    ('رَسُولُ اللهِ', 'رَسُولُ اللهِ.'),  # already vocalized source is not guessed over
    ('', ''),
]
for src, want in EXTRA_CASES:
    got = N(prepare(src))
    ok = got == N(want)
    bad += (not ok)
    print('OK ' if ok else 'FAIL', repr(src), '=>', repr(got))
sys.exit(1 if bad else 0)
