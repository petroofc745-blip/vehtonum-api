import warnings
from datetime import datetime, timedelta
import requests as _reqs
from flask import Flask, request, jsonify

warnings.filterwarnings("ignore", category=_reqs.packages.urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# 10 Days Auto-Expire Configuration (Adjusted from current deployment date)
EXPIRY_DATE = datetime.now() + timedelta(days=10)

SMC_API_URL = "https://www.smcinsurance.com/central/centralcall/CallReqWithHeader"
_smc_sess = None
_smc_primed = False

def _get_smc_sess():
    global _smc_sess, _smc_primed
    if _smc_sess is None:
        s = _reqs.Session()
        s.headers.update({"User-Agent": "okhttp/4.9.2"})
        s.verify = False
        adapter = _reqs.adapters.HTTPAdapter(pool_connections=5, pool_maxsize=10, max_retries=0)
        s.mount("https://", adapter)
        _smc_sess = s
    if not _smc_primed:
        try:
            _smc_sess.post(SMC_API_URL, json={"url": "GetVaahanDetailsByVehicleNo", "props": ["", "", "0"]}, timeout=5)
        except Exception:
            pass
        _smc_primed = True
    return _smc_sess

def _fetch_vehicle_smc(reg_no):
    sess = _get_smc_sess()
    resp = sess.post(SMC_API_URL, json={"url": "GetVaahanDetailsByVehicleNo", "props": [reg_no, "", "0"]}, timeout=10)
    if resp.status_code != 200:
        raise Exception(f"SMC API HTTP {resp.status_code}")
    data = resp.json()
    if data.get("statusCode") == 200 and data.get("response"):
        return data["response"]
    raise Exception(f"SMC API failed: {data.get('statusMessage', 'unknown error')}")

@app.after_request
def _add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

@app.route("/")
def _index():
    if datetime.now() > EXPIRY_DATE:
        return jsonify({
            "success": False, 
            "error": "API has expired.",
            "developed_by": "@endedfrr coder petro"
        }), 403
    return jsonify({
        "name": "Vehicle API", 
        "status": "Active",
        "developed_by": "@endedfrr coder petro",
        "usage": "/api/rc?key=petro-vehtonum-key&demo-query=KL41V3504"
    })

@app.route("/api/rc", methods=["GET"])
def _api_rc_get():
    # Auto-Expire Check
    if datetime.now() > EXPIRY_DATE:
        return jsonify({
            "success": False,
            "error": "API license has expired (10-day limit reached).",
            "developed_by": "@endedfrr coder petro"
        }), 403

    # Parameter Validation based on requested format: key & demo-query
    api_key = request.args.get("key", "").strip()
    vehicle = request.args.get("demo-query", "").upper().strip()

    if api_key != "petro-vehtonum-key":
        return jsonify({
            "success": False, 
            "error": "Invalid or missing API key",
            "developed_by": "@endedfrr coder petro"
        }), 401

    if not vehicle or len(vehicle) < 6 or len(vehicle) > 12:
        return jsonify({
            "success": False, 
            "error": "Valid demo-query (vehicle number) required",
            "developed_by": "@endedfrr coder petro"
        }), 400

    try:
        data = _fetch_vehicle_smc(vehicle)
        formatted_data = {
            "success": True,
            "developed_by": "@endedfrr coder petro",
            "registration_number": vehicle,
            "owner_name": data.get("ownerName"),
            "maker_model": f"{data.get('maker')} {data.get('model')}",
            "fuel_type": data.get("fuel"),
            "registration_date": data.get("regDate"),
            "fitness_upto": data.get("fitUpto"),
            "insurance_upto": data.get("insuranceUpto"),
            "chassis_number": data.get("chassis"),
            "engine_number": data.get("engine"),
            "rc_status": data.get("status")
        }
        return jsonify(formatted_data), 200
    except Exception as e:
        return jsonify({
            "success": False, 
            "error": str(e),
            "developed_by": "@endedfrr coder petro"
        }), 500
