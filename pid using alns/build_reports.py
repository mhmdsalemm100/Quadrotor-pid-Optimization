"""Seven data-driven PDF reports. Run with Python containing reportlab and Pillow."""
from pathlib import Path
import json,csv,html,argparse
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as PILImage
R=Path(__file__).resolve().parent;O=R/'results';P=O/'plots';DEST=R/'output/pdf';DEST.mkdir(parents=True,exist_ok=True)
METHODS=['GDA','TA','ALNS','VND','SBRS','PRW']
NAMES={'GDA':'Great Deluge Algorithm','TA':'Threshold Accepting','ALNS':'Adaptive Large Neighborhood Search','VND':'Variable Neighborhood Descent','SBRS':'Shrinking Ball Random Search','PRW':'Pure Random Walk'}
VARIANTS={
'GDA':'A reflected, fixed-length proposal is accepted if it improves the current fitness or lies below a descending water level in log(1 + fitness). The water level falls linearly from the initial best merit plus slack to zero.',
'TA':'A reflected, fixed-length proposal is accepted when its log(1 + fitness) is no greater than current log merit plus the threshold. The threshold decreases linearly to zero.',
'ALNS':'A continuous-variable adaptation: destroy 1, 2, 4 or 8 gain coordinates; repair by uniform replacement, Gaussian perturbation or elite difference. Separate adaptive roulette weights select destroy and repair operators. Threshold acceptance permits temporary deterioration.',
'VND':'Budgeted multistart, first-improvement coordinate descent. Both signs of each coordinate are tested at four radii [r, r/2, r/10, r/50]. Improvement returns to the first neighborhood; exhaustion of all neighborhoods starts a new uniformly sampled point.',
'SBRS':'Uniform sampling in an eight-dimensional ball around the best point, before reflecting into the gain box. Only strict improvements are accepted. The radius decreases geometrically from radius0 to radius0 multiplied by radius_ratio.',
'PRW':'A pure random walk with fixed proposal length and isotropic direction. Every proposal is accepted, including worse points; a separate archive retains the best visited point. Boundary reflection can reduce net displacement, while the pre-reflection proposal length remains constant.'}
SHORT_VARIANTS={
'GDA':'Reflected fixed-radius proposals; linearly falling water level in log merit, with improving moves accepted.',
'TA':'Reflected fixed-radius proposals; a linearly decreasing threshold in log merit.',
'ALNS':'Adaptive continuous destroy/repair operators and threshold acceptance. Fixed operator inventory documented in code.',
'VND':'First-improvement coordinate descent at four radii, with uniform restarts after neighborhood exhaustion.',
'SBRS':'Uniform-ball proposals before reflection, strict improvement acceptance and geometric radius contraction.',
'PRW':'Fixed-length isotropic proposals; every move accepted, with a separate best-visited archive.'}
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def rows(p):
    with open(p,encoding='utf-8') as f:return list(csv.DictReader(f))
def fmt(v,n=5):
    try:return f'{float(v):.{n}g}'
    except (ValueError,TypeError):return str(v)
pdfmetrics.registerFont(TTFont('Arial',r'C:\Windows\Fonts\arial.ttf'))
pdfmetrics.registerFont(TTFont('Arial-Bold',r'C:\Windows\Fonts\arialbd.ttf'))
pdfmetrics.registerFontFamily('Arial',normal='Arial',bold='Arial-Bold',italic='Arial',boldItalic='Arial-Bold')
S=getSampleStyleSheet()
for name in ['Normal','BodyText','Heading1','Heading2','Heading3','Title']:
    S[name].fontName='Arial-Bold' if name.startswith('Heading') or name=='Title' else 'Arial'
    S[name].textColor=colors.HexColor('#213345')
