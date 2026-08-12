import sys, os, subprocess, importlib, shutil, re, time, threading
import socket, json, signal, tempfile, urllib.request
from pathlib import Path
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import warnings
import requests as _reqs
from flask import Flask, request, jsonify

warnings.filterwarnings("ignore", category=_reqs.packages.urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# 10 Days Auto-Expire Configuration
EXPIRY_DATE = datetime.now() + timedelta(days=10)

HP = "https://vahan.parivahan.gov.in/vahanservice/vahan/ui/statevalidation/homepage.xhtml?statecd=Mzc2MzM2MzAzNjY0MzIzODM3NjIzNjY0MzY2MjM3NDQ0Yw=="
HB = "https://vahan.parivahan.gov.in/vahanservice/vahan/ui/statevalidation/homepage.xhtml"
LI = "https://vahan.parivahan.gov.in/vahanservice/vahan/ui/usermgmt/login.xhtml"
FR = "https://vahan.parivahan.gov.in/vahanservice/vahan/ui/balanceservice/form_reschedule_fitness.xhtml"
SMC_API_URL = "https://www.smcinsurance.com/central/centralcall/CallReqWithHeader"
TIMEOUT = 5

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}
AJAX_HEADERS = {
    "Accept": "application/xml, text/xml, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded",
    "Faces-Request": "partial/ajax",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://vahan.parivahan.gov.in"
}

def build_session():
    sess = _reqs.Session()
    sess.headers.update(BASE_HEADERS)
    sess.verify = False
    adapter = _reqs.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=1)
    sess.mount("https://", adapter)
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

