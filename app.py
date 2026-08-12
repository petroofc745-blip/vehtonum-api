from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def get_vehicle_info(vehicle: str = Query(..., description="Vehicle Number e.g. KL59U6037")):
    # --- API EXPIRY CONFIGURATION ---
    expiry_date_str = "2026-08-24"  # expiry date
    current_date = datetime.now().date()
    expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()

    # Expiry Check
    if current_date > expiry_date:
        return {
            "status": "error",
            "message": "API has expired. Please contact the developer @endedfrr.",
            "note": f"api expired on {expiry_date_str}"
        }

    clean_vehicle_no = vehicle.upper().strip()

    #source API URL
    target_api = f"https://vehicleaddress.suryajasoos.workers.dev/?vehicle={clean_vehicle_no}"

    try:
        # Source APi
        response = requests.get(target_api, timeout=10)
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch data from source API")
        
        data = response.json()

        # enter the data 
        data["owner"] = "@endedfrr"
        data["developer"] = "coder petro"
        data["note"] = f"api expire in {expiry_date_str}"

        return data

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

# Run 