S['BodyText'].fontSize=9;S['BodyText'].leading=13;S['BodyText'].spaceAfter=7
S['Heading1'].fontSize=18;S['Heading1'].leading=22;S['Heading1'].spaceAfter=12
S['Heading2'].fontSize=12;S['Heading2'].leading=15
S.add(ParagraphStyle('Small',parent=S['BodyText'],fontSize=7.5,leading=10,spaceAfter=5))
S.add(ParagraphStyle('Cell',parent=S['BodyText'],fontSize=7.2,leading=9,spaceAfter=0))
W=499
def para(s,style='BodyText'):return Paragraph(s,S[style])
def table(headers,data,widths=None):
    rr=[[para(html.escape(str(x)),'Cell') for x in headers]]+[[para(html.escape(str(x)),'Cell') for x in row] for row in data]
    t=Table(rr,colWidths=widths or [W/len(headers)]*len(headers),repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e5edf3')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#879caf')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f6f8fa')]),('BOTTOMPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5)]))
    return t
def pic(path,maxheight=260):
    with PILImage.open(path) as im:w,h=im.size
    scale=min(W/w,maxheight/h);return Image(str(path),width=w*scale,height=h*scale,hAlign='CENTER')
def title(s,kicker=None):
    a=[]
    if kicker:a+=[para(kicker,'Small')]
    return a+[para(s,'Heading1')]
def page(story,s):story.append(PageBreak());story.extend(title(s))
def footer(c,doc):
    c.setStrokeColor(colors.HexColor('#c2cdd6'));c.line(48,43,547,43);c.setFont('Arial',7)
    c.setFillColor(colors.HexColor('#526575'));c.drawString(48,31,'Quadrotor attitude tuning | Offline simulation study | October 2026')
    c.drawRightString(547,31,str(doc.page))
def build(path,story):
    SimpleDocTemplate(str(path),pagesize=(595.28,841.89),leftMargin=48,rightMargin=48,topMargin=44,bottomMargin=55,title=path.stem.replace('_',' '),author='Quadrotor optimization study').build(story,onFirstPage=footer,onLaterPages=footer)

def protocol(story):
    story+=[para('Plant and controller equations','Heading2'),pic(P/'equations/plant.png',160),pic(P/'equations/controller.png',165),
        para('The nonlinear plant uses a quaternion attitude state, three body rates and four rotor speeds. Ω = (p, q, r). The propeller torque equations above exclude the separately added damping and gyroscopic terms. The attitude kinematics are integrated with the original model equations; no small-angle approximation is used for optimization.','Small'),
        para('The transfer functions are local hover approximations only. At throttle h = 0.609, ω₀ = 1148h − 141.4. The motor-pattern torque coefficients are kφ = kθ = 8(RCt/√2)ω₀ and kr = 8Cmω₀. The angle transfer function applies to roll and pitch; yaw is controlled as angular rate. Saturation, coupling and quadratic damping are retained in the nonlinear simulator.','Small'),
        para('Roll/pitch controller outputs are clipped to ±1; yaw to ±0.5; yaw integral state to ±0.2; motor commands to [0, 1]. The roll/pitch recurrence retains its unsaturated previous output. The inherited outer-rate limit is 220 rad/s. This interpretation and the affine motor model are preserved for comparability and need checking against the actual deployment implementation.','Small'),
        para('Controller update: 1 ms. Mixer hold: 4 ms. RK4 integration: 1 ms. Pre-step: 0.2 s; response horizon: 3 s. The gains are fixed after offline optimization; there is no online retuning.','Small'),
        table(['Nominal quantity','Value'],[['Principal inertias (kg m²)','Jxx 0.0211; Jyy 0.0219; Jzz 0.0366'],['Arm length / motor time constant','R = 0.225 m; τm = 0.020 s'],['Propeller coefficients','Ct = 0.00001105; Cm = 0.0000001779 (SI angular-speed convention)'],['Quadratic damping coefficients','Dx = 0.0035; Dy = 0.0039; Dz = 0.0034'],['Rotor inertia / trim throttle','Jr = 0.0001287 kg m²; h = 0.609']],[180,319])]

