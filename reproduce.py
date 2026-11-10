"""Reproduce the published finite-archive comparisons and certificate analysis.

Python 3.9+ standard library; run from any current working directory.
Only the frozen 27-observation development file is opened.
"""
from __future__ import annotations
import hashlib
import csv
import itertools
import json
import math
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'selection.csv'
SOURCE_SHA256 = '7ad2caa267ad466db92afc9240aaf4376d8a7bfd1c76cf16bbd912f03c244321'
BUDGETS = (9, 12, 18, 27)
METHODS = ('wor_width', 'wor_challenger', 'cgabs', 'lucb', 'racing', 'greedy', 'round_robin')
EXPECTED_MEANS = {
  9:(892.5578,892.5578,892.5578,892.5578,892.5578,892.5578,892.5578),
 12:(902.9444,894.1322,894.1322,893.9967,886.6767,886.8867,891.1089),
 18:(903.0211,903.0211,903.0211,903.0211,923.7311,923.0278,903.0211),
 27:(926.,926.,926.,926.,926.,926.,926.)
}


def development():
    rows=[]
    with SOURCE.open(newline='') as f:
        for record in csv.DictReader(f):
            rows.append({'policy':[float(record['p1']),float(record['p2']),float(record['p3'])],
                         'replicate':record['replicate'],'cycles':int(record['cycles']),
                         'split':'selection'})
    canonical=(json.dumps(rows,indent=2)+'\n').encode()
    if hashlib.sha256(canonical).hexdigest()!=SOURCE_SHA256:
        raise ValueError('Development data integrity check failed')
    data=defaultdict(list)
    for row in rows:
        data[tuple(row['policy'])].append((row['replicate'],float(row['cycles'])))
    if len(rows)!=27 or len(data)!=9 or any(len(v)!=3 for v in data.values()):
        raise ValueError('Archive shape mismatch')
    if any(len({r for r,v in vals})!=3 for vals in data.values()):
        raise ValueError('Duplicate replicate identifiers')
    return dict(data)


def deterministic(observed, N=3, a=0., b=2000.):
    n = len(observed)
    if n>N or any(not a<=x<=b for x in observed):
        raise ValueError('Outcome violates declared bounds')
    s = sum(observed)
    return ((s+(N-n)*a)/N, (s+(N-n)*b)/N)


def wor_interval(observed, N=3, K=9, alpha=.05, a=0., b=2000.):
    n = len(observed)
    L,U = deterministic(observed,N,a,b)
    if not n or n==N:
        return (L,U)
    delta = alpha/(K*(N-1))
    radius = (b-a)*math.sqrt((1-(n-1)/N)*math.log(2/delta)/(2*n))
    mu = st.mean(observed)
    return max(L,mu-radius), min(U,mu+radius)


def strict_winner(seen,arms,interval):
    bounds={a:interval(seen[a]) for a in arms}
    leader=max(arms,key=lambda a:bounds[a][0])
    if all(bounds[leader][0]>bounds[a][1] for a in arms if a!=leader):
        return leader
    return None


def replay(data, method, budget, seed):
    arms=list(data)
    rng=random.Random(seed)
    queues={a:rng.sample(values,len(values)) for a,values in data.items()}
    seen={a:[] for a in arms}
    for _ in range(budget):
        available=[a for a in arms if queues[a]]
        unseen=[a for a in available if not seen[a]]
        if method in ('cgabs','lucb','racing','greedy','round_robin') and unseen:
            chosen=unseen[0]
        elif method=='round_robin':
            chosen=min(available,key=lambda a:(len(seen[a]),arms.index(a)))
        elif method=='wor_width':
            chosen=max(available,key=lambda a:(wor_interval(seen[a])[1]-wor_interval(seen[a])[0],-arms.index(a)))
        elif method=='wor_challenger':
            bd={a:wor_interval(seen[a]) for a in arms}
            leader=max(arms,key=lambda a:bd[a][0])
            challenger=max((a for a in arms if a!=leader),key=lambda a:bd[a][1])
            pair=[a for a in (leader,challenger) if a in available]
            chosen=max(pair,key=lambda a:(bd[a][1]-bd[a][0],-arms.index(a))) if pair else max(available,key=lambda a:(bd[a][1],-arms.index(a)))
        elif method=='greedy':
            chosen=max(available,key=lambda a:(st.mean(seen[a]),-arms.index(a)))
        elif method=='racing':
            chosen=max(available,key=lambda a:(st.mean(seen[a])+100/math.sqrt(len(seen[a])),-arms.index(a)))
        elif method=='lucb':
            mean={a:st.mean(seen[a]) for a in arms}
            rad=lambda a:2000*math.sqrt(math.log(2*len(arms)*27/.05)/(2*len(seen[a])))
            leader=max(arms,key=lambda a:(mean[a],-arms.index(a)))
            challenger=max((a for a in arms if a!=leader),key=lambda a:(mean[a]+rad(a),-arms.index(a)))
            pair=[a for a in (leader,challenger) if a in available]
            chosen=max(pair,key=lambda a:(rad(a),-arms.index(a))) if pair else min(available,key=lambda a:len(seen[a]))
        elif method=='cgabs':
            bd={a:deterministic(seen[a]) for a in arms}
            leader=max(arms,key=lambda a:(bd[a][0],-arms.index(a)))
            challenger=max((a for a in arms if a!=leader),key=lambda a:(bd[a][1],-arms.index(a)))
            pair=[a for a in (leader,challenger) if a in available]
            chosen=max(pair,key=lambda a:(bd[a][1]-bd[a][0],bd[a][1],-arms.index(a))) if pair else max(available,key=lambda a:(bd[a][1],-arms.index(a)))
        else:
            raise ValueError('Unknown allocation rule')
        _,value=queues[chosen].pop(0)
        seen[chosen].append(value)
    selected=max((a for a in arms if seen[a]),key=lambda a:(st.mean(seen[a]),-arms.index(a)))
    return selected,strict_winner(seen,arms,deterministic)


