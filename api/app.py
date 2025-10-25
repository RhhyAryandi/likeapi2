from flask import Flask, jsonify, request
import json, time, threading, requests, asyncio, binascii
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from google.protobuf.json_format import MessageToJson
from google.protobuf.message import DecodeError

# import protobuf modules
from protobuf import like_pb2, like_count_pb2, uid_generator_pb2

app = Flask(__name__)

# AES Key dan IV
AES_KEY = b'Yg&tc%DEuh6%Zc^8'
AES_IV = b'6oyZDr22E3ychjM%'

# ---------- 🔁 TOKEN AUTO REFRESH ---------- #
def generate_tokens_from_api():
    """Generate JWT token dari idpw.json via kasjajwtgen1.vercel.app"""
    try:
        with open("idpw.json", "r") as f:
            accounts = json.load(f)

        tokens = []
        for acc in accounts:
            uid, pw = acc.get("uid"), acc.get("password")
            if not uid or not pw:
                continue
            url = f"https://kasjajwtgen1.vercel.app/token?uid={uid}&password={pw}"
            try:
                r = requests.get(url, timeout=15)
                if r.status_code == 200:
                    data = r.json()
                    token = data.get("token")
                    if token:
                        tokens.append({"token": token})
                        print(f"✅ Token OK untuk UID {uid}")
                    else:
                        print(f"⚠️ UID {uid}: token tidak ditemukan")
                else:
                    print(f"❌ UID {uid}: HTTP {r.status_code}")
            except Exception as e:
                print(f"⚠️ Error UID {uid}: {e}")
            time.sleep(1)

        with open("token_bd.json", "w") as f:
            json.dump(tokens, f, indent=2)

        print(f"✅ Total {len(tokens)} token disimpan ke token_bd.json")
    except Exception as e:
        print(f"❌ Error generate token: {e}")

def auto_refresh_tokens(interval_hours=6):
    """Thread untuk refresh token tiap 6 jam"""
    def loop():
        while True:
            print("\n🕒 Refresh token otomatis...")
            generate_tokens_from_api()
            time.sleep(interval_hours * 3600)
    threading.Thread(target=loop, daemon=True).start()

# ---------- 🔒 AES ENCRYPTION ---------- #
def encrypt_message(plaintext: bytes):
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    padded = pad(plaintext, AES.block_size)
    encrypted = cipher.encrypt(padded)
    return binascii.hexlify(encrypted).decode('utf-8')

# ---------- 🧩 PROTOBUF HANDLERS ---------- #
def create_protobuf_message(uid, region):
    msg = like_pb2.like()
    msg.uid = int(uid)
    msg.region = region
    return msg.SerializeToString()

def decode_protobuf(binary):
    try:
        obj = like_count_pb2.Info()
        obj.ParseFromString(binary)
        return obj
    except DecodeError:
        return None

def create_uid_proto(uid):
    msg = uid_generator_pb2.uid_generator()
    msg.saturn_ = int(uid)
    msg.garena = 1
    return msg.SerializeToString()

def enc_uid(uid):
    return encrypt_message(create_uid_proto(uid))

# ---------- 🌐 MAIN ROUTES ---------- #
@app.route("/")
def home():
    return jsonify({
        "status": "online",
        "credits": "Dev By Flexbase",
        "auto_refresh": "6 jam sekali"
    })

@app.route("/generate_tokens")
def manual_generate():
    threading.Thread(target=generate_tokens_from_api).start()
    return jsonify({"status": "generating in background"})

@app.route("/like")
def like_profile():
    uid = request.args.get("uid")
    server = request.args.get("server_name", "").upper()
    if not uid or not server:
        return jsonify({"error": "uid dan server_name wajib diisi"}), 400

    try:
        with open("token_bd.json", "r") as f:
            tokens = json.load(f)
        if not tokens:
            return jsonify({"error": "token_bd.json kosong"}), 500
        token = tokens[0]["token"]

        # encode uid
        encrypted_uid = enc_uid(uid)
        edata = bytes.fromhex(encrypted_uid)

        # pilih URL berdasarkan server
        if server == "IND":
            url = "https://client.ind.freefiremobile.com/GetPlayerPersonalShow"
        elif server in {"BR", "US", "SAC", "NA"}:
            url = "https://client.us.freefiremobile.com/GetPlayerPersonalShow"
        else:
            url = "https://clientbp.ggblueshark.com/GetPlayerPersonalShow"

        headers = {
            'Authorization': f'Bearer {token}',
            'User-Agent': "Dalvik/2.1.0",
            'Connection': "Keep-Alive",
            'Content-Type': "application/x-www-form-urlencoded"
        }

        response = requests.post(url, data=edata, headers=headers, verify=False)
        obj = decode_protobuf(response.content)
        if obj is None:
            return jsonify({"error": "gagal decode protobuf"}), 500

        js = json.loads(MessageToJson(obj))
        return jsonify(js)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------- 🚀 STARTUP ---------- #
print("🚀 Initial token generation disabled (manual trigger only).")