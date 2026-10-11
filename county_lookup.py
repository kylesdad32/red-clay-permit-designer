"""Route metro addresses to their county assessor's original building sketches."""
import re
import base64
from urllib.parse import urljoin, urlparse, parse_qs
import httpx
from bs4 import BeautifulSoup
from assessor import retrieve, SketchError, street

GEOCODE='https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates'
OK_BASE='https://docs.oklahomacounty.org/assessorwp5/'
GRADY_BASE='https://okcountydata.com/'
COVERAGE={
 'Cleveland':{'status':'automatic','cities':['Moore','Norman','Noble','Oklahoma City']},
 'Oklahoma':{'status':'automatic','cities':['Oklahoma City','Midwest City','Del City','Bethany','Warr Acres','Choctaw','Edmond','Valley Brook','The Village','Nichols Hills','Spencer','Harrah','Jones','Nicoma Park','Forest Park','Luther']},
 'Canadian':{'status':'automatic','cities':['Yukon','Mustang','El Reno','Piedmont','Oklahoma City']},
 'Grady':{'status':'automatic','cities':['Tuttle','Blanchard','Bridge Creek','Chickasha']},
 'McClain':{'status':'provider_access_required','cities':['Newcastle','Blanchard','Purcell','Goldsby','Dibble'],'record_url':'https://www.actdatascout.com/RealProperty/Oklahoma/McClain'},
 'Logan':{'status':'provider_access_required','cities':['Edmond','Guthrie'],'record_url':'https://www.actdatascout.com/RealProperty/Oklahoma/Logan'},
}

async def embed_image(client,url):
    r=await client.get(url)
    r.raise_for_status()
    p=urlparse(str(r.url))
    origin=urlparse(url)
    grady_cdn=(origin.hostname=='okcountydata.com' and origin.path.lower()=='/images/image_view.asp' and p.hostname=='arcdstorage.blob.core.windows.net' and p.path.lower()=='/countyfiles/gdytax/camadocuments/'+parse_qs(origin.query.lower()).get('guid',[''])[0]+'.jpg')
    if p.scheme!='https' or (p.hostname!=origin.hostname and not grady_cdn):
        raise SketchError(502,'Assessor sketch redirected outside its verified source.')
    mime=r.headers.get('content-type','').split(';')[0].lower()
    valid=(mime=='image/jpeg' and r.content.startswith(b'\xff\xd8\xff')) or (mime=='image/png' and r.content.startswith(b'\x89PNG\r\n\x1a\n'))
    if not valid or not 1000<len(r.content)<=8_000_000:
        raise SketchError(404,'The assessor has no usable published building sketch for this property.')
    return {'sketch_url':url,'image_data':'data:'+mime+';base64,'+base64.b64encode(r.content).decode()}


def result(county,account,address,record,sketches):
    if not sketches:raise SketchError(404,'No published building sketch was found in '+county+' County.')
    return {'status':'found','county':county,'account':account,'address':address,'record_url':record,
            'source':county+' County Assessor', 'sketches':sketches,**sketches[0]}


def require_unique(matches):
    if len(matches)!=1:
        raise SketchError(409 if matches else 404,'Multiple matching properties; enter a complete street address.' if matches else 'No exact assessor street-address match was found.')
    return matches[0]


async def oklahoma(client,address):
    r=await client.post(OK_BASE+'AddressSearch.asp',data={'FormattedLocation':street(address),'fpdbr_1_PagingMove':'  |<  '})
    r.raise_for_status(); soup=BeautifulSoup(r.text,'html.parser');matches=[]
    for row in soup.select('tr'):
        cells=row.find_all('td',recursive=False)
        if len(cells)!=4:continue
        a=cells[0].find('a',href=True)
        if a and re.fullmatch(r'AN-R\.asp\?PROPERTYID=\d+',a['href'],re.I) and street(cells[2].get_text(' ',strip=True))==street(address):
            matches.append((urljoin(OK_BASE,a['href']),a.get_text(strip=True),cells[2].get_text(' ',strip=True)))
    record,account,actual=require_unique(matches)
    r=await client.get(record);r.raise_for_status();soup=BeautifulSoup(r.text,'html.parser')
    # Verify the record itself, independent of the search-result row.
    location=None
    for cell in soup.select('td'):
        if cell.get_text(' ',strip=True)=='Location:':
            nxt=cell.find_next_sibling('td');location=nxt.get_text(' ',strip=True) if nxt else None;break
    if not location or street(location)!=street(address):raise SketchError(409,'Oklahoma County property record does not match the requested address.')
    urls=[]
    for a in soup.select('a[href]'):
        href=a['href']
        if re.fullmatch(r'ShowSketchdb\.asp\?Propertyid=\d+(?:&BuildingSequence=\d+)?',href,re.I):
            u=urljoin(OK_BASE,href)
            if u not in urls:urls.append(u)
    sketches=[await embed_image(client,u) for u in urls]
    return result('Oklahoma',account,actual,record,sketches)


def form_defaults(form):
    values={}
    for e in form.select('input[name],select[name],textarea[name]'):
        if e.name=='select':
            o=e.select_one('option[selected]') or e.select_one('option');values[e['name']]=o.get('value',o.text) if o else ''
        elif e.get('type','') not in ('submit','checkbox','radio'):
            values[e['name']]=e.get('value','')
    return values


