#!/usr/bin/env python3
"""Read OOXML evidence without changing the source; no python-pptx required."""
import argparse, collections, json, posixpath, re, zipfile
from pathlib import Path
from lxml import etree as E

NS = {'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
      'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
EMU = 914400

def inspect(source):
    z = zipfile.ZipFile(source)
    def xml(path): return E.fromstring(z.read(path))
    def rels(path):
        rp = posixpath.join(posixpath.dirname(path),'_rels',posixpath.basename(path)+'.rels')
        if rp not in z.namelist(): return {}
        return {x.get('Id'): {'target':posixpath.normpath(posixpath.join(posixpath.dirname(path),x.get('Target'))).lstrip('/'), 'type':x.get('Type').split('/')[-1]} for x in xml(rp) if x.get('TargetMode')!='External'}
    def relation(path, kind): return next(v['target'] for v in rels(path).values() if v['type']==kind)
    pre = xml('ppt/presentation.xml'); dim = pre.find('p:sldSz',NS)
    sw,sh = int(dim.get('cx')),int(dim.get('cy'))
    pages=[]; all_sizes=collections.Counter(); all_fonts=collections.Counter()
    for pid in pre.findall('p:sldIdLst/p:sldId',NS):
        spath=rels('ppt/presentation.xml')[pid.get('{'+NS['r']+'}id')]['target']
        slide=xml(spath); lpath=relation(spath,'slideLayout'); layout=xml(lpath)
        mpath=relation(lpath,'slideMaster'); master=xml(mpath)
        theme=xml(relation(mpath,'theme'))
        fonts={}
        for kind,label in [('majorFont','mj'),('minorFont','mn')]:
            node=theme.find('a:themeElements/a:fontScheme/a:'+kind,NS)
            for tag,suf in [('latin','lt'),('ea','ea'),('cs','cs')]:
                fonts['+'+label+'-'+suf]=node.find('a:'+tag,NS).get('typeface')
        def ph_for(shape,parent):
            ph=shape.find('p:nvSpPr/p:nvPr/p:ph',NS)
            if ph is None: return None
            for candidate in parent.findall('.//p:sp',NS):
                cp=candidate.find('p:nvSpPr/p:nvPr/p:ph',NS)
                if cp is not None and cp.get('idx','0')==ph.get('idx','0'): return candidate
            return None
        def geometry(shape):
            tf=shape.find('p:spPr/a:xfrm',NS)
            if tf is None: tf=shape.find('p:xfrm',NS)
            if tf is None:
                inherited=ph_for(shape,layout)
                if inherited is not None: tf=inherited.find('p:spPr/a:xfrm',NS)
            if tf is None: return None
            off,ext=tf.find('a:off',NS),tf.find('a:ext',NS)
            if off is None or ext is None: return None
            x,y,w,h=map(float,[off.get('x'),off.get('y'),ext.get('cx'),ext.get('cy')])
            sx=sy=1.
            for anc in shape.iterancestors():
                if anc.tag!='{'+NS['p']+'}grpSp': continue
                gt=anc.find('p:grpSpPr/a:xfrm',NS)
                if gt is None: continue
                go,ge,gco,gce=[gt.find('a:'+t,NS) for t in ['off','ext','chOff','chExt']]
                if any(t is None for t in [go,ge,gco,gce]): continue
                gx=float(ge.get('cx'))/float(gce.get('cx') or 1);gy=float(ge.get('cy'))/float(gce.get('cy') or 1)
                x=float(go.get('x'))+(x-float(gco.get('x')))*gx;y=float(go.get('y'))+(y-float(gco.get('y')))*gy;w*=gx;h*=gy;sx*=gx;sy*=gy
            return {'in':[round(v/EMU,4) for v in [x,y,w,h]],'normalized':[round(x/sw,4),round(y/sh,4),round(w/sw,4),round(h/sh,4)],'group_scale':[round(sx,5),round(sy,5)]}
        page_sizes=collections.Counter(); page_fonts=collections.Counter(); resolved_by=collections.Counter(); records=[]
        for shape in slide.xpath('.//p:sp|.//p:graphicFrame|.//p:pic',namespaces=NS):
            nv=shape.find('.//p:cNvPr',NS);name=nv.get('name') if nv is not None else None
            ph=shape.find('p:nvSpPr/p:nvPr/p:ph',NS)
            style='titleStyle' if ph is not None and ph.get('type') in ('title','ctrTitle') else ('bodyStyle' if ph is not None and ph.get('type')=='body' else 'otherStyle')
            inherited=[ph_for(shape,layout),ph_for(shape,master)]
            runs=[]
            for para in shape.findall('.//a:p',NS):
                ppr=para.find('a:pPr',NS);level=int(ppr.get('lvl','0'))+1 if ppr is not None else 1
                for run in para.findall('a:r',NS)+para.findall('a:fld',NS):
                    txt=''.join(run.itertext())
                    if not txt.strip(): continue
                    cands=[('run',run.find('a:rPr',NS)),('paragraph',para.find('a:pPr/a:defRPr',NS)),('shape-list',shape.find('p:txBody/a:lstStyle/a:lvl%dpPr/a:defRPr'%level,NS))]
                    for kind,ishape in zip(['layout','master-placeholder'],inherited):
                        if ishape is not None:
                            cands += [(kind,ishape.find('p:txBody/a:lstStyle/a:lvl%dpPr/a:defRPr'%level,NS)),(kind,ishape.find('p:txBody/a:p/a:pPr/a:defRPr',NS)),(kind,ishape.find('p:txBody/a:p/a:r/a:rPr',NS))]
                    cands += [('master-style',master.find('p:txStyles/p:'+style+'/a:lvl%dpPr/a:defRPr'%level,NS)),('presentation-default',pre.find('p:defaultTextStyle/a:lvl%dpPr/a:defRPr'%level,NS))]
                    sz=ea=latin=via=None
                    for kind,node in cands:
                        if node is None: continue
                        if sz is None and node.get('sz') is not None: sz=float(node.get('sz'))/100;via=kind
                        if ea is None and node.find('a:ea',NS) is not None: ea=node.find('a:ea',NS).get('typeface')
                        if latin is None and node.find('a:latin',NS) is not None: latin=node.find('a:latin',NS).get('typeface')
                    ea=fonts.get(ea,ea) or fonts.get('+mn-ea');latin=fonts.get(latin,latin) or fonts.get('+mn-lt')
                    runs.append({'text':txt,'size_pt':sz,'size_source':via,'ea':ea,'latin':latin})
                    page_sizes[str(sz)]+=len(txt);page_fonts[ea]+=len(txt);resolved_by[via]+=1
            text='\n'.join(''.join(p.itertext()) for p in shape.findall('.//a:p',NS))
            fills=shape.xpath('./p:spPr/a:solidFill/*/@val',namespaces=NS)
            record={'id':nv.get('id') if nv is not None else None,'name':name,'type':E.QName(shape).localname,'chars':len(''.join(r['text'] for r in runs)),'text':text,'geometry':geometry(shape),'fills':fills,'sizes_pt_by_runs':dict(collections.Counter(str(r['size_pt']) for r in runs)),'runs':runs}
            records.append(record)
        all_sizes.update(page_sizes);all_fonts.update(page_fonts)
        colors=collections.Counter(slide.xpath('.//a:srgbClr/@val',namespaces=NS))
        ptext=[''.join(s.itertext()) for s in slide.findall('.//a:t',NS)]
        pages.append({'page':len(pages)+1,'zip_path':spath,'chars':sum(len(x) for x in ptext),'shapes':len(slide.findall('.//p:sp',NS)),'groups':len(slide.findall('.//p:grpSp',NS)),'pictures':len(slide.findall('.//p:pic',NS)),'tables':len(slide.findall('.//a:tbl',NS)),'sizes_pt_by_characters':dict(page_sizes),'east_asian_font_by_characters':dict(page_fonts),'size_resolution_by_runs':dict(resolved_by),'explicit_rgb_counts':colors.most_common(12),'records':records})
    return {'source':str(source),'count':len(pages),'dimensions_emu':[sw,sh],'dimensions_inches':[sw/EMU,sh/EMU],'aspect':sw/sh,'method':'OOXML run -> paragraph -> shape list -> layout placeholder -> master placeholder -> master style -> presentation default; theme font references resolved. Text-size histogram is raw logical pt, not multiplied by group transforms. Group transforms separately retained. Tables are counted; full table style cascade is not resolved. Character counts include whitespace and Latin characters, exclude notes/master text. RGB frequency is XML occurrence frequency, not area.', 'sizes_pt_by_characters':dict(all_sizes),'east_asian_font_by_characters':dict(all_fonts),'pages':pages}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source');parser.add_argument('--output', required=True);args=parser.parse_args()
    result=inspect(Path(args.source));Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='pages'},ensure_ascii=False,indent=2))
