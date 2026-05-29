"""
Video Generator — produces a 30-second MP4 reel in the Kingdom In Action style.
Static KIA background, white serif text, random ambient worship music.
"""
import os, wave, random, tempfile, subprocess, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ── Paths ──────────────────────────────────────────────────────────────────────
ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')
BG_PATH    = os.path.join(ASSETS_DIR, 'background.png')
FONT_PATH  = os.path.join(ASSETS_DIR, 'Caladea-Regular.ttf')

# ── Video settings ─────────────────────────────────────────────────────────────
W, H         = 1080, 1920
FPS          = 30
DURATION     = 30
SAMPLE_RATE  = 44100
FONT_REF_SZ  = 84
REF_Y        = 159
VERSE_Y      = 376
SAFE_BOTTOM  = 1810
TARGET_VBPS  = 4600

# ── Music styles ───────────────────────────────────────────────────────────────
MUSIC = {
    'peaceful_d':    {'label':'Peaceful (D major)',   'key':293.66,'mood':'pad',   'ch':[[293.66,369.99,440.00,587.33],[196.00,246.94,293.66,392.00],[220.00,277.18,329.63,440.00],[246.94,293.66,369.99,493.88]],'rv':0.38,'sh':0.012},
    'uplifting_c':   {'label':'Uplifting (C major)',  'key':261.63,'mood':'bright','ch':[[261.63,329.63,392.00,523.25],[174.61,220.00,261.63,349.23],[196.00,246.94,293.66,392.00],[220.00,261.63,329.63,440.00]],'rv':0.30,'sh':0.018},
    'reflective_am': {'label':'Reflective (A minor)', 'key':220.00,'mood':'soft',  'ch':[[220.00,261.63,329.63,440.00],[174.61,220.00,261.63,349.23],[196.00,246.94,293.66,392.00],[146.83,174.61,220.00,293.66]],'rv':0.45,'sh':0.008},
    'majestic_g':    {'label':'Majestic (G major)',   'key':196.00,'mood':'organ', 'ch':[[196.00,246.94,293.66,392.00],[130.81,164.81,196.00,261.63],[146.83,185.00,220.00,293.66],[164.81,207.65,246.94,329.63]],'rv':0.35,'sh':0.010},
    'gentle_f':      {'label':'Gentle (F major)',     'key':174.61,'mood':'soft',  'ch':[[174.61,220.00,261.63,349.23],[116.54,146.83,174.61,233.08],[130.81,164.81,196.00,261.63],[146.83,185.00,220.00,293.66]],'rv':0.50,'sh':0.006},
    'hopeful_e':     {'label':'Hopeful (E major)',    'key':164.81,'mood':'bright','ch':[[164.81,207.65,246.94,329.63],[110.00,138.59,164.81,220.00],[123.47,155.56,185.00,246.94],[138.59,164.81,207.65,277.18]],'rv':0.28,'sh':0.020},
    'solemn_dm':     {'label':'Solemn (D minor)',     'key':293.66,'mood':'pad',   'ch':[[293.66,349.23,440.00,587.33],[220.00,261.63,329.63,440.00],[174.61,220.00,261.63,349.23],[196.00,246.94,293.66,392.00]],'rv':0.55,'sh':0.005},
    'praise_bb':     {'label':'Praise (Bb major)',    'key':233.08,'mood':'organ', 'ch':[[233.08,293.66,349.23,466.16],[155.56,196.00,233.08,311.13],[174.61,220.00,261.63,349.23],[196.00,233.08,293.66,392.00]],'rv':0.25,'sh':0.022},
}

def _tone(mood, freq, t, vol):
    if   mood=='bright': h=[0.45,0.30,0.15,0.08,0.02]; p=[1,2,3,5,7]
    elif mood=='organ':  h=[0.40,0.32,0.18,0.06,0.04]; p=[1,2,3,4,6]
    elif mood=='soft':   h=[0.65,0.20,0.10,0.05,0.00]; p=[1,2,3,.5,1]
    else:                h=[0.52,0.24,0.13,0.07,0.04]; p=[1,2,3,4,.5]
    return sum(vol*h[i]*np.sin(2*np.pi*freq*p[i]*t) for i in range(5))

