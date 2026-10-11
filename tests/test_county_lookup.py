import unittest
import httpx
from county_lookup import lookup,oklahoma,SketchError
class CountyTests(unittest.IsolatedAsyncioTestCase):
 async def test_blocked_county_never_fetches_alternative_image(self):
  def handler(r):
   self.assertIn('GeocodeServer',str(r.url))
   return httpx.Response(200,json={'candidates':[{'score':100,'address':'Newcastle, OK','attributes':{'RegionAbbr':'OK','Addr_type':'PointAddress','Subregion':'McClain County','StAddr':'100 MAIN ST'}}]})
  async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
   with self.assertRaises(SketchError) as e:await lookup('100 Main St, Newcastle, OK',client=c)
   self.assertEqual(e.exception.status,503)
 async def test_oklahoma_only_explicit_sketch_and_exact_record(self):
  paths=[]
  def handler(r):
   paths.append(r.url.path)
   if r.method=='POST':return httpx.Response(200,text='<tr><td><a href="AN-R.asp?PROPERTYID=1">R1</a></td><td>Owner</td><td>845 NW 49TH ST</td><td>OKC</td></tr>')
   if r.url.path.endswith('AN-R.asp'):return httpx.Response(200,text='<table><tr><td>Location:</td><td>845 NW 49TH ST</td></tr></table><a href="ShowImageDB.asp?Propertyid=1">Photo</a><a href="ShowSketchdb.asp?Propertyid=1">Sketch</a>')
   return httpx.Response(200,headers={'Content-Type':'image/jpeg'},content=b'\xff\xd8\xff'+b'x'*1200)
  async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
   data=await oklahoma(c,'845 NW 49th St')
  self.assertEqual(data['county'],'Oklahoma');self.assertTrue(data['image_data'].startswith('data:image/jpeg;base64,'))
  self.assertFalse(any('ShowImageDB' in p for p in paths))
