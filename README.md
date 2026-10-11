# Red Clay Permit Designer

FastAPI app deployed on Render from the GitHub `main` branch.

## Run

```sh
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Automatic dimensioned building sketches

`GET /api/property?address=420%20SW%202nd%20St,%20Moore,%20OK%2073160`

The Cleveland County adapter initializes the public Spatialest session and CSRF token, submits an address-category search to `api/v2/search`, verifies the record's `FormattedLocation` through `api/v1/recordcard/{account}`, and reads the county's published image list from `https://api.spatialest.com/v1/ok/cleveland/images-api/{imageid}`. Only the image CDN's `cleveland-images/.../Sketch/` resources are accepted. Photos, aerial images, and parcel polygons are never substituted.

The original image is validated and embedded into the drawing canvas, saved projects, printed output, and exported SVG. Multiple published sketches appear in a selector. New lookups clear previous property images and annotations. Calibrate from a printed wall dimension before adding a carport.

Test address: **420 SW 2nd St, Moore, OK 73160** resolves to **account 4889**, with published sketch `Sketch/4889_1.jpg`.

`/api/assessor-sketch` also accepts an `address` or numeric `account`. Optional GIS parcel lookup remains available separately at `/api/parcel`; it is not used for sketch retrieval or superimposed on the building sketch.

## Validation

```sh
python -m unittest discover -s tests -v
python -m py_compile main.py assessor.py county_lookup.py
```

## Scope

Automatic sketches cover Cleveland, Oklahoma, Canadian and Grady counties, routed by the geocoded county rather than a city guess. McClain and Logan currently require manual upload of the original assessor sketch because their current provider blocks automated access; no parcel or aerial fallback is used. Missing and ambiguous assessor records return explicit errors. An assessor building sketch is a building-dimension reference, not a surveyed site plan or recorded plat. Dimensions remain the assessor's original raster labels. County service outages or missing/ambiguous records return explicit errors instead of unrelated imagery. Projects save in browser localStorage.

Verified county samples: 420 SW 2nd St, Moore (Cleveland); 845 NW 49th St, Oklahoma City (Oklahoma); 12216 SW 15th Terrace, Yukon (Canadian); 1867 County Road 1250, Tuttle (Grady). `/api/coverage` reports county availability. Cities crossing county lines are routed per address; an address without a published sketch cannot return one.
