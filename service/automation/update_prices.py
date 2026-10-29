"""Fetch exact selected retail SKUs; never replace a failed quote with zero or a guessed pack."""
import concurrent.futures
import datetime as dt
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import urllib.request
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.skip=0
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style','noscript'): self.skip+=1
    def handle_endtag(self, tag):
        if tag in ('script','style','noscript'): self.skip=max(0,self.skip-1)
    def handle_data(self, data):
        if not self.skip: self.parts.append(data)

def extract_price(raw, source):
    page=Page(); page.feed(raw)
    text=re.sub(r'\s+', ' ', ' '.join(page.parts)).strip()
    if source['identity'].casefold() not in text.casefold():
        raise ValueError('Product identity missing')
    # The short article following this exact label belongs to the selected pack.
    article=re.search(r'(?:Короткий артикул|Артикул)\s*:?\s*([0-9]{7}-[0-9A-Z]{3})\b',text,re.I)
    if not article or article.group(1)!=source['sku']:
        raise ValueError('Selected SKU missing or differs; refusing to guess package')
    suffix=source['sku'].rsplit('-',1)[1]
    if not suffix.isdigit() or int(suffix)!=source['pack']:
        raise ValueError('Package and SKU disagree')
    # Shop's visible primary price; do not scrape related product cards or lowPrice.
    match=re.search(r'\bЦена\s*:?\s*([0-9][0-9\s]*(?:[.,][0-9]{1,2})?)\s*(?:₽|руб\.?)(?:\s|$)',text)
    if not match: raise ValueError('Primary RUB price unavailable')
    try: price=Decimal(re.sub(r'\s','',match.group(1)).replace(',','.'))
    except InvalidOperation: raise ValueError('Invalid price')
    if not Decimal('50') <= price <= Decimal('1000000'): raise ValueError('Price outside sanity bounds')
    return float(price.quantize(Decimal('.01')))

def fetch_quote(item):
    key,source=item
    errors=[]
    for url in [source['url']]+source.get('fallback_urls',[]):
        try:
            if urllib.parse.urlparse(url).hostname not in ('shop.ravenol.ru','catalog.ravenol.ru'):
                raise ValueError('Unapproved source host')
            request=urllib.request.Request(url,headers={'User-Agent':'SMCHIP-PriceCheck/1.0 (+https://github.com/artemmalov58-bit/SMCHIP)','Accept-Language':'ru'})
            with urllib.request.urlopen(request,timeout=20) as response:
                if urllib.parse.urlparse(response.url).hostname not in ('shop.ravenol.ru','catalog.ravenol.ru'):
                    raise ValueError('Unexpected source host')
                html=response.read(8_000_000).decode('utf-8')
            return key,extract_price(html,source),url
        except Exception as exc:
            errors.append(urllib.parse.urlparse(url).hostname+': '+type(exc).__name__+' '+str(exc)[:80])
    raise ValueError('; '.join(errors))

def update():
    sources=json.loads((ROOT/'price_sources.json').read_text())
    target=ROOT/'prices.json'; data=json.loads(target.read_text()); now=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    failed=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures={executor.submit(fetch_quote,item):item[0] for item in sources.items()}
        for future,key in [(f,k) for f,k in futures.items()]:
            row=data['products'][key];row['lastAttemptAt']=now
            try:
                _,price,source_url=future.result();row.update(price=price,sourceURL=source_url,pack=sources[key]['pack'],sku=sources[key]['sku'],url=sources[key]['url'],verifiedAt=now,verification='direct',status='ok');row.pop('error',None)
                print(key,price,'RUB /',row['pack'],'L',row['sku'])
            except Exception as exc:
                row['status']='error';row['error']=str(exc)[:200];failed.append(key);print(key,'UNCHANGED:',type(exc).__name__,str(exc)[:160])
    data['lastAttemptAt']=now;data['cadenceHours']=6
    temp=target.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');temp.replace(target)
    print('Successful:',len(sources)-len(failed),'Failed:',len(failed))
    return 1 if failed else 0

if __name__=='__main__': sys.exit(update())
