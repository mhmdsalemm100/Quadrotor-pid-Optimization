"""Presentation PDF for the completed 30-seed benchmark; uses bundled reportlab."""
from pathlib import Path
import csv,json
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor,white
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph,Table,TableStyle
ROOT=Path(__file__).resolve().parent; OUT=ROOT/'results'; PDF=OUT/'Thirty_Seed_Equal_Budget_Comparison.pdf'
def rows(n): return list(csv.DictReader((OUT/n).open(encoding='utf-8')))
summary=rows('summary.csv'); pairs=rows('paired_comparisons.csv'); robust=rows('robustness_summary.csv'); selected=rows('selected_candidates.csv')
statistics=json.loads((OUT/'statistics.json').read_text()); check=json.loads((OUT/'verification.json').read_text()); cfg=json.loads((OUT/'contract.json').read_text())
methods=['GA','PSO','CSO','DSA','CMA-ES']; budget=cfg['budget']; winner=check['main_median_winner']
pdfmetrics.registerFont(TTFont('Arial',r'C:\Windows\Fonts\arial.ttf')); pdfmetrics.registerFont(TTFont('Arial-Bold',r'C:\Windows\Fonts\arialbd.ttf'))
c=canvas.Canvas(str(PDF),pagesize=(960,540)); c.setTitle('Thirty-seed equal-budget attitude-control optimization comparison'); c.setAuthor('')
page=0; titles=[]
def text(s,x=46,y=125,w=868,size=19,bold=False,color='#17344b'):
    p=Paragraph(s,ParagraphStyle('p',fontName='Arial-Bold' if bold else 'Arial',fontSize=size,leading=size*1.3,textColor=HexColor(color)))
    _,h=p.wrap(w,1000)
    if y+h>497: raise ValueError(f'Overflow page {page}: {s[:40]}')
    p.drawOn(c,x,540-y-h); return h
def start(title,section='RESULTS',sub=''):
    global page
    if page: c.showPage()
    page+=1; titles.append(title); c.setFillColor(white); c.rect(0,0,960,540,fill=1,stroke=0)
    c.setFillColor(HexColor('#00858b')); c.rect(0,532,960,8,fill=1,stroke=0)
    text(section,y=24,size=10,bold=True,color='#00858b'); text(title,y=45,size=27,bold=True)
    if sub: text(sub,y=88,size=12,color='#536a7e')
    c.setStrokeColor(HexColor('#d6e1e7')); c.line(42,34,918,34); c.setFillColor(HexColor('#536a7e')); c.setFont('Arial',9)
    c.drawString(42,19,'ATTITUDE CONTROL | Updated 30-seed benchmark | 05 October 2026'); c.drawRightString(918,19,f'{page:02d}')
def note(s):
    c.setFillColor(HexColor('#edf3f7')); c.roundRect(42,47,876,43,8,fill=1,stroke=0); text(s,x=53,y=457,w=854,size=12)
def table(headers,data,y=125,widths=None,size=15):
    def cell(v,b=False): return Paragraph(str(v),ParagraphStyle('t',fontName='Arial-Bold' if b else 'Arial',fontSize=size,leading=size*1.2,textColor=white if b else HexColor('#17344b')))
    t=Table([[cell(h,True) for h in headers]]+[[cell(v) for v in r] for r in data],colWidths=widths or [876/len(headers)]*len(headers))
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),HexColor('#17344b')),('ROWBACKGROUNDS',(0,1),(-1,-1),[white,HexColor('#edf3f7')]),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
    _,h=t.wrap(876,1000)
    if y+h>497: raise ValueError(f'Table overflow page {page}')
    t.drawOn(c,42,540-y-h)
def picture(name,y=119,h=315,asset=False):
    p=(ROOT/'assets' if asset else OUT/'plots')/(name+'.png'); iw,ih=Image.open(p).size; s=min(876/iw,h/ih)
    c.drawImage(str(p),42+(876-iw*s)/2,540-y-ih*s,width=iw*s,height=ih*s,mask='auto')
def bullets(items,y=126,size=19,gap=16):
    for s in items:
        c.setFillColor(HexColor('#00858b')); c.circle(49,540-y-10,3,fill=1,stroke=0)
        y+=text(s,x=65,y=y,w=848,size=size)+gap

start('Five methods. Thirty seeds. Equal evaluation budget.','UPDATED STUDY','GA | PSO | Cat Swarm (CSO) | Dolphin Swarm (DSA) | CMA-ES')
text('A stronger comparison of controller tuning methods',y=148,size=31,bold=True)
text('I extend my earlier study from three seeds and unequal full-run costs to 30 paired seeds with a strictly enforced evaluation budget.',y=215,size=23)
table(['Completed searches','Budget per search','Total training evaluations'],[['150',f'{budget:,}',f'{150*budget:,}']],y=329,size=21)
note(f'The lowest median final fitness is achieved by {winner}. The following results distinguish typical performance, best runs and validation.')

