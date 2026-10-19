from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/property")
async def get_property(address: str):
    addr_lower = address.lower()
    
    # Regional default profiles based on municipality rules
    if "norman" in addr_lower:
        # Norman R-1 zoning standards
        return {"width": 24, "depth": 24, "setback_side": 5, "setback_rear": 10, "city": "Norman"}
    elif "moore" in addr_lower:
        # Moore residential standards
        return {"width": 20, "depth": 20, "setback_side": 5, "setback_rear": 10, "city": "Moore"}
    elif "yukon" in addr_lower:
        # Yukon residential standards
        return {"width": 22, "depth": 22, "setback_side": 5, "setback_rear": 15, "city": "Yukon"}
    else:
        # Default Oklahoma City (OKC) profile
        return {"width": 20, "depth": 20, "setback_side": 5, "setback_rear": 10, "city": "Oklahoma City"}
