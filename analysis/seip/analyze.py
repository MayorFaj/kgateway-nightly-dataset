import json, numpy as np, datetime
from collections import defaultdict
from common import *
from edivisive import e_divisive
R=load()
out={}
# ---- per-branch summaries (full series) ----
def summ(sel, col):
    x=[r[col] for r in R if sel(r) and r[col] is not None]
    return dict(n=len(x), med=round(pct(x,50),3), p10=round(pct(x,10),3), p90=round(pct(x,90),3), max=round(max(x),3), min=round(min(x),3)) if x else None
br=['v2.2.x','v2.3.x','v2.4.x','main']
for b in br:
    for col in ['setup_time_s','teardown_time_s','controller_restart_time_s']:
        for sc in ['1000','5000','all']:
            out[f'{b}|{col}|{sc}']=summ(lambda r: r['branch']==b and (sc=='all' or r['routes']==sc), col)
# teardown main before/after (step between 12 and 13 Aug)
out['main_td5k_before']=summ(lambda r: r['branch']=='main' and r['routes']=='5000' and r['date']<='2026-08-12','teardown_time_s')
out['main_td5k_after']=summ(lambda r: r['branch']=='main' and r['routes']=='5000' and r['date']>='2026-08-13','teardown_time_s')
out['v24_td5k_before']=summ(lambda r: r['branch']=='v2.4.x' and r['routes']=='5000' and r['date']<='2026-08-12','teardown_time_s')
out['v24_td5k_after']=summ(lambda r: r['branch']=='v2.4.x' and r['routes']=='5000' and r['date']>='2026-08-13','teardown_time_s')
out['v23_td5k']=summ(lambda r: r['branch']=='v2.3.x' and r['routes']=='5000','teardown_time_s')
out['main_td1k']=summ(lambda r: r['branch']=='main' and r['routes']=='1000','teardown_time_s')
# restart strict vs standard on main / v2.4
for b in ['main','v2.4.x']:
    for mode in ['standard','strict']:
        for sc in ['1000','5000']:
            out[f'restart|{b}|{mode}|{sc}']=summ(lambda r: r['branch']==b and r['validation_mode']==mode and r['routes']==sc,'controller_restart_time_s')
            out[f'setup|{b}|{mode}|{sc}']=summ(lambda r: r['branch']==b and r['validation_mode']==mode and r['routes']==sc,'setup_time_s')
# k8s version effect on setup (main)
for b in ['main','v2.4.x','v2.3.x']:
    for k in ['min_versions','max_versions']:
        out[f'setupk8s|{b}|{k}']=summ(lambda r: r['branch']==b and r['k8s']==k,'setup_time_s')
# thresholds headroom
th={('setup_time_s','1000'):30,('setup_time_s','5000'):90,('teardown_time_s','1000'):10,('teardown_time_s','5000'):20}
for (c,sc),t in th.items():
    x=[r[c] for r in R if r['routes']==sc and r[c] is not None]
    out[f'headroom|{c}|{sc}']=dict(max=round(max(x),3), threshold=t, max_frac=round(max(x)/t,3))
# distinct values (quantisation)
for c in ['setup_time_s','teardown_time_s','controller_restart_time_s']:
    x=[r[c] for r in R if r[c] is not None]
    step={'setup_time_s':1,'teardown_time_s':0.1,'controller_restart_time_s':0.5}[c]
    out[f'quant|{c}']=dict(n=len(x), distinct_raw=len(set(x)), distinct_steps=len(set(int(v//step) for v in x)))
# ---- nightly series ----
def series(b,col,sc):
    d=defaultdict(list)
    for r in R:
        if r['branch']==b and r['routes']==sc and r[col] is not None: d[r['date']].append(r[col])
    ds=sorted(d); return ds, np.array([np.median(d[k]) for k in ds])
cpd={}
for b in ['main','v2.4.x','v2.3.x']:
    for col in ['setup_time_s','teardown_time_s','controller_restart_time_s']:
        for sc in ['1000','5000']:
            ds,y=series(b,col,sc)
            if len(y)<20: continue
            cps=e_divisive(y)
            # relative gates: alarm if night > k * median(previous 7) (regression) or < median/k (improvement)
            gates={}
            for k in (1.5,2.0):
                reg=[ds[i] for i in range(7,len(y)) if y[i]>k*np.median(y[i-7:i])]
                imp=[ds[i] for i in range(7,len(y)) if y[i]<np.median(y[i-7:i])/k]
                gates[str(k)]=dict(regression=reg, improvement=imp)
            cv=float(np.std(y)/np.mean(y))
            cpd[f'{b}|{col}|{sc}']=dict(nights=len(y), first=ds[0], last=ds[-1], cps=[(ds[t],round(p,3), round(float(np.median(y[:t] if i==0 else y[cps[i-1][0]:t])),3), round(float(np.median(y[t:(cps[i+1][0] if i+1<len(cps) else len(y))])),3)) for i,(t,p) in enumerate(cps)], gates=gates, cv=round(cv,3))
out['cpd']=cpd
# detection delay for the known step: run E-divisive on main teardown 5k up to each night after 13 Aug
ds,y=series('main','teardown_time_s','5000'); i0=ds.index('2026-08-13')
delay=None
for j in range(i0+1,len(y)+1):
    c=e_divisive(y[:j]); 
    if any(ds[t]=='2026-08-13' for t,_ in c): delay=(j-i0, ds[j-1]); break
out['detect_delay_nights']=delay
json.dump(out,open('results.json','w'),indent=1,default=str)
print(json.dumps({k:v for k,v in out.items() if k!='cpd'},default=str)[:6000])
for k,v in cpd.items(): print(k, v['nights'], 'cv',v['cv'], 'cps',v['cps'], 'gate1.5', {g:len(x) for g,x in v['gates']['1.5'].items()}, 'gate2', {g:len(x) for g,x in v['gates']['2.0'].items()})
print('delay', delay)