start('What changed from the previous comparison','01 / PROTOCOL')
table(['Earlier work','Updated benchmark'],[['3 main seeds per method','30 seeds per method; 150 completed runs'],['50 iterations with unequal evaluation counts','Exactly 3264 unique objective evaluations per run'],['CSO/DSA retrospective budget snapshots','Hard stopping inside the search, including partial batches'],['Emphasis on the best selected candidate','Median, mean, spread, ranks, paired tests and all seed winners'],['GA/PSO schedules tied to generation count','GA mutation and PSO inertia tied to budget consumption']],y=125,widths=[418,458],size=17)
note('The plant, gain bounds, fitness and acceptance criteria are unchanged. Earlier folders are retained as historical results.')

start('Equal budget: my exact definition','01 / PROTOCOL')
bullets(['An evaluation means one new gain vector evaluated on all six training scenarios. The source baseline and initial population count toward the cap.',
'Duplicate normalized points, rounded to 13 decimals for caching, do not consume the budget. No dummy evaluations are added.',
'If the last population or probe batch crosses the cap, only the remaining new points are evaluated in deterministic order; the best archive is then returned.',
'The final partial batch may not update optimizer state. This cannot change the returned best evaluated candidate. Runtime is not the controlled budget.'],size=19)

start('Seeds, initialization and search settings','01 / PROTOCOL')
text('Seeds: 11, 29, 47 and 101 through 127. The same stratified 64-point initial population, including the original controller, is used for every method within each seed.',y=123,size=20)
table(['Method','Settings retained from the previous implementation'],[['GA','4 elites; tournament 3; crossover 0.9; mutation 0.25; sigma 0.14 → 0.035; immigrants 0.08'],['PSO','Inertia 0.9 → 0.4; personal/social coefficients 1.7; velocity cap ±0.2'],['CSO','SMP 5; seeking range 0.2; 4/8 coordinates; 13/64 tracing; coefficient 2'],['DSA','2 directions × 2 search times; speed 0.08; acceleration 10; reduction 3'],['CMA-ES','pycma 4.5.0; active full covariance; sigma0 0.25; bounded transform; mean from best initial point']],y=208,widths=[135,741],size=14)

start('Same nonlinear system and controller structure','02 / MODEL')
picture('eq_dynamics',asset=True,y=126,h=228)
text('Roll and pitch use outer angle P loops and inner discrete rate controllers. Yaw uses a rate PI loop. The X mixer, motor lag, torque allocation, damping, gyroscopic effects and inertia coupling are retained.',y=386,size=18)
note('Python equations come from Sim.zip. The optimizer does not use a small-angle approximation or execute MATLAB/Simulink.')

start('Controller mapping and interpretation','02 / MODEL')
picture('eq_controllers',asset=True,y=124,h=240)
text('Roll/pitch outputs clip at ±1. Yaw PI uses forward Euler, integral limit ±0.2 and output limit ±0.5. All four motor commands clip to [0,1].',y=385,size=18)
note('Controller Ts = 1 ms is assumed; mixer period = 4 ms. Export b0/b1 coefficients rather than putting equivalent gains into a different PI form.')

start('Fitness and acceptance criteria are fixed','02 / OBJECTIVE')
picture('eq_fitness',asset=True,y=123,h=238)
text('H = 3 s. Feasibility requires overshoot ≤10%, final error ≤2%, settling within H, clipping duty ≤5%, nonnegative motor speed and limits on uncommanded motion and tilt.',y=382,size=18)
note('V is the summed violation. Infeasible runs remain in the statistics; lower fitness is better. Cost reduction is not a physical speed percentage.')

start('Final fitness: the full 30-seed distribution','03 / RESULTS')
table(['Method','Best','Median','Mean','Sample SD','Feasible'],[[r['method']]+[f'{float(r[k]):.6f}' for k in ['best','median','mean','std']]+[r['feasible_runs']+'/30'] for r in summary],y=137,widths=[121,151,151,151,151,151],size=17)
text(f'{winner} has the lowest median score. Best-of-30 values describe selected extremes and should not be interpreted as the performance expected from a typical run.',y=371,size=20)
note('All methods used exactly the same number of new objective evaluations. This benchmark is for one plant, objective and hyperparameter setting.')

start('Distribution plot: every seed is visible','03 / RESULTS')
picture('01_fitness_distributions',h=320)
note('Dots are individual runs. Boxes summarize the interquartile range and median; no infeasible outcomes were removed.')

