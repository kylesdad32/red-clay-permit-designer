from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import httpx

app=FastAPI(title='Red Clay Permit Designer',version='1.1')
ROOT=Path(__file__).parent
app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')
GEOCODE='https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates'
SERVICES=[
    ('City of Moore TaxParcels (August 2025)','https://gis.cityofmoore.com/arcgis/rest/services/Hosted/Parcels/FeatureServer/0/query'),
    ('Cleveland County Assessor / Moore parcel layer','https://services.arcgis.com/DO4gTjwJVIJ7O9Ca/ArcGIS/rest/services/Moore_Parcels/FeatureServer/0/query'),
    ('Cleveland County parcels (2020)','https://services6.arcgis.com/2mzSgEVuNJwBvEDM/arcgis/rest/services/Cleveland_County_Parcels/FeatureServer/0/query')
]


# Assessor sketch discovery is best-effort: a parcel outline is never substituted for a sketch.
from urllib.parse import urljoin, quote
from html.parser import HTMLParser
import re

ASSESSOR_BASE = 'https://property.spatialest.com/ok/cleveland/'
class _SketchLinks(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs); target=a.get('src') or a.get('href') or ''
        if target and (tag in ('img','a','iframe','embed','object')):
            self.links.append((target, a.get('alt','')+' '+a.get('title','')))

async def _find_assessor_sketch(client, account):
    """Only accept independently retrievable image/PDF resources clearly identified as sketches."""
    if not account: return None
    account=str(account).strip()
    if not re.fullmatch(r'[A-Za-z0-9-]{4,30}',account): return None
    page=ASSESSOR_BASE+'#/property/'+quote(account)
    # Hash routes are rendered by JavaScript; never pretend the HTML shell is a sketch.
    try:
        r=await client.get(ASSESSOR_BASE, timeout=10)
        if r.status_code!=200: return {'record_url':page,'status':'assessor_unavailable'}
        parser=_SketchLinks();parser.feed(r.text[:500000])
        for target,desc in parser.links:
            if not re.search(r'(sketch|apex|floor.?plan|building.?diagram)',target+' '+desc,re.I):continue
            url=urljoin(ASSESSOR_BASE,target)
            if not url.startswith('https://'):continue
            try:
                image=await client.get(url,timeout=8)
                if image.status_code==200 and image.headers.get('content-type','').lower().split(';')[0] in ('image/png','image/jpeg','image/webp','application/pdf'):
                    return {'record_url':page,'status':'found','sketch_url':url}
            except httpx.RequestError: pass
        return {'record_url':page,'status':'not_exposed'}
    except (httpx.RequestError,ValueError):
        return {'record_url':page,'status':'assessor_unavailable'}

@app.get('/api/assessor-sketch')
async def assessor_sketch(account:str):
    async with httpx.AsyncClient(follow_redirects=True,timeout=12) as client:
        return await _find_assessor_sketch(client,account)

@app.get('/')
def home():
    return FileResponse(ROOT/'static'/'index.html')

@app.get('/api/property')
async def property_lookup(address:str):
    if len(address.strip())<8:
        raise HTTPException(400,'Enter a complete street address')
    async with httpx.AsyncClient(timeout=16,follow_redirects=True) as client:
        try:
            g=(await client.get(GEOCODE,params={'SingleLine':address,'f':'json','outFields':'*','maxLocations':5})).json()
            candidates=[c for c in g.get('candidates',[]) if c.get('score',0)>=85 and ('OK' in c.get('address','') or 'Oklahoma' in c.get('address',''))]
            if not candidates:
                raise HTTPException(404,'No confident Oklahoma address match')
            c=candidates[0]
            loc=c['location']
            errors=[]
            for name,url in SERVICES:
                try:
                    p={
                        'f':'json',
                        'geometry':f'{loc["x"]},{loc["y"]}',
                        'geometryType':'esriGeometryPoint',
                        'inSR':4326,
                        'spatialRel':'esriSpatialRelIntersects',
                        'outFields':'*',
                        'returnGeometry':'true',
                        'outSR':3857
                    }
                    data=(await client.get(url,params=p)).json()
                    for feature in data.get('features',[]):
                        if feature.get('geometry',{}).get('rings'):
                            return {
                                'address':c['address'],
                                'score':c['score'],
                                'source':name,
                                'source_url':url,
                                'type':'GIS PARCEL — NOT RECORDED PLAT',
                                'geometry':feature['geometry'],
                                'attributes':feature.get('attributes',{}),
                                'plat_verified':False,
                                'geocode_location':loc,
                                'assessor_sketch': await _find_assessor_sketch(client, next((str(v) for k,v in feature.get('attributes',{}).items() if v and re.search(r'^(account|accountno|account_num|propertyid|property_id|prop_id|parcelid)$',k,re.I)), ''))
                            }
                    errors.append(name+': no intersecting parcel')
                except Exception as e:
                    errors.append(name+': '+str(e)[:120])
            return {
                'address':c['address'],
                'score':c['score'],
                'type':'NO PARCEL VERIFIED',
                'plat_verified':False,
                'errors':errors,
                'geocode_location':loc
            }
        except httpx.RequestError as e:
            raise HTTPException(502,'External GIS service unavailable: '+str(e)[:120])
