"""Vector-quality two-page conceptual permit sheets. No invented survey or engineering certification."""
from io import BytesIO
from html import escape
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

router = APIRouter()

class Plan(BaseModel):
    address: str = Field(min_length=8, max_length=240)
    structure: str = Field(pattern="^(carport|patio_cover)$")
    attachment: str = Field(pattern="^(attached|freestanding)$")
    width_ft: float = Field(gt=0, le=150)
    projection_ft: float = Field(gt=0, le=150)
    roof_pitch: str = "2:12"
    jurisdiction: str = "UNVERIFIED — confirm authority"
    source_reference: str = "NOT PROVIDED"
    setback_front_ft: float | None = None
    setback_rear_ft: float | None = None
    setback_left_ft: float | None = None
    setback_right_ft: float | None = None
    structural_reference: str = "ENGINEERING NOT PROVIDED"

def sheet(p: Plan, page: int) -> str:
    def t(x,y,s,size=11,weight="normal"):
        return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" font-family="Arial,sans-serif">{escape(str(s))}</text>'
    def line(x1,y1,x2,y2):
        return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#18232e" stroke-width="1.5"/>'
    a=['<svg xmlns="http://www.w3.org/2000/svg" width="816" height="1056" viewBox="0 0 816 1056">','<rect width="816" height="1056" fill="white"/>','<rect x="24" y="24" width="768" height="1008" fill="none" stroke="#18232e" stroke-width="2"/>']
    a += [t(40,54,"RED CLAY CARPORT AND PATIO LLC",20,"bold"),t(40,77,"RESIDENTIAL PERMIT PLAN — CONCEPT / REVIEW REQUIRED",12),line(24,91,792,91),t(40,115,p.address,13,"bold"),t(40,136,f'{p.attachment.upper()} {p.structure.replace("_"," ").upper()} — {p.width_ft:g} FT x {p.projection_ft:g} FT',12),line(24,151,792,151)]
    if page==1:
        a += [t(40,185,"SHEET 1 — SITE PLAN / PROPERTY INFORMATION",16,"bold"),'<rect x="55" y="215" width="706" height="530" fill="#f7f9fb" stroke="#9ba4ac" stroke-dasharray="8 5"/>',t(90,260,"SITE / ASSESSOR IMAGE: INSERT VERIFIED SOURCE",17,"bold"),t(90,291,"Do not infer parcel boundaries from building sketches."),t(90,319,"Place surveyed/recorded boundary data and measured carport footprint here."),t(90,365,"PROPOSED FOOTPRINT",14,"bold"),'<rect x="170" y="390" width="290" height="210" fill="#e7eef3" stroke="#17222e" stroke-width="3"/>',t(210,485,f'{p.width_ft:g} FT x {p.projection_ft:g} FT',18,"bold")]
        a += [t(55,785,"SETBACKS — MEASURED FROM VERIFIED PROPERTY LINES",13,"bold")]
        for i,(name,v) in enumerate([("Front",p.setback_front_ft),("Rear",p.setback_rear_ft),("Left",p.setback_left_ft),("Right",p.setback_right_ft)]):
            a.append(t(60+(i%2)*350,815+(i//2)*32,f'{name}: {str(v)+" ft" if v is not None else "NOT VERIFIED"}'))
        a += [t(55,907,"Source: "+p.source_reference[:90]),t(55,929,"Jurisdiction: "+p.jurisdiction[:80])]
    else:
        a += [t(40,185,"SHEET 2 — STRUCTURAL LAYOUT / ELEVATIONS",16,"bold"),t(55,218,"ROOF FRAMING SCHEMATIC — MEMBER DESIGN PENDING",12,"bold"),'<rect x="90" y="250" width="320" height="285" fill="#eef3f7" stroke="#18232e" stroke-width="3"/>']
        for x in (96,404):
            for y in (256,529):
                a.append(f'<rect x="{x-5}" y="{y-5}" width="10" height="10" fill="white" stroke="#18232e" stroke-width="2"/>')
        for y in range(285,520,36):a.append(line(90,y,410,y))
        a += [t(150,556,f'WIDTH: {p.width_ft:g} FT'),t(430,385,f'PROJECTION: {p.projection_ft:g} FT'),t(55,615,"ELEVATION — SCHEMATIC ONLY",13,"bold"),line(100,795,690,795),line(130,665,130,795),line(610,700,610,795),line(130,665,610,700),t(145,650,"ROOF SLOPE: "+p.roof_pitch),t(55,844,"STRUCTURAL REFERENCE: "+p.structural_reference[:90]),t(55,874,"Posts, beams, footings, anchors and ledger connections require verified design."),t(55,898,"Wind/snow loads, uplift, soil conditions and adopted local code must be checked.")]
    a += [line(24,962,792,962),t(40,984,"NOT FOR CONSTRUCTION OR PERMIT SUBMISSION UNTIL VERIFIED",12,"bold"),t(40,1010,f'PAGE {page} OF 2  |  VECTOR PRINT MASTER  |  8.5 x 11 IN')]
    return ''.join(a)+'</svg>'

@router.post("/api/permit-sheets")
def permit_sheets(p: Plan):
    return {"page1_svg":sheet(p,1),"page2_svg":sheet(p,2),"verified":False,"missing":["verified site plan / boundaries","structural design and jurisdictional requirements"],"status":"DRAFT — NOT READY FOR SUBMISSION"}
