from flask import Flask, request, jsonify, render_template_string
import base64
import random
import string

app = Flask(__name__)

# store active sessions
db = {}

# generate 12-digit code
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

{% if code %}
<h3>Activation Code:</h3>
<h2 style="color:green;">{{code}}</h2>
{% endif %}

</body>
</html>
"""

@app.route("/", methods=["GET","POST"])
def index():
    code = None

    if request.method == "POST":
        file = request.files["file"]

        encoded = file.read().decode().strip()
        decoded = base64.b64decode(encoded).decode()

        parts = decoded.split("|")

        hwid = parts[0]
        request_id = parts[2]

        code = generate_code()

        # store session
        db[code] = {
            "hwid": hwid,
            "request_id": request_id
        }

        print("Generated:", code, hwid, request_id)

    return render_template_string(HTML, code=code)

@app.route("/verify", methods=["POST"])
def verify():
    data = request.json

    code = data.get("code")
    hwid = data.get("hwid")
    request_id = data.get("request_id")

    print("Verify:", code, hwid, request_id)

    # check code
    if code in db:
        record = db[code]

        # strict match
        if record["hwid"] == hwid and record["request_id"] == request_id:
            del db[code]  # one-time use
            return jsonify({"valid": True})

    return jsonify({"valid": False})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)