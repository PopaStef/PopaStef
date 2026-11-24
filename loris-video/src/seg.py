from PIL import Image, ImageFilter
import numpy as np
from scipy import ndimage as ndi
src=Image.open('/root/.claude/uploads/e3f9dc8d-eacc-5954-a8a2-047060305802/f2ab8e4b-image.png').convert('RGB')
def seg(box, out, floory, tol=24, shoe=None):
    im=src.crop(box); a=np.asarray(im).astype(int)
    H,W,_=a.shape
    rowbg=np.stack([a[:,2,:],a[:,-3,:]]).mean(0)  # per-row bg
    d=np.abs(a-rowbg[:,None,:]).sum(2)
    isbg=d<tol
    r,g,b=a[...,0],a[...,1],a[...,2]
    light=(r>140)&(np.abs(r-g)<25)&(np.abs(g-b)<25)&(r<232)
    light[:floory]=False
    if shoe:
        x0,y0,x1,y1=shoe; light[y0:y1,x0:x1]=False; isbg_s=isbg[y0:y1,x0:x1]
    cand=isbg|light
    lab,n=ndi.label(cand)
    keep=set()
    for arr in [lab[0],lab[-1],lab[:,0],lab[:,-1]]:
        keep|=set(np.unique(arr))-{0}
    fg=~np.isin(lab,list(keep))
    fg=ndi.binary_opening(fg,iterations=2)
    lab2,n2=ndi.label(fg); sizes=ndi.sum(fg,lab2,range(1,n2+1))
    fg=lab2==(np.argmax(sizes)+1)
    fg=ndi.binary_fill_holes(fg)
    alpha=Image.fromarray((fg*255).astype('uint8')).filter(ImageFilter.GaussianBlur(0.8))
    im.putalpha(alpha); bb=alpha.getbbox(); im=im.crop(bb); im.save(out); print(out,im.size)
seg((0,0,640,690),'loris_front.png',560,shoe=(236,580,404,650))
seg((1440,770,1920,1190),'loris_jump.png',300,tol=30,shoe=(178,340,298,398))
for f in ['loris_front.png','loris_jump.png']:
  im=Image.open(f); bg=Image.new('RGBA',im.size,(255,0,255,255)); bg.alpha_composite(im); bg.convert('RGB').save('chk_'+f)
