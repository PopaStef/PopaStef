import math, random, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

W, H, FPS, DUR = 1080, 1920, 30, 14.0
N = int(DUR * FPS)
UP = '/root/.claude/uploads/e3f9dc8d-eacc-5954-a8a2-047060305802/'
FONT = '/usr/share/fonts/opentype/inter/InterDisplay-Black.otf'
NAVY = (11, 31, 122); NAVY2 = (8, 22, 92); DEEP = (4, 10, 50)
CYAN = (43, 179, 207); LIME = (143, 209, 79); WHITE = (255, 255, 255)

def font(s): return ImageFont.truetype(FONT, s)
def clamp(x, a=0., b=1.): return max(a, min(b, x))
def ease_out(t): t = clamp(t); return 1 - (1 - t) ** 3
def ease_in(t): t = clamp(t); return t ** 3
def back_out(t, s=1.9):
    t = clamp(t) - 1; return t * t * ((s + 1) * t + s) + 1
def prog(t, a, b): return clamp((t - a) / (b - a))

# ---------- assets ----------
front = Image.open('loris_front.png').convert('RGBA')
jump = Image.open('loris_jump.png').convert('RGBA')
logo = Image.open(UP + '6b2e6fa3-image.png').convert('RGBA')
# logo: drop white background
la = np.asarray(logo).astype(int)
white = (la[..., 0] > 245) & (la[..., 1] > 245) & (la[..., 2] > 245)
la[..., 3] = np.where(white, 0, la[..., 3])
logo = Image.fromarray(la.astype('uint8'))
cards = [Image.open(f).convert('RGB') for f in ('arena.jpg', 'team.jpg', 'city.jpg')]

def scaled(im, h):
    return im.resize((int(im.width * h / im.height), h), Image.LANCZOS)

FRONT_H = 1000
front_big = scaled(front, FRONT_H)
alpha = front_big.split()[3]
sil = Image.new('RGBA', front_big.size, DEEP + (255,)); sil.putalpha(alpha)
glow_a = alpha.filter(ImageFilter.MaxFilter(15)).filter(ImageFilter.GaussianBlur(14))
glow = Image.new('RGBA', front_big.size, CYAN + (255,)); glow.putalpha(glow_a)
pad = 60
def padded(im):
    p = Image.new('RGBA', (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0)); p.alpha_composite(im, (pad, pad)); return p
sil_p, glow_p, col_p = padded(sil), padded(glow), padded(front_big)
white_sil = Image.new('RGBA', front_big.size, WHITE + (255,)); white_sil.putalpha(alpha); white_sil_p = padded(white_sil)

# ---------- background rays ----------
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
def rays_bg(t, cx, cy, c1, c2, glowc, n=18, speed=0.25):
    ang = np.arctan2(yy - cy, xx - cx) + t * speed
    r = np.hypot(xx - cx, yy - cy)
    m = (np.floor(ang / (2 * np.pi) * n * 2) % 2)[..., None]
    base = np.where(m > 0, np.array(c1, np.float32), np.array(c2, np.float32))
    g = np.exp(-(r / 520.0) ** 2)[..., None]
    base = base * (1 - g * 0.85) + np.array(glowc, np.float32) * g * 0.85
    vig = np.clip(1 - (r / 1500.0) ** 2 * 0.55, 0.3, 1)[..., None]
    return Image.fromarray(np.clip(base * vig, 0, 255).astype('uint8'), 'RGB').convert('RGBA')

def text_img(txt, size, fill=WHITE, stroke=NAVY, sw=14, shadow=True, spacing=0):
    f = font(size)
    d = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    bb = d.multiline_textbbox((0, 0), txt, font=f, stroke_width=sw, align='center', spacing=spacing)
    w, h = int(bb[2] - bb[0] + 40), int(bb[3] - bb[1] + 50)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    if shadow:
        dr.multiline_text((20 - bb[0], 32 - bb[1]), txt, font=f, fill=(0, 0, 0, 110), stroke_width=sw, stroke_fill=(0, 0, 0, 110), align='center', spacing=spacing)
    dr.multiline_text((20 - bb[0], 20 - bb[1]), txt, font=f, fill=fill, stroke_width=sw, stroke_fill=stroke, align='center', spacing=spacing)
    return im

