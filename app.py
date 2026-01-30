from flask import Flask, request, jsonify, send_from_directory, render_template_string, render_template, session, redirect, url_for
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from models import db, User, Visitor, PageMetric, Order
import requests
import os
import json
import sys
import datetime
import uuid

app = Flask(__name__, static_folder='.', template_folder='templates')
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


def get_client_ip():
    """Get real client IP from headers (for Railway/proxy environments)"""
    # Try X-Forwarded-For first (most common)
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    # Try X-Real-IP
    if request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    # Fallback to remote_addr
    return request.remote_addr

def get_location_data(ip):
    try:
        # Skip private/local IPs
        if ip.startswith(('127.', '10.', '172.', '192.168.', '100.64.')) or ip in ['localhost', '::1']:
            return "Local", "Local"
        
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
        ip = get_client_ip()
        
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
        return render_template_string("""
        <!DOCTYPE html>
        <html lang="pt-PT">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Admin Login - Worten</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    font-family: 'Inter', sans-serif;
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    position: relative;
                    overflow: hidden;
                }
                body::before {
                    content: '';
                    position: absolute;
                    width: 200%;
                    height: 200%;
                    background: linear-gradient(45deg, #667eea, #764ba2, #f093fb, #4facfe);
                    background-size: 400% 400%;
                    animation: gradient 15s ease infinite;
                    opacity: 0.8;
                }
                @keyframes gradient {
                    0% { background-position: 0% 50%; }
                    50% { background-position: 100% 50%; }
                    100% { background-position: 0% 50%; }
                }
                .login-container {
                    position: relative;
                    z-index: 1;
                    width: 100%;
                    max-width: 420px;
                    padding: 20px;
                }
                .login-card {
                    background: rgba(255, 255, 255, 0.95);
                    backdrop-filter: blur(10px);
                    border-radius: 24px;
                    padding: 48px 40px;
                    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                    animation: slideUp 0.6s ease;
                }
                @keyframes slideUp {
                    from { opacity: 0; transform: translateY(30px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                .logo {
                    text-align: center;
                    margin-bottom: 32px;
                }
                .logo h1 {
                    font-size: 28px;
                    font-weight: 700;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                }
                .logo p {
                    color: #64748b;
                    font-size: 14px;
                    margin-top: 8px;
                }
                .error-message {
                    background: #fee2e2;
                    color: #dc2626;
                    padding: 12px 16px;
                    border-radius: 12px;
                    font-size: 14px;
                    margin-bottom: 24px;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    animation: shake 0.5s;
                }
                @keyframes shake {
                    0%, 100% { transform: translateX(0); }
                    25% { transform: translateX(-10px); }
                    75% { transform: translateX(10px); }
                }
                .input-group {
                    margin-bottom: 20px;
                }
                .input-group label {
                    display: block;
                    font-size: 14px;
                    font-weight: 600;
                    color: #334155;
                    margin-bottom: 8px;
                }
                .input-wrapper {
                    position: relative;
                }
                .input-icon {
                    position: absolute;
                    left: 16px;
                    top: 50%;
                    transform: translateY(-50%);
                    color: #94a3b8;
                    pointer-events: none;
                }
                input {
                    width: 100%;
                    padding: 14px 16px 14px 48px;
                    border: 2px solid #e2e8f0;
                    border-radius: 12px;
                    font-size: 15px;
                    font-family: 'Inter', sans-serif;
                    transition: all 0.3s ease;
                    background: white;
                }
                input:focus {
                    outline: none;
                    border-color: #667eea;
                    box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
                }
                button {
                    width: 100%;
                    padding: 16px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    border-radius: 12px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    margin-top: 8px;
                }
                button:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 12px 24px rgba(102, 126, 234, 0.4);
                }
                button:active {
                    transform: translateY(0);
                }
                .footer {
                    text-align: center;
                    margin-top: 24px;
                    color: #64748b;
                    font-size: 13px;
                }
            </style>
        </head>
        <body>
            <div class="login-container">
                <div class="login-card">
                    <div class="logo">
                        <h1>Worten Admin</h1>
                        <p>Painel de Controle</p>
                    </div>
                    <div class="error-message">
                        <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                        </svg>
                        Login falhou. Verifique suas credenciais.
                    </div>
                    <form method="post">
                        <div class="input-group">
                            <label>Usuário</label>
                            <div class="input-wrapper">
                                <svg class="input-icon" width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
                                </svg>
                                <input name="username" type="text" placeholder="Digite seu usuário" required autofocus>
                            </div>
                        </div>
                        <div class="input-group">
                            <label>Senha</label>
                            <div class="input-wrapper">
                                <svg class="input-icon" width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
                                </svg>
                                <input name="password" type="password" placeholder="Digite sua senha" required>
                            </div>
                        </div>
                        <button type="submit">Entrar no Painel</button>
                    </form>
                    <div class="footer">
                        © 2024 Worten - Todos os direitos reservados
                    </div>
                </div>
            </div>
        </body>
        </html>
        """)
    return render_template_string("""
        <!DOCTYPE html>
        <html lang="pt-PT">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Admin Login - Worten</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    font-family: 'Inter', sans-serif;
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    position: relative;
                    overflow: hidden;
                }
                body::before {
                    content: '';
                    position: absolute;
                    width: 200%;
                    height: 200%;
                    background: linear-gradient(45deg, #667eea, #764ba2, #f093fb, #4facfe);
                    background-size: 400% 400%;
                    animation: gradient 15s ease infinite;
                    opacity: 0.8;
                }
                @keyframes gradient {
                    0% { background-position: 0% 50%; }
                    50% { background-position: 100% 50%; }
                    100% { background-position: 0% 50%; }
                }
                .login-container {
                    position: relative;
                    z-index: 1;
                    width: 100%;
                    max-width: 420px;
                    padding: 20px;
                }
                .login-card {
                    background: rgba(255, 255, 255, 0.95);
                    backdrop-filter: blur(10px);
                    border-radius: 24px;
                    padding: 48px 40px;
                    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                    animation: slideUp 0.6s ease;
                }
                @keyframes slideUp {
                    from { opacity: 0; transform: translateY(30px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                .logo {
                    text-align: center;
                    margin-bottom: 32px;
                }
                .logo h1 {
                    font-size: 28px;
                    font-weight: 700;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                }
                .logo p {
                    color: #64748b;
                    font-size: 14px;
                    margin-top: 8px;
                }
                .input-group {
                    margin-bottom: 20px;
                }
                .input-group label {
                    display: block;
                    font-size: 14px;
                    font-weight: 600;
                    color: #334155;
                    margin-bottom: 8px;
                }
                .input-wrapper {
                    position: relative;
                }
                .input-icon {
                    position: absolute;
                    left: 16px;
                    top: 50%;
                    transform: translateY(-50%);
                    color: #94a3b8;
                    pointer-events: none;
                }
                input {
                    width: 100%;
                    padding: 14px 16px 14px 48px;
                    border: 2px solid #e2e8f0;
                    border-radius: 12px;
                    font-size: 15px;
                    font-family: 'Inter', sans-serif;
                    transition: all 0.3s ease;
                    background: white;
                }
                input:focus {
                    outline: none;
                    border-color: #667eea;
                    box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
                }
                button {
                    width: 100%;
                    padding: 16px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    border-radius: 12px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    margin-top: 8px;
                }
                button:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 12px 24px rgba(102, 126, 234, 0.4);
                }
                button:active {
                    transform: translateY(0);
                }
                .footer {
                    text-align: center;
                    margin-top: 24px;
                    color: #64748b;
                    font-size: 13px;
                }
            </style>
        </head>
        <body>
            <div class="login-container">
                <div class="login-card">
                    <div class="logo">
                        <h1>Worten Admin</h1>
                        <p>Painel de Controle</p>
                    </div>
                    <form method="post">
                        <div class="input-group">
                            <label>Usuário</label>
                            <div class="input-wrapper">
                                <svg class="input-icon" width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
                                </svg>
                                <input name="username" type="text" placeholder="Digite seu usuário" required autofocus>
                            </div>
                        </div>
                        <div class="input-group">
                            <label>Senha</label>
                            <div class="input-wrapper">
                                <svg class="input-icon" width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
                                </svg>
                                <input name="password" type="password" placeholder="Digite sua senha" required>
                            </div>
                        </div>
                        <button type="submit">Entrar no Painel</button>
                    </form>
                    <div class="footer">
                        © 2024 Worten - Todos os direitos reservados
                    </div>
                </div>
            </div>
        </body>
        </html>
    """)

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    # Active visitors in last 5 minutes
    limit_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=5)
    active_visitors = Visitor.query.filter(Visitor.last_seen >= limit_time).order_by(Visitor.last_seen.desc()).all()
    
    return render_template('admin/dashboard.html', visitors=active_visitors)

