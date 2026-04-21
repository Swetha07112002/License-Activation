from flask import Flask, request, jsonify, render_template_string
import base64
import random
import string
import json
import os

app = Flask(__name__)

# one-time active sessions
db = {}

DB_FILE = "hwid_db.json"


# -------------------------------
# Create json file if not exists
# -------------------------------
def ensure_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump([], f, indent=4)


# -------------------------------
# Load HWID list
# -------------------------------
def load_hwid():
    ensure_db()
    with open(DB_FILE, "r") as f:
        return json.load(f)


# -------------------------------
# Save HWID list
# -------------------------------
def save_hwid(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)


# -------------------------------
# Generate 12-digit code
# -------------------------------
def generate_code():
    chars = string.ascii_uppercase
    return "-".join(
        "".join(random.choice(chars) for _ in range(4))
        for _ in range(3)
    )


# -------------------------------
# HTML
# -------------------------------
HTML = """
<!DOCTYPE html>
<html>
<body style="text-align:center;margin-top:50px;font-family:Arial">

<h2>Upload license.req</h2>

<form method="POST" enctype="multipart/form-data">
<input type="file" name="file" required><br><br>
<button type="submit">Generate Code</button>
</form>

{% if msg %}
<h3>{{msg}}</h3>
{% endif %}

{% if code %}
<h2 style="color:green;">{{code}}</h2>
{% endif %}

</body>
</html>
"""


# -------------------------------
# Home
# -------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    code = None
    msg = None

    if request.method == "POST":

        try:
            file = request.files["file"]

            encoded = file.read().decode().strip()
            decoded = base64.b64decode(encoded).decode()

            parts = decoded.split("|")

            hwid = parts[0].strip()
            request_id = parts[2].strip()

            print("REQ HWID:", repr(hwid))
            print("REQ ID:", request_id)

            hwids = load_hwid()

            found = None

            for row in hwids:
                db_hwid = row["hwid"].strip()

                print("DB HWID:", repr(db_hwid))

                if db_hwid.lower() == hwid.lower():
                    found = row
                    break

            # HWID not found
            if found is None:
                msg = "HWID Mismatch ❌"
                return render_template_string(HTML, code=None, msg=msg)

            # Already activated
            if found["status"] == "Activated":
                msg = "Already Activated ✅"
                return render_template_string(HTML, code=None, msg=msg)

            # Generate activation code
            code = generate_code()

            db[code] = {
                "hwid": hwid,
                "request_id": request_id
            }

            # update status
            found["status"] = "Code Generated"
            save_hwid(hwids)

            print("Generated:", code)

        except Exception as e:
            print(e)
            msg = "Invalid license.req ❌"

    return render_template_string(HTML, code=code, msg=msg)


# -------------------------------
# Verify code from launcher
# -------------------------------
@app.route("/verify", methods=["POST"])
def verify():

    try:
        data = request.json

        code = data.get("code", "").strip()
        hwid = data.get("hwid", "").strip()
        request_id = data.get("request_id", "").strip()

        print("VERIFY:", code, hwid, request_id)

        if code in db:

            row = db[code]

            if (
                row["hwid"].strip().lower() == hwid.lower()
                and row["request_id"].strip() == request_id
            ):

                # remove one-time code
                del db[code]

                # update json status
                hwids = load_hwid()

                for item in hwids:
                    if item["hwid"].strip().lower() == hwid.lower():
                        item["status"] = "Activated"

                save_hwid(hwids)

                return jsonify({"valid": True})

        return jsonify({"valid": False})

    except Exception as e:
        print(e)
        return jsonify({"valid": False})


# -------------------------------
# Run
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)