#!/usr/bin/env python3
"""Normalize Latin/EA/CS slots in a newly authored deck; never mutate the input."""
import argparse
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E

def normalize(source, output, font):
    if Path(source).resolve() == Path(output).resolve():
        raise ValueError('Choose a different output; input is preserved')
    if Path(output).exists():
        raise FileExistsError(output)
    ns='http://schemas.openxmlformats.org/drawingml/2006/main'
    count=0
    with ZipFile(source) as zin, ZipFile(output,'w') as zout:
        for info in zin.infolist():
            data=zin.read(info.filename)
            if info.filename.startswith('ppt/') and info.filename.endswith('.xml'):
                root=E.fromstring(data)
                for e in root.iter():
                    local=E.QName(e).localname
                    if E.QName(e).namespace!=ns:continue
                    if local in ('latin','ea','cs','font') and 'typeface' in e.attrib:
                        e.set('typeface',font);count+=1
                    if local in ('rPr','defRPr','endParaRPr'):
                        for tag in ('latin','ea','cs'):
                            f=e.find('{'+ns+'}'+tag)
                            if f is None:f=E.SubElement(e,'{'+ns+'}'+tag)
                            f.set('typeface',font)
                data=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
            zout.writestr(info,data)
    return count

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source');p.add_argument('output');p.add_argument('--font',default='Microsoft YaHei');a=p.parse_args()
    print({'normalized_existing_slots':normalize(a.source,a.output,a.font),'output':a.output})
