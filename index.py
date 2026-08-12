import os
from flask import Flask, request, jsonify
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
SMC_API_URL = "https://www.smcinsurance.com/central/centralcall/CallReqWithHeader"

# API Expiry set to 10 days from now
EXPIRY_DATE = datetime.now() + timedelta(days=15)

def get_vehicle_details(reg_no):
    payload = {"url": "GetVaahanDetailsByVehicleNo", "props": [reg_no, "", "0"]}
    try:
        resp = requests.post(SMC_API_URL, json=payload, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("statusCode") == 200 and data.get("response"):
                res = data["response"]
                return {
                    "success": True,
                    "owner_name": res.get("owner"),
                    "father_name": res.get("ownerFatherName"),
                    "present_address": res.get("presentAddress"),
                    "permanent_address": res.get("permAddress"),
                    "pincode": res.get("pincode"),
                    "maker": res.get("manufacturer"),
                    "model": res.get("vehicle"),
                    "variant": res.get("variant"),
                    "fuel": res.get("fuelType"),
                    "chassis": res.get("chassis"),
                    "engine": res.get("engine"),
                    "reg_date": res.get("regDate"),
                    "insurance_company": res.get("insuranceCompanyName"),
                    "insurance_upto": res.get("insuranceUpto"),
                    "insurance_expired": res.get("insuranceExpired"),
                    "pucc_valid_upto": res.get("puccValidUpto"),
                    "financer": res.get("financerName"),
                    "rto_name": res.get("rtoData", {}).get("rtoName"),
                    "developed_by": "@endedfrr",
                    "api_expiry_date": EXPIRY_DATE.strftime("%d-%m-%Y")
                }
        return {"success": False, "error": "Vehicle not found or API error"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.route("/api/details", methods=["GET"])
def details():
    # Check if API expired
    if datetime.now() > EXPIRY_DATE:
        return jsonify({
            "success": False, 
            "error": "API Key Expired", 
            "developed_by": "@endedfrr",
            "expiry_date": EXPIRY_DATE.strftime("%d-%m-%Y")
        }), 403

    vehicle = request.args.get("query", "").upper().strip()
    key = request.args.get("key", "").strip()
    
    if key != "petro-vehtonum-key":
        return jsonify({"error": "Invalid API Key", "developed_by": "@endedfrr"}), 401
    
    if not vehicle:
        return jsonify({"error": "Query required", "developed_by": "@endedfrr"}), 400
        
    result = get_vehicle_details(vehicle)
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