def _gen_music(out_path, style_key=None):
    if not style_key or style_key not in MUSIC:
        style_key = random.choice(list(MUSIC.keys()))
    st  = MUSIC[style_key]
    sr  = SAMPLE_RATE
    n   = sr * DURATION
    sig = np.zeros(n, dtype=np.float64)
    cd  = DURATION / len(st['ch'])
    for ci, freqs in enumerate(st['ch']):
        ss = int(ci*cd*sr); ee = min(int(ss+cd*sr), n)
        tc = np.linspace(0, cd, ee-ss, endpoint=False)
        cs = sum(_tone(st['mood'], f, tc, [0.40,0.22,0.16,0.10][fi]) for fi,f in enumerate(freqs))
        fl = int(min(0.85*sr,(ee-ss)//4)); env=np.ones(ee-ss)
        env[:fl]=np.linspace(0,1,fl)**2; env[-fl:]=np.linspace(1,0,fl)**2
        sig[ss:ee] += cs*env
    tf = np.linspace(0,DURATION,n,endpoint=False)
    for sf in [st['key']*3, st['key']*4, st['key']*6]:
        sig += st['sh']*np.sin(2*np.pi*sf*tf)*np.sin(2*np.pi*0.28*tf)
    def rv(s,ms,dc): d=int(ms*sr/1000); o=s.copy(); (o.__setitem__(slice(d,None),o[d:]+s[:len(s)-d]*dc) if d<len(s) else None); return o
    r=st['rv']; sig=rv(rv(rv(sig,75,r),155,r*.55),310,r*.30)
    fi,fo=int(1.6*sr),int(2.2*sr)
    sig[:fi]*=np.linspace(0,1,fi)**1.5; sig[-fo:]*=np.linspace(1,0,fo)**1.5
    pk=np.max(np.abs(sig))
    if pk>0: sig=sig/pk*0.70
    with wave.open(out_path,'w') as wf:
        wf.setnchannels(1); wf.setsampwidth(2)
        wf.setframerate(sr); wf.writeframes((sig*32767).astype(np.int16).tobytes())
    return st['label']

# ── Video rendering ────────────────────────────────────────────────────────────
_bg_cache = None
def _get_bg():
    global _bg_cache
    if _bg_cache is None:
        _bg_cache = Image.open(BG_PATH).convert('RGB').resize((W,H), Image.LANCZOS)
    return _bg_cache

def _tw(text, font):
    bb = ImageDraw.Draw(Image.new('RGB',(1,1))).textbbox((0,0),text,font=font)
    return bb[2]-bb[0]

def _ls(font):
    d = ImageDraw.Draw(Image.new('RGB',(1,1)))
    a = d.textbbox((0,0),'Tg\nTg',font=font); b = d.textbbox((0,0),'Tg',font=font)
    return (a[3]-a[1])-(b[3]-b[1])

def _wrap(text, font, max_w):
    d=ImageDraw.Draw(Image.new('RGB',(1,1)))
    words,lines,cur=text.split(),[],''
    for w in words:
        t=(cur+' '+w).strip()
        if d.textbbox((0,0),t,font=font)[2]<=max_w: cur=t
        else:
            if cur: lines.append(cur)
            cur=w
    if cur: lines.append(cur)
    return lines

def _fit(text):
    for sz in range(115,71,-2):
        f=ImageFont.truetype(FONT_PATH,sz); sp=_ls(f)
        for mw in range(820,1082,20):
            lns=_wrap(text,f,mw)
            if VERSE_Y+(len(lns)-1)*sp<=SAFE_BOTTOM:
                return f,sp,lns
    f=ImageFont.truetype(FONT_PATH,72); sp=_ls(f)
    return f,sp,_wrap(text,f,1000)

def _put(frame, text, font, y, alpha):
    a=int(255*max(0.0,min(1.0,alpha)))
    if a==0: return frame
    x=(W-_tw(text,font))//2
    ov=Image.new('RGBA',(W,H),(0,0,0,0))
    ImageDraw.Draw(ov).text((x,y),text,font=font,fill=(255,255,255,a))
    return Image.alpha_composite(frame,ov)

def _frame(t, ref_font, ref_text, vf, vs, vlines):
    frame=_get_bg().copy().convert('RGBA')
    vig=Image.new('RGBA',(W,H),(0,0,0,0)); vd=ImageDraw.Draw(vig)
    for i in range(250):
        a=int(65*(1-i/250)**1.2); vd.line([(0,i),(W,i)],fill=(0,0,0,a))
    frame=Image.alpha_composite(frame,vig)
    fo=DURATION-1.2
    def fa(st=0.0):
        t2=t-st
        if t2<=0: return 0.0
        if t2<0.7: return (t2/0.7)**0.55
        if t>fo: return max(0,(DURATION-t)/1.2)**0.55
        return 1.0
    frame=_put(frame,ref_text,ref_font,REF_Y,fa())
    for i,line in enumerate(vlines):
        frame=_put(frame,line,vf,VERSE_Y+i*vs,fa(st=0.5+i*0.22))
    return frame.convert('RGB')

# ── Public function ────────────────────────────────────────────────────────────
def generate_reel(reference: str, verse_text: str) -> str:
    """
    Generates a 30-second MP4 reel.
    Returns path to the generated MP4 file (caller is responsible for cleanup).
    """
    tmp = tempfile.mkdtemp(prefix='kia_')
    out = os.path.join(tmp, 'reel.mp4')
    try:
        ref_font = ImageFont.truetype(FONT_PATH, FONT_REF_SZ)
        vf, vs, vlines = _fit(verse_text)
        total = FPS * DURATION
        for i in range(total):
            _frame(i/FPS, ref_font, reference, vf, vs, vlines).save(
                f'{tmp}/f{i:05d}.jpg', quality=96)

        wav = f'{tmp}/music.wav'
        music_label = _gen_music(wav)

        subprocess.run([
            'ffmpeg','-y','-framerate',str(FPS),
            '-i',f'{tmp}/f%05d.jpg','-i',wav,
            '-c:v','libx264','-profile:v','high','-level','4.0',
            '-b:v',f'{TARGET_VBPS}k','-maxrate','5200k','-bufsize','9000k',
            '-pix_fmt','yuv420p','-preset','slow','-movflags','+faststart',
            '-c:a','aac','-b:a','128k','-ar','44100','-shortest', out
        ], check=True, capture_output=True)

        # Move final file out of tmp so caller can keep it after cleanup
        final = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        final.close()
        shutil.copy(out, final.name)
        return final.name

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
