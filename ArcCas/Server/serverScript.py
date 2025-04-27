from flask import Flask, render_template, send_from_directory, jsonify, request
import os
import jwt
import json
import datetime
import asyncio
import random
import threading
from functools import wraps
from flask_sock import Sock

# Atur lokasi templates agar Flask bisa menemukannya
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # Ambil path folder ArcCas
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'), static_folder=os.path.join(BASE_DIR, 'static'))
sock = Sock(app)  # Inisialisasi Flask-Sock untuk WebSocket
SECRET_KEY = "ini_rahasia"
app.config['SECRET_KEY'] = SECRET_KEY

# Nilai awal untuk game state
game_state = {
    "GameStatus": [
        {
            "Status": "Playing",
            "Multiply": "1.00"
        }
    ]
}
PlayerList = {
    "PlayerList": [
        {
            
        }
    ]
}
timerInfo = 0

# Daftar koneksi WebSocket aktif
active_connections = set()

# Baca data dari file JSON
def load_users():
    try:
        with open('C:\\Users\\isakm\\OneDrive\\Desktop\\ArcCas\\Server\\dataManagement\\playerData\\userdat.json', 'r') as file:
            data = json.load(file)
        return {user["username"]: user["password"] for user in data["users"]}
    except Exception as e:
        print(f"Error loading users: {e}")
        return {}

USER_DB = load_users()  # Simpan data pengguna dalam dict

# Decorator untuk proteksi endpoint
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Ambil token dari Authorization header
        if "Authorization" in request.headers:
            auth_header = request.headers["Authorization"]
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]  # Ambil token tanpa "Bearer "

        if not token:
            return jsonify({"message": "Token tidak ditemukan!"}), 403

        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            current_user = data["username"]
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token sudah kadaluarsa!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "Token tidak valid!"}), 401

        return f(current_user, *args, **kwargs)

    return decorated

# Game logic
async def game_loop():
    global timerInfo
    while True:
        try:
            # Generate angka acak antara 1.00 sampai 1.5 (2 angka dibelakang koma)
            crash_point = round(random.uniform(1.00, 1.5), 2)

            
            # Reset multiply ke 1.00
            game_state["GameStatus"][0]["Multiply"] = "1.00"
            game_state["GameStatus"][0]["Status"] = "Playing"
            
            # Loop sampai crash point
            current_multiply = 1.00
            while current_multiply < crash_point:
                await asyncio.sleep(0.1)  # Tunggu 0.1 detik
                current_multiply += 0.01
                current_multiply = round(current_multiply, 2)  # Pastikan 2 angka dibelakang koma
                game_state["GameStatus"][0]["Multiply"] = f"{current_multiply:.2f}"
                
                # Broadcast ke semua koneksi
                await broadcast_game_state()
            
            # Crash
            game_state["GameStatus"][0]["Status"] = "Crash"
            print(f"Game crash pada multiply: {current_multiply}")
            await broadcast_game_state()
            await asyncio.sleep(3)  # Tunggu 3 detik
            
            # Waiting
            game_state["GameStatus"][0]["Status"] = "Waiting"
            
            await broadcast_game_state()
            
            timerInfo = 0
            while timerInfo <= 4:
                timerInfo += 1
                game_state["GameStatus"][0]["Status"] = "Waiting " + str(timerInfo)
                
                await broadcast_game_state()
                await asyncio.sleep(1)  # Tunggu 1 detik
            timerInfo = 0
        except Exception as e:
            print(f"Error in game loop: {e}")
            await asyncio.sleep(3)  # Tunggu sebelum mencoba lagi

# Broadcast game state ke semua koneksi
async def broadcast_game_state():
    game_status = game_state['GameStatus'][0]
    message = ""
    
    if "Playing" in str(game_status["Status"]):
        message = str(game_status["Multiply"])
    elif "Crash" in str(game_status["Status"]):
        message = str(game_status["Multiply"] + "x")
        with open("C:\\Users\\isakm\\OneDrive\\Desktop\\ArcCas\\Server\\dataManagement\\playerData\\playerList.json", "w") as pl_file:
            s = {
                    "PlayerList": [
                        
                    ]
                }
            json.dump(s, pl_file, indent=4)
    else:
        message = str(game_status["Status"])
    
    # Salin koneksi untuk mencegah error saat iterasi
    connections_copy = active_connections.copy()
    connections_to_remove = set()
    
    for ws in connections_copy:
        try:
            if ws and hasattr(ws, 'send'):
                ws.send(message)
            else:
                connections_to_remove.add(ws)
        except Exception as e:
            print(f"Error sending to WebSocket: {e}")
            connections_to_remove.add(ws)
    
    # Hapus koneksi yang tidak valid
    for ws in connections_to_remove:
        if ws in active_connections:
            active_connections.remove(ws)

# WebSocket route via Flask-Sock
@sock.route('/ws/game')
def game_socket(ws):
    print("WebSocket connected")
    active_connections.add(ws)
    try:
        while True:
            # Terima message dari client
            message = ws.receive()
            # Process message if needed
    except Exception as e:
        print(f"WebSocket disconnected: {e}")
    finally:
        print("Removing WebSocket connection")
        if ws in active_connections:
            active_connections.remove(ws)

# Flask routes
@app.route('/')
def home():
    return render_from_folder('homepage', 'main.html')

@app.route('/game/tenor')
def web1():
    return render_from_folder('games/Tenor', 'main.html')

@app.route('/account')
def web3():
    return render_from_folder('homepage', 'LoginRegister.html')

@app.route('/TenorData')
def SendTenorData():
    return render_from_folder('homepage', 'LoginRegister.html')

