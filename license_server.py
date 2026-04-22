from flask import Flask, request, jsonify, render_template_string
import mysql.connector
import base64
import json
import random
import string

app = Flask(__name__)

# =========================
# 🔥 DB CONFIG (CHANGE HERE ONLY IF NEEDED)
# =========================
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Swetha@0711",
    "database": "licenses_db"
}

# =========================
# DB CONNECTION
# =========================
def get_db():
    return mysql.connector.connect(**DB_CONFIG)

# =========================
# 12-digit CODE GENERATOR
# =========================
def generate_code():
    chars = string.ascii_uppercase
    return "-".join(
        "".join(random.choice(chars) for _ in range(4))
        for _ in range(3)
    )

# =========================
# HOME PAGE (UPLOAD PAGE)
# =========================
HTML = """
<!DOCTYPE html>
<html>
<head>
<title>License Server</title>
</head>
<body style="text-align:center;font-family:Arial;margin-top:50px">

<h2>Upload license.req</h2>

<form method="POST" enctype="multipart/form-data">
<input type="file" name="file" required>
<br><br>
<button type="submit">Generate License</button>
</form>

{% if code %}
<h2 style="color:green">Activation Code: {{code}}</h2>
{% endif %}

<br><br>
<a href="/dashboard">View HWID Dashboard</a>

</body>
</html>
"""

# =========================
# UPLOAD license.req + GENERATE CODE
# =========================
@app.route("/", methods=["GET", "POST"])
def index():
    code = None

    if request.method == "POST":
        file = request.files["file"]

        encoded = file.read().decode().strip()
        decoded = base64.b64decode(encoded).decode()

        # format: hwid|random|request_id
        parts = decoded.split("|")

        hwid = parts[0]
        request_id = parts[2]

        code = generate_code()

        conn = get_db()
        cur = conn.cursor()

        # store in SQL
        cur.execute("""
            INSERT INTO licenses (license_key, hwid, request_id, status)
            VALUES (%s, %s, %s, %s)
        """, (code, hwid, request_id, "PENDING"))

        conn.commit()
        conn.close()

        print("Generated:", code, hwid)

    return render_template_string(HTML, code=code)

# =========================
# VERIFY API (Launcher calls this)
# =========================
@app.route("/verify", methods=["POST"])
def verify():
    data = request.json

    code = data.get("code")
    hwid = data.get("hwid")
    request_id = data.get("request_id")

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM licenses WHERE license_key=%s", (code,))
    row = cur.fetchone()

    if row:
        if row["hwid"] == hwid and row["request_id"] == request_id:

            # mark active
            cur2 = conn.cursor()
            cur2.execute("""
                UPDATE licenses 
                SET status='ACTIVE'
                WHERE id=%s
            """, (row["id"],))

            conn.commit()
            conn.close()

            return jsonify({"valid": True})

    conn.close()
    return jsonify({"valid": False})

# =========================
# DASHBOARD (YOUR "SHEET VIEW")
# =========================
@app.route("/dashboard")
def dashboard():
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM licenses ORDER BY created_at DESC")
    data = cur.fetchall()

    html = """
    <h2>License Dashboard</h2>
    <table border="1" cellpadding="10">
        <tr>
            <th>ID</th>
            <th>License</th>
            <th>HWID</th>
            <th>Status</th>
            <th>Time</th>
        </tr>
    """

    for row in data:
        html += f"""
        <tr>
            <td>{row['id']}</td>
            <td>{row['license_key']}</td>
            <td>{row['hwid'][:20]}...</td>
            <td>{row['status']}</td>
            <td>{row['created_at']}</td>
        </tr>
        """

    html += "</table>"

    conn.close()
    return html

# =========================
# RUN SERVER
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)