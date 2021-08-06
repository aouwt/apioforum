# various utility things

import hsluv
import hashlib

# same algorithm as xep-0392
def gen_colour(s):
    b=s.encode("utf-8")
    h=hashlib.sha1(b)
    two_bytes=h.digest()[:2]
    val = int.from_bytes(two_bytes, 'little')
    angle = 360*(val/65536)
    col = hsluv.hsluv_to_hex([angle, 80, 70])
    return col
    
    