start('Convergence at equal computational effort','03 / RESULTS')
picture('02_convergence',h=316)
note('Lines are medians over 30 runs; bands show the interquartile range. The horizontal axis counts unique fitness evaluations, not iterations.')

start('Uncertainty in the estimated performance','03 / RESULTS')
table(['Method','95% CI of mean','95% CI of median','Mean paired rank'],[[r['method'],f"[{float(r['mean_ci95_low']):.6f}, {float(r['mean_ci95_high']):.6f}]",f"[{float(r['median_ci95_low']):.6f}, {float(r['median_ci95_high']):.6f}]",f"{float(r['mean_paired_rank']):.3f}"] for r in summary],y=132,widths=[140,270,270,196],size=17)
text('Intervals use 10,000 bootstrap resamples of the 30 seed blocks. They describe variability from optimizer randomness and do not include uncertainty in the plant model.',y=375,size=19)
note('Lower rank is better. Intervals are percentile-bootstrap intervals and are not multiplicity-adjusted; overlap alone is not a pairwise test.')

start('Paired statistical comparisons','04 / STATISTICS')
text(f"Overall Friedman statistic: <b>{statistics['friedman_statistic']:.5g}</b>. Within-seed permutation p-value: <b>{statistics['within_seed_permutation_p']:.5g}</b>, from 20,000 permutations.",y=121,size=19)
table(['Pair A / B','A wins / ties / B wins','Holm-adjusted p'],[[r['A']+' / '+r['B'],r['A_wins']+' / '+r['ties']+' / '+r['B_wins'],f"{float(r['holm_p']):.4g}"] for r in pairs[:5]],y=207,widths=[274,320,282],size=16)
note('Two-sided paired Wilcoxon tests, Holm correction across all 10 pairs. Wins use lower fitness; numerical ties use a 1e-10 threshold.')

start('Remaining pairs and practical effect sizes','04 / STATISTICS')
table(['Pair A / B','A wins / ties / B wins','Holm-adjusted p'],[[r['A']+' / '+r['B'],r['A_wins']+' / '+r['ties']+' / '+r['B_wins'],f"{float(r['holm_p']):.4g}"] for r in pairs[5:]],y=127,widths=[274,320,282],size=16)
text('The CSV report also gives paired mean differences and their 95% bootstrap intervals. Negative A-minus-B favors A. Statistical evidence and a practically useful improvement are different questions.',y=365,size=19)
note('Wilcoxon uses a symmetric paired-difference null. These tests do not establish general superiority across other control systems or objectives.')

start('Held-out validation of all 150 selected controllers','05 / VALIDATION')
table(['Method','Median passes /60','Range /60','All 60 passed','Combined passes /900'],[[r['method'],r['median_single_axis_passes'],r['min_single_axis_passes']+' - '+r['max_single_axis_passes'],r['controllers_passing_all_60']+'/30',r['total_combined_passes_out_of_900']] for r in robust],y=134,widths=[128,180,174,180,214],size=17)
text('Each seed winner receives the same 18 deterministic hold-outs, 60 single-axis uncertainty cases and 30 combined-axis stress cases. Validation does not choose the gains or the best seed.',y=378,size=19)
note('No separate robust-search or hyperparameter-tuning results are mixed into this main 30-seed experiment.')

start('Robustness variation across seeds','05 / VALIDATION')
picture('03_robustness',h=320)
note('These fixed synthetic cases are reused across controllers. Pass counts are descriptive, not independent hardware success probabilities.')

start('Best versus a typical representative','06 / CANDIDATES')
table(['Method','Best seed','Best fitness','Median-representative seed','Its fitness'],[[m,next(r['seed'] for r in selected if r['method']==m and r['selection']=='best'),f"{float(next(r['fitness'] for r in selected if r['method']==m and r['selection']=='best')):.6f}",next(r['seed'] for r in selected if r['method']==m and r['selection']=='median_representative'),f"{float(next(r['fitness'] for r in selected if r['method']==m and r['selection']=='median_representative')):.6f}"] for m in methods],y=132,widths=[130,130,180,256,180],size=16)
text('The median representative is an actual run closest to the median fitness; ties use seed order. I export both candidates so that a favorable extreme is not confused with typical performance.',y=370,size=19)
note('All exports include exact discrete coefficients and the held-out results of that candidate. Training fitness alone determines these selections.')

start('Best-of-30 response comparison','06 / CANDIDATES','All candidates below are selected by training fitness; these are not median-response curves.')
picture('04_best_responses',y=112,h=328)
note('Physical response depends on the axis and metric. The fastest individual rise or settling time need not give the lowest constrained aggregate fitness.')

