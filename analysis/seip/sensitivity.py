import numpy as np, json
from collections import defaultdict
from common import *
from edivisive import e_divisive
R=load()
def series(b,col,sc):
    d=defaultdict(list)
    for r in R:
        if r['branch']==b and r['routes']==sc and r[col] is not None: d[r['date']].append(r[col])
    ds=sorted(d); return ds, np.array([np.median(d[k]) for k in ds])
S={}
for b in ['main','v2.4.x','v2.3.x']:
    for col in ['setup_time_s','teardown_time_s','controller_restart_time_s']:
        for sc in ['1000','5000']:
            ds,y=series(b,col,sc)
            if len(y)>=20: S[(b,col,sc)]=(ds,y)
known=('main','teardown_time_s','5000')
out={'relative':[], 'edivisive':[]}
for w in (3,7,14):
    for k in (1.25,1.5,2.0,3.0):
        fa=0; first=None; n=0
        for key,(ds,y) in S.items():
            for i in range(w,len(y)):
                base=np.median(y[i-w:i]); n+=1
                if y[i]>k*base or y[i]<base/k:
                    if key==known and '2026-08-13'<=ds[i]<='2026-08-13'+'' : first=first or ds[i]
                    elif key==known and ds[i]<= '2026-08-%02d'%(13+w): pass
                    else: fa+=1
        out['relative'].append(dict(window=w,k=k,first=first,false_alarms=fa,series_nights=n,per_night=round(fa/ (len(S['main','setup_time_s','1000'][1])-w),2)))
step={'setup_time_s':1.0,'teardown_time_s':0.1,'controller_restart_time_s':0.5}
for sig in (0.01,0.05):
    for ms in (3,5):
        det=[]; 
        for key,(ds,y) in S.items():
            for t,p in e_divisive(y,sig=sig,min_size=ms):
                before=np.median(y[:t]); after=np.median(y[t:])
                det.append(dict(series='|'.join(key), date=ds[t], p=round(p,3), before=round(before,3), after=round(after,3), above_floor=bool(abs(after-before)>=step[key[1]])))
        out['edivisive'].append(dict(sig=sig,min_size=ms,detections=det))
# noise profile per series: CV of nightly medians, distinct quantised levels in individual values, k8s min-max median paired diff
noise=[]
for key,(ds,y) in S.items():
    b,col,sc=key
    vals=[r[col] for r in R if r['branch']==b and r['routes']==sc and r[col] is not None]
    lv=len(set(int(round(v/step[col])) for v in vals))
    pair=defaultdict(dict)
    for r in R:
        if r['branch']==b and r['routes']==sc and r[col] is not None: pair[(r['date'],r['validation_mode'])].setdefault(r['k8s'],[]).append(r[col])
    diffs=[np.median(v['max_versions'])-np.median(v['min_versions']) for v in pair.values() if 'max_versions' in v and 'min_versions' in v]
    noise.append(dict(series='|'.join(key), nights=len(y), median=round(float(np.median(vals)),3), cv_nightly=round(float(np.std(y)/np.mean(y)),3), levels=lv, k8s_diff_median=round(float(np.median(diffs)),3)))
out['noise']=noise
json.dump(out,open('sensitivity.json','w'),indent=1)
for r in out['relative']: print(r)
for e in out['edivisive']: print(e['sig'],e['min_size'],[(d['series'],d['date'],d['before'],d['after'],d['above_floor']) for d in e['detections']])
for n in noise: print(n)
