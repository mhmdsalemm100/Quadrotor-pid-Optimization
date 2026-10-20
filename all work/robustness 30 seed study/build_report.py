"""Create the final report only from completed, audited results."""
from pathlib import Path
import csv,json,html,shutil,re
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor,white
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph,Table,TableStyle
from reportlab.lib.utils import ImageReader

ROOT=Path(__file__).resolve().parent; OUT=ROOT/'results'; PDFDIR=ROOT/'output/pdf'
STUDY_DATE='2026-10-05'  # User's Asia/Riyadh study date.
PDFDIR.mkdir(parents=True,exist_ok=True)
def read(name): return json.loads((OUT/name).read_text())
def rows(name):
    with (OUT/name).open(newline='',encoding='utf-8') as f: return list(csv.DictReader(f))
def fmt(x):
    try:
        n=float(x)
        return str(int(n)) if n.is_integer() else f'{n:.5g}'
    except (ValueError,TypeError): return str(x)

def main():
    audit=read('verification.json'); assert audit['completed_runs']==150 and audit['validated_tuned_controllers']==300
    fitness=rows('robust_fitness_summary.csv'); comp=rows('nominal_vs_robust.csv')
    changes=rows('paired_tuning_changes.csv'); selected=rows('selected_candidates.csv'); stats=read('statistics.json')
    corners=rows('corner_validation_summary.csv')
    robust=[r for r in comp if r['mode']=='robust']; nominal=[r for r in comp if r['mode']=='nominal']
    bestfitness=min(fitness,key=lambda r:float(r['median']))
    # A tied validation result is reported as a tie, not broken using the validation set.
    maxmean=max(float(r['mean_mc_passes']) for r in robust)
    bestheld=[r['method'] for r in robust if abs(float(r['mean_mc_passes'])-maxmean)<1e-12]
    conclusion=(f"{bestfitness['method']} has the lowest median robust-training fitness. "
                f"The highest mean held-out single-axis pass count is {maxmean:.2f}/300, achieved by {', '.join(bestheld)}. "
                "Training fitness and held-out robustness answer different questions.")
    bestcorners=[int(r['passes']) for r in corners if r['mode']=='robust' and r['selection']=='best']
    corner_note=f"The five best robust-training exports pass {min(bestcorners)} to {max(bestcorners)} of 1,536 joint-boundary cases."
    fullcorners=[r['method'] for r in corners if r['mode']=='robust' and r['selection']=='best' and int(r['passes'])==1536]
    if fullcorners:
        corner_note+=' Best exports passing all joint-boundary cases: '+', '.join(fullcorners)+'. This selected-candidate result does not describe all 30 seeds.'
    width,height=960,600; margin=44
    c=canvas.Canvas(str(PDFDIR/'Robustness_Optimization_Comparison.pdf'),pagesize=(width,height))
    c.setTitle('Robustness optimization: five methods, 30 seeds, equal budgets')
    c.setAuthor('Attitude-control optimization study')
    pages=[]
    style=ParagraphStyle('body',fontName='Helvetica',fontSize=14,leading=20,textColor=HexColor('#253b4e'))
    def page(title,subtitle=''):
        title=re.sub(r'^\d+\.\s+','',title)
        c.setFillColor(HexColor('#f6f8fb')); c.rect(0,0,width,height,fill=1,stroke=0)
        c.setFillColor(HexColor('#173447')); c.rect(0,height-100,width,100,fill=1,stroke=0)
        c.setFillColor(white); c.setFont('Helvetica-Bold',25); c.drawString(margin,height-48,title)
        c.setFont('Helvetica',12); c.drawString(margin,height-74,subtitle)
        pages.append(title)
    def para(text,y,x=margin,w=width-2*margin,size=14):
        s=ParagraphStyle('p',parent=style,fontSize=size,leading=size*1.4)
        p=Paragraph(text,s); _,h=p.wrap(w,500)
        if y-h<45: raise ValueError(f'Paragraph overflow on {pages[-1]}: bottom={y-h}')
        p.drawOn(c,x,y-h); return y-h-16
    def table(data,y,colwidths=None,size=11,padding=8):
        s=ParagraphStyle('cell',parent=style,fontSize=size,leading=size*1.25)
        cells=[[Paragraph(html.escape(fmt(v)),s) for v in row] for row in data]
        t=Table(cells,colWidths=colwidths or [(width-2*margin)/len(data[0])]*len(data[0]),repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),HexColor('#dce8ef')),('ROWBACKGROUNDS',(0,1),(-1,-1),[white,HexColor('#edf2f6')]),
            ('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),padding),('BOTTOMPADDING',(0,0),(-1,-1),padding),
            ('LINEBELOW',(0,0),(-1,0),1,HexColor('#9eb6c6'))]))
        _,h=t.wrap(width-2*margin,500)
        if y-h<45: raise ValueError(f'Table overflow on {pages[-1]}: bottom={y-h}')
        t.drawOn(c,margin,y-h); return y-h-16
    def figure(name,y=477,h=380):
        path=OUT/'plots'/name; im=ImageReader(str(path)); iw,ih=im.getSize(); w=min(width-2*margin,h*iw/ih); hh=w*ih/iw
        c.drawImage(im,(width-w)/2,y-hh,width=w,height=hh,mask='auto'); return y-hh-10
    def end():
        c.setFont('Helvetica',9); c.setFillColor(HexColor('#617887'))
        c.drawString(margin,23,'Equation-based attitude control | Sampled robustness | Study date '+STUDY_DATE)
        c.drawRightString(width-margin,23,str(len(pages))); c.showPage()

    page('Robustness optimization of attitude control','GA | PSO | Cat Swarm | Dolphin Swarm | CMA-ES')
    y=para('I extended my nominal-response study to tune controller gains while inertia, motor parameters and rotational damping vary.',465,size=20)
    y=para('<b>Completed:</b> 150 robust searches, 30 optimizer seeds per method, 3,264 unique evaluations per search.',y)
    y=para('<b>Independent comparison:</b> the 150 new controllers and all 150 previous nominal-tuned controllers are tested on the same 444 held-out cases.',y)
    y=para(conclusion,y)
    para(corner_note,y,size=13); end()

    page('1. Research question','Can I retain acceptable response when the plant changes?')
    y=para('My earlier objective emphasized fast nominal response. Here I preserve that response score but require the controller to pass it across a fixed set of uncertain training plants.',472)
    y=para('I compare two outcomes: <b>robustness</b> (passing unseen changed plants) and <b>nominal speed</b> (settling time and tracking error on the original plant).',y)
    y=para('I keep the nonlinear source plant, controller architecture, gain bounds, saturation limits and optimizer settings unchanged. Roll and pitch regulate angle; yaw regulates angular rate.',y)
    para('This is a sampled robustness study. Passing all tested cases does not prove robustness over every point in the continuous parameter range.',y); end()

    page('2. Plant equations and the uncertain parameters','Same physical model as the source Simulink system')
    y=para('J<sub>x</sub> dp/dt = M<sub>x</sub> - (J<sub>z</sub> - J<sub>y</sub>) q r; similarly for pitch and yaw.',472)
    y=para('M<sub>x</sub> = (R C<sub>t</sub>/sqrt(2))(-omega<sub>1</sub><super>2</super> + omega<sub>2</sub><super>2</super> + omega<sub>3</sub><super>2</super> - omega<sub>4</sub><super>2</super>) - C<sub>dx</sub> p |p| + J<sub>rotor</sub> q S.',y)
    y=para('M<sub>z</sub> = C<sub>m</sub>(omega<sub>1</sub><super>2</super> + omega<sub>2</sub><super>2</super> - omega<sub>3</sub><super>2</super> - omega<sub>4</sub><super>2</super>) - C<sub>dz</sub> r |r|; S = omega<sub>1</sub> + omega<sub>2</sub> - omega<sub>3</sub> - omega<sub>4</sub>.',y)
    y=para('tau d(omega<sub>i</sub>)/dt + omega<sub>i</sub> = 1148 u<sub>i</sub> - 141.4.',y)
    para('Quaternion kinematics retain nonlinear attitude coupling. Damping is quadratic in angular rate; it is not a linear viscous damping term. The full equations and source files are included in the project.',y,size=12); end()

    page('3. Uncertainty ranges','Approved study assumptions; independent factors in validation')
    y=table([['Parameter','Source nominal','Variation'],['Jxx, Jyy, Jzz','0.0211, 0.0219, 0.0366 kg m^2','+/-15% each'],['Motor time constant','0.020 s','+/-30%'],['Thrust coefficient Ct','1.105e-5','+/-10%'],['Torque coefficient Cm','1.779e-7','+/-10%'],['Damping Cdx, Cdy, Cdz','0.0035, 0.0039, 0.0034','+/-30% each']],470)
    y=para('Each varied parameter is theta = theta<sub>0</sub>(1 + delta). There are nine uncertain scalar factors.',y,size=13)
    para('The motor speed-map coefficients, individual motor mismatch, geometry and rotor inertia are fixed. These ranges are not measured vehicle tolerances.',y,size=13); end()

    page('4. Controller and gain mapping','Eight tuned values; source controller structure preserved')
    y=para('Roll/pitch outer loops: desired body rate = K<sub>outer</sub> x angle error, followed by the source rate limiter.',472)
    y=para('Inner discrete controller: C(z) = (b<sub>0</sub> + b<sub>1</sub> z<super>-1</super>) / (1 - 0.9997 z<super>-1</super>).',y)
    y=para('Equivalent gain mapping: b<sub>0</sub> = K<sub>p</sub> + K<sub>i</sub>T<sub>s</sub>; b<sub>1</sub> = -0.9997 K<sub>p</sub>. Yaw uses the original forward-Euler PI rate controller.',y)
    y=para('Eight variables: roll outer/P/I, pitch outer/P/I, yaw P/I. The gain bounds and logarithmic parameterization match the nominal study.',y)
    para('Controller interval = 1 ms (assumed); mixer interval = 4 ms; RK4 integration = 1 ms. Selected gains also receive a 0.5 ms integration check. Exported coefficients must be verified in Simulink.',y,size=13); end()

    page('Local transfer functions and stability','Linear hover interpretation; nonlinear simulation remains the optimization model')
    y=para('The local rate plant has the form G<sub>rate</sub>(s) = K / [s(tau s + 1)]. Roll/pitch angle plants include another integration: G<sub>angle</sub>(s) = K / [s<super>2</super>(tau s + 1)].',472,size=18)
    y=para('K depends on inertia, motor speed-map gain, hover motor speed, arm geometry and Ct (roll/pitch) or Cm (yaw). The study computes these coefficients from the original equations.',y)
    y=para('The local closed loop retains the 1 ms controller and 4 ms mixer hold. Its lifted transition matrix is locally stable when every eigenvalue has magnitude below one.',y)
    y=para('Quadratic damping has zero small-signal derivative at zero angular rate. Its response effects therefore require the nonlinear simulations; a hover linearization alone cannot assess them.',y,size=13)
    para('Selected best gains are checked at nominal hover and across the sampled uncertain plants. These checks are local and unsaturated, not global nonlinear robustness guarantees.',y,size=13); end()

    page('5. Robust training cases','Identical fixed cases for every method, candidate and optimizer seed')
    y=table([['Part','Design','Cases'],['Nominal','Roll/pitch 5 and 20 deg; yaw 30 and 100 deg/s','6'],['Interior uncertainty','6 Latin-hypercube plants x 3 single-axis steps','18'],['Boundary stress','2 directed boundary plants x 3 single-axis steps','6'],['Total per evaluation','All cases called; no candidate-level early termination','30']],470,[165,615,92])
    y=para('Uncertain training steps use roll 20 deg, pitch 20 deg and yaw 100 deg/s. Boundary plants pair high inertia, slow motors, weak coefficients and low damping, and the opposite combination.',y,size=13)
    para('These two boundary plants are candidate stress combinations, not a certified worst-case search. Training sampling seed = 20261005.',y,size=13); end()

    page('6. Fitness: feasibility first, then response quality','Same score construction; uncertain plants now enter optimization')
    y=para('q<sub>s</sub> = 0.45 t<sub>settle</sub>/T + 0.20 t<sub>rise</sub>/T + 0.25(2 ITAE/T<super>2</super>) + 0.10 IAE/T.',472,size=18)
    y=para('Q = 0.70 mean(q<sub>s</sub>) + 0.30 max(q<sub>s</sub>) + 0.01 mean(motor effort).',y,size=18)
    y=para('F = Q if every training case passes; otherwise F = 1000 + 100 sum(violations) + (2/pi) atan(Q).',y,size=16)
    y=para('IAE and ITAE use absolute tracking error normalized by command amplitude. T = 3 s. The maximum is over the 30 sampled cases. Feasible gains always outrank infeasible gains.',y,size=13)
    para('The robustness objective does not discard nominal speed: both remain part of the same constrained optimization. Raw nominal-study and robust-study fitness values use different scenario sets and must not be ranked against each other directly.',y,size=13); end()

    page('7. Acceptance criteria','Applied without relaxing thresholds for the new study')
    y=table([['Requirement','Limit'],['Overshoot / final tracking error','<=10% / <=2%'],['Settling','2% band, with at least 0.25 s final hold'],['Motor clipping','<=5% of response samples'],['Motor speeds','Nonnegative'],['Uncommanded response','Roll/pitch <=0.5 deg; yaw rate <=3 deg/s'],['Attitude / numerical behavior','Bank <=75 deg; no divergence']],470,[290,582])
    para('Source limits stay active: roll/pitch control +/-1, yaw +/-0.5, yaw integral +/-0.2, motor commands 0..1. Finite-horizon acceptance is not a global stability proof.',y,size=13); end()

    page('8. Equal-budget experiment','30 paired optimizer seeds per method')
    y=para('<b>150 searches x 3,264 unique candidates = 489,600 objective evaluations.</b><br/>Each objective evaluates 30 cases: <b>14,688,000 training scenario simulations</b>.',472,size=18)
    y=para('Seeds: 11, 29, 47 and 101..127. Each paired seed starts from the same 64-point population, including the source baseline. Previous optimized gains are not injected.',y)
    y=para('GA, PSO, CSO, DSA and CMA-ES retain the prior settings. GA mutation and PSO inertia follow consumed budget. Cached duplicates do not count; final batches stop exactly at the cap.',y)
    para('Nominal-versus-robust tuning matches candidate budgets, but robust tuning uses five times more scenario simulations per candidate (30 vs 6). Within this new five-method comparison, both budgets match.',y,size=13); end()

    page('Optimizer settings','Population 64; eight logarithmically scaled gain coordinates')
    y=table([['Method','Settings retained from the nominal comparison'],
       ['GA','4 elites; tournament 3; crossover .9; blend [-.15,1.15]; mutation probability .25; sigma .14 to .035; immigrants .08'],
       ['PSO','c1=c2=1.7; inertia .9 to .4; velocity +/- .2; boundary velocity damping .5'],
       ['CSO','13 tracing cats; SMP=5 including current point; SRD=.2; CDC=4; tracing coefficient 2; velocity +/- .2'],
       ['DSA','2 directions; 2 search ticks; speed .08; communication acceleration 10; radius reduction 3; timer maximum 1000000'],
       ['CMA-ES','Active full covariance; sigma0=.25; BoundTransform [0,1]; best initial point as the initial mean']],470,[130,742],size=12)
    para('GA mutation and PSO inertia schedules follow consumed evaluations. Different methods complete different numbers of iterations; all stop at the same candidate budget.',y,size=13); end()

    page('Gain bounds','Identical to the earlier nominal study; no range expansion')
    cfg=read('contract.json')['configuration']
    y=table([['Parameter','Lower','Upper','Scale']]+[[p['name'],p['lower'],p['upper'],p['scale']] for p in cfg['parameters']],470,[450,140,140,142],size=12)
    para('The eight gain values map to outer P, inner discrete-controller coefficients and yaw PI as described earlier. These bounds constrain the search; they are not uncertainty ranges.',y,size=12); end()

    page('9. Independent validation','Same unseen cases for all 300 tuned controllers')
    y=table([['Test set','Design','Cases/controller'],['Single-axis uncertainty','Uniform independent parameters; signed unseen commands','300'],['Parameter boundaries','9 factors x 2 limits x 3 axes, one factor varied at a time','54'],['Combined-axis stress','Simultaneous commands and throttle 0.54..0.68','90']],470,[180,520,172])
    y=para('Validation seed = 20261006. The primary robustness outcome is the distribution of passes out of 300 and the number of controllers passing all 300.',y)
    para('Every seed winner is tested. Best and median gain exports are selected using training fitness only. Validation cases are never used to tune, rank candidate gains for export, or change the protocol.',y); end()

    page('10. Robust-training results','Lower fitness is better; values >=1000 indicate a training violation')
    y=table([['Method','Best','Median','Mean','SD','Feasible /30']]+[[r[k] for k in ['method','best','median','mean','std','training_feasible_runs']] for r in fitness],470,size=12)
    para(conclusion,y); end()
    page('11. Fitness distributions','Across the 30 independent optimizer seeds'); figure('01_training_fitness.png'); end()
    page('12. Search convergence','Evaluation count is comparable; algorithm iteration counts differ'); figure('02_convergence.png'); end()

    page('13. Does robustness improve?','300 unseen single-axis uncertainty cases per controller')
    y=table([['Method','Nominal median passes','Robust median passes','Nominal all-300 /30','Robust all-300 /30']]+
        [[m,next(r['median_mc_passes'] for r in nominal if r['method']==m),next(r['median_mc_passes'] for r in robust if r['method']==m),
          next(r['all_300_controllers'] for r in nominal if r['method']==m),next(r['all_300_controllers'] for r in robust if r['method']==m)] for m in [r['method'] for r in fitness]],470,size=12)
    y=para('The nominal controllers are the saved winners from the prior 30-seed study. Both sets are re-evaluated here on identical new validation scenarios.',y,size=13)
    base=rows('baseline_validation.csv')[0]
    para(f"Original source controller: {base['single_axis_mc_passes']}/300 uncertainty passes; mean nominal settling time {float(base['nominal_mean_settling_s']):.4f} s. This reference is not an additional optimized run.",y,size=13); end()
    page('14. Robustness and nominal speed','Gray: nominal-tuned. Teal: robust-tuned.'); figure('03_robustness_speed_tradeoff.png'); end()
    page('15. Consistency across optimizer seeds','Passing every sampled uncertainty case'); figure('04_all_cases.png'); end()
    page('16. Parameter sensitivity','Boundary tests isolate one uncertain coefficient at a time'); figure('05_parameter_sensitivity.png'); end()
    page('17. Responses on unseen changed plants','Best training candidate per method; normalized signed step responses')
    y=figure('06_heldout_response_envelopes.png',h=320)
    para('Lines show median responses over 100 cases per axis. Shading spans their minimum and maximum. Different command amplitudes are normalized; these are sampled envelopes, not guaranteed bounds.',y,size=12); end()

    page('18. Paired evidence for the tuning change','A = robust-tuned; B = nominal-tuned. Positive pass-count difference favors robust tuning.')
    effect=[r for r in changes if r['metric']=='single_axis_mc_passes']
    y=table([['Method','Mean pass gain','95% CI low','95% CI high','Holm p']]+[[r[k] for k in ['method','mean_A_minus_B','mean_difference_ci95_low','mean_difference_ci95_high','holm_p']] for r in effect],470,size=12)
    y=para('Paired Wilcoxon tests use a single Holm correction family of 15 comparisons: pass counts, nominal fitness and nominal settling time across five methods. The complete results are saved as CSV.',y,size=13)
    para('Bootstrap intervals resample the 30 paired seeds (10,000 draws). They describe optimizer variability and are not multiplicity-adjusted or hardware reliability intervals.',y,size=13); end()

    page('19. Comparing the five robust optimizers','Training-score inference is separate from held-out pass-count inference')
    y=para(f"Friedman statistic = {stats['friedman_statistic']:.5g}; within-seed permutation p = {stats['permutation_p']:.5g} (20,000 permutations).",472,size=18)
    y=para('Ten pairwise two-sided Wilcoxon tests on robust-training fitness use Holm correction. Another explicitly separate family compares held-out failure counts across the five robust optimizers.',y)
    y=para('A seed pairs identical initial populations, not identical search paths. Wilcoxon assumes symmetric paired differences. All inference is conditional on this one model, scenario design, budget and optimizer settings.',y)
    para('The best run is a selected extreme. I use the full 30-seed distribution to compare methods and export both best and median-representative candidates.',y); end()

    page('Pairwise robust-training comparisons','Paired seeds; negative mean difference favors method A')
    pairs=rows('robust_fitness_pairwise.csv')
    y=table([['A','B','Mean A - B','95% CI low','95% CI high','Holm p']]+
        [[r[k] for k in ['A','B','mean_A_minus_B','mean_difference_ci95_low','mean_difference_ci95_high','holm_p']]
         for r in pairs],470,size=10,padding=6)
    para('Holm p-values adjust the ten method comparisons. The bootstrap intervals are individual 95% intervals, not simultaneous intervals. This table compares training score, not hardware reliability.',y,size=12); end()

    page('20. Remaining limitations: combined-axis control','Reported separately from single-axis parameter robustness')
    y=table([['Method','Nominal median /90','Robust median /90','Robust boundary median /54']]+
        [[m,next(r['median_combined_passes'] for r in nominal if r['method']==m),next(r['median_combined_passes'] for r in robust if r['method']==m),
          next(r['median_boundary_passes'] for r in robust if r['method']==m)] for m in [r['method'] for r in fitness]],470,size=12)
    y=para('Combined-axis tests add simultaneous commands and throttle variation. They test more than the parameter changes in the single-axis training set.',y)
    para('Any failure remains a limitation of these gains and this controller/model combination. Retuning gains alone must not be claimed to solve nonlinear multi-axis tracking. Simulink trace validation is still required.',y,size=13); end()

    page('Combined-axis acceptance failures','Robust tuning; 30 controllers x 90 cases = 2,700 tests per method')
    grouped=rows('validation_failure_reasons_by_group.csv')
    y=table([['Method','Overshoot','Final error','Not settled','Motor clipping','Negative speed','Divergence']]+
        [[r[k] for k in ['method','fails_overshoot','fails_final_error','fails_settling','fails_motor_clipping','fails_negative_speed','fails_numerical']]
         for r in grouped if r['mode']=='robust' and r['group']=='combined_stress'],470,size=11)
    y=para('Counts overlap: one simulated response can violate several requirements. The full CSV includes both tuning approaches and all three validation groups.',y,size=13)
    para('These diagnostics identify failed criteria, not the physical cause. Isolating simultaneous-command effects from throttle changes would require a separate controlled experiment.',y,size=13); end()

    page('Inertia consistency: a supplemental check','Independent inertia bounds include some non-realizable combinations')
    y=para('A realizable rigid-body inertia must satisfy Jx + Jy >= Jz and the two cyclic inequalities. All training plants satisfy these conditions. Twenty of the 300 validation plants do not.',472,size=14)
    physical=rows('physical_inertia_subset_summary.csv')
    y=table([['Method','Nominal median /280','Robust median /280','Robust all-280 /30']]+
        [[m,next(r['median_passes'] for r in physical if r['method']==m and r['mode']=='nominal'),
          next(r['median_passes'] for r in physical if r['method']==m and r['mode']=='robust'),
          next(r['controllers_passing_all'] for r in physical if r['method']==m and r['mode']=='robust')] for m in [r['method'] for r in fitness]],y,size=12)
    para('The full 300-case box remains the primary pre-specified result. This supplemental subset uses geometry only, not pass/fail performance. It does not establish that every retained inertia matches the actual vehicle.',y,size=12); end()

    page('Joint-boundary audit: 512 parameter combinations','Supplemental audit of selected gains; no retuning or validation-based selection')
    corners=rows('corner_validation_summary.csv')
    y=table([['Method','Nominal best /1536','Robust best /1536','Robust median /1536','Robust best physical subset']]+
        [[m,next(r['passes'] for r in corners if r['method']==m and r['mode']=='nominal' and r['selection']=='best'),
          next(r['passes'] for r in corners if r['method']==m and r['mode']=='robust' and r['selection']=='best'),
          next(r['passes'] for r in corners if r['method']==m and r['mode']=='robust' and r['selection']=='median'),
          next(r['physical_passes']+'/'+r['physical_cases'] for r in corners if r['method']==m and r['mode']=='robust' and r['selection']=='best')]
         for m in [r['method'] for r in fitness]],470,size=11)
    y=para('Each of 512 vertices is tested with roll 20 deg, pitch 20 deg and yaw 100 deg/s. The audit was added during execution, separately from the pre-specified primary validation.',y,size=13)
    para('Any failures here qualify the interpretation of a 300/300 random-case result. Even passing every vertex does not prove nonlinear robustness at every interior point.',y,size=13); end()

    page('What causes the joint-boundary failures?','Best training-selected gain set from each method; counts can overlap')
    y=table([['Method','Tuning','Overshoot','Motor clipping','Negative motor speed','Not settled','Divergence']]+
        [[r[k] for k in ['method','mode','overshoot_failures','motor_clipping_failures','negative_speed_failures','settling_failures','numerical_failures']]
         for r in corners if r['mode']!='baseline' and r['selection']=='best'],470,size=10)
    para('The original motor equation permits negative speeds at low commands; this study preserves that equation and rejects such responses. A failed performance or motor constraint does not by itself establish closed-loop instability.',y,size=12); end()

    page('21. Selected candidates','Selection uses robust-training fitness; validation never chooses the export')
    y=table([['Method','Selection','Seed','Training F','MC /300','Boundary /54','Combined /90']]+
        [[r[k] for k in ['method','selection','seed','fitness','mc_passes','boundary_passes','combined_passes']] for r in selected],470,size=10)
    para('Exact gains and source transfer-function coefficients are in results/exports. All 150 run gains remain in results/runs.',y,size=12); end()

    for block in [['GA','PSO','CSO'],['DSA','CMA-ES']]:
        page('Best robust-training gains: '+', '.join(block),'Full-precision JSON and Simulink parameter maps accompany this rounded table')
        rr=[]
        for m in block:
            exp=read(f'exports/{m}_best_gains.json')
            for key,value in exp['gains'].items(): rr.append([m,key,f'{value:.8g}'])
        # Two-column parameter groups would be cramped: compact fixed rows fit 24 entries.
        y=table([['Method','Parameter','Value']]+rr,477,[130,500,242],size=10,padding=2)
        end()

    page('23. Verification and reproducibility','Completed result files are audited before this report is generated')
    y=para('All 150 ledgers contain exactly 3,264 unique bounded candidates. Best-so-far histories are monotone, starting populations and initial scores match within seed, and every selected fitness is recomputed.',472)
    y=para('The shared model and strict-budget optimizers passed 19 tests. Both tuning approaches are validated with the same cases. Selected best gains receive a smaller integration-step check and nominal local sampled-system stability analysis.',y)
    y=para('Read README.md, config.json and results/contract.json for the complete protocol. NPZ ledgers, compressed case details, CSV statistics, PNG/SVG figures, gain exports and scripts are included.',y)
    para('Local linear stability does not certify nonlinear or uncertain stability. Timing assumptions, hardware ranges and Simulink agreement remain to be verified.',y,size=13); end()

    page('Numerical and local stability checks','Checks on the best robust-training candidate from each method')
    checks=rows('integration_checks.csv'); stability=rows('sampled_local_stability.csv')
    y=table([['Method','Max angle difference (deg)','Max rate difference (deg/s)','Sampled plants locally stable']]+
        [[m,max(float(r['max_angle_difference_deg']) for r in checks if r['method']==m),
          max(float(r['max_rate_difference_deg_s']) for r in checks if r['method']==m),
          str(sum(r['all_axes_locally_stable']=='True' for r in stability if r['method']==m))+'/'+str(sum(r['method']==m for r in stability))]
         for m in [r['method'] for r in fitness]],470,size=12)
    y=para('Integration comparison: RK4 at 1 ms versus 0.5 ms, while the controller and mixer sampling periods stay fixed. Four cases per method include the highest-scoring sampled training case.',y,size=13)
    para('Local stability uses the sampled-system eigenvalues around hover. Detailed spectral radii and plant values are saved in sampled_local_stability.csv.',y,size=13); end()

    page('24. Conclusions','What the evidence supports')
    y=para(conclusion,472,size=15)
    for m in [r['method'] for r in fitness]:
        a=next(r for r in nominal if r['method']==m); b=next(r for r in robust if r['method']==m)
        y=para(f"<b>{m}:</b> median uncertainty passes {fmt(a['median_mc_passes'])} to {fmt(b['median_mc_passes'])}/300; median nominal mean settling {float(a['median_nominal_mean_settling_s']):.4f} to {float(b['median_nominal_mean_settling_s']):.4f} s.",y,size=13)
    y=para(corner_note,y,size=12)
    para('These are finite sampled results. Combined-axis and boundary failures remain limitations. I do not claim guaranteed worst-case robustness or completed hardware validation.',y,size=12); end()

    page('25. References and model provenance','Python computation; source Simulink files retained for verification')
    y=para('Model provenance: supplied Sim.zip, AttitudeControl_Sim.slx and initialization scripts. The source inventory and unchanged nonlinear model.py are included.',472)
    y=para('MathWorks: Robustness and Worst-Case Analysis. Monte Carlo sampling cannot guarantee the worst-case parameter combination.<br/><link href="https://www.mathworks.com/help/robust/worst-case-analysis.html">mathworks.com/help/robust/worst-case-analysis.html</link>',y,size=13)
    y=para('SciPy statistical definitions: Friedman test and Wilcoxon signed-rank test.<br/><link href="https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.friedmanchisquare.html">SciPy: friedmanchisquare</link> | <link href="https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wilcoxon.html">SciPy: wilcoxon</link>',y,size=13)
    para('Optimizer implementations and settings are retained from the preceding equal-budget study. The new study changes the training scenario set to include parameter uncertainty. Package versions are recorded in requirements-lock.txt.',y,size=13); end()
    c.save(); dump={'page_count':len(pages),'pages':pages}; (OUT/'pdf_pages.json').write_text(json.dumps(dump,indent=2))
    shutil.copy2(PDFDIR/'Robustness_Optimization_Comparison.pdf',OUT/'Robustness_Optimization_Comparison.pdf')
    def htable(rr):
        keys=list(rr[0]); return '<div class="scroll"><table><tr>'+''.join('<th>'+html.escape(k)+'</th>' for k in keys)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(fmt(r[k]))+'</td>' for k in keys)+'</tr>' for r in rr)+'</table></div>'
    content='''<!doctype html><html><meta charset="utf-8"><title>Robustness study</title><style>body{font:16px Segoe UI,sans-serif;margin:40px auto;max-width:1250px;color:#173447;line-height:1.6}img{max-width:100%}table{border-collapse:collapse;font-size:13px}td,th{padding:9px;border-bottom:1px solid #ddd;text-align:left}th{background:#eaf0f5}.scroll{overflow:auto}</style><h1>Robustness optimization: five methods, 30 seeds</h1>'''
    content+='<p>'+html.escape(conclusion)+'</p><p>'+html.escape(corner_note)+'</p><p>Completed 150 searches and 489,600 unique evaluations; 30 training scenarios per evaluation. All 300 nominal/robust controllers evaluated on 444 identical held-out cases.</p>'
    content+='<p><a href="Robustness_Optimization_Comparison.pdf">Open the complete PDF report</a> | <a href="../README.md">Protocol</a></p>'
    content+='<h2>Robust training fitness</h2>'+htable(fitness)+'<h2>Nominal versus robust tuning</h2>'+htable(comp)
    for p in sorted((OUT/'plots').glob('*.png')): content+=f'<img src="plots/{p.name}" alt="{p.stem}">'
    content+='<h2>Paired tuning changes</h2>'+htable(changes)+'<h2>Selected candidates</h2>'+htable(selected)
    content+='<p>Validation did not select gains. Sampling does not guarantee worst-case robustness. The complete limitations, equations, ranges, statistical assumptions and simulation-cost distinction are in the PDF and README.</p></html>'
    (OUT/'REPORT.html').write_text(content,encoding='utf-8')
    print(f'Created {len(pages)} PDF pages and HTML report.',flush=True)

if __name__=='__main__': main()
