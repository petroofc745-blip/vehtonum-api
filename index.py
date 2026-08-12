import os
import re
import time
from datetime import datetime, timedelta
from curl_cffi import requests as _reqs
from flask import Flask, request, jsonify

app = Flask(__name__)

# 10 Days Auto-Expire Configuration
EXPIRY_DATE = datetime.now() + timedelta(days=10)

HP = "https://vahan.parivahan.gov.in/vahanservice/vahan/ui/statevalidation/homepage.xhtml?statecd=Mzc2MzM2MzAzNjY0MzIzODM3NjIzNjY0MzY2MjM3NDQ0Yw=="
HB = "https://vahan.parivahan.gov.in/vahanservice/vahan/ui/statevalidation/homepage.xhtml"
LI = "https://vahan.parivahan.gov.in/vahanservice/vahan/ui/usermgmt/login.xhtml"
FR = "https://vahan.parivahan.gov.in/vahanservice/vahan/ui/balanceservice/form_reschedule_fitness.xhtml"
SMC_API_URL = "https://www.smcinsurance.com/central/centralcall/CallReqWithHeader"
TIMEOUT = 10

def build_session():
    # impersonate="chrome" spoofs real browser TLS fingerprint to bypass cloud blocks
    sess = _reqs.Session(impersonate="chrome")
    return sess

def _req(sess, url, data=None, headers=None, referer=None):
    hdrs = {}
    if headers: hdrs.update(headers)
    if referer: hdrs["Referer"] = referer
    if data is not None:
        resp = sess.post(url, data=data, headers=hdrs, timeout=TIMEOUT)
    else:
        resp = sess.get(url, headers=hdrs, timeout=TIMEOUT)
    return resp.text, dict(resp.headers)

def _extract_vs(html):
    m = re.search(r'<input[^>]*name="javax\.faces\.ViewState"[^>]*value="([^"]+)"', html)
    return m.group(1) if m else None

def _extract_vs_ajax(html):
    m = re.search(r'<update id="j_id1:javax\.faces\.ViewState:0"><!\[CDATA\[(.*?)\]\]></update>', html)
    return m.group(1) if m else None

def _fetch_vehicle_smc(reg_no):
    sess = _reqs.Session(impersonate="chrome")
    resp = sess.post(SMC_API_URL, json={"url": "GetVaahanDetailsByVehicleNo", "props": [reg_no, "", "0"]}, timeout=10)
    if resp.status_code != 200:
        raise Exception(f"SMC API HTTP {resp.status_code}")
    data = resp.json()
    if data.get("statusCode") == 200 and data.get("response"):
        return data["response"]
    raise Exception(f"SMC API failed: {data.get('statusMessage', 'unknown error')}")