start('Updated best-of-30 gain sets','06 / CANDIDATES','Rounded for presentation. Full-precision JSON files and discrete coefficient maps are the implementation authority.')
exports={m:json.loads((OUT/'exports'/f'{m}_best_gains.json').read_text()) for m in methods}
gain_keys=list(exports['GA']['gains'])
gain_labels=['Roll outer K','Roll inner Kp (eq.)','Roll inner Ki (eq.)','Pitch outer K','Pitch inner Kp (eq.)','Pitch inner Ki (eq.)','Yaw Kp','Yaw Ki']
table(['Parameter']+methods,[[label]+[f"{exports[m]['gains'][key]:.6g}" for m in methods] for label,key in zip(gain_labels,gain_keys)],y=120,widths=[236,128,128,128,128,128],size=14)

start('Updated settling-time comparison','06 / CANDIDATES','Best-of-30 candidates; seconds after step, ±2% band with a final 0.25 s in-band hold.')
metric_rows=rows('best_metrics.csv'); cases=['roll_5deg','roll_20deg','pitch_5deg','pitch_20deg','yaw_30dps','yaw_100dps']
table(['Command']+methods,[[case.replace('_',' ')]+[f"{float(next(r['settling_s'] for r in metric_rows if r['controller']==m and r['scenario']==case)):.3f}" for m in methods] for case in cases],y=136,widths=[236,128,128,128,128,128],size=17)
note('The aggregate fitness also includes rise time, normalized integral errors and effort, subject to all constraints. No method must win every row.')

start('My updated conclusion','07 / CONCLUSION')
robust_leader=max(robust,key=lambda r:int(r['controllers_passing_all_60']))
pso_ga=next(r for r in pairs if r['A']=='GA' and r['B']=='PSO')
bullets([f'<b>{winner} gives the best median training fitness.</b> PSO beats GA in {pso_ga["B_wins"]}/30 paired seeds; the Holm-adjusted p-value is {float(pso_ga["holm_p"]):.4f}. This supports a nominal-performance advantage under this protocol.',
f'<b>{robust_leader["method"]} has the most controllers passing all 60 single-axis uncertainty cases: {robust_leader["controllers_passing_all_60"]}/30.</b> For PSO the count is 13/30. I treat this as a sampled speed-versus-robustness trade-off, not a general robustness proof.',
'Every method records 0/900 combined-axis stress passes. Even the best PSO seed passes only 58/60 single-axis cases. I would not transfer a training winner blindly.',
'My next step is matched Simulink validation and a coupled outer-loop design. More seeds strengthen evidence about search randomness; they do not validate the plant or prove global optimality.'],size=18,gap=14)

start('How I will use the results in Simulink','07 / NEXT STEPS')
bullets(['Start from the selected gain JSON and SIMULINK_MAP files. Preserve roll/pitch transfer-function structure, yaw integration convention and all saturations.',
'Confirm inherited controller timing, match motor initialization and command timing, then compare identical traces with Python.',
'Inspect the validation details before deciding between the best and median representative. Failed cases are included in the delivered results.',
'For combined-axis motion, test kinematic compensation or a coupled attitude controller, then repeat the same controlled evaluation protocol.'],size=19,gap=18)

start('Data and references','APPENDIX')
text('<b>Local evidence</b><br/>Sim.zip source files; unchanged model.py and study.py; contract.json with seeds, budget and source hashes; 150 run summaries and evaluation ledgers; 150 complete held-out assessments; best and median gain exports.',y=124,size=19)
text('<b>Algorithm references</b><br/>Kennedy & Eberhart (1995), PSO: doi:10.1109/ICNN.1995.488968.<br/>Chu, Tsai & Pan (2006), Cat Swarm: doi:10.1007/978-3-540-36668-3_94.<br/>Wu, Yao & Yang (2016), Dolphin Swarm: doi:10.1631/FITEE.1500287.<br/>CMA-ES implementation: github.com/CMA-ES/pycma, version 4.5.0.<br/>Statistical definitions: SciPy documentation for friedmanchisquare and wilcoxon.<br/>GA is the real-valued implementation defined in benchmark.py and README.md.',y=246,size=16)
note('The earlier small-seed results are historical. This report supersedes their algorithm comparison for the stated 3264-evaluation budget.')
c.save()
from pypdf import PdfReader
r=PdfReader(PDF); assert len(r.pages)==page and all(len(p.extract_text())>100 for p in r.pages)
(OUT/'pdf_pages.json').write_text(json.dumps(titles,indent=2))
print(f'{PDF}: {page} pages')
