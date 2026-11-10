"""Independent raster/text/image inspection of final real and explicitly labeled fixture PDFs."""
from pathlib import Path
import json
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runtime/analytics-reports-final';results={}
for path in sorted(OUT.glob('*.pdf')):
 doc=fitz.open(path);pages=[]
 for old in OUT.glob(path.stem+'-page-*.png'):
  assert old.parent==OUT
  old.unlink()
 for index,page in enumerate(doc):
  page.get_pixmap(matrix=fitz.Matrix(1.6,1.6)).save(OUT/(path.stem+'-page-'+str(index+1)+'.png'))
  spans=[s for b in page.get_text('dict')['blocks'] if 'lines' in b for line in b['lines'] for s in line['spans']]
  outside=[s['text'] for s in spans if s['bbox'][0]<-1 or s['bbox'][1]<-1 or s['bbox'][2]>page.rect.width+1 or s['bbox'][3]>page.rect.height+1]
  assert not outside,(path.name,index+1,outside)
  if 'Incident Records' in page.get_text() and 'No data' not in page.get_text():assert '#' in page.get_text(),(path.name,index+1,'Empty trailing incident table')
  overlaps=[]
  for a,s in enumerate(spans):
   r=fitz.Rect(s['bbox'])
   for t in spans[a+1:]:
    q=fitz.Rect(t['bbox']);intersection=r&q
    if intersection.width>1 and intersection.height>1 and intersection.get_area()>.3*min(r.get_area(),q.get_area()):overlaps.append([s['text'],t['text']])
  assert not overlaps,(path.name,index+1,'overlapping text',overlaps)
  images=[]
  for image in page.get_image_info():
   bounds=fitz.Rect(image['bbox']);dpi=min(image['width']/(bounds.width/72),image['height']/(bounds.height/72));assert dpi>=250,(path.name,index+1,dpi)
   images.append({'pixels':[image['width'],image['height']],'effective_DPI':round(dpi,1)})
  assert abs(page.rect.width-595.28)<2 and abs(page.rect.height-841.89)<2
  pages.append({'page':index+1,'vector_drawings':len(page.get_drawings()),'images':images,'minimum_font_pt':round(min(s['size'] for s in spans),2),'outside_page':outside,'major_text_overlaps':overlaps,'text_chars':len(page.get_text())})
 results[path.name]={'source':'explicit UI stress fixture' if path.stem.startswith(('long-labels','large-dataset')) else 'actual SQLite selection','pages':pages}
for name in ['download-visual.pdf','print-visual.pdf']:
 assert not results[name]['pages'][0]['images'] and not results[name]['pages'][1]['images']
 assert results[name]['pages'][0]['vector_drawings']>15
 assert sum(len(p['images']) for p in results[name]['pages'])==4
for name in ['private-metadata.pdf','no-data.pdf']:assert not any(p['images'] for p in results[name]['pages'])
assert len(results['download-visual.pdf']['pages'])==len(results['print-visual.pdf']['pages'])
assert len(results['large-dataset.pdf']['pages'])==len(results['large-dataset-print.pdf']['pages'])
(OUT/'pdf-inspection.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps({'PDFs':len(results),'pages_inspected':sum(len(r['pages']) for r in results.values()),'no_clipped_or_overlapping_text':True,'vector_charts':True,'minimum_evidence_DPI':min(i['effective_DPI'] for r in results.values() for p in r['pages'] for i in p['images'])}))
