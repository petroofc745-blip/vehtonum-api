import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
SMC_API_URL = "https://www.smcinsurance.com/central/centralcall/CallReqWithHeader"

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
                    "owner_name": res.get("ownerName"),
                    "maker_model": f"{res.get('maker')} {res.get('model')}",
                    "fuel": res.get("fuel"),
                    "rc_status": res.get("rcStatus"),
                    "chassis": res.get("chassis"),
                    "engine": res.get("engine"),
                    "insurance_upto": res.get("insuranceUpto"),
                    "developed_by": "@endedfrr coder petro"
                }
        return {"success": False, "error": "Vehicle not found or API error"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.route("/api/details", methods=["GET"])
def details():
    vehicle = request.args.get("query", "").upper().strip()
    key = request.args.get("key", "").strip()
    
    if key != "petro-vehtonum-key":
        return jsonify({"error": "Invalid API Key", "developed_by": "@endedfrr coder petro"}), 401
    
    if not vehicle:
        return jsonify({"error": "Query required", "developed_by": "@endedfrr coder petro"}), 400
        
    result = get_vehicle_details(vehicle)
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