def fitness_page(story,cfg):
    story+=[pic(P/'equations/fitness.png',180),para('Fitness and feasibility','Heading2'),
        para('A is the set of commanded channels; T is the response horizon. Rise time uses 10%-90% crossings. Settling requires the 2% band and a final hold of at least 0.25 s. A failed settling measurement uses the horizon as a score sentinel and is separately flagged as infeasible. IAE and ITAE are integrated on normalized error; E is the mean squared motor-command deviation from throttle. V sums the positive normalized constraint violations.','Small'),
        table(['Constraint','Acceptance limit'],[['Overshoot','≤10%'],['Final error','≤2%: absolute mean signed error over the final 0.25 s'],['Settling','Within 2%, with at least 0.25 s final hold'],['Motor clipping','≤5% of post-step samples (any motor clipped)'],['Rotor speed','Nonnegative'],['Uncommanded motion','Roll/pitch ≤0.5°; yaw rate ≤3°/s'],['Bank / guards','Bank ≤75°; numerical guards include |body rate| >30 rad/s or |pitch| >1.4 rad']],[120,379]),
        Spacer(1,9),para('Eight optimized gains and fixed search bounds','Heading2'),
        table(['Gain','Lower','Upper'],[[p['name'],fmt(p['lower']),fmt(p['upper'])] for p in cfg['parameters']],[319,90,90]),
        para('The penalty makes a feasible controller preferable to an infeasible one. A low score is meaningful only together with feasibility and held-out results. The score combines response speed, tracking error and effort; it is not settling time alone.','Small')]

def experimental_design(story):
    story+=[para('Development and final evaluation','Heading2'),
        table(['Stage','Design'],[['Parameter selection','4 settings × 3 development seeds × 2 regimes per method; 3264 unique evaluations per run. Lowest mean within-seed/regime rank wins; ties use candidate index.'],['Main comparison','30 original seeds × 2 regimes × 6 methods = 360 runs; 3264 unique evaluations each. Identical 64-point initialization per seed, charged to the budget.'],['Nominal training','6 steps: roll/pitch 5° and 20°; yaw rate 30°/s and 100°/s.'],['Robust training','Nominal 6 plus 8 uncertain plants × 3 large commands = 30 cases.'],['Uncertainty','Independent Jxx, Jyy, Jzz ±15%; motor time constant ±30%; thrust and torque coefficients ±10%; three damping coefficients ±30%.'],['Common validation','300 random single-axis cases, 54 one-factor boundaries, 90 combined-axis stress cases, for every final controller.'],['Joint boundaries','All 512 uncertainty-box vertices × 3 large commands = 1536 cases for best and median representatives.'],['Physical subset','Report inertia-triangle-admissible cases separately; independent inertia boxes include nonphysical combinations.']],[120,379]),
        Spacer(1,10),para('Interpretation limits','Heading2'),
        para('A selected parameter setting is best among the four tested settings on three development seeds, not proven globally optimal. Parameter selection never uses final seeds or validation scores. One setting per method is frozen for both training regimes. Best and median controller representatives are selected by training fitness only; the median representative is the actual run closest to the median score, with seed as tie-breaker.'),
        para('Development uses 470,016 candidate evaluations; the main study uses 1,175,040. Nominal and robust evaluations cost 6 and 30 scenario simulations respectively. Completed run ledgers represent 29,611,008 training-case simulations, excluding warm-up, discarded partial attempts, smoke tests, validation and diagnostics.'),
        para('The original five algorithms did not receive this additional parameter-selection stage. Eleven-method comparisons therefore have equal final-run budgets but unequal development effort. They are exploratory. Reusing the earlier validation suite ensures comparability but is not a new prospective blind test.'),
        para('Inference concerns optimization seeds on one fixed quadrotor model. Paired Wilcoxon tests use Holm correction within declared families; 10,000 seed-level bootstrap resamples provide descriptive 95% intervals. These intervals are not adjusted for multiple comparisons. The same validation plants are reused across controllers; they are not thousands of independent plant samples. Finite uncertainty tests and local eigenvalues do not prove global nonlinear robustness.')]

def references(story,m=None):
    story.append(para('Algorithm references and adaptations','Heading2'))
    ids=['GDA','TA','ALNS','VND'] if m is None else ([m] if m in ['GDA','TA','ALNS','VND'] else [])
    for key in ids:
        d=read(R/'references'/f'{key}.json');d=d.get('message',d)
        authors=', '.join((a.get('given','')+' '+a.get('family','')).strip() for a in d.get('author',[]))
        tt=d.get('title',[''])[0];doi=d.get('DOI','')
        story.append(para(html.escape(f'{authors}. {tt}. DOI: {doi}'),'Small'))
    story.append(para('The implementations are explicitly specified bounded continuous-search variants. ALNS uses problem-specific continuous destroy/repair operators; VND uses budgeted restarts. SBRS and PRW are defined by the supplied equations and code rather than attributed to an unverified canonical publication. Citation metadata was verified; the current adaptation is not represented as the exact original paper implementation.','Small'))

