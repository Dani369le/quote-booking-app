import os
import re
import sqlite3
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Note: For production, restrict origins: CORS(app, resources={r"/api/*": {"origins": "https://yourdomain.com"}})

DATABASE_FILE = "leads.db"

# Master Pricing Matrix (Keep this server-side so clients cannot temper with rates)
PRICING_CONFIG = {
    "vehicles": {
        "sedan": 100.00,
        "suv": 130.00,
        "truck": 150.00
    },
    "packages": {
        "basic": 50.00,
        "premium": 120.00,
        "full_detail": 200.00
    },
    "addons": {
        "addonPet": 30.00,
        "addonHeadlight": 45.00
    }
}

# --- DATABASE SETUP ---
def init_db():
    """Initializes SQLite database to persist leads across server restarts."""
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                customer_email TEXT NOT NULL,
                vehicle_type TEXT NOT NULL,
                package_type TEXT NOT NULL,
                addons TEXT,
                calculated_total REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

# Run DB initialization at startup
init_db()

# --- UTILITIES ---
def is_valid_email(email):
    """Simple regex check for email validity."""
    email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(email_regex, email or ''))

def calculate_quote(vehicle_key, package_key, addon_keys):
    """Calculates the authoritative server-side price."""
    base_price = PRICING_CONFIG["vehicles"].get(vehicle_key, 0.0)
    package_price = PRICING_CONFIG["packages"].get(package_key, 0.0)
    
    addons_price = sum(
        PRICING_CONFIG["addons"].get(addon, 0.0) for addon in addon_keys
    )
    
    return round(base_price + package_price + addons_price, 2)

# --- ROUTES ---
@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/api/quote', methods=['POST'])
def receive_quote():
    """
    Accepts raw selection keys, validates payload, re-calculates 
    authoritative price, saves lead to database, and responds.
    """
    try:
        data = request.get_json() or {}

        # 1. Validation Checks
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        vehicle = data.get('vehicle_type')
        package = data.get('package_type')
        addons = data.get('addons', []) # Expected list of string keys

        if not name or not email or not vehicle or not package:
            return jsonify({
                "status": "error",
                "message": "Missing required fields (name, email, vehicle, package)."
            }), 400

        if not is_valid_email(email):
            return jsonify({
                "status": "error",
                "message": "Invalid email address format."
            }), 400

        # 2. Server-side Pricing Calculation
        total_price = calculate_quote(vehicle, package, addons)

        # 3. Store in Database
        with sqlite3.connect(DATABASE_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO quotes (customer_name, customer_email, vehicle_type, package_type, addons, calculated_total)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, email, vehicle, package, ",".join(addons), total_price))
            conn.commit()
            quote_id = cursor.lastrowid

        # 4. Success Response
        return jsonify({
            "status": "success",
            "message": "Quote request received successfully!",
            "data": {
                "quote_id": quote_id,
                "calculated_price": f"${total_price:.2f}"
            }
        }), 201

    except Exception as e:
        app.logger.error(f"Error processing quote: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "An internal error occurred processing your quote."
        }), 500

# Endpoint for business owners to fetch submitted leads (Admin Feature)
@app.route('/api/admin/leads', methods=['GET'])
def get_leads():
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM quotes ORDER BY created_at DESC")
            rows = cursor.fetchall()
            
            leads = [dict(row) for row in rows]

        return jsonify({"status": "success", "leads": leads}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)