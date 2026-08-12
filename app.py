import os
from flask import Flask, request, jsonify
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
SMC_API_URL = "https://www.smcinsurance.com/central/centralcall/CallReqWithHeader"

EXPIRY_DATE = datetime.now() + timedelta(days=10)

def get_vehicle_details(reg_no):
    payload = {"url": "GetVaahanDetailsByVehicleNo", "props": [reg_no, "", "0"]}
    try:
        resp = requests.post(SMC_API_URL, json=payload, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("statusCode") == 200 and data.get("response"):
                res = data["response"]
                
                # Mapping to match your exact requested format
                return {
                    "success": True,
                    "asset_number": reg_no,
                    "asset_type": "vehicle",
                    "chassis_number": res.get("chassis"),
                    "engine_number": res.get("engine"),
                    "fuel_type": res.get("fuelType"),
                    "is_commercial": False,
                    "make_model": f"{res.get('manufacturer')} {res.get('vehicle')}",
                    "make_name": res.get("manufacturer"),
                    "make_name2": res.get("manufacturer"),
                    "model_name": res.get("vehicle"),
                    "model_name2": res.get("variant"),
                    "permanent_address": res.get("permAddress"),
                    "present_address": res.get("presentAddress"),
                    "previous_insurer": res.get("insuranceCompanyName"),
                    "previous_policy_expired": res.get("insuranceExpired"),
                    "previous_policy_expiry_date": res.get("insuranceUpto"),
                    "registration_address": res.get("rtoData", {}).get("rtoName"),
                    "registration_date": res.get("regDate"),
                    "vehicle_color": res.get("color"),
                    "vehicle_type": res.get("vehicleCategory"),
                    "developed_by": "@endedfrr",
                    "api_expiry_date": EXPIRY_DATE.strftime("%d-%m-%Y")
                }
        return {"success": False, "error": "Vehicle not found or API error"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "Active",
        "endpoint": "/api/details?key=petro-vehinfo-key&query=REG_NO",
        "developed_by": "@endedfrr",
        "expiry_date": EXPIRY_DATE.strftime("%d-%m-%Y")
    })

@app.route("/api/details", methods=["GET"])
def details():
    if datetime.now() > EXPIRY_DATE:
        return jsonify({
            "success": False, 
            "error": "API Key Expired", 
            "developed_by": "@endedfrr",
            "expiry_date": EXPIRY_DATE.strftime("%d-%m-%Y")
        }), 403

    vehicle = request.args.get("query", "").upper().strip()
    key = request.args.get("key", "").strip()
    
    if key != "petro-vehinfo-key":
        return jsonify({"error": "Invalid API Key", "developed_by": "@endedfrr"}), 401
    
    if not vehicle:
        return jsonify({"error": "Query required", "developed_by": "@endedfrr"}), 400
        
    result = get_vehicle_details(vehicle)
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