def get_mobile(reg_no):
    start = time.time()
    result = {"success": False, "mobile_number": "", "chassis_number": "", "engine_number": "",
              "owner_name": "", "maker_model": "", "error": "", "response_time_seconds": 0}
    try:
        smc_data = _fetch_vehicle_smc(reg_no)
        chassis_full = smc_data.get("chassis", "").replace(" ", "")
        engine_no = smc_data.get("engine", "")
        chassis_no_last5 = chassis_full[-5:]
        
        result["chassis_number"] = chassis_full
        result["engine_number"] = engine_no
        result["owner_name"] = smc_data.get("ownerName")
        result["maker_model"] = f"{smc_data.get('maker')} {smc_data.get('model')}"

        sess = build_session()
        html, _ = _req(sess, HP)
        vs = _extract_vs(html)
        if not vs: raise Exception("No ViewState in homepage")
        
        cid = "j_idt193"
        ajax_h = {"Accept": "application/xml, text/xml, */*; q=0.01", "Content-Type": "application/x-www-form-urlencoded", "Faces-Request": "partial/ajax", "X-Requested-With": "XMLHttpRequest", "Origin": "https://vahan.parivahan.gov.in", "Referer": HP}
        
        form = {"javax.faces.partial.ajax": "true", "homepageformid": "homepageformid", "javax.faces.ViewState": vs, "javax.faces.source": "fit_c_office_to", "javax.faces.partial.execute": "fit_c_office_to", "javax.faces.behavior.event": "change", "javax.faces.partial.event": "change", "fit_c_office_to_input": "1"}
        html, _ = _req(sess, HB, data=form, headers=ajax_h)
        vs = _extract_vs_ajax(html) or vs

        form = {"javax.faces.partial.ajax": "true", "homepageformid": "homepageformid", "javax.faces.ViewState": vs, "javax.faces.source": cid, "javax.faces.partial.execute": cid, "javax.faces.partial.render": "proccedHomeButtonId", "javax.faces.behavior.event": "change", f"{cid}_input": "on"}
        html, _ = _req(sess, HB, data=form, headers=ajax_h)
        vs = _extract_vs_ajax(html) or vs

        form = {"javax.faces.partial.ajax": "true", "homepageformid": "homepageformid", "javax.faces.ViewState": vs, "javax.faces.source": "proccedHomeButtonId", "javax.faces.partial.execute": "@all", "proccedHomeButtonId": "proccedHomeButtonId", f"{cid}_input": "on"}
        html, _ = _req(sess, HB, data=form, headers=ajax_h)
        vs = _extract_vs_ajax(html) or vs

        dlg = "j_idt536"
        form = {"javax.faces.partial.ajax": "true", "homepageformid": "homepageformid", "javax.faces.ViewState": vs, "javax.faces.source": dlg, "javax.faces.partial.execute": "@all", dlg: dlg, f"{cid}_input": "on"}
        html, _ = _req(sess, HB, data=form, headers=ajax_h)
        vs = _extract_vs_ajax(html) or vs

        html, _ = _req(sess, LI + "?faces-redirect=true", referer=HP)
        vs = _extract_vs(html)
        
        html, _ = _req(sess, LI, data={"loginForm": "loginForm", "javax.faces.ViewState": vs, "fitbalcTest": "fitbalcTest", "pur_cd": "86"}, headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": "https://vahan.parivahan.gov.in"}, referer=LI + "?faces-redirect=true")
        html, _ = _req(sess, FR, referer=LI + "?faces-redirect=true")
        vs = _extract_vs(html)
        
        ajax_h["Referer"] = FR
        html, _ = _req(sess, FR, data={
            "javax.faces.partial.ajax": "true", "javax.faces.source": "balanceFeesFine:validate_dtls",
            "javax.faces.partial.execute": "@all", "javax.faces.partial.render": "balanceFeesFine:auth_panel",
            "balanceFeesFine:validate_dtls": "balanceFeesFine:validate_dtls", "balanceFeesFine": "balanceFeesFine",
            "balanceFeesFine:tf_reg_no": reg_no, "balanceFeesFine:tf_chasis_no": chassis_no_last5, "javax.faces.ViewState": vs
        }, headers=ajax_h)

        mobile = None
        for p in [r'id="balanceFeesFine:tf_mobile"[^>]*value="(\d{10})"', r'value="(\d{10})"[^>]*id="balanceFeesFine:tf_mobile"']:
            m = re.search(p, html)
            if m and re.match(r'^[6-9]', m.group(1)):
                mobile = m.group(1)
                break
        if not mobile:
            nums = re.findall(r'\b[6-9]\d{9}\b', html)
            if nums: mobile = nums[0]

        if mobile:
            result["success"] = True
            result["mobile_number"] = mobile
        else:
            result["error"] = "Mobile number not found"
    except Exception as e:
        result["error"] = str(e)
    
    result["response_time_seconds"] = round(time.time() - start, 2)
    return result

@app.after_request
def _add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

@app.route("/api/rc", methods=["GET"])
def _api_rc_get():
    if datetime.now() > EXPIRY_DATE:
        return jsonify({"success": False, "error": "API expired", "developed_by": "@endedfrr coder petro"}), 403

    api_key = request.args.get("key", "").strip()
    vehicle = request.args.get("demo-query", "").upper().strip()

    if api_key != "petro-vehtonum-key":
        return jsonify({"success": False, "error": "Invalid API key", "developed_by": "@endedfrr coder petro"}), 401

    if not vehicle:
        return jsonify({"success": False, "error": "Missing vehicle query", "developed_by": "@endedfrr coder petro"}), 400

    res = get_mobile(vehicle)
    res["developed_by"] = "@endedfrr coder petro"
    return jsonify(res), (200 if res.get("success") else 500)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
