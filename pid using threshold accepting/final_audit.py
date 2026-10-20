"""Final numerical/export audit. Run with bundled Python (pypdf installed)."""
from pathlib import Path
import json,csv,gzip,math,hashlib,zipfile,xml.etree.ElementTree as ET
from pypdf import PdfReader
from PIL import Image
R=Path(__file__).resolve().parent;O=R/'results';METHODS=['GDA','TA','ALNS','VND','SBRS','PRW']
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def rows(p):
    with Path(p).open(encoding='utf-8') as f:return list(csv.DictReader(f))
def main():
    assert read(O/'audit.json')['passed'] and read(O/'analysis_complete.json')['complete']
    manuscript=read(O/'manuscript_preservation.json')
    assert hashlib.sha256(Path(manuscript['path']).read_bytes()).hexdigest()==manuscript['sha256']
    g=rows(O/'exports/all_runs_gains.csv');assert len(g)==360
    assert len({(r['mode'],r['method'],r['seed']) for r in g})==360
    cfg=read(O/'contract.json')['configuration'];names=[p['name'] for p in cfg['parameters']]
    for r in g:
        rr=read(O/r['mode']/'runs'/f'{r["method"]}_{r["seed"]}.json')
        assert [float(r[k]) for k in names]==rr['gains']
        assert float(r['fitness'])==rr['fitness']
        for axis,idx in [('roll',0),('pitch',3)]:
            assert float(r[axis+'_b0'])==rr['gains'][idx+1]+.001*rr['gains'][idx+2]
            assert float(r[axis+'_b1'])==-.9997*rr['gains'][idx+1]
    selected=rows(O/'selected_candidates.csv');assert len(selected)==24
    for row in selected:
        export=read(O/'exports'/f'{row["mode"]}_{row["method"]}_{row["selection"]}_gains.json')
        assert export['seed']==int(row['seed'])
        assert export['validation']['single_axis_mc_passes']==int(row['mc_passes'])
    vv=rows(O/'validation_summary.csv');assert len(vv)==361
    for row in vv:
        with gzip.open(O/'validation'/f'{row["mode"]}_{row["method"]}_{row["seed"]}.json.gz','rt',encoding='utf-8') as f:d=json.load(f)
        assert len(d['cases'])==444 and len({c['name'] for c in d['cases']})==444
        for group,n in [('single_axis_mc',300),('one_at_a_time',54),('combined_stress',90)]:
            cc=[c for c in d['cases'] if c['group']==group];assert len(cc)==n
            assert sum(c['feasible'] for c in cc)==int(row[group+'_passes'])
    cc=rows(O/'corner_validation_summary.csv');assert len(cc)==25
    assert all(int(r['cases'])==1536 and int(r['physical_cases'])==1344 for r in cc)
    pdfs=list((R/'output/pdf').glob('*.pdf'));assert len(pdfs)==7
    pdfmeta=[]
    for p in pdfs:
        r=PdfReader(p);assert len(r.pages)>=8
        text='\n'.join(page.extract_text() for page in r.pages)
        assert 'nan' not in text.lower().split() and 'placeholder' not in text.lower()
        pdfmeta.append({'file':p.name,'pages':len(r.pages),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    images=list((O/'plots').rglob('*.png'));assert len(images)==52,len(images)
    for p in images:
        with Image.open(p) as im:im.verify()
    workbook=R/'output/Six_methods_results.xlsx';ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(workbook) as z:
        ws=[n for n in z.namelist() if n.startswith('xl/worksheets/sheet') and n.endswith('.xml')];assert len(ws)==9
        for name in ws:
            root=ET.fromstring(z.read(name));assert not [c for c in root.findall('.//s:c',ns) if c.get('t')=='e'],name
        shared=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            shared=[''.join(t.text or '' for t in item.findall('.//s:t',ns)) for item in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        rels={e.get('Id'):e.get('Target') for e in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        sheets={}
        for sh in ET.fromstring(z.read('xl/workbook.xml')).findall('.//s:sheet',ns):
            target=rels[sh.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')]
            target=target.lstrip('/') if target.startswith('/') else 'xl/'+target
            sheets[sh.get('name')]={c.get('r'):c for c in ET.fromstring(z.read(target)).findall('.//s:c',ns)}
        def column(j):
            result='';j+=1
            while j:j,k=divmod(j-1,26);result=chr(65+k)+result
            return result
        def value(cell):
            if cell is None:return None
            kind=cell.get('t');v=cell.find('s:v',ns)
            if kind=='inlineStr':return ''.join(t.text or '' for t in cell.findall('.//s:t',ns))
            if v is None:return None
            if kind=='s':return shared[int(v.text)]
            if kind=='b':return v.text=='1'
            if kind=='str':return v.text
            return float(v.text)
        for table in read(O/'workbook_input.json'):
            actual=sheets[table['name']]
            expected=[[h.replace('_',' ') for h in table['headers']]]+table['data']
            for i,row in enumerate(expected,5):
                for j,wanted in enumerate(row):
                    address=f'{column(j)}{i}';got=value(actual.get(address))
                    if isinstance(wanted,bool):assert got is wanted,(table['name'],address,got,wanted)
                    elif isinstance(wanted,(int,float)):
                        assert isinstance(got,(int,float)) and math.isclose(got,wanted,rel_tol=1e-13,abs_tol=0),(table['name'],address,got,wanted)
                    else:assert got==wanted or (wanted is None and got==''),(table['name'],address,got,wanted)
    q=read(O/'visual_qa.json');assert q['passed']
    assert {r['sha256'] for r in pdfmeta}==set(q['pdf_sha256'].values()),'Visual QA does not match final PDFs'
    result={'passed':True,'main_runs':360,'development_runs':144,'heldout_controllers':361,'heldout_cases_per_controller':444,
            'joint_boundary_controllers':25,'joint_boundary_cases_per_controller':1536,'gains_export_rows':360,'selected_controllers':24,
            'png_figures':len(images),'pdfs':pdfmeta,'workbook':workbook.name,'workbook_tables_verified_cell_by_cell':9,'workbook_sha256':hashlib.sha256(workbook.read_bytes()).hexdigest()}
    (O/'final_audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
