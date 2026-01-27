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
        
        # 1. Create Transaction on WayMB (with Smart Retry for MBWAY Phone formats)
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0'
        }

        r = None
        resp = {}
        
        # Define formats to try
        phones_to_try = []
        if method == 'mbway':
            raw_phone = str(payer.get('phone', '')).strip()
            # Clean non-chars just in case, but keep + if present
            clean = "".join(filter(lambda x: x.isdigit() or x == '+', raw_phone))
            digits = "".join(filter(str.isdigit, raw_phone))
            
            phones_to_try.append(clean) # As sent by frontend
            if len(digits) == 9: 
                phones_to_try.append(f"351{digits}")  # 351 prefix
                phones_to_try.append(f"+351{digits}") # +351 prefix
            
            # Remove duplicates preserving order
            phones_to_try = list(dict.fromkeys(phones_to_try))
        else:
            phones_to_try = [payer.get('phone', '')] # Multibanco doesn't care about phone usually

        # LOOP Attempts
        success_found = False
        
        for p in phones_to_try:
            print(f"[Backend] Attempting MBWAY with phone: {p}")
            waymb_payload['payer']['phone'] = p
            
            try:
                r = requests.post("https://api.waymb.com/transactions/create", json=waymb_payload, headers=headers, timeout=15)
                try:
                    resp = r.json()
                except:
                    resp = {"message": r.text}
                
                # Check Success
                if r.status_code == 200:
                    if resp.get('statusCode') == 200 or resp.get('success') == True or 'transaction' in resp or 'id' in resp:
                         success_found = True
                         print(f"[Backend] Success with phone: {p}")
                         break
            except Exception as e:
                print(f"[Backend] Request Error: {e}")
                resp = {"message": str(e)}

        print(f"[Backend] Final WayMB Response: {r.status_code if r else 'ERR'} - {resp}")

        if success_found:
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
        print(f"[Backend] Critical Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
