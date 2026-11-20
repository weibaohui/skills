#!/usr/bin/env python3
"""Report dense deck properties, hard geometry failures and editable-object evidence.
No minimum body font or arbitrary character quota is imposed. This does not certify visual fit.
"""
import argparse,collections,json,re
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E

NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
def check(src):
    pages=[];fail=[];warnings=[]
    with ZipFile(src) as z:
        p=E.fromstring(z.read('ppt/presentation.xml'));sz=p.find('p:sldSz',NS);w,h=int(sz.get('cx')),int(sz.get('cy'))
        rels=E.fromstring(z.read('ppt/_rels/presentation.xml.rels'));targets={r.get('Id'):r.get('Target') for r in rels}
        for i,sid in enumerate(p.findall('p:sldIdLst/p:sldId',NS),1):
            target=targets[sid.get('{'+NS['r']+'}id')];name=target.lstrip('/') if target.startswith('/') else 'ppt/'+target
            root=E.fromstring(z.read(name)); texts=root.findall('.//a:t',NS);hist=collections.Counter();fonts=collections.Counter();unknown=0
            for r in root.findall('.//a:r',NS):
                t=''.join(r.find('a:t',NS).itertext()) if r.find('a:t',NS) is not None else '';pr=r.find('a:rPr',NS)
                if pr is None or pr.get('sz') is None:unknown+=len(t)
                else:hist[str(int(pr.get('sz'))/100)]+=len(t)
                if pr is not None:
                    for tag in ['latin','ea','cs']:
                        f=pr.find('a:'+tag,NS)
                        if f is not None:fonts[tag+':'+f.get('typeface','')]+=1
            # Deliberately skip grouped objects here; use inspect_pptx.py for mapped group coordinates.
            tree=root.find('p:cSld/p:spTree',NS);out=[];fullpictures=[]
            for s in tree:
                xf=s.find('p:spPr/a:xfrm',NS)
                if xf is None:xf=s.find('p:xfrm',NS)
                if xf is None:continue
                off=xf.find('a:off',NS);ext=xf.find('a:ext',NS)
                if off is None or ext is None:continue
                x,y,cx,cy=[int(v) for v in [off.get('x'),off.get('y'),ext.get('cx'),ext.get('cy')]]
                if x < -9525 or y < -9525 or x+cx>w+9525 or y+cy>h+9525:out.append(s.find('.//p:cNvPr',NS).get('name',''))
                if E.QName(s).localname=='pic' and cx*cy/(w*h)>.8:fullpictures.append(True)
            if out:fail.append({'page':i,'out_of_canvas':out})
            chars=sum(len(t.text or '') for t in texts);tables=len(root.findall('.//a:tbl',NS));pictures=len(root.findall('.//p:pic',NS))
            if fullpictures and chars<40:warnings.append({'page':i,'warning':'Possible full-page raster slide: inspect editability'})
            if unknown:warnings.append({'page':i,'warning':'Some font sizes are inherited; run inspect_pptx.py for deeper resolution','characters':unknown})
            pages.append({'page':i,'characters':chars,'text_shapes':len(root.findall('.//p:sp[p:txBody]',NS)),'native_tables':tables,'pictures':pictures,'explicit_pt_character_histogram':dict(hist),'font_slots':dict(fonts),'unknown_font_characters':unknown})
    return {'input':str(src),'slides':len(pages),'canvas_emu':[w,h],'pages':pages,'failures':fail,'warnings':warnings,'limits':'No glyph overflow or nested containment is certified. Native counts are evidence, not a visual editability guarantee. Inspect every final slide and small blocks at enlarged scale.'}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source');p.add_argument('--output',required=True);a=p.parse_args();r=check(a.source);Path(a.output).write_text(json.dumps(r,ensure_ascii=False,indent=2));print(json.dumps({'slides':r['slides'],'failures':len(r['failures']),'warnings':len(r['warnings']),'report':a.output}));raise SystemExit(1 if r['failures'] else 0)
