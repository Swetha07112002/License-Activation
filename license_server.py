from flask import Flask, request, jsonify, render_template_string
import base64
import random
import string
import json
import os

app = Flask(__name__)

db = {}

DB_FILE = "hwid_db.json"


def load_hwid():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r") as f:
        return json.load(f)


def save_hwid(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)


def generate_code():
    chars = string.ascii_uppercase
    return "-".join(
        "".join(random.choice(chars) for _ in range(4))
        for _ in range(3)
    )


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
<h2 style="color:green">{{code}}</h2>
{% endif %}

</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    code = None
    msg = None

    if request.method == "POST":
        try:
            file = request.files["file"]

            encoded = file.read().decode().strip()
            decoded = base64.b64decode(encoded).decode()

            # hwid|random|requestid|time
            parts = decoded.split("|")

            hwid = parts[0]
            request_id = parts[2]

            hwids = load_hwid()

            found = None
for row in hwids:
    print("REQ:", repr(hwid))
    print("DB :", repr(row["hwid"]))

    if row["hwid"].strip().lower() == hwid.strip().lower():
        found = row
        break

            if not found:
                msg = "HWID Mismatch ❌"
                return render_template_string(HTML, msg=msg)

            if found["status"] == "Activated":
                msg = "Already Activated ✅"
                return render_template_string(HTML, msg=msg)

            code = generate_code()

            db[code] = {
                "hwid": hwid,
                "request_id": request_id
            }

            msg = "Activation Code Generated"

        except:
            msg = "Invalid license.req"

    return render_template_string(HTML, code=code, msg=msg)


@app.route("/verify", methods=["POST"])
def verify():
    data = request.json

    code = data.get("code")
    hwid = data.get("hwid")
    request_id = data.get("request_id")

    if code in db:
        rec = db[code]

        if rec["hwid"] == hwid and rec["request_id"] == request_id:

            hwids = load_hwid()

            for row in hwids:
                if row["hwid"] == hwid:
                    row["status"] = "Activated"

            save_hwid(hwids)

            del db[code]

            return jsonify({"valid": True})

    return jsonify({"valid": False})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)