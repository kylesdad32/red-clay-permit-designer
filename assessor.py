"""Cleveland County Spatialest address -> record -> published Sketch images."""
import base64
import re
from urllib.parse import urlparse
import httpx

BASE = 'https://property.spatialest.com/ok/cleveland/'
IMAGES = 'https://api.spatialest.com/v1/ok/cleveland/images-api/'

class SketchError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message
        super().__init__(message)


def street(address):
    value = address.split(',')[0].upper().strip()
    value = re.sub(r'\b(?:STREET|STR)\b', 'ST', value)
    for full, short in [('AVENUE','AVE'),('DRIVE','DR'),('ROAD','RD'),('COURT','CT'),('LANE','LN'),('TERRACE','TER'),('PLACE','PL')]:
        value = re.sub(r'\b'+full+r'\b', short, value)
    return re.sub(r'[^A-Z0-9 ]', '', re.sub(r'\s+', ' ', value)).strip()


def is_sketch(url):
    p = urlparse(url)
    return (p.scheme == 'https' and p.netloc == 'image-cdn.spatialest.com'
            and re.fullmatch(r'/image/cleveland-images/(?:med|sml|lrg)/Sketch/[A-Za-z0-9_-]+\.(?:jpg|jpeg|png)', p.path) is not None)


async def retrieve(address=None, account=None, client=None):
    if client is None:
        async with httpx.AsyncClient(timeout=25, follow_redirects=True,
                headers={'User-Agent':'RedClayPermitDesigner/1.2'}) as c:
            return await retrieve(address, account, c)
    try:
        shell = await client.get(BASE)
        shell.raise_for_status()
        token = re.search(r'name="csrf-token" content="([^"]+)"', shell.text)
        if not token:
            raise SketchError(502, 'Assessor session could not be initialized. Try again later.')
        headers = {'X-CSRF-TOKEN':token.group(1), 'X-Requested-With':'XMLHttpRequest',
                   'Accept':'application/json', 'Referer':BASE}
        if address:
            term = street(address)
            if not re.match(r'^\d+\s+\S', term):
                raise SketchError(400, 'Enter a complete street address.')
            result = await client.post(BASE+'api/v2/search', headers=headers,
                data={'filters[term]':term,'filters[category]':'address','page':'1','limit':'21'})
            result.raise_for_status()
            search = result.json()
            account = search.get('id')
            if not account:
                # Never choose a fuzzy/multiple match silently.
                raise SketchError(409 if search.get('results') else 404,
                    'No unique assessor address match. Include the street number and complete street name.')
        if not re.fullmatch(r'\d{1,12}', str(account or '')):
            raise SketchError(400, 'A numeric assessor account or street address is required.')
        record = await client.get(BASE+'api/v1/recordcard/'+str(account), headers=headers)
        record.raise_for_status()
        data = record.json()
        header = data.get('parcel',{}).get('header',{})
        actual = header.get('FormattedLocation','')
        if address and street(actual) != street(address):
            raise SketchError(409, 'Assessor result does not exactly match the requested street address.')
        image_id = str(data.get('imageid') or account)
        if not re.fullmatch(r'\d{1,12}',image_id):
            raise SketchError(502, 'Invalid assessor image identifier.')
        listing = await client.get(IMAGES+image_id)
        listing.raise_for_status()
        urls = listing.json()
        if not isinstance(urls,list):
            raise SketchError(502, 'Assessor image list format changed.')
        sketches = []
        for url in urls:
            if not isinstance(url,str) or not is_sketch(url):
                continue
            image = await client.get(url)
            image.raise_for_status()
            mime = image.headers.get('content-type','').split(';')[0].lower()
            if mime not in ('image/jpeg','image/png') or len(image.content)>8_000_000:
                raise SketchError(502, 'Assessor sketch returned an invalid image.')
            if not (image.content.startswith(b'\xff\xd8\xff') or image.content.startswith(b'\x89PNG\r\n\x1a\n')):
                raise SketchError(502, 'Assessor sketch returned an invalid image.')
            sketches.append({'sketch_url':url,'image_data':'data:'+mime+';base64,'+base64.b64encode(image.content).decode()})
        if not sketches:
            raise SketchError(404, 'The assessor has no published building sketch for this address.')
        return {'status':'found','account':str(account),'address':actual,
            'record_url':BASE+'#/property/'+str(account),
            'source':'Cleveland County Assessor / Spatialest',
            'sketch_url':sketches[0]['sketch_url'],'image_data':sketches[0]['image_data'],
            'sketches':sketches}
    except SketchError:
        raise
    except (httpx.HTTPError, ValueError, TypeError, AttributeError) as e:
        raise SketchError(502, 'Assessor service could not return the building sketch. Please retry later.') from e
