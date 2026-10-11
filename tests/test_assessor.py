import asyncio
import json
import unittest
import httpx
from assessor import retrieve, SketchError, is_sketch, street

SKETCH='https://image-cdn.spatialest.com/image/cleveland-images/med/Sketch/4889_1.jpg?v=260520'
PHOTO='https://image-cdn.spatialest.com/image/cleveland-images/med/Images/4889_1_1.jpg?v=260520'

class RetrievalTests(unittest.TestCase):
    def run_lookup(self, mode='ok'):
        calls=[]
        def handler(request):
            calls.append(str(request.url))
            path=request.url.path
            if path.endswith('/cleveland/'):
                return httpx.Response(200,text='<meta name="csrf-token" content="test">',headers={'set-cookie':'session=test'})
            if path.endswith('/search'):
                self.assertEqual(request.method,'POST')
                self.assertIn(b'filters%5Bcategory%5D=address',request.content)
                self.assertIn(b'420+SW+2ND+ST',request.content)
                self.assertEqual(request.headers['x-csrf-token'],'test')
                return httpx.Response(200,json={} if mode=='missing' else {'id':4889})
            if '/recordcard/' in path:
                return httpx.Response(200,json={'imageid':'4889','parcel':{'header':{'FormattedLocation':'422 SW 2ND ST' if mode=='wrong' else '420 SW 2ND ST'}}})
            if '/images-api/' in path:
                return httpx.Response(200,json=[PHOTO] if mode=='photo-only' else [PHOTO,SKETCH])
            if '/Sketch/' in path:
                return httpx.Response(200,content=b'<html>error</html>' if mode=='bad-image' else b'\xff\xd8\xffvalid',headers={'content-type':'image/jpeg'})
            raise AssertionError('Unexpected request '+str(request.url))
        async def run():
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                return await retrieve('420 SW 2nd St, Moore, OK 73160',client=client)
        return asyncio.run(run()),calls
    def test_original_sketch_only_and_embedded(self):
        result,calls=self.run_lookup()
        self.assertEqual(result['account'],'4889')
        self.assertEqual(result['sketch_url'],SKETCH)
        self.assertTrue(result['image_data'].startswith('data:image/jpeg;base64,'))
        self.assertNotIn(PHOTO,calls)
    def test_failures_never_substitute_photo(self):
        for mode,status in [('missing',404),('wrong',409),('photo-only',404),('bad-image',502)]:
            with self.subTest(mode=mode),self.assertRaises(SketchError) as caught:
                self.run_lookup(mode)
            self.assertEqual(caught.exception.status,status)
    def test_asset_allowlist(self):
        self.assertTrue(is_sketch(SKETCH))
        for value in [PHOTO,SKETCH.replace('image-cdn.spatialest.com','evil.example'),SKETCH.replace('/Sketch/','/Aerial/'),'http://localhost/private']:
            self.assertFalse(is_sketch(value))
    def test_address_normalization(self):
        self.assertEqual(street('420 sw 2nd Street, Moore, OK 73160'),'420 SW 2ND ST')

if __name__=='__main__':unittest.main()
