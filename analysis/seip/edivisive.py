"""E-divisive change-point detection (Matteson and James, JASA 2014), univariate, alpha=1.
Hierarchical bisection; each candidate is kept if a permutation test gives p < sig."""
import numpy as np

def _qstat(x, min_size):
    n=len(x); best=(-1,None)
    D=np.abs(x[:,None]-x[None,:])
    for t in range(min_size, n-min_size+1):
        a, b = D[:t,:t], D[t:,t:]
        ab = D[:t,t:]
        m, k = t, n-t
        e = 2*ab.mean() - a.mean() - b.mean()
        q = m*k/(m+k)*e
        if q > best[0]: best=(q,t)
    return best

def e_divisive(x, sig=0.05, perms=199, min_size=3, seed=0):
    rng=np.random.default_rng(seed); x=np.asarray(x,float)
    cps=[]; segs=[(0,len(x))]
    while True:
        cand=None
        for (s,e) in segs:
            if e-s < 2*min_size: continue
            q,t=_qstat(x[s:e],min_size)
            if t is None: continue
            if cand is None or q>cand[0]: cand=(q,s+t,s,e)
        if cand is None: break
        q,t,s,e=cand
        seg=x[s:e]; cnt=0
        for _ in range(perms):
            qp,_=_qstat(rng.permutation(seg),min_size)
            if qp>=q: cnt+=1
        p=(cnt+1)/(perms+1)
        if p>=sig: break
        cps.append((t,p)); segs.remove((s,e)); segs+= [(s,t),(t,e)]
    return sorted(cps)
