from flask import Flask, jsonify
import json
import requests
import time
import threading

app = Flask(__name__)

def generate_tokens_from_api():
    """
    Generate tokens otomatis dari idpw.json menggunakan API kasjajwtgen1.vercel.app
    dan simpan hanya field 'token' ke token_bd.json
    """
    try:
        # Baca akun dari idpw.json
        with open("idpw.json", "r") as f:
            accounts = json.load(f)

        token_list = []

        for account in accounts:
            uid = account.get("uid")
            pw = account.get("password")

            if not uid or not pw:
                print(f"❌ Skip data tidak valid: {account}")
                continue

            url = f"https://kasjajwtgen1.vercel.app/token?uid={uid}&password={pw}"
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()

                    # Ambil field token dari JSON response
                    token = data.get("token")
                    if token:
                        token_list.append({"token": token})
                        print(f"✅ Token berhasil dibuat untuk UID {uid}")
                    else:
                        print(f"⚠️ UID {uid}: respon tanpa field 'token'")
                else:
                    print(f"❌ UID {uid}: HTTP {response.status_code}")
            except Exception as e:
                print(f"❌ Error ambil token UID {uid}: {e}")

            time.sleep(1)  # delay untuk hindari limit API

        # Simpan hasil token ke token_bd.json
        with open("token_bd.json", "w") as out_file:
            json.dump(token_list, out_file, indent=2)

        print(f"✅ Selesai generate {len(token_list)} token dan disimpan ke token_bd.json.\n")
        return True

    except FileNotFoundError:
        print("❌ File idpw.json tidak ditemukan.")
    except json.JSONDecodeError:
        print("❌ Format JSON di idpw.json salah.")
    except Exception as e:
        print(f"❌ Kesalahan tidak terduga: {e}")

    return False


def auto_refresh_tokens(interval_hours=6):
    """
    Jalankan generate token otomatis setiap interval tertentu (default: 6 jam)
    """
    def loop():
        while True:
            print("🕒 Mulai generate token otomatis...")
            generate_tokens_from_api()
            print(f"🟢 Selesai! Menunggu {interval_hours} jam berikutnya...\n")
            time.sleep(interval_hours * 3600)

    t = threading.Thread(target=loop, daemon=True)
    t.start()


@app.route('/generate_tokens', methods=['GET'])
def generate_tokens_endpoint():
    """
    Endpoint manual untuk regenerasi token via browser / API
    """
    success = generate_tokens_from_api()
    if success:
        return jsonify({"status": "success", "message": "token_bd.json updated"})
    return jsonify({"status": "failed", "message": "check server logs"}), 500


if __name__ == '__main__':
    # Generate token sekali saat server start
    print("🚀 Server start — generate token pertama...")
    generate_tokens_from_api()

    # Jalankan auto-refresh setiap 6 jam
    auto_refresh_tokens(6)

    app.run(debug=True, use_reloader=False)