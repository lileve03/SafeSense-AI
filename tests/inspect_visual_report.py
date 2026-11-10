"""Inspect real PDF pages and render review artifacts. Run with .venv/Scripts/python.exe."""
from pathlib import Path
import json
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runtime/visual-pdf-report'
results={}
for name in ['download-visual','print-visual','filtered-visual','private-metadata','no-data']:
 doc=fitz.open(OUT/(name+'.pdf'));rows=[]
 for index,page in enumerate(doc):
  page.get_pixmap(matrix=fitz.Matrix(1.6,1.6)).save(OUT/(name+'-page-'+str(index+1)+'.png'))
  spans=[span for block in page.get_text('dict')['blocks'] if 'lines' in block for line in block['lines'] for span in line['spans']]
  outside=[span['text'] for span in spans if span['bbox'][0]<-1 or span['bbox'][1]<-1 or span['bbox'][2]>page.rect.width+1 or span['bbox'][3]>page.rect.height+1]
  assert not outside,(name,index+1,outside)
  assert len(page.get_text())>40,(name,index+1,'empty page')
  rows.append({'page':index+1,'drawings':len(page.get_drawings()),'drawn_images':len(page.get_image_info()),'minimum_font_pt':round(min(s['size'] for s in spans),2),'outside_page':outside,'text_chars':len(page.get_text())})
 results[name]=rows
assert len(results['download-visual'])==len(results['print-visual'])
for name in ['download-visual','print-visual']:
 assert results[name][0]['drawn_images']==results[name][1]['drawn_images']==0
 assert results[name][0]['drawings']>15 and results[name][1]['drawings']>10
 assert results[name][2]['drawn_images']==4
assert all(p['drawn_images']==0 for name in ['private-metadata','no-data'] for p in results[name])
(OUT/'pdf-inspection.json').write_text(json.dumps(results,indent=2))
print(json.dumps({'PDFs':len(results),'pages_inspected':sum(len(v) for v in results.values()),'matching_full_report_pages':len(results['download-visual']),'no_text_outside_A4':True,'charts_are_vector':True,'private_images':0}))
