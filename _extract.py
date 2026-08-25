import zipfile, re, os, json
from xml.etree import ElementTree as ET

PPTX = "ArcticSBI_Results_DefengLu_v3.pptx"
NS = {
    'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
    'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
    'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
}

z = zipfile.ZipFile(PPTX)

def get_rels(slide):
    rels = slide.replace('slides/slide','slides/_rels/slide') + '.rels'
    tree = ET.fromstring(z.read(rels))
    mapping = {}
    for rel in tree:
        rid = rel.get('Id')
        tgt = rel.get('Target')
        if tgt.startswith('..'):
            tgt = 'ppt/' + tgt.split('/',1)[1]
        elif not tgt.startswith('ppt'):
            tgt = 'ppt/slides/' + tgt
        mapping[rid] = tgt
    return mapping

def text_of(shape):
    out = []
    for t in shape.iter('{http://schemas.openxmlformats.org/drawingml/2006/main}t'):
        out.append(t.text or '')
    return ''.join(out)

def walk(spTree, slide_media, slide_text):
    for child in list(spTree):
        tag = child.tag.split('}')[-1]
        if tag in ('sp','graphicFrame','pic','grpSp'):
            if tag == 'pic':
                blip = child.find('.//{http://schemas.openxmlformats.org/drawingml/2006/main}blip')
                if blip is not None:
                    rid = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                    if rid in slide_media:
                        slide_text.append(('IMAGE', slide_media[rid]))
            txt = text_of(child)
            if txt.strip():
                slide_text.append(('TEXT', txt.strip()))
            if tag == 'grpSp':
                walk(child, slide_media, slide_text)
        # recurse into groups handled above; spTree children handled

result = {}
for i in range(1, 100):
    sname = f'ppt/slides/slide{i}.xml'
    if sname not in z.namelist():
        break
    tree = ET.fromstring(z.read(sname))
    media = get_rels(sname)
    spTree = tree.find('.//{http://schemas.openxmlformats.org/presentationml/2006/main}spTree')
    slide_text = []
    walk(spTree, media, slide_text)
    result[i] = slide_text

for i in range(1, len(result)+1):
    print(f"\n===== SLIDE {i} =====")
    for kind, val in result[i]:
        if kind == 'IMAGE':
            print(f"[IMAGE] {val}")
        else:
            print(val)