def method_report(m,cfg):
    fs=[r for r in rows(O/'fitness_summary.csv') if r['method']==m];nv=[r for r in rows(O/'nominal_vs_robust.csv') if r['method']==m]
    ss=[r for r in rows(O/'selected_candidates.csv') if r['method']==m];pp=[r for r in rows(O/'parameter_selection.csv') if r['method']==m]
    params=read(O/'selected_parameters.json')[m]
    story=title(NAMES[m],f'{m} | SIX-METHOD EXTENSION | 30-SEED EXPERIMENT')
    story+=[para(VARIANTS[m]),para('Selected search parameters','Heading2'),para(html.escape(json.dumps(params))),
        table(['Regime','Median fitness','Feasible /30','All 300 MC /30','Median MC passes'],[[r['mode'],fmt(r['median']),r['training_feasible_runs'],next(v['all_300_controllers'] for v in nv if v['mode']==r['mode']),next(v['median_mc_passes'] for v in nv if v['mode']==r['mode'])] for r in fs]),
        Spacer(1,10),para('What the result means','Heading2'),
        para('Fitness is the training objective; MC denotes the independent random single-axis validation suite. Passing training does not imply passing every uncertainty case. The following pages show the actual controller responses, motor behavior, boundaries and failure counts. All reported gains are offline candidates, with no HIL or flight evidence.'),
        para('Parameter study','Heading2'),table(['Setting','Parameters','Mean rank','Selected'],[[r['candidate'],r['parameters'],fmt(r['mean_rank'],4),'Yes' if r['selected']=='True' else 'No'] for r in pp],[42,322,70,65]),
        para('Each setting receives the same 3 development seeds under both regimes. The chosen setting minimizes average rank across these 6 blocks. This small grid supports a defensible tested choice, not a claim of globally best parameters.','Small')]
    page(story,'Model and implemented controller');protocol(story)
    page(story,'Fitness, constraints and search space');fitness_page(story,cfg)
    page(story,'Experimental design and limitations');experimental_design(story)
    page(story,'The gains found')
    labels=[f'{r["mode"]} {r["selection"]}\nseed {r["seed"]}' for r in ss]
    story+=[table(['Parameter']+labels,[[p['name']]+[fmt(r[p['name']],8) for r in ss] for p in cfg['parameters']],[159,85,85,85,85]),Spacer(1,10),
        table(['Selection','Training fitness','Random /300','Edges /54','Combined /90','Corners /1536'],[[r['mode']+' '+r['selection'],fmt(r['fitness']),r['mc_passes'],r['boundary_passes'],r['combined_passes'],r['corner_passes']] for r in ss],[119,76,76,76,76,76]),
        para('Displayed gains are rounded for reading. Use results/exports/*_gains.json for full precision and exact b0, b1, a0, a1 coefficients. Roll/pitch numerator: [Kp + KiTs, −aKp]; denominator: [1, −a], with Ts = 0.001 s and a = 0.9997. The yaw gains apply to a rate PI controller.','Small'),
        para('The best controller is the lowest training-fitness seed, not the controller with the most favorable validation outcome. The median representative is an actual seed; gains are never averaged across controllers.','Small')]
    page(story,'Nominal responses and convergence');story+=[pic(P/m/'01_responses.png',330),pic(P/m/'02_convergence.png',225),para('Response plots show the first second; the complete horizon appears in the appendix. Solid curves: best representative; dashed curves: median representative. The reference controller is dotted. Gray bands show ±2%. Convergence retains all 30 trajectories and the median; horizontal stretches represent no improvement.','Small')]
    page(story,'Uncertainty responses and actuation');story+=[pic(P/m/'03_uncertain_responses.png',240),pic(P/m/'04_actuation.png',335),para('Uncertainty response lines show nine individual training plants for the best robust controller. They are not confidence intervals. Actuation plots use the nominal plant and the large training commands. Plot windows focus on the transient; complete three-second traces, raw and clipped motor signals and rotor speeds are in plot_data.','Small')]
    page(story,'Independent validation and sensitivity');story+=[pic(P/m/'05_validation.png',210),pic(P/m/'06_sensitivity.png',265)]
    cc=[r for r in rows(O/'corner_validation_summary.csv') if r['method']==m]
    story+=[table(['Selection','All corners','Physical corners','Worst violation'],[[r['mode']+' '+r['selection'],r['passes']+'/'+r['cases'],r['physical_passes']+'/'+r['physical_cases'],fmt(r['worst_violation'])] for r in cc],[150,110,120,119]),para('Sensitivity cells give the percentage of 30 controllers passing a specific factor-bound/axis case. R/P/Y mean roll/pitch/yaw rate; −/+ identify the lower/upper uncertain parameter bound. The physical subset enforces the principal-inertia triangle inequality.','Small')]
    phy=[r for r in rows(O/'physical_inertia_subset_summary.csv') if r['method']==m and r['group']=='single_axis_mc']
    story.append(para('Physical random subset: '+'. '.join(f'{r["mode"]} tuning passes all {r["cases_per_controller"]} cases for {r["controllers_passing_all"]}/{r["controllers"]} controllers' for r in phy)+'.','Small'))
    page(story,'Failure audit and numerical checks')
    fr=[r for r in rows(O/'failure_categories.csv') if r['method']==m];keys=[k for k in fr[0] if k.startswith('fails_')]
    story+=[para('Failure counts across all 30 controllers and 444 held-out cases per controller. Categories can overlap and must not be added to obtain unique failures.','Small'),table(['Failure category','Nominal tuned','Robust tuned'],[[k.removeprefix('fails_').replace('_',' '),sum(int(r[k]) for r in fr if r['mode']=='nominal'),sum(int(r[k]) for r in fr if r['mode']=='robust')] for k in keys],[259,120,120])]
    nn=[r for r in rows(O/'integration_checks.csv') if r['method']==m];ll=[r for r in rows(O/'sampled_local_stability.csv') if r['method']==m]
    story+=[Spacer(1,10),para('Best robust controller: 1 ms versus 0.5 ms integration','Heading2'),table(['Case','Max angle difference (°)','Max rate difference (°/s)','Settling difference (s)'],[[r['scenario'],fmt(r['max_angle_difference_deg']),fmt(r['max_rate_difference_deg_s']),fmt(r['max_settling_difference_s'])] for r in nn],[190,103,103,103]),
        para(f'Finite integration checks: {sum(r["finite"]=="True" for r in nn)}/{len(nn)}. Numerical-guard activations: {sum(r["numerical_guard_dt1ms"]=="True" or r["numerical_guard_dt05ms"]=="True" for r in nn)}. Locally stable on all three axes for {sum(r["all_axes_locally_stable"]=="True" for r in ll)}/{len(ll)} sampled plants. Local stability retains the 1 ms controller and 4 ms mixer timing, but excludes nonlinear saturation and large-angle effects.','Small'),
        para('Additional diagnostics cover command extrapolation, coupled commands, throttle changes, a torque pulse, deterministic measurement perturbation, startup, timing changes and isolated inner-loop commands. These are reported separately in additional_diagnostics.csv and never enter the optimization or primary ranking.','Small')]
    page(story,'Appendix: full response horizon');story+=[pic(P/m/'07_full_responses.png',360)]
    met=[r for r in rows(O/'plot_data'/m/'selected_response_metrics.csv') if r['mode']=='robust' and r['selection']=='best']
    story+=[para('Best robust controller: nominal response metrics','Heading2'),table(['Command','Rise (s)','Settling (s)','Settled','Overshoot (%)','Final error (%)'],[[r['scenario'],fmt(r['rise_s']),fmt(r['settling_s']),r['settled'],fmt(r['overshoot_pct']),fmt(r['final_error_pct'])] for r in met],[134,73,73,73,73,73]),para('A reported settling score at the horizon can be a failure sentinel. Always read the Settled column. Full metrics for all four representatives are included in selected_response_metrics.csv.','Small')]
    page(story,'Reproduction and evidence');reproduction(story);references(story,m)
    build(DEST/f'{m}_complete_study.pdf',story)

