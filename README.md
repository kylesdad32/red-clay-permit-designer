# Red Clay Permit Designer — deployable starter

## Run locally

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000. To deploy, use any Python web host supporting FastAPI/uvicorn. No ArcGIS API key is required for the public endpoints used here, but upstream services can change or throttle requests.

## What works

- Server-side address geocoding and two public Cleveland County/Moore parcel dataset fallbacks.
- Visible parcel polygon when a parcel is returned, plus a clear source label.
- Point-to-point drawing, post markers, two-point dimension calibration, image overlay, local save/load, SVG export and browser PDF printing.
- Unaltered original user-provided logo embedded as an image.

## Not implemented / limitations

- **Automatic original recorded plat retrieval**: Cleveland County Clerk's public search is an interactive record-search website; no documented public machine-readable document API was confirmed. The application never claims that GIS polygons are recorded plats.
- No cadastral survey-grade positioning, authoritative setbacks, verified structural engineering, or guaranteed permit acceptance.
- No persistent cloud account/database; projects save in browser localStorage, not across devices.
- GIS lookup currently targets Cleveland County/Moore; other city selections do not imply other county integrations.
- The dimension calibration is based on screen points, not authoritative ground coordinates; drawing width/depth fields are project notes, not constraints on the outline.

## Next production steps

Obtain county-clerk access/license for recorded document retrieval, implement county-specific document adapters, verify legal descriptions and document matches, add authenticated project storage and a true CAD-like constrained editor, then complete jurisdiction-specific compliance verification.
