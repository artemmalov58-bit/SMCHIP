from pathlib import Path
import json,re,html,shutil
p=Path(__file__).resolve().parent;(p/'dist').mkdir(exist_ok=True);
if (p.parent/'dist/assets').is_dir():shutil.copytree(p.parent/'dist/assets',p/'dist/assets',dirs_exist_ok=True)
data=json.loads((p/'data.json').read_text());sources=data['sources'];m=data['models']['001'];esc=html.escape

def link(k):
 if not k:return '<span class="tag gray">Нужна сверка по VIN</span>'
 return '<a class="source-link" target="_blank" rel="noopener noreferrer" href="'+esc(sources[k]['url'])+'">'+('RAVENOL · справка' if k.startswith('r') else 'Zeekr · документ')+' ↗</a>'
schedule=''.join('<tr><td>'+esc(r[0])+'</td><td><strong>'+esc(r[1])+'</strong></td><td>'+esc(r[2])+'<small>'+('Рекомендация сервиса SM CHIP' if 'SM CHIP' in r[0] else link(r[3]))+'</small></td></tr>' for r in m['schedule'])
fluids=''.join('<tr><td>'+esc(r[0])+'</td><td>'+esc(r[1])+'</td><td>'+esc(r[2])+'<small>'+('Подбор производителя масел, не заводской допуск Zeekr' if r[4] else 'Применимость не подтверждена')+'</small></td><td>'+esc(r[3])+'<small>'+link(r[4])+'</small></td></tr>' for r in m['fluids'])
sourcehtml=''.join('<a class="source-item" target="_blank" rel="noopener noreferrer" href="'+esc(sources[k]['url'])+'"><span>'+esc(sources[k]['type'])+'</span><strong>'+esc(sources[k]['name'])+' ↗</strong><small>'+esc(sources[k]['scope'])+'</small></a>' for k in m['sources'])
js=(p/'app.js').read_text().replace('__DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':')))
s=(p/'page.html').read_text()
for a,b in {'__INITIAL_SCHEDULE__':schedule,'__INITIAL_FLUIDS__':fluids,'__INITIAL_NOTE__':esc(m['note']),'__INITIAL_SOURCES__':sourcehtml,'__R8X__':esc(sources['r8X']['url']),'__GCC__':esc(sources['gcc']['url']),'__001__':esc(sources['manual001']['url']),'__SCRIPT__':js}.items():s=s.replace(a,b)
(p/'dist/index.html').write_text(s)
(p/'compiled-check.js').write_text(js)
print('Page characters',len(s),'bytes',len(s.encode()))

asset='https://raw.githubusercontent.com/artemmalov58-bit/SMCHIP/c15ac2f8dc1b2c5d76e1f0afeb5937b9ef8b0511/dist/assets/'
(p/'github-index.html').write_text(s.replace('src="assets/','src="../dist/assets/').replace("'assets/'","'../dist/assets/'"))
(p/'tilda-public.css').write_text(re.search(r'<style>(.*?)</style>',s,re.S).group(1).replace('sm-service','zs'))
(p/'runtime-public.js').write_text(js.replace('sm-service','zs').replace("'assets/'","'"+asset+"'"))