def paste_center(dst, im, cx, cy, scale=1.0, rot=0.0, opacity=1.0):
    if scale <= 0.01 or opacity <= 0: return
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    if rot: im = im.rotate(rot, Image.BICUBIC, expand=True)
    if opacity < 1:
        a = im.split()[3].point(lambda v: int(v * opacity)); im = im.copy(); im.putalpha(a)
    dst.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def pill(txt, size=54, bg=LIME, fg=NAVY):
    f = font(size); d = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    bb = d.textbbox((0, 0), txt, font=f)
    w, h = int(bb[2] - bb[0] + 70), int(bb[3] - bb[1] + 44)
    im = Image.new('RGBA', (w + 12, h + 16), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    dr.rounded_rectangle((6, 12, w + 6, h + 12), h // 2, fill=(0, 0, 0, 90))
    dr.rounded_rectangle((6, 4, w + 6, h + 4), h // 2, fill=bg, outline=NAVY, width=6)
    dr.text((6 + 35 - bb[0], 4 + 22 - bb[1]), txt, font=f, fill=fg)
    return im

TITLE = text_img('CINE ESTE\nACEASTĂ\nMASCOTĂ?', 112, sw=16, spacing=4)
QMARK = text_img('?', 300, fill=LIME, sw=18)
HINTS = [pill('INDICIU 1 · OCHI URIAȘI'), pill('INDICIU 2 · HANORAC NEON'), pill('INDICIU 3 · CONSTRUIEȘTE ROBOȚI')]
NUMS = {n: text_img(str(n), 260, fill=LIME, sw=18) for n in (3, 2, 1)}
ANSWER_SMALL = text_img('E...', 120, sw=16)
ANSWER = text_img('LoRIS!', 230, fill=LIME, sw=22)
SUB1 = text_img('Mascota echipei de robotică', 64, sw=10)
SUB2 = text_img('Facultatea de Automatică\nși Calculatoare', 56, fill=CYAN, stroke=DEEP, sw=10, spacing=8)
HANDLE = text_img('@loris_ac  ·  loris-robotics.ro', 52, sw=0, shadow=False)
FOLLOW = pill('+ URMĂREȘTE', 54, bg=LIME, fg=NAVY)
LOGO_BIG = scaled(logo.crop(logo.getbbox()), 560)
WORD = text_img('LoRIS', 170, fill=WHITE, sw=0, shadow=False)
JUMP_BIG = scaled(jump, 720)

def card_img(img, w=460, h=700):
    c = img.copy(); c = c.resize((w, int(c.height * w / c.width)), Image.LANCZOS).crop((0, 0, w, h))
    im = Image.new('RGBA', (w + 36, h + 36), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    dr.rounded_rectangle((8, 14, w + 28, h + 34), 28, fill=(0, 0, 0, 100))
    dr.rounded_rectangle((0, 0, w + 20, h + 20), 28, fill=WHITE)
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w, h), 20, fill=255)
    cr = c.convert('RGBA'); cr.putalpha(m); im.alpha_composite(cr, (10, 10))
    return im
CARDS = [card_img(c) for c in cards]

# confetti
random.seed(7)
CONF = [dict(x=random.choice([-40, W + 40]), y=random.uniform(-400, -20), vx=random.uniform(150, 700), vy=random.uniform(-2300, -1300),
             s=random.uniform(14, 30), r=random.uniform(0, 360), vr=random.uniform(-500, 500),
             c=random.choice([LIME, CYAN, WHITE, (255, 214, 90), (120, 150, 230)])) for _ in range(170)]
def draw_confetti(img, tt):
    if tt < 0: return
    d = ImageDraw.Draw(img)
    for p in CONF:
        dirx = 1 if p['x'] < 0 else -1
        x = p['x'] + dirx * p['vx'] * tt
        y = H + 40 + p['vy'] * tt + 1500 * tt * tt
        if y > H + 50: continue
        a = math.radians(p['r'] + p['vr'] * tt); s = p['s']
        w2 = s * abs(math.cos(a * 1.7)) * 0.5 + 3
        pts = [(x + math.cos(a) * s - math.sin(a) * w2, y + math.sin(a) * s + math.cos(a) * w2),
               (x - math.cos(a) * s - math.sin(a) * w2, y - math.sin(a) * s + math.cos(a) * w2),
               (x - math.cos(a) * s + math.sin(a) * w2, y - math.sin(a) * s - math.cos(a) * w2),
               (x + math.cos(a) * s + math.sin(a) * w2, y + math.sin(a) * s - math.cos(a) * w2)]
        d.polygon(pts, fill=p['c'])

T_REVEAL, T_PART3, T_END = 6.0, 8.3, 12.0
CX, CY = W / 2, 1030

def frame(i):
    t = i / FPS
    if t < T_PART3:
        revealed = t >= T_REVEAL
        if not revealed:
            img = rays_bg(t, CX, CY, NAVY, NAVY2, CYAN, speed=0.35)
        else:
            img = rays_bg(t, CX, CY, (20, 60, 170), NAVY, (190, 240, 255), speed=0.9)
        # silhouette / reveal
        intro = back_out(prog(t, 0.25, 0.95))
        bob = math.sin(t * 3.2) * 14
        if not revealed:
            sc = 0.92 * intro
            paste_center(img, glow_p, CX, CY + bob, sc)
            paste_center(img, sil_p, CX, CY + bob, sc)
            # floating ?s
            for k, (qx, qy, ph) in enumerate([(170, 760, 0), (910, 650, 1.7), (900, 1330, 3.1)]):
                a = prog(t, 0.9 + k * 0.25, 1.3 + k * 0.25)
                paste_center(img, QMARK, qx, qy + math.sin(t * 2.5 + ph) * 18, 0.55 * back_out(a), rot=math.sin(t * 2 + ph) * 12)
        else:
            rt = t - T_REVEAL
            draw_confetti(img, rt)
            sc = 0.92 * (1 + 0.14 * math.exp(-rt * 6) * math.cos(rt * 22))
            paste_center(img, col_p, CX, CY + bob, sc)
            if rt < 0.35:
                paste_center(img, white_sil_p, CX, CY + bob, sc, opacity=1 - rt / 0.35)
        # title
        tin = back_out(prog(t, 0.0, 0.5))
        tout = 1 - ease_in(prog(t, T_REVEAL - 0.25, T_REVEAL))
        if tout > 0:
            paste_center(img, TITLE, W / 2, 290, 1.0 * tin * (0.6 + 0.4 * tout), rot=-3 * math.sin(t * 2.0), opacity=tout)
        # hints
        if not revealed:
            for k, ht in enumerate([1.9, 2.9, 3.9]):
                a = prog(t, ht, ht + 0.35)
                if a > 0:
                    x = W / 2 + (1 - ease_out(a)) * 900 * (1 if k % 2 == 0 else -1)
                    paste_center(img, HINTS[k], x, 1590 + k * 0, 1.0, opacity=1 if t < ht + 1.0 or k == 2 and t < 4.4 else 0) if False else None
            # stack hints: show the latest one fully, keep it simple
            cur = None
            for k, ht in enumerate([1.9, 2.9, 3.9]):
                if t >= ht: cur = (k, ht)
            if cur and t < 4.45:
                k, ht = cur
                a = prog(t, ht, ht + 0.35)
                x = W / 2 + (1 - ease_out(a)) * 900 * (1 if k % 2 == 0 else -1)
                paste_center(img, HINTS[k], x, 1640)
            # countdown
            for n, nt in ((3, 4.45), (2, 4.95), (1, 5.45)):
                if nt <= t < nt + 0.5:
                    a = (t - nt) / 0.5
                    paste_center(img, NUMS[n], W / 2, 1640, 0.5 + back_out(a * 2) * 0.6, opacity=1 - ease_in(prog(a, 0.7, 1)))
        else:
            rt = t - T_REVEAL
            paste_center(img, ANSWER_SMALL, W / 2, 250, back_out(prog(rt, 0.0, 0.3)), rot=-4)
            paste_center(img, ANSWER, W / 2, 1690, back_out(prog(rt, 0.15, 0.55)), rot=-3 + math.sin(t * 3) * 2)
            # flash
            if rt < 0.25:
                fl = Image.new('RGBA', (W, H), (255, 255, 255, int(255 * (1 - rt / 0.25))))
                img.alpha_composite(fl)
        # exit wipe into part 3
        w = prog(t, T_PART3 - 0.3, T_PART3)
        if w > 0:
            d = ImageDraw.Draw(img); x = int(W * 1.6 * ease_in(w))
            d.polygon([(x - 500, 0), (x, 0), (x - 300, H), (x - 800, H)], fill=LIME)
            d.polygon([(0, 0), (x - 500, 0), (x - 800, H), (0, H)], fill=NAVY)
        return img.convert('RGB')
    elif t < T_END:
        pt = t - T_PART3
        img = rays_bg(t, W / 2, 1150, NAVY, NAVY2, CYAN, speed=0.3)
        # entry wipe remainder
        # cards fan
        specs = [(-1, 250, 760, -10), (1, 830, 760, 9), (0, 540, 700, -2)]
        for k, (side, cx, cy, rot) in enumerate(specs):
            a = ease_out(prog(pt, 0.1 + k * 0.18, 0.6 + k * 0.18))
            x = cx + (1 - a) * 900 * (side if side else 1)
            paste_center(img, CARDS[[0, 2, 1][k]], x, cy + math.sin(t * 2 + k) * 8, 0.78, rot=rot * a)
        # jump loris bouncing
        jt = (pt * 1.6) % 1.0
        hop = abs(math.sin(math.pi * jt)) * 70
        a = back_out(prog(pt, 0.5, 1.0))
        paste_center(img, JUMP_BIG, W / 2, 1300 - hop, a)
        paste_center(img, SUB1, W / 2, 1620, back_out(prog(pt, 0.8, 1.2)))
        paste_center(img, SUB2, W / 2, 1760, back_out(prog(pt, 1.0, 1.4)))
        d = ImageDraw.Draw(img)
        # entry wipe (navy/lime sweeping out)
        w = prog(pt, 0, 0.3)
        if w < 1:
            x = int(W * 1.6 * ease_out(w)) + 0
            d.polygon([(x, 0), (W + 900, 0), (W + 900, H), (x - 300, H)], fill=NAVY)
            d.polygon([(x - 500, 0), (x, 0), (x - 300, H), (x - 800, H)], fill=LIME) if False else None
        return img.convert('RGB')
    else:
        et = t - T_END
        img = Image.new('RGBA', (W, H), (12, 36, 140, 255))
        paste_center(img, LOGO_BIG, W / 2, 760, back_out(prog(et, 0.0, 0.45)))
        paste_center(img, WORD, W / 2, 1140, back_out(prog(et, 0.15, 0.6)))
        paste_center(img, HANDLE, W / 2, 1290, 1, opacity=prog(et, 0.4, 0.8))
        paste_center(img, FOLLOW, W / 2, 1480, back_out(prog(et, 0.6, 1.0)) * (1 + 0.04 * math.sin(et * 8)))
        fi = 1 - prog(et, 0, 0.2)
        if fi > 0: img.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(255 * fi))))
        return img.convert('RGB')

if __name__ == '__main__':
    if len(sys.argv) > 1:
        for s in sys.argv[1:]:
            frame(int(float(s) * FPS)).resize((540, 960)).save(f'prev_{s}.jpg')
        sys.exit()
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', 'video_noaudio.mp4'], stdin=subprocess.PIPE)
    for i in range(N):
        p.stdin.write(frame(i).tobytes())
        if i % 60 == 0: print(i, flush=True)
    p.stdin.close(); p.wait()