def reproduction(story):
    story+=[table(['File / directory','Contents'],[['methods.py','Exact method variants, proposal rules, acceptance and schedules.'],['model.py / study.py','Plant, controller, constraints and fitness preserved from earlier benchmark.'],['results/contract.json','Frozen code hashes, settings grid, seeds and scenarios.'],['results/nominal/runs and robust/runs','Every run, complete evaluation ledger, iterations and acceptance transitions.'],['results/exports','Full-precision gains and Simulink coefficient maps.'],['results/validation','444 held-out case records per controller, including constraint flags.'],['results/corner_validation','Full boundary-case audit for selected representatives.'],['results/plot_data and plots','Machine-readable figure data and PNG figures.'],['results/*pairwise.csv / statistics.json','Paired tests, Holm adjustments, confidence intervals and test-family definitions.'],['run_method.py','Reproduce one delivered method; completed runs resume after checks.']],[205,294]),Spacer(1,9),
        para('Create a Python environment from requirements-lock.txt and run: python run_method.py --processes 4. The central project uses run_extension.py followed by analyze_extension.py and plot_extension.py. Existing results are reused; intentionally changing the scientific protocol requires a separate study directory. The final archive includes the source-model extracts used by the earlier study.','Small'),
        para('Evaluation count is the primary budget. Iterations are method-specific and are not an equal-work unit. A 64-point initialization is followed by sequential proposals; cached duplicates cost no additional unique evaluation. The final evaluated point is included in the best archive even when the strict budget exception prevents a subsequent trajectory-state update.','Small'),
        para('Hardware: Intel Core i7-13620H, 10 physical cores, 16 logical processors, 32 GB memory. The 144 development runs and first 6 nominal main runs used 6 workers. The pool then resumed with 10; completed results were reused and unfinished seeds restarted. Recorded wall times depend on concurrent load and are descriptive. Exact environment and execution events are retained.','Small'),
        para('The original model, selected manuscript and previous five-method results were not retuned by this extension. Controller deployment still requires confirming model units, discrete block conventions, actuator calibration and hardware timing.','Small')]

