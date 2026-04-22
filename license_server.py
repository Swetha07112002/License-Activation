from flask import Flask, request, jsonify, render_template_string
import mysql.connector
import base64
import random
import string

app = Flask(__name__)

# =========================
# DB CONFIG
# =========================
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "Swetha@0711",
    "database": "licenses_db"
}

# =========================
# DB CONNECTION
# =========================
def get_db():
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="Swetha@0711",
        database="licenses_db",
        port=3306,
        auth_plugin="mysql_native_password",
        use_pure=True
    )

# =========================
# CODE GENERATOR
# =========================
def generate_code():
    chars = string.ascii_uppercase
    return "-".join(
        "".join(random.choice(chars) for _ in range(4))
        for _ in range(3)
    )

# =========================
# HTML PAGE
# =========================
HTML = """
<!DOCTYPE html>
<html>
<head>
<title>License Panel</title>

<style>
body{
    font-family:Arial;
    background:#f4f6f9;
    text-align:center;
    padding:40px;
}

.box{
    background:white;
    padding:30px;
    border-radius:15px;
    width:95%;
    margin:auto;
    box-shadow:0 0 10px rgba(0,0,0,.1);
}

input,button{
    padding:10px;
    margin:5px;
}

table{
    width:100%;
    border-collapse:collapse;
    margin-top:20px;
}

th,td{
    border:1px solid #ddd;
    padding:10px;
    text-align:center;
    word-break:break-all;
}

th{
    background:#0d6efd;
    color:white;
}

#hwidlist{
    display:none;
}

.codebox{
    color:green;
    font-size:28px;
    font-weight:bold;
    margin-top:20px;
}

.msg{
    font-size:20px;
    margin-top:15px;
}
</style>

<script>
function showList(){
    let box = document.getElementById("hwidlist");
    if(box.style.display === "none"){
        box.style.display = "block";
    }else{
        box.style.display = "none";
    }
}
</script>

</head>
<body>

<div class="box">

<h1>Upload License File</h1>

<form method="POST" enctype="multipart/form-data">
<input type="file" name="file" required>
<button type="submit">Generate</button>
</form>

{% if message %}
<div class="msg">{{message}}</div>
{% endif %}

{% if code %}
<div class="codebox">Activation Code: {{code}}</div>
{% endif %}

<br>
<button type="button" onclick="showList()">Show HWID List</button>

<div id="hwidlist">

<h2>Saved HWID List</h2>

<table>
<tr>
<th>ID</th>
<th>HWID</th>
<th>Status</th>
<th>Date</th>
<th>Time</th>
</tr>

{% for row in rows %}
<tr>
<td>{{ row.id }}</td>
<td>{{ row.hwid }}</td>
<td>{{ row.status }}</td>
<td>{{ row.created_at.strftime('%d-%m-%Y') if row.created_at else '' }}</td>
<td>{{ row.created_at.strftime('%I:%M %p') if row.created_at else '' }}</td>
</tr>
{% endfor %}

</table>

</div>

</div>

</body>
</html>
"""

# =========================
# HOME PAGE
# =========================
@app.route("/", methods=["GET", "POST"])
def index():

    code = None
    message = None

    if request.method == "POST":
        try:
            file = request.files.get("file")

            if not file:
                message = "No file selected ❌"
            else:
                raw = file.read()
                encoded = raw.decode().strip()
                decoded = base64.b64decode(encoded).decode()

                parts = decoded.split("|")

                hwid = parts[0].strip()
                request_id = parts[2].strip()

                conn = get_db()
                cur = conn.cursor(dictionary=True, buffered=True)

                # HWID exists ah check pannum
                cur.execute(
                    "SELECT * FROM licenses WHERE hwid=%s LIMIT 1",
                    (hwid,)
                )
                allowed = cur.fetchone()

                if allowed:
                    # Existing pending code irukka?
                    cur.execute(
                        "SELECT * FROM licenses WHERE hwid=%s AND status='PENDING' ORDER BY id DESC LIMIT 1",
                        (hwid,)
                    )
                    old = cur.fetchone()

                    if old and old.get("license_key"):
                        code = old["license_key"]
                        message = "Existing Code Loaded ✅"
                    else:
                        code = generate_code()

                        if old:
                            # Existing row update pannum
                            cur.execute("""
                                UPDATE licenses
                                SET license_key=%s, request_id=%s, status='PENDING'
                                WHERE id=%s
                            """, (code, request_id, old["id"]))
                        else:
                            # New row insert pannum
                            cur.execute("""
                                INSERT INTO licenses
                                (license_key, hwid, request_id, status)
                                VALUES (%s, %s, %s, %s)
                            """, (code, hwid, request_id, "PENDING"))

                        conn.commit()
                        message = "New Code Generated ✅"
                else:
                    message = "HWID Mismatch ❌"

                conn.close()

        except Exception as e:
            message = "ERROR: " + str(e)

    conn = get_db()
    cur = conn.cursor(dictionary=True, buffered=True)

    cur.execute("""
        SELECT id, hwid, status, created_at
        FROM licenses
        ORDER BY id DESC
    """)
    rows = cur.fetchall()

    conn.close()

    return render_template_string(
        HTML,
        code=code,
        message=message,
        rows=rows
    )

# =========================
# VERIFY API
# =========================
@app.route("/verify", methods=["POST"])
def verify():

    data = request.json

    code = data.get("code", "").strip()
    hwid = data.get("hwid", "").strip()

    conn = get_db()
    cur = conn.cursor(dictionary=True, buffered=True)

    cur.execute(
        "SELECT * FROM licenses WHERE license_key=%s",
        (code,)
    )
    row = cur.fetchone()

    if row:
        if row["hwid"].strip().lower() == hwid.lower():
            cur.execute(
                "UPDATE licenses SET status='ACTIVE' WHERE id=%s",
                (row["id"],)
            )
            conn.commit()
            conn.close()
            return jsonify({"valid": True})

    conn.close()
    return jsonify({"valid": False})

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)