async def grady(client,address):
    r=await client.get(GRADY_BASE+'county.asp?county=Grady&directlogin=True');r.raise_for_status()
    form=BeautifulSoup(r.text,'html.parser').select_one('#search_form')
    if not form:raise SketchError(503,'Grady County public search is unavailable.')
    term=street(address);parts=term.split();number=parts.pop(0);direction=parts.pop(0) if parts and parts[0] in ('N','S','E','W','NW','NE','SW','SE') else ''
    if parts and parts[-1] in ('ST','AVE','DR','RD','CT','LN','TER','PL','BLVD','CIR','PKWY','HWY'):parts.pop()
    search_name=' '.join(parts)
    if search_name.startswith('COUNTY RD '):search_name=search_name.replace('COUNTY RD ','COUNTY ROAD ',1)
    params=form_defaults(form);params.update(StreetNumber=number,StreetName=search_name,siteDirection=direction,search1='Search')
    r=await client.post(GRADY_BASE+'results.asp',data=params);r.raise_for_status();soup=BeautifulSoup(r.text,'html.parser');matches=[]
    for a in soup.select('a[href*="parcel.asp?item="]'):
        row=a.find_parent('tr');cells=row.find_all('td',recursive=False) if row else []
        if len(cells)<4:continue
        lines=[line.strip() for line in cells[3].get_text('\n',strip=True).splitlines() if line.strip()]
        actual=next((x for x in lines if re.match(r'^\d+\s+',x)), '')
        if street(actual)==term:
            url=urljoin(GRADY_BASE,a['href']);p=urlparse(url);qs=parse_qs(p.query)
            if p.hostname=='okcountydata.com' and p.path=='/parcel.asp' and qs.get('countycode')==['GRDOK']:
                matches.append((url,a.get_text(strip=True),actual))
    record,account,actual=require_unique(matches)
    r=await client.get(record);r.raise_for_status();soup=BeautifulSoup(r.text,'html.parser')
    prop_row=next((tr for tr in soup.select('tr') if tr.find('td') and tr.find('td').get_text(' ',strip=True)=='Property Address:'),None)
    if not prop_row or not any(street(x)==term for x in prop_row.get_text('\n',strip=True).splitlines()):
        raise SketchError(409,'Grady County record does not match the requested street address.')
    # Grady's published improvement table pairs photo (left) and sketch (right).
    # Read only the right sketch cell, never arbitrary record-page image links.
    urls=[]
    for table in soup.select('table.table-striped-yellow'):
        for tr in table.find_all('tr',recursive=False):
            cells=tr.find_all('td',recursive=False)
            if len(cells)!=2 or not all(c.get('colspan')=='2' for c in cells):continue
            for img in cells[1].select('img[src]'):
                u=urljoin(GRADY_BASE,img['src']);p=urlparse(u);q=parse_qs(p.query.lower())
                guid=q.get('guid',[''])[0]
                if p.hostname=='okcountydata.com' and p.path.lower()=='/images/image_view.asp' and q.get('countycode')==['grdok'] and re.fullmatch(r'[a-f0-9-]{36}',guid) and u not in urls:
                    urls.append(u)
    sketches=[await embed_image(client,u) for u in urls]
    return result('Grady',account,actual,record,sketches)


async def resolve_county(client,address):
    r=await client.get(GEOCODE,params={'SingleLine':address,'f':'json','outFields':'*','maxLocations':3});r.raise_for_status()
    candidates=r.json().get('candidates',[])
    good=[c for c in candidates if c.get('score',0)>=95 and c.get('attributes',{}).get('RegionAbbr')=='OK' and c.get('attributes',{}).get('Addr_type') in ('PointAddress','StreetAddress','Subaddress')]
    if not good:raise SketchError(404,'Address could not be confidently located in Oklahoma. Include street, city and ZIP code.')
    c=good[0];attrs=c['attributes'];county=attrs.get('Subregion','').removesuffix(' County')
    if county not in COVERAGE:raise SketchError(422,'Automatic sketches currently cover the Oklahoma City metro counties. This address is in '+(county or 'an unidentified')+' County.')
    # Use only routing/address normalization from geocoding, never its imagery or geometry.
    if not attrs.get('StAddr'):raise SketchError(502,'Address service did not return a street address.')
    return county,attrs['StAddr'],c['address']


async def lookup(address,county=None,client=None):
    if len(address.strip())<8 or len(address)>250:raise SketchError(400,'Enter a complete street address with city and ZIP.')
    if client is None:
        async with httpx.AsyncClient(timeout=25,follow_redirects=True,headers={'User-Agent':'RedClayPermitDesigner/1.3'}) as c:
            return await lookup(address,county,c)
    try:
        resolved,normalized,label=await resolve_county(client,address)
        if county and county.lower()!=resolved.lower():raise SketchError(409,'The address is in '+resolved+' County, not the selected county.')
        county=resolved
        if COVERAGE[county]['status']!='automatic':
            raise SketchError(503,county+' County building sketches require access to its current assessor provider. Automatic retrieval is not connected for this county. Upload the original assessor sketch to continue.')
        if county in ('Cleveland','Canadian'):
            value=await retrieve(normalized,client=client,county=county.lower())
        elif county=='Oklahoma':value=await oklahoma(client,normalized)
        else:value=await grady(client,normalized)
        value['matched_address']=label
        return value
    except SketchError:raise
    except (httpx.HTTPError,ValueError,TypeError,AttributeError,KeyError) as e:
        raise SketchError(502,'The county assessor service could not return the original building sketch. Please retry later.') from e