def subsets(values):
    for n in range(len(values)+1):
        yield from itertools.combinations(values,n)


def certificate_analysis(data,b):
    arms=list(data)
    values={a:[v for _,v in data[a]] for a in arms}
    if any(not 0<=v<=b for xs in values.values() for v in xs):
        raise ValueError('Inconsistent bound')
    means={a:st.mean(v) for a,v in values.items()}
    ordered=sorted(arms,key=lambda a:means[a],reverse=True)
    w,runner=ordered[:2]
    assert means[w]>means[runner]
    Dw=(sum(values[w])-min(values[w]))/len(values[w])
    Cj={a:(sum(values[a])-max(values[a])+b)/len(values[a]) for a in arms if a!=w}
    census=(Dw<=means[runner] and all(x>=means[w] for x in Cj.values()))
    for a in arms:
        xs=values[a];proper=(s for s in subsets(xs) if len(s)<len(xs))
        extreme=(max(deterministic(s,len(xs),0,b)[0] for s in proper) if a==w else min(deterministic(s,len(xs),0,b)[1] for s in proper))
        assert abs(extreme-(Dw if a==w else Cj[a]))<1e-9
    possible=[]
    for sw in subsets(values[w]):
        Lw=deterministic(sw,len(values[w]),0,b)[0]
        steps=len(sw)
        for a in arms:
            if a==w:continue
            fits=[len(s) for s in subsets(values[a]) if deterministic(s,len(values[a]),0,b)[1]<Lw-1e-10]
            if not fits:break
            steps+=min(fits)
        else:
            possible.append(steps)
    earliest=min(possible) if possible else None
    assert census == (earliest==27)
    threshold=max(len(values[a])*means[w]-sum(values[a])+max(values[a]) for a in arms if a!=w)
    return {'upper_bound':b,'winner_mean':means[w],'runner_up_mean':means[runner],
            'maximum_incomplete_winner_lower':Dw,'minimum_incomplete_rival_upper':min(Cj.values()),
            'critical_upper_bound':threshold,'full_census_necessary':census,'earliest_certificate_budget':earliest}


def synthetic_coverage(trials=5000):
    rng=random.Random(14)
    failures=0
    for _ in range(trials):
        populations=[[rng.uniform(0,2000) for j in range(3)] for i in range(9)]
        any_failure=False
        for population in populations:
            mean=st.mean(population)
            order=rng.sample(population,3)
            for n in range(1,4):
                lo,hi=wor_interval(order[:n])
                if not lo-1e-9<=mean<=hi+1e-9:
                    any_failure=True
        failures+=int(any_failure)
    return {'trials':trials,'simultaneous_failures':failures,'alpha':.05}


def main():
    data=development()
    arms=list(data)
    truth={a:st.mean(v for _,v in data[a]) for a in arms}
    winner=max(arms,key=lambda a:truth[a])
    results={}
    for B in BUDGETS:
        output={m:[] for m in METHODS}
        certificates={m:0 for m in METHODS}
        for k in range(300):
            for m in METHODS:
                selected,cert=replay(data,m,B,20261110+k)
                output[m].append(truth[selected])
                certificates[m]+=int(cert is not None)
        summaries={}
        for i,m in enumerate(METHODS):
            y=output[m]
            expected=EXPECTED_MEANS[B][i]
            actual=st.mean(y)
            assert abs(actual-expected)<.000051,(B,m,actual,expected)
            difference=[x-z for x,z in zip(y,output['racing'])]
            summaries[m]={'mean_archive_score':actual,'mean_archive_simple_regret':truth[winner]-actual,
                          'selection_correct_fraction':sum(x==truth[winner] for x in y)/300,
                          'certificates':certificates[m],
                          'mean_paired_difference_vs_racing':st.mean(difference),
                          'median_paired_difference_vs_racing':st.median(difference),
                          'positive_paired_fraction':sum(x>0 for x in difference)/300,
                          'tie_paired_fraction':sum(x==0 for x in difference)/300}
        results[str(B)]=summaries
    sensitivity={str(b):certificate_analysis(data,b) for b in (1500,2000,2500)}
    assert [sensitivity[str(b)]['earliest_certificate_budget'] for b in (1500,2000,2500)]==[25,27,27]
    assert all(sensitivity[str(b)]['critical_upper_bound']==1881 for b in (1500,2000,2500))
    diagnostic=synthetic_coverage()
    assert diagnostic['simultaneous_failures']==0
    out={'data_sha256':SOURCE_SHA256,'protected_outcomes_opened':False,
         'seed_sequence':[20261110,20261409], 'method_budget_checks':28,
         'results':results,'exact_certificate_sensitivity':sensitivity,'synthetic_coverage':diagnostic}
    dest=ROOT/'results.json'
    dest.write_text(json.dumps(out,indent=2)+'\n')
    print('PASS: 28 matched method-budget means, three exact certificate audits, synthetic coverage')
    print('Earliest possible certificate:',{b:sensitivity[str(b)]['earliest_certificate_budget'] for b in (1500,2000,2500)})
    print('Results:',dest)


if __name__=='__main__':
    main()
