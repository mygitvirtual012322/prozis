from flask import Flask, request, jsonify, send_from_directory, render_template_string, session, redirect, url_for
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from models import db, User, Visitor, PageMetric, Order
import requests
import os
import json
import sys
import datetime
import uuid

app = Flask(__name__, static_folder='.')
app.secret_key = os.environ.get("SECRET_KEY", "super_secret_key_123") # Change in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)
db.init_app(app)

# Credentials
CLIENT_ID = os.environ.get("WAYMB_CLIENT_ID", "modderstore_c18577a3")
CLIENT_SECRET = os.environ.get("WAYMB_CLIENT_SECRET", "850304b9-8f36-4b3d-880f-36ed75514cc7")
ACCOUNT_EMAIL = os.environ.get("WAYMB_ACCOUNT_EMAIL", "modderstore@gmail.com")
PUSHCUT_URL = "https://api.pushcut.io/XPTr5Kloj05Rr37Saz0D1/notifications/Pendente%20delivery"

# Initialize DB
with app.app_context():
    db.create_all()
    # Create default admin if not exists
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', password='adminpassword') # Default password
        db.session.add(admin)
        db.session.commit()
        print("[INIT] Default Admin created: admin / adminpassword")

def log(msg):
    print(f"[BACKEND] {msg}")
    sys.stdout.flush()

def get_location_data(ip):
    try:
        # Don't track local dev
        if ip in ['127.0.0.1', 'localhost']: return "Localhost", "Local"
        r = requests.get(f"http://ip-api.com/json/{ip}", timeout=3)
        data = r.json()
        if data.get('status') == 'success':
            return data.get('city', 'Unknown'), data.get('country', 'Unknown')
    except:
        pass
    return "Unknown", "Unknown"

# --- Tracking API ---

@app.route('/api/track/init', methods=['POST'])
def track_init():
    try:
        data = request.json
        sid = data.get('session_id')
        path = data.get('path')
        ip = request.remote_addr
        
        visitor = Visitor.query.filter_by(session_id=sid).first()
        if not visitor:
            city, country = get_location_data(ip)
            visitor = Visitor(
                session_id=sid,
                ip_address=ip,
                city=city,
                country=country,
                user_agent=request.headers.get('User-Agent')
            )
            db.session.add(visitor)
        
        visitor.last_seen = datetime.datetime.utcnow()
        visitor.current_page = path
        db.session.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/track/heartbeat', methods=['POST'])
def track_heartbeat(): # Supports Beacon (text/plain) or JSON
    try:
        if request.content_type == 'text/plain': # Beacon sometimes sends as text
            data = json.loads(request.data)
        else:
            data = request.json

        sid = data.get('session_id')
        path = data.get('path')
        duration = float(data.get('duration', 0))

        visitor = Visitor.query.filter_by(session_id=sid).first()
        if visitor:
            visitor.last_seen = datetime.datetime.utcnow()
            visitor.current_page = path
            
            # Update Page Metric
            metric = PageMetric.query.filter_by(visitor_id=visitor.id, page_path=path).first()
            if not metric:
                metric = PageMetric(visitor_id=visitor.id, page_path=path)
                db.session.add(metric)
            
            # Only update if duration increases (simple max-hold logic for session)
            if duration > metric.duration_seconds:
                metric.duration_seconds = duration
                
            db.session.commit()
    except Exception as e:
        log(f"Tracking Error: {e}")
    return jsonify({"status": "ok"})


# --- Admin Routes ---

