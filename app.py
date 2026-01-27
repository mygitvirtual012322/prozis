from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os

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
        amount = data.get("amount")

        # Revert to simple Proxy behavior (User reported localhost JS worked)
        # Ensure amount is a number (float), not string, not int if possible
        try:
             amount = float(amount)
        except:
             pass

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
        # Payload must match JS success: amount as number, phone as 9 digits string
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0'
        }

        # Ensure phone is clean 9 digits string (if that's what user sends)
        if method == 'mbway' and payer.get('phone'):
             payer['phone'] = str(payer['phone']).strip()

        print(f"[Backend] Payload: {waymb_payload}") # Log full payload for verification

        try:
            r = requests.post("https://api.waymb.com/transactions/create", json=waymb_payload, headers=headers, timeout=15)
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
                    requests.post(PUSHCUT_URL, json=push_body, timeout=5)
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