def combined(cfg):
    fs=rows(O/'fitness_summary.csv');nv=rows(O/'nominal_vs_robust.csv');ss=rows(O/'selected_candidates.csv')
    bestnom=min((r for r in fs if r['mode']=='nominal'),key=lambda r:float(r['median']))
    bestrob=min((r for r in fs if r['mode']=='robust'),key=lambda r:float(r['median']))
    story=title('Six additional methods for quadrotor attitude tuning','30 SEEDS | EQUAL FINAL BUDGETS | NOMINAL AND ROBUST TRAINING')
    baseline=next(r for r in rows(O/'validation_summary.csv') if r['mode']=='baseline')
    story+=[para('This extension compares the Great Deluge Algorithm (GDA), Threshold Accepting (TA), Adaptive Large Neighborhood Search (ALNS), Variable Neighborhood Descent (VND), Shrinking Ball Random Search (SBRS) and constant-step Pure Random Walk (PRW).'),
        para('These methods broaden the comparison beyond the earlier population-based optimizers. They test controlled acceptance of worse moves, adaptive neighborhoods, multiscale descent, contracting random search and an unguided constant-step walk. This provides simpler reference methods against which the value of optimizer complexity can be assessed.'),
        para(f'Within these six implementations, {bestnom["method"]} has the lowest median nominal-training fitness ({fmt(bestnom["median"])}); {bestrob["method"]} has the lowest median robust-training fitness ({fmt(bestrob["median"])}). These are rankings on the specified model, bounds, objectives and tested settings, not universal algorithm rankings.'),
        table(['Method','Nominal median F','Robust median F','Robust feasible /30','Robust all-MC /30'],[[m,next(fmt(r['median']) for r in fs if r['method']==m and r['mode']=='nominal'),next(fmt(r['median']) for r in fs if r['method']==m and r['mode']=='robust'),next(r['training_feasible_runs'] for r in fs if r['method']==m and r['mode']=='robust'),next(r['all_300_controllers'] for r in nv if r['method']==m and r['mode']=='robust')] for m in METHODS]),
        Spacer(1,10),para('How to interpret the outcome','Heading2'),
        para('Read training feasibility first, then response speed, random uncertainty, boundary failures and combined-axis stress. A method can have an excellent best seed while being inconsistent across the other 29 seeds. Median fitness and distributions capture repeatability; best and median controller gains are exported separately.'),
        para(f'The original controller passes {baseline["nominal_passes"]}/6 nominal cases, {baseline["training_passes"]}/30 robust-training cases and {baseline["single_axis_mc_passes"]}/300 random single-axis cases. Its nominal mean settling score is {fmt(baseline["nominal_mean_settling_s"])} s. Its training penalty is therefore not directly interpretable as a response-time ratio.'),
        para('The extension tunes gains offline. Robust training seeks a fixed gain vector that tolerates sampled plant changes; it is not online adaptation. Results are numerical candidates. No hardware-in-the-loop or flight validation was performed.'),
        para('The earlier five algorithms are included only as an exploratory reference: their final evaluation budgets match, but they did not receive this new hyperparameter pilot.')]
    page(story,'Equations and implementation');protocol(story)
    page(story,'Fitness, constraints and gain bounds');fitness_page(story,cfg)
    page(story,'Budget, uncertainty and statistical design');experimental_design(story)
    page(story,'Search parameters selected on development seeds')
    params=read(O/'selected_parameters.json');story+=[table(['Method','Selected setting','Variant'],[[m,json.dumps(params[m]),SHORT_VARIANTS[m]] for m in METHODS],[45,150,304]),Spacer(1,8),pic(P/'05_parameter_study.png',260)]
    page(story,'Fitness and convergence');story+=[pic(P/'01_fitness_distributions.png',230),pic(P/'02_convergence.png',350),para('The robust-fitness panel uses a marked broken axis to display infeasibility penalties and feasible scores clearly; all 30 runs enter each boxplot. Each run contains exactly 3264 unique evaluations. Median convergence and interquartile bands summarize 30 seeds; nominal and robust objectives measure different training sets.','Small')]
    page(story,'Speed and held-out robustness');story+=[pic(P/'03_validation_passes.png',225),pic(P/'04_speed_robustness.png',335),para('Each point is an actual seed. The x-axis is the nominal six-case mean settling score, including horizon sentinels for failed cases; the y-axis is the independent random single-axis pass percentage. Interpret the scatter together with feasibility and the separate stress tests.','Small')]
    page(story,'Boundary limits and earlier methods');story+=[pic(P/'06_joint_boundaries.png',250),pic(P/'07_eleven_methods.png',260),para('Earlier methods: genetic algorithm (GA), particle swarm optimization (PSO), cat swarm optimization (CSO), dolphin swarm algorithm (DSA), and covariance matrix adaptation evolution strategy (CMA-ES). Joint-boundary testing is separate from primary random validation. The eleven-method chart is exploratory because total development effort differs. An improved training score alone is not evidence of superiority in every uncertainty or command regime.','Small')]
    for mode in ['nominal','robust']:
        page(story,mode.capitalize()+' best-seed gains')
        rr=[next(r for r in ss if r['method']==m and r['mode']==mode and r['selection']=='best') for m in METHODS]
        story+=[table(['Parameter']+METHODS,[[p['name']]+[fmt(r[p['name']],6) for r in rr] for p in cfg['parameters']],[157]+[57]*6),Spacer(1,12),table(['Method','Seed','Fitness','MC /300','Edges /54','Stress /90','Corners /1536'],[[r['method'],r['seed'],fmt(r['fitness']),r['mc_passes'],r['boundary_passes'],r['combined_passes'],r['corner_passes']] for r in rr],[55,45,79,80,80,80,80]),
            para('Rounded display only. Full-precision gains for all 360 runs and exact discrete coefficients are in results/exports/all_runs_gains.csv. Both best and median selections in each regime are supplied as individual JSON maps. Controller selection uses training fitness, not validation.','Small')]
    page(story,'Statistical comparisons and numerical verification')
    st=read(O/'statistics.json');story+=[table(['Comparison family','Regime','Friedman statistic','Permutation p'],[[r['scope'],r['mode'],fmt(r['friedman_statistic']),fmt(r['permutation_p'])] for r in st['tests']],[159,90,125,125]),Spacer(1,10)]
    pr=rows(O/'fitness_pairwise.csv');winnerpairs=[r for r in pr if r['scope']=='new_six' and r['mode']=='robust' and bestrob['method'] in [r['A'],r['B']]]
    story+=[para('Robust-training median leader: paired comparisons','Heading2'),table(['A','B','Mean A−B','95% bootstrap CI','Holm p'],[[r['A'],r['B'],fmt(r['mean_A_minus_B']),f'[{fmt(r["mean_difference_ci95_low"])}, {fmt(r["mean_difference_ci95_high"])}]',fmt(r['holm_p'])] for r in winnerpairs],[45,45,100,209,100]),para(st['inference'],'Small')]
    nn=rows(O/'integration_checks.csv');ll=rows(O/'sampled_local_stability.csv')
    story+=[para('Best robust candidates: numerical and local checks','Heading2'),table(['Method','Max Δ angle (°)','Max Δ rate (°/s)','Stable plants / sampled'],[[m,fmt(max(float(r['max_angle_difference_deg']) for r in nn if r['method']==m)),fmt(max(float(r['max_rate_difference_deg_s']) for r in nn if r['method']==m)),f'{sum(r["all_axes_locally_stable"]=="True" for r in ll if r["method"]==m)}/{sum(r["method"]==m for r in ll)}'] for m in METHODS],[65,125,125,184]),para('Integration differences compare 1 ms and 0.5 ms RK4 steps with controller and mixer periods fixed. Local eigenvalue checks use the exact lifted sampled controller at hover; they do not establish large-signal stability. Failure categories and additional diagnostics remain available for inspection.','Small')]
    page(story,'Reproducibility and evidence');reproduction(story)
    page(story,'References and conclusion');references(story)
    story+=[para('Conclusion','Heading2'),para(f'This benchmark quantifies how six additional search procedures behave under a fixed control problem and final evaluation budget. {bestrob["method"]} leads the new methods by median robust-training fitness, but a defensible choice must also consider seed consistency, constraint compliance, held-out pass rates and joint-boundary failures. The useful output is an auditable set of fixed-gain candidates and evidence of their operating limits, rather than a claim that one algorithm is universally best.')]
    stress=[int(r['combined_stress_passes']) for r in rows(O/'validation_summary.csv') if r['mode']!='baseline']
    story.append(para(f'Across all {len(stress)} final controllers, combined-axis stress passes range from {min(stress)} to {max(stress)} out of 90 cases. This is a material limitation of the tested controller/model/constraint combination. Improved random single-axis performance must not be presented as successful general maneuvering or flight validation.'))
    runnerup=sorted((r for r in fs if r['mode']=='robust'),key=lambda r:float(r['median']))[1]
    close=next(r for r in winnerpairs if runnerup['method'] in [r['A'],r['B']])
    story.append(para(f'The paired comparison between the robust median leader ({bestrob["method"]}) and runner-up ({runnerup["method"]}) has Holm-adjusted p = {fmt(close["holm_p"])}. '+('The observed median ordering is not statistically resolved at the 5% level.' if float(close['holm_p'])>=.05 else 'The paired fitness difference is statistically significant at the 5% level within this declared comparison family.')))
    build(DEST/'Six_methods_comparison.pdf',story)

def main():
    assert read(O/'analysis_complete.json')['complete'] and read(O/'plots_complete.json')['complete']
    cfg=read(O/'contract.json')['configuration']
    ap=argparse.ArgumentParser();ap.add_argument('--method',choices=METHODS);args=ap.parse_args()
    m=args.method or (read(R/'METHOD.json')['method'] if (R/'METHOD.json').exists() else None)
    for selected_method in ([m] if m else METHODS):method_report(selected_method,cfg);print('Report '+selected_method,flush=True)
    if not m:combined(cfg)
    print('Reports created; visual QA remains.',flush=True)
if __name__=='__main__':main()
