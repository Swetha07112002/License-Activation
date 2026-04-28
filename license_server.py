from flask import Flask, request, jsonify, render_template_string, redirect
import psycopg2
from psycopg2.extras import RealDictCursor
import base64
import random
import string
import os

app = Flask(__name__)

def get_db():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        port=os.environ.get("DB_PORT", "5432")
    )

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS licenses (
        id SERIAL PRIMARY KEY,
        license_key VARCHAR(50),
        hwid TEXT,
        request_id TEXT,
        status VARCHAR(20),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        activated_at TIMESTAMP NULL
    )
    """)

    cur.execute("""
    ALTER TABLE licenses
    ADD COLUMN IF NOT EXISTS activated_at TIMESTAMP NULL
    """)

    conn.commit()
    cur.close()
    conn.close()
def generate_code():
    chars = string.ascii_uppercase
    return "-".join(
        "".join(random.choice(chars) for _ in range(4))
        for _ in range(3)
    )

HTML = """
<!DOCTYPE html>
<html>
<head>
<title>License Panel</title>
<style>
body{font-family:Arial;background:#f4f6f9;text-align:center;padding:40px}
.box{background:white;padding:30px;border-radius:15px;width:95%;margin:auto;box-shadow:0 0 10px rgba(0,0,0,.1)}
input,button{padding:10px;margin:5px}
table{width:100%;border-collapse:collapse;margin-top:20px}
th,td{border:1px solid #ddd;padding:10px;text-align:center;word-break:break-all}
th{background:#0d6efd;color:white}
#hwidlist{display:none}
.codebox{color:green;font-size:28px;font-weight:bold;margin-top:20px}
.msg{font-size:20px;margin-top:15px}
.delete{color:red;text-decoration:none;font-weight:bold}
</style>

<script>
function showList(){
    let box=document.getElementById("hwidlist");
    box.style.display = box.style.display==="none" ? "block" : "none";
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

{% if message %}<div class="msg">{{message}}</div>{% endif %}
{% if code %}<div class="codebox">Activation Code: {{code}}</div>{% endif %}

<br>
<a href="/add-hwid"><button type="button">Add HWID</button></a>
<button type="button" onclick="showList()">Show HWID List</button>

<div id="hwidlist">
<h2>Saved HWID List</h2>

<table>
<tr>
<th>ID</th>
<th>HWID</th>
<th>Status</th>
<th>Added Date</th>
<th>Added Time</th>
<th>Activated Date</th>
<th>Activated Time</th>
<th>Action</th>
</tr>

{% for row in rows %}
<tr>
<td>{{ loop.index }}</td>
<td>{{ row.hwid }}</td>
<td>{{ row.status }}</td>
<td>{{ row.created_at.strftime('%d-%m-%Y') if row.created_at else '' }}</td>
<td>{{ row.created_at.strftime('%I:%M %p') if row.created_at else '' }}</td>
<td>{{ row.activated_at.strftime('%d-%m-%Y') if row.activated_at else '-' }}</td>
<td>{{ row.activated_at.strftime('%I:%M %p') if row.activated_at else '-' }}</td>
<td>
<a class="delete" href="/delete/{{row.id}}" onclick="return confirm('Delete this HWID?')">Delete</a>
</td>
</tr>
{% endfor %}
</table>
</div>

</div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    code = None
    message = None

    if request.method == "POST":
        try:
            file = request.files.get("file")

            if not file:
                message = "No file selected"
            else:
                raw = file.read()
                encoded = raw.decode().strip()
                decoded = base64.b64decode(encoded).decode()

                parts = decoded.split("|")

                hwid = parts[0].strip()
                request_id = parts[2].strip()

                conn = get_db()
                cur = conn.cursor(cursor_factory=RealDictCursor)

                cur.execute("SELECT * FROM licenses WHERE hwid=%s LIMIT 1", (hwid,))
                allowed = cur.fetchone()

                if allowed:
                    cur.execute(
                        """
                        SELECT * FROM licenses
                        WHERE hwid=%s AND status='PENDING'
                        ORDER BY id DESC
                        LIMIT 1
                        """,
                        (hwid,)
                    )
                    old = cur.fetchone()

                    if old and old.get("license_key"):
                        code = old["license_key"]
                        message = "Existing Code Loaded"
                    else:
                        code = generate_code()

                        cur.execute(
                            """
                            UPDATE licenses
                            SET license_key=%s, request_id=%s, status='PENDING'
                            WHERE id=%s
                            """,
                            (code, request_id, allowed["id"])
                        )

                        conn.commit()
                        message = "New Code Generated"
                else:
                    message = "HWID Mismatch"

                cur.close()
                conn.close()

        except Exception as e:
            message = "ERROR: " + str(e)

    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT id, hwid, status, created_at, activated_at
        FROM licenses
        ORDER BY id DESC
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return render_template_string(HTML, code=code, message=message, rows=rows)

@app.route("/add-hwid", methods=["GET", "POST"])
def add_hwid():
    message = None

    if request.method == "POST":
        hwid = request.form.get("hwid", "").strip()

        if hwid:
            try:
                conn = get_db()
                cur = conn.cursor()

                cur.execute(
                    "INSERT INTO licenses (hwid, status) VALUES (%s, %s)",
                    (hwid, "NOT USED")
                )

                conn.commit()
                cur.close()
                conn.close()

                message = "HWID Added Successfully"

            except Exception as e:
                message = "ERROR: " + str(e)
        else:
            message = "HWID Required"

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:80px;">
        <h2>Add New HWID</h2>

        <form method="POST">
            <input type="text" name="hwid" placeholder="Enter HWID" required style="padding:10px;width:650px;">
            <br><br>
            <button type="submit" style="padding:10px 25px;">Add HWID</button>
        </form>

        {% if message %}<h3>{{message}}</h3>{% endif %}
        <br>
        <a href="/">Back</a>
    </body>
    </html>
    """, message=message)

@app.route("/delete/<int:id>")
def delete_hwid(id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM licenses WHERE id=%s", (id,))

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/")

@app.route("/verify", methods=["POST"])
def verify():
    data = request.json

    code = data.get("code", "").strip()
    hwid = data.get("hwid", "").strip()

    print("VERIFY CODE:", code)
    print("VERIFY HWID:", hwid)

    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT * FROM licenses WHERE license_key=%s", (code,))
    row = cur.fetchone()

    print("DB ROW:", row)

    if row and row["hwid"].strip().lower() == hwid.lower():
        cur.execute(
            "UPDATE licenses SET status='ACTIVE', activated_at=CURRENT_TIMESTAMP WHERE id=%s",
            (row["id"],)
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"valid": True})

    cur.close()
    conn.close()
    return jsonify({"valid": False})
init_db()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=True
    )