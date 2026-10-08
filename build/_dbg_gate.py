import sys, os, re
sys.path.insert(0, r'D:\Dictionary\build')
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import app as A

t = 'I Love You'
print('_EN_WORDS 共', len(A._EN_WORDS), '个；含 i/you/love:',
      ('i' in A._EN_WORDS, 'you' in A._EN_WORDS, 'love' in A._EN_WORDS))
low = ' ' + re.sub(r"[^a-zA-Zà-ÿ' ]", ' ', t).lower() + ' '
print('low =', repr(low))
print('命中的 FR 词:', [w for w in A._FR_WORDS if w in low])
print('norm:', repr(A._norm_sent(t)), repr(A._norm_sent('我爱你')))
print('looks_like_target =', A._looks_like_target(t, 'fr', '我爱你'))