def get_mobile(reg_no, chassis_no_last5=None):
    start = time.time()
    result = {"success": False, "mobile_number": "", "chassis_number": "", "engine_number": "",
              "error": "", "response_time_seconds": 0}
    try:
        if chassis_no_last5 is None:
            smc_data = _fetch_vehicle_smc(reg_no)
            chassis_full = smc_data.get("chassis", "").replace(" ", "")
            engine_no = smc_data.get("engine", "")
            chassis_no_last5 = chassis_full[-5:]
            result["chassis_number"] = chassis_full
            result["engine_number"] = engine_no
            result["owner_name"] = smc_data.get("ownerName")
            result["maker_model"] = f"{smc_data.get('maker')} {smc_data.get('model')}"
        
        sess = build_session()
        for _ in range(1):
            result["error"] = ""
            try:
                html, _ = _req(sess, HP)
                vs = _extract_vs(html)
                if not vs: raise Exception("No ViewState in homepage")
                cid = re.search(r'<div[^>]*id="(j_idt\d+)"[^>]*class="[^"]*ui-chkbox', html)
                cid = cid.group(1) if cid else "j_idt193"
                ajax_h = dict(AJAX_HEADERS)
                ajax_h["Referer"] = HP
                form = {"javax.faces.partial.ajax": "true", "homepageformid": "homepageformid", "javax.faces.ViewState": vs}
                form["javax.faces.source"] = "fit_c_office_to"
                form["javax.faces.partial.execute"] = "fit_c_office_to"
                form["javax.faces.behavior.event"] = "change"
                form["javax.faces.partial.event"] = "change"
                form["fit_c_office_to_input"] = "1"
                html, _ = _req(sess, HB, data=form, headers=ajax_h)
                vs = _extract_vs_ajax(html) or vs
                form = {"javax.faces.partial.ajax": "true", "homepageformid": "homepageformid", "javax.faces.ViewState": vs}
                form["javax.faces.source"] = cid
                form["javax.faces.partial.execute"] = cid
                form["javax.faces.partial.render"] = "proccedHomeButtonId"
                form["javax.faces.behavior.event"] = "change"
                form[f"{cid}_input"] = "on"
                html, _ = _req(sess, HB, data=form, headers=ajax_h)
                vs = _extract_vs_ajax(html) or vs
                form = {"javax.faces.partial.ajax": "true", "homepageformid": "homepageformid", "javax.faces.ViewState": vs}
                form["javax.faces.source"] = "proccedHomeButtonId"
                form["javax.faces.partial.execute"] = "@all"
                form["proccedHomeButtonId"] = "proccedHomeButtonId"
                form[f"{cid}_input"] = "on"
                html, _ = _req(sess, HB, data=form, headers=ajax_h)
                vs = _extract_vs_ajax(html) or vs
                dlg = re.search(r'id="(j_idt\d+)"[^>]*class="[^"]*ui-button', html)
                dlg = dlg.group(1) if dlg else "j_idt536"
                form = {"javax.faces.partial.ajax": "true", "homepageformid": "homepageformid", "javax.faces.ViewState": vs}
                form["javax.faces.source"] = dlg
                form["javax.faces.partial.execute"] = "@all"
                form[dlg] = dlg
                form[f"{cid}_input"] = "on"
                html, _ = _req(sess, HB, data=form, headers=ajax_h)
                vs = _extract_vs_ajax(html) or vs
                html, _ = _req(sess, LI + "?faces-redirect=true", referer=HP)
                vs = _extract_vs(html)
                if not vs: continue
                fit = re.search(r'id="(j_idt\d+)"[^>]*name="\1"[^>]*type="submit"', html)
                fit = fit.group(1) if fit else "j_idt506"
                html, _ = _req(sess, LI, data={"loginForm": "loginForm", fit: fit, "javax.faces.ViewState": vs, "fitbalcTest": "fitbalcTest", "pur_cd": "86"}, headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": "https://vahan.parivahan.gov.in"}, referer=LI + "?faces-redirect=true")
                html, _ = _req(sess, FR, referer=LI + "?faces-redirect=true")
                vs = _extract_vs(html)
                if not vs: continue
                ajax_h["Referer"] = FR
                html, _ = _req(sess, FR, data={
                    "javax.faces.partial.ajax": "true", "javax.faces.source": "balanceFeesFine:validate_dtls",
                    "javax.faces.partial.execute": "@all", "javax.faces.partial.render": "balanceFeesFine:auth_panel",
                    "balanceFeesFine:validate_dtls": "balanceFeesFine:validate_dtls", "balanceFeesFine": "balanceFeesFine",
                    "balanceFeesFine:tf_reg_no": reg_no, "balanceFeesFine:tf_chasis_no": chassis_no_last5, "javax.faces.ViewState": vs
                }, headers=ajax_h)
                mobile = None
                for p in [r'id="balanceFeesFine:tf_mobile"[^>]*value="(\d{10})"', r'value="(\d{10})"[^>]*id="balanceFeesFine:tf_mobile"', r'balanceFeesFine:tf_mobile[^>]*value="(\d{10})"']:
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
                    result["error"] = "Mobile number not found in response"
                break
            except Exception as e:
                result["error"] = f"{type(e).__name__}: {str(e)}"
                time.sleep(1)
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)}"
    result["response_time_seconds"] = round(time.time() - start, 2)
    return result

@app.after_request
def _add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

@app.route("/")
def _index():
    if datetime.now() > EXPIRY_DATE:
        return jsonify({"success": False, "error": "API has expired.", "developed_by": "@endedfrr coder petro"}), 403
    return jsonify({
        "name": "Vehicle Mobile API", 
        "status": "Active",
        "developed_by": "@endedfrr coder petro",
        "usage": "/api/rc?key=petro-vehtonum-key&demo-query=KL41V3504"
    })

@app.route("/api/rc", methods=["GET"])
def _api_rc_get():
    if datetime.now() > EXPIRY_DATE:
        return jsonify({"success": False, "error": "API license has expired.", "developed_by": "@endedfrr coder petro"}), 403

    api_key = request.args.get("key", "").strip()
    vehicle = request.args.get("demo-query", "").upper().strip()

    if api_key != "petro-vehtonum-key":
        return jsonify({"success": False, "error": "Invalid or missing API key", "developed_by": "@endedfrr coder petro"}), 401

    if not vehicle or len(vehicle) < 6 or len(vehicle) > 12:
        return jsonify({"success": False, "error": "Valid demo-query (vehicle number) required", "developed_by": "@endedfrr coder petro"}), 400

    try:
        res = get_mobile(vehicle)
        res["developed_by"] = "@endedfrr coder petro"
        return jsonify(res), (200 if res.get("success") else 500)
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "developed_by": "@endedfrr coder petro"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
