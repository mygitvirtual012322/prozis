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
        # Construct Secure Payload for WayMB
        waymb_payload = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "account_email": ACCOUNT_EMAIL,
            "amount": data.get("amount"),
            "method": data.get("method"),
            "currency": "EUR",
            "payer": data.get("payer")
        }
        
        # 1. Create Transaction on WayMB
        print(f"[Backend] Creating WayMB Transaction: {waymb_payload.get('payer')}") # Log only safe info
        r = requests.post("https://api.waymb.com/transactions/create", json=waymb_payload, timeout=10)
        
        try:
            resp = r.json()
        except:
            resp = {"message": r.text}

        print(f"[Backend] WayMB Response: {r.status_code} - {resp}")

        # Check Success (WayMB sometimes returns 200 but logic failure, or statusCode nested)
        is_success = False
        if r.status_code == 200:
             if resp.get('statusCode') == 200 or resp.get('success') == True:
                 is_success = True
             # Some APIs return transaction object directly on success
             if 'transaction' in resp or 'id' in resp: 
                 is_success = True

        if is_success:
            # 2. Trigger Pushcut on Success (Server-to-Server)
            method_name = data.get("method", "UNK").upper()
            amt = data.get("amount", "0")
            push_body = {
                "text": f"Novo pedido gerado: {amt}€ ({method_name})",
                "title": "Worten Venda"
            }
            try:
                requests.post(PUSHCUT_URL, json=push_body, timeout=5)
                print("[Backend] Pushcut fired successfully.")
            except Exception as e:
                print(f"[Backend] Pushcut error: {e}")

            return jsonify({"success": True, "data": resp})
        else:
            # Pass original error to frontend
            return jsonify({"success": False, "error": resp.get("message", "Erro ao comunicar com Gateway de Pagamento"), "details": resp}), 400

    except Exception as e:
        print(f"[Backend] Critical Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
