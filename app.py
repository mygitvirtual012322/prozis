from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os
import json

app = Flask(__name__, static_folder='.')
CORS(app)

# Credentials (Managed via Env Vars for Security, defaults provided for dev)
CLIENT_ID = os.environ.get("WAYMB_CLIENT_ID", "modderstore_c18577a3")
CLIENT_SECRET = os.environ.get("WAYMB_CLIENT_SECRET", "850304b9-8f36-4b3d-880f-36ed75514cc7")
ACCOUNT_EMAIL = os.environ.get("WAYMB_ACCOUNT_EMAIL", "modderstore@gmail.com")
# Pushcut URL
PUSHCUT_URL = "https://api.pushcut.io/XPTr5Kloj05Rr37Saz0D1/notifications/Pendente%20delivery"

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)

@app.route('/api/payment', methods=['POST'])
def create_payment():
    data = request.json
    try:
        # --- PRE-PROCESS PAYLOAD ---
        payer = data.get("payer", {})
        method = data.get("method")
        amount = data.get("amount", 9.00)

        # force float with 2 decimal places
        try:
            amount = round(float(amount), 2)
        except:
            amount = 9.00

        # Special handling for MB WAY phone in payer
        if method == "mbway" and "phone" in payer:
            # Clean non-digits and ensure 9 digits
            phone = str(payer["phone"]).replace(" ", "").replace("+351", "")
            phone = "".join(filter(str.isdigit, phone))
            if len(phone) > 9: phone = phone[-9:]
            payer["phone"] = phone

        # Construct Secure Payload for WayMB
        waymb_payload = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "account_email": ACCOUNT_EMAIL,
            "amount": amount,
            "method": method,
            "currency": "EUR",
            "payer": payer
        }
        
        # 1. Create Transaction on WayMB (Standard Format Verified by User)
        # Payload must match JS success: amount as number (int 9), phone as 9 digits string
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/plain, */*',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'pt-PT,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Referer': 'https://worten.pt/'
        }
        
        # Log payload format check
        print(f"[Backend] Payload: {json.dumps(waymb_payload)}")

        try:
            # Increase timeout just in case
            r = requests.post("https://api.waymb.com/transactions/create", json=waymb_payload, headers=headers, timeout=30)
            try:
                resp = r.json()
            except:
                resp = {"message": r.text}
            
            print(f"[Backend] WayMB Response: {r.status_code} - {resp}")

            # Check Success
            is_success = False
            if r.status_code == 200:
                if resp.get('statusCode') == 200 or resp.get('success') == True or 'transaction' in resp or 'id' in resp:
                        is_success = True

            if is_success:
                # 2. Trigger Pushcut on Success
                method_name = str(method).upper()
                amt = str(amount)
                push_body = {
                    "text": f"Novo pedido gerado: {amt}€ ({method_name})",
                    "title": "Worten Venda"
                }
                try:
                    p_res = requests.post(PUSHCUT_URL, json=push_body, timeout=5)
                    print(f"[Backend] Pushcut Response: {p_res.status_code} - {p_res.text}")
                except Exception as e:
                    print(f"[Backend] Pushcut error: {e}")

                return jsonify({"success": True, "data": resp})
            else:
                return jsonify({"success": False, "error": resp.get("message", "Payment Gateway Error"), "details": resp}), 400

        except Exception as e:
            print(f"[Backend] Request Error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    except Exception as e:
        print(f"[Backend] Critical Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/status', methods=['POST'])
def check_status():
    data = request.json
    tx_id = data.get("id")
    try:
        r = requests.post("https://api.waymb.com/transactions/info", json={"id": tx_id}, timeout=10)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/notify', methods=['POST'])
def send_notification():
    data = request.json
    type = data.get("type", "Pendente delivery")
    text = data.get("text", "Novo pedido")
    title = data.get("title", "Worten")
    
    url = f"https://api.pushcut.io/XPTr5Kloj05Rr37Saz0D1/notifications/{type.replace(' ', '%20')}"
    
    try:
        p_res = requests.post(url, json={"text": text, "title": title}, timeout=5)
        print(f"[Backend] Generic Pushcut ({type}) Response: {p_res.status_code}")
        return jsonify({"success": True})
    except Exception as e:
        print(f"[Backend] Generic Pushcut error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