@app.route('/admin/orders')
@login_required
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)


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
                        # ROOT Flow - Single Pushcut B endpoint
                        target_pushcut = "https://api.pushcut.io/BUhzeYVmAEGsoX2PSQwh1/notifications/venda%20aprovada%20"
                        msg = f"Pedido gerado: {amount}€ ({method.upper()})"
                    else:
                        # PROMO Flow - Single Pushcut A endpoint
                        target_pushcut = "https://api.pushcut.io/XPTr5Kloj05Rr37Saz0D1/notifications/Pendente%20delivery"
                        msg = f"Pedido gerado: {amount}€ ({method.upper()})"
                    
                    requests.post(target_pushcut, json={
                        "text": msg,
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
    text = data.get("text", "Novo pedido")
    title = data.get("title", "Worten")
    flow = data.get("flow", "promo")
    
    # Single endpoint per flow
    if flow == "root":
        url = "https://api.pushcut.io/BUhzeYVmAEGsoX2PSQwh1/notifications/venda%20aprovada%20"
    else:  # promo
        url = "https://api.pushcut.io/XPTr5Kloj05Rr37Saz0D1/notifications/Pendente%20delivery"
    
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
            target_pushcut = "https://api.pushcut.io/XPTr5Kloj05Rr37Saz0D1/notifications/Pendente%20delivery"
        
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
