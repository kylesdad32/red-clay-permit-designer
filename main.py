from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import httpx

app=FastAPI(title='Red Clay Permit Designer',version='1.0')
ROOT=Path(__file__).parent
app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')
GEOCODE='https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates'
SERVICES=[('Cleveland County Assessor / Moore parcel layer','https://services.arcgis.com/DO4gTjwJVIJ7O9Ca/ArcGIS/rest/services/Moore_Parcels/FeatureServer/0/query'),('Cleveland County parcels (2020)','https://services6.arcgis.com/2mzSgEVuNJwBvEDM/arcgis/rest/services/Cleveland_County_Parcels/FeatureServer/0/query')]
@app.get('/')
def home(): return FileResponse(ROOT/'static'/'index.html')
@app.get('/api/property')
async def property_lookup(address:str):
    if len(address.strip())<8: raise HTTPException(400,'Enter a complete street address')
    async with httpx.AsyncClient(timeout=16,follow_redirects=True) as client:
        try:
            g=(await client.get(GEOCODE,params={'SingleLine':address,'f':'json','outFields':'*','maxLocations':5})).json()
            candidates=[c for c in g.get('candidates',[]) if c.get('score',0)>=85 and ('OK' in c.get('address','') or 'Oklahoma' in c.get('address',''))]
            if not candidates: raise HTTPException(404,'No confident Oklahoma address match')
            c=candidates[0]; loc=c['location']; errors=[]
            for name,url in SERVICES:
                try:
                    p={'f':'json','geometry':f'{loc["x"]},{loc["y"]}','geometryType':'esriGeometryPoint','inSR':4326,'spatialRel':'esriSpatialRelIntersects','outFields':'*','returnGeometry':'true','outSR':3857}
                    data=(await client.get(url,params=p)).json()
                    for feature in data.get('features',[]):
                        if feature.get('geometry',{}).get('rings'):
                            return {'address':c['address'],'score':c['score'],'source':name,'source_url':url,'type':'GIS PARCEL — NOT RECORDED PLAT','geometry':feature['geometry'],'attributes':feature.get('attributes',{}),'plat_verified':False}
                    errors.append(name+': no intersecting parcel')
                except Exception as e: errors.append(name+': '+str(e)[:120])
            return {'address':c['address'],'score':c['score'],'type':'NO PARCEL VERIFIED','plat_verified':False,'errors':errors}
        except httpx.RequestError as e: raise HTTPException(502,'External GIS service unavailable: '+str(e)[:120])
