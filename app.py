from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS allow cheyyan (Frontend-ilninnu fetch cheyyumpol error varathirikkan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def get_vehicle_info(vehicle: str = Query(..., description="Vehicle Number eg KL59U6037")):
    # --- API EXPIRY CONFIGURATION ---
    expiry_date_str = "2026-08-25"  # Ningalkku ishtamulla date kodukkam
    current_date = datetime.now().date()
    expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()

    # Expiry Check
    if current_date > expiry_date:
        return {
            "status": "error",
            "message": "API has expired. Please contact the developer.",
            "note": f"api expired on {expiry_date_str}"
        }

    # Ningal thanna exact JSON structure
    vehicle_data = {
        "asset_number": vehicle.upper(),
        "asset_type": "vehicle",
        "chassis_number": "MBLHAW090KHA*****",
        "engine_number": "HA10AGKHA*****",
        "fuel_type": "PETROL",
        "is_commercial": False,
        "make_model": "Hero Honda Splendor",
        "make_name": "Hero Honda",
        "make_name2": "HERO MOTOCORP LTD",
        "model_name": "Splendor",
        "model_name2": "SPLENDOR+ (SELF-DRUM-CAST)",
        "owner_name": "SANAL T",
        "permanent_address": "KAROTH, ARIL PO, PARAPPOL,PATTUVAM, Kannur-670143",
        "present_address": "KAROTH, ARIL PO, PARAPPOL,PATTUVAM, Kannur-670143",
        "previous_insurer": "new-india",
        "previous_policy_expired": False,
        "previous_policy_expiry_date": "31-Jul-2027",
        "registration_address": "THALIPARAMBA SRTO, Kerala",
        "registration_date": "03-Aug-2019",
        "registration_month": "8",
        "registration_year": "2019",
        "source": "VMS",
        "variant_id": [14190],
        "vehicle_color": "Grey Black",
        "vehicle_type": "TWO_WHEELER",
        "vehicle_type_processed": "2WN",
        "vehicle_type_v2": "TWO_WHEELER",
        "owner": "@endedfrr",
        "developer": "coder petro",
        "note": f"api expire in {expiry_date_str}"
    }

    return vehicle_data

# Run cheyyan: uvicorn filename:app --reload