def login_required(f):
    def wrapper(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect('/admin/login')
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['logged_in'] = True
            return redirect('/admin/dashboard')
        return "Login Failed"
    return render_template_string("""
        <form method="post" style="margin: 50px auto; width: 300px; display: flex; flex-direction: column; gap: 10px;">
            <h2>Admin Login</h2>
            <input name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
    """)

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    # Active visitors in last 5 minutes
    limit_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=5)
    active_visitors = Visitor.query.filter(Visitor.last_seen >= limit_time).order_by(Visitor.last_seen.desc()).all()
    
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Live Dashboard</title>
        <meta http-equiv="refresh" content="5">
        <style>
            body { font-family: sans-serif; padding: 20px; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { padding: 10px; border: 1px solid #ddd; text-align: left; }
            th { background-color: #f4f4f4; }
            .status { color: green; font-weight: bold; }
            .nav { margin-bottom: 20px; }
            .nav a { margin-right: 15px; text-decoration: none; color: #007bff; }
        </style>
    </head>
    <body>
        <div class="nav">
            <a href="/admin/dashboard"><b>Live View</b></a>
            <a href="/admin/orders">Orders</a>
            <a href="/logout">Logout</a>
        </div>
        <h1>Live Visitors ('Active in last 5m')</h1>
        <table>
            <tr>
                <th>IP</th>
                <th>City/Country</th>
                <th>Current Page</th>
                <th>Last Seen</th>
                <th>Session Duration</th>
            </tr>
            {% for v in visitors %}
            <tr>
                <td>{{ v.ip_address }}</td>
                <td>{{ v.city }}, {{ v.country }}</td>
                <td>{{ v.current_page }}</td>
                <td>{{ v.last_seen.strftime('%H:%M:%S') }}</td>
                <td>
                   {% set total = 0 %}
                   {% for m in v.page_metrics %}
                     {% set total = total + m.duration_seconds %}
                   {% endfor %}
                   {{ total|round|int }}s
                </td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """, visitors=active_visitors)

@app.route('/admin/orders')
@login_required
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Orders</title>
        <style>
            body { font-family: sans-serif; padding: 20px; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { padding: 8px; border: 1px solid #ddd; text-align: left; font-size: 14px; }
            th { background-color: #f4f4f4; }
            .details { font-size: 12px; color: #555; }
            .nav { margin-bottom: 20px; }
            .nav a { margin-right: 15px; text-decoration: none; color: #007bff; }
            pre { margin: 0; white-space: pre-wrap; }
        </style>
    </head>
    <body>
        <div class="nav">
            <a href="/admin/dashboard">Live View</a>
            <a href="/admin/orders"><b>Orders</b></a>
            <a href="/logout">Logout</a>
        </div>
        <h1>All Orders</h1>
        <table>
            <tr>
                <th>ID</th>
                <th>Date</th>
                <th>Amount</th>
                <th>Method</th>
                <th>Customer Data</th>
                <th>Visit History (Time on Pages)</th>
            </tr>
            {% for o in orders %}
            <tr>
                <td>{{ o.id }}</td>
                <td>{{ o.created_at.strftime('%Y-%m-%d %H:%M') }}</td>
                <td>{{ o.amount }}€</td>
                <td>{{ o.method }}</td>
                <td>
                    <pre>{{ o.customer_data }}</pre>
                </td>
                <td>
                    {% if o.visitor %}
                        <ul>
                        {% for m in o.visitor.page_metrics %}
                            <li><b>{{ m.page_path }}:</b> {{ m.duration_seconds|round|int }}s</li>
                        {% endfor %}
                        </ul>
                    {% else %}
                        <span style="color:red">No Session Linked</span>
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """, orders=orders)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect('/admin/login')

# --- Public Routes ---

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)

@app.route('/promo')
def promo_index():
    return send_from_directory('promo', 'index.html')


@app.route('/api/payment', methods=['POST'])
def create_payment():
    try:
        data = request.json
        log(f"New Payment Request: {json.dumps(data)}")
        
        payer = data.get("payer", {})
        method = data.get("method")
        amt_raw = data.get("amount", 9)
        # Try to link session
        try:
             # Just a heuristic, we can pass session_id from frontend if needed, 
             # but IP matching is okay-ish for MVP or we add it to payload later.
             # For now let's hope frontend generates tracked session.
             # Actually, best practice is to pass header or payload.
             # Let's assume frontend sends nothing specialized yet, so we match by IP (latest active session on IP)
             ip = request.remote_addr
             visitor = Visitor.query.filter_by(ip_address=ip).order_by(Visitor.last_seen.desc()).first()
        except:
            visitor = None

        # Force Amount as Float (matching successful test)
        try:
            amount = float(amt_raw)
        except:
            amount = 9.0

        # STRICT SANITIZATION
        if "phone" in payer:
            p = "".join(filter(str.isdigit, str(payer["phone"])))
            if p.startswith("351") and len(p) > 9: p = p[3:]
            if len(p) > 9: p = p[-9:]
            payer["phone"] = p
            
        if "document" in payer:
            d = "".join(filter(str.isdigit, str(payer["document"])))
            if len(d) > 9: d = d[-9:]
            payer["document"] = d

        # Construct WayMB Body (without currency to match working test)
        waymb_body = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "account_email": ACCOUNT_EMAIL,
            "amount": amount,
            "method": method,
            "payer": payer
        }
        
        log(f"Calling WayMB API...")

        try:
            r = requests.post("https://api.waymb.com/transactions/create", 
                             json=waymb_body, 
                             headers={'Content-Type': 'application/json'}, 
                             timeout=30)
            
            try:
                resp = r.json()
            except:
                resp = {"raw_error": r.text}
            
            # success flags
            is_ok = False
            if r.status_code in [200, 201] and not resp.get("error"):
                is_ok = True

            if is_ok:
                log("Payment Created OK.")
                
                # SAVE ORDER TO DB
                new_order = Order(
                    amount=amount,
                    method=method,
                    status="CREATED",
                    customer_data=json.dumps(payer, indent=2),
                    visitor_id=visitor.id if visitor else None
                )
                db.session.add(new_order)
                db.session.commit()

                # Notify Pushcut
                try:
                    flow = data.get("flow", "promo")  # Default to promo for backward compat
                    
                    if flow == "root":
                        # ROOT Flow - Pushcut B
                        target_pushcut = "https://api.pushcut.io/BUhzeYVmAEGsoX2PSQwh1/notifications/Pendente%20delivery"
                    else:
                        # PROMO Flow - Pushcut A
                        target_pushcut = "https://api.pushcut.io/XPTr5Kloj05Rr37Saz0D1/notifications/Pendente%20delivery"
                    
                    requests.post(target_pushcut, json={
                        "text": f"Pedido: {amount}€ ({method.upper()})",
                        "title": "Worten Promo"
                    }, timeout=3)
                except: pass
                
                return jsonify({"success": True, "data": resp})
            else:
                log(f"Payment Failed by Gateway: {resp}")
                
                 # SAVE FAILED ORDER ATTEMPT? (Optional, let's save for debug)
                failed_order = Order(
                    amount=amount,
                    method=method,
                    status="FAILED_GATEWAY",
                    customer_data=json.dumps(payer, indent=2),
                    visitor_id=visitor.id if visitor else None
                )
                db.session.add(failed_order)
                db.session.commit()

                return jsonify({
                    "success": False, 
                    "error": resp.get("error", "Gateway Rejection"),
                    "details": resp,
                    "gateway_status": r.status_code
                })

        except Exception as e:
            log(f"Gateway Communication Error: {str(e)}")
            return jsonify({"success": False, "error": f"Erro de comunicação: {str(e)}"}), 502

    except Exception as e:
        log(f"Fatal Route Error: {str(e)}")
        return jsonify({"success": False, "error": f"Erro interno: {str(e)}"}), 500

@app.route('/api/status', methods=['POST'])
def check_status():
    data = request.json
    tx_id = data.get("id")
    try:
        r = requests.post("https://api.waymb.com/transactions/info", json={"id": tx_id}, timeout=15)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/notify', methods=['POST'])
def send_notification():
    data = request.json
    type = data.get("type", "Pendente delivery")
    text = data.get("text", "Novo pedido")
    title = data.get("title", "Worten")
    flow = data.get("flow", "promo")  # NEW: detect flow
    
    # Route based on flow, not amount
    if flow == "root":
        base_url = "https://api.pushcut.io/BUhzeYVmAEGsoX2PSQwh1/notifications"
        if type == "Aprovado delivery":
            safe_type = "venda%20aprovada%20"
        else:
            safe_type = type.replace(' ', '%20')
    else:  # promo
        base_url = "https://api.pushcut.io/XPTr5Kloj05Rr37Saz0D1/notifications"
        safe_type = type.replace(' ', '%20')
    
    url = f"{base_url}/{safe_type}"
    try:
        requests.post(url, json={"text": text, "title": title}, timeout=5)
        return jsonify({"success": True})
    except:
        return jsonify({"success": False}), 500

@app.route('/api/webhook/mbway', methods=['POST'])
def mbway_webhook():
    try:
        data = request.json or {}
        log(f"WEBHOOK RECEIVED: {json.dumps(data)}")

        amount = 0.0
        if "amount" in data:
            try: amount = float(data["amount"])
            except: pass
        elif "valor" in data:
            try: amount = float(data["valor"])
            except: pass
        
        # Determine flow by amount (12.49 = root, 12.50 = promo)
        flow = "root" if abs(amount - 12.49) < 0.01 else "promo"
        
        if flow == "root":
            target_pushcut = "https://api.pushcut.io/BUhzeYVmAEGsoX2PSQwh1/notifications/venda%20aprovada%20"
        else:
            target_pushcut = "https://api.pushcut.io/XPTr5Kloj05Rr37Saz0D1/notifications/Aprovado%20delivery"
        
        msg_text = f"Pagamento Confirmado: {amount}€" if amount > 0 else "Pagamento MBWAY Recebido!"
        
        requests.post(target_pushcut, json={
            "text": msg_text, 
            "title": "Worten Sucesso"
        }, timeout=4)
        
        return jsonify({"status": "received"}), 200

    except Exception as e:
        log(f"Webhook Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