def render_from_folder(folder, filename):
    return render_template(f'{folder}/{filename}')

@app.route('/Main1.css')
def serve_css():
    css_folder = os.path.join(os.path.dirname(__file__), '/static')
    return send_from_directory(css_folder, 'Main1.css', mimetype='text/css')

@app.route('/images/<path:filename>')
def serve_images(filename):
    img_folder = os.path.join(os.path.dirname(__file__), 'img')
    return send_from_directory(img_folder, filename)


import json
import os

@app.route('/play/tenor', methods=['POST'])
@token_required
def playTenor(current_user):
    global player_list
    print(game_state["GameStatus"][0]["Status"])
    x = game_state["GameStatus"][0]["Status"].split()
    if "Waiting" == x[0]:
        try:
            # Baca file JSON untuk mendapatkan data pemain dan PlayerList
            player_data_path = "C:\\Users\\isakm\\OneDrive\\Desktop\\ArcCas\\Server\\dataManagement\\playerData\\userdat.json"
            
            with open(player_data_path, "r") as file:
                data = json.load(file)

            # Cari user berdasarkan username
            player = None
            for user in data["users"]:
                if user["username"] == current_user:

                    # Dapatkan taruhan yang dikirim dari frontend (menggunakan JSON)
                    bet = request.json.get("bet", 100)  # Jika bet tidak ada, anggap 100
                    bet = int(request.json.get("bet", 100))


                    # Validasi taruhan, misalnya bet tidak boleh negatif
                    if bet <= 0:
                        return jsonify({"message": "Bet must be greater than zero"}), 400
                    else:
                        player_list_path = "C:\\Users\\isakm\\OneDrive\\Desktop\\ArcCas\\Server\\dataManagement\\playerData\\playerList.json"
                        try:
                            with open(player_list_path, "r") as pl_file:
                                player_list = json.load(pl_file)

                        except FileNotFoundError:
                            print("File Not Found")

                        for i in player_list["PlayerList"]:  # <-- jangan lupa ["PlayerList"] ya
                            username = i["name"]["username"]  # username dari playerList
                            
                            print(username)  # Untuk cek debug di server

                            if username == current_user:  # Bandingkan dengan username yang login sekarang
                                return jsonify({
                                    "Status": "Failed",
                                    "Msg": "You can't bet twice"
                                }), 409  # 409 Conflict

                                


                        user['Balance'] -= bet
                        if int(user['Balance']) < bet:
                            return jsonify({
                                "Status": "Faild",
                                "Msg": "Infucent Balance"  # ⬅️ Tambahkan Balance ke respon
                            }), 505
                        # Tambahkan data player ke PlayerList
                        new_player = {
                            "name": user,
                            "bet": bet
                        }

                        # Baca data PlayerList jika ada


                        # Tambahkan player baru ke dalam PlayerList
                        player_list["PlayerList"].append(new_player)

                        # Simpan kembali PlayerList yang telah diperbarui ke file JSON
                        with open(player_list_path, "w") as pl_file:
                            json.dump(player_list, pl_file, indent=4)

                        print(player_list)
                        # Menyimpan kembali ke file JSON
                        with open(player_data_path, 'w') as file:
                            json.dump(data, file, indent=4)



                    return jsonify({
                        "Status": "Success",
                        "Balance": user['Balance']  # ⬅️ Tambahkan Balance ke respon
                    }), 200

            if player is None:
                return jsonify({"message": "User not found"}), 404
        except Exception as e:
            print(f"Error in /play/tenor: {e}")
            return jsonify({"message": "Server error"}), 500
    return jsonify({
        "Status": "Faild",
        "Msg": "You cannot bet while the game is in progress"  # ⬅️ Tambahkan Balance ke respon
    }), 505





@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    try:
        with open("C:\\Users\\isakm\\OneDrive\\Desktop\\ArcCas\\Server\\dataManagement\\playerData\\userdat.json", "r") as file:
            data = json.load(file)

        # Cari user
        for user in data["users"]:
            if user["username"] == username:
                if user['password'] == password:
                    # Buat payload untuk token JWT
                    payload = {
                        "username": username,
                        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)  # Token berlaku 1 jam
                    }

                    # Encode token
                    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

                    return jsonify({"token": token}), 200
                else:
                    return jsonify({"message": "Login gagal"}), 401
        
        return jsonify({"message": "User tidak ditemukan"}), 401
    except Exception as e:
        print(f"Error in login: {e}")
        return jsonify({"message": "Server error"}), 500

@app.route('/dashboard', methods=['GET'])
@token_required
def dashboard(current_user):
    try:
        # Buka file JSON
        with open("C:\\Users\\isakm\\OneDrive\\Desktop\\ArcCas\\Server\\dataManagement\\playerData\\userdat.json", "r") as file:
            data = json.load(file)


        # Cari user
        for user in data["users"]:
            if user["username"] == current_user:
                print(f"Balance {user['username']}: {user['Balance']}")
                twg = {
                    "Status": "Success",
                    "Username": current_user,
                    "Balance": user['Balance'],
                }
                print(current_user)
                return jsonify(twg)
        return jsonify({"message": "Something Went Wrong..."}), 404
    except Exception as e:
        print(f"Error in dashboard: {e}")
        return jsonify({"message": "Server error"}), 500

# Inisialisasi dan jalankan game loop dalam background
def start_game_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(game_loop())
    loop.run_forever()

if __name__ == '__main__':
    # Mulai game loop di thread terpisah
    game_thread = threading.Thread(target=start_game_loop, daemon=True)
    game_thread.start()
    
    # Jalankan Flask server
    app.run(debug=True, use_reloader=False, port=5000)  # disable use_reloader untuk menghindari duplikasi thread