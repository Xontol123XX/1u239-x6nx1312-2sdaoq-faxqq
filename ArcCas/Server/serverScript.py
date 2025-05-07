from flask import Flask, render_template, send_from_directory, jsonify, request, session
import os
import jwt
import json
import datetime
import asyncio
import random
import threading
import hashlib
import secrets
from functools import wraps
from flask_sock import Sock
from werkzeug.security import generate_password_hash, check_password_hash
from pathlib import Path
import logging
from dotenv import load_dotenv
import traceback
import math

# Load environment variables
load_dotenv()

# Set up proper logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get the absolute path to the project directory
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'), static_folder=os.path.join(BASE_DIR, 'static'))

# Get secret key from environment variable, use a random secure string as fallback
SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Set up WebSocket
sock = Sock(app)

# Initialize game state
game_state = {
    "GameStatus": [
        {
            "Status": "Playing",
            "Multiply": "0.00"
        }
    ]
}

# Initialize player list
PlayerList = {
    "PlayerList": []
}

TenorTotalBet = 0
Temp_TenorMultiplyCashout = []
TotalPlayerCashoutTenor = 0



# Hitung multiplier berdasarkan strategi data

def calculate_profit_strategy(data):
    crash_history = data.get("crashHistory", [])
    tenor_profit = data.get("TenorProfit", [])
    avg_multiply_cashout_raw = data.get("AvgMultiplyCashout", [])

    crash_valid = [x for x in crash_history if isinstance(x, (int, float))]
    cashout_valid = [x for x in avg_multiply_cashout_raw if isinstance(x, (int, float))]

    crash_avg = sum(crash_valid[-20:]) / len(crash_valid[-20:]) if crash_valid[-20:] else 0
    profit_last_20 = sum(tenor_profit[-20:])
    cashout_avg = sum(cashout_valid) / len(cashout_valid) if cashout_valid else 0

    # Deteksi strategi "cashout terlalu cepat"
    early_cashouts = [x for x in cashout_valid[-50:] if 1.01 < x <= 1.70]
    early_ratio = len(early_cashouts) / len(cashout_valid[-50:]) if cashout_valid[-50:] else 0

    return {
        "crash_avg": crash_avg,
        "profit_last_20": profit_last_20,
        "cashout_avg": cashout_avg,
        "early_cashout_ratio": early_ratio,
        "GameLength": len(avg_multiply_cashout_raw),
        "CrashHistory": crash_history
    }

# Fungsi utama untuk generate crash point agar bandar tetap untung

def generate_crash_point(TotalBet):
    file_path = "C:\\Users\\isakm\\OneDrive\\Desktop\\ArcCas\\Server\\dataManagement\\GameData\\TenorData.json"
    crash_point = 0

    with open(file_path, "r") as f:
        data = json.load(f)

    stats = calculate_profit_strategy(data)
    profit = stats["profit_last_20"]
    history = stats["CrashHistory"]
    early_cash_ratio = stats["early_cashout_ratio"]

    # Jika tidak ada taruhan, kasih multiplier tinggi
    
        

    # Jika banyak pemain cashout cepat, sesekali paksa crash 1.00
    if early_cash_ratio > 0.7 and random.random() < 0.25 and profit < 5000:
        print("KONTOL")
        x = random.choices([0,1],weights=[35,65])
        if x == 0:
            return 1.00
        else:
            crash_point = random.uniform(1,2)
    # Profit band rules
    elif profit < 500:
        crash_point = random.uniform(1.1, 1.6)
    elif profit < 1000:
        crash_point = random.uniform(1,2)
    elif profit < 2500:
        crash_point = random.uniform(1.1, 2.0)
    elif profit <= 5000:
        crash_point = random.uniform(2.0, 3.5)
    elif profit <= 7000:
        crash_point = random.uniform(5, 10)
    elif profit >= 20000:
        crash_point = random.uniform(7, 14)
        if profit - TotalBet*stats["cashout_avg"] > 10000 and stats["cashout_avg"] < 2:
            crash_point = crash_point + random.uniform(7, 14)
    
    if TotalBet == 0:
        bias = 0
        x = random.choices([0,1], weights=[40,60])
        if x == 1:
            low = 2
        else:
            low = 1
        if sum(history[-4:]) / 4 < 1:
            bias = 4
        elif sum(history[-4:]) / 4 < 3:
            bias = 5
        elif sum(history[-4:]) / 4 < 5:
            bias = 5.5
        elif sum(history[-4:]) / 4 < 6:
            bias = 6
        elif sum(history[-4:]) / 4 > 6:
            bias = 10
        high = 99
        print(str(sum(history[-4:]))+"KONTOLLL")
        print(str(bias)+"KONTOLLL")

        r = random.random()         # hasil antara 0 dan 1
        biased_r = r ** bias        # bikin angka tinggi makin jarang
        value = low + (high - low) * biased_r

        crash_point = value
    if stats["GameLength"] >= 40 and profit > 10000:
        file_path = "C:\\Users\\isakm\\OneDrive\\Desktop\\ArcCas\\Server\\dataManagement\\GameData\\TenorData.json"
        print(str(stats["GameLength"])+"Kontol")
        default_data = {
            "crashHistory": stats["CrashHistory"][-30:],
            "TenorProfit": [],
            "TenorLastBetTotal": [],
            "AvgMultiplyCashout": [],
            "TotalPlayerCashout":[]
        }
        with open(file_path, "w") as f:
            json.dump(default_data, f, indent=4)
    if crash_point <= 1:
        crash_point = 1

    return round(crash_point, 2)





timerInfo = 0

# Store active WebSocket connections
active_connections = set()

# Ensure data directories exist
def ensure_data_dirs():
    data_dir = os.path.join(BASE_DIR, 'Server', 'dataManagement', 'playerData')
    os.makedirs(data_dir, exist_ok=True)
    # Initialize user data file if it doesn't exist
    user_data_path = os.path.join(data_dir, 'userdat.json')
    if not os.path.exists(user_data_path):
        with open(user_data_path, 'w') as f:
            json.dump({"users": []}, f, indent=4)
    # Initialize player list file if it doesn't exist
    player_list_path = os.path.join(data_dir, 'playerList.json')
    if not os.path.exists(player_list_path):
        with open(player_list_path, 'w') as f:
            json.dump({"PlayerList": []}, f, indent=4)

# Load user data from JSON file
def load_users():
    try:
        path = os.path.join(BASE_DIR, 'Server', 'dataManagement', 'playerData', 'userdat.json')
        with open(path, 'r') as file:
            data = json.load(file)
        return data
    except Exception as e:
        logger.error(f"Error loading users: {e}")
        traceback.print_exc()
        return {"users": []}

# Safe file writing function to prevent race conditions
def safe_write_json(data, filepath):
    # Create a temporary file and write to it
    temp_filepath = f"{filepath}.tmp"
    with open(temp_filepath, 'w') as file:
        json.dump(data, file, indent=4)
    
    # Rename the temporary file to the target filepath (atomic operation)
    os.replace(temp_filepath, filepath)

# JWT token validation decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Get token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        if not token:
            return jsonify({"message": "Authentication token is missing!"}), 401

        try:
            # Decode and validate token
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            current_user = data["username"]
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Authentication token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "Invalid authentication token!"}), 401

        return f(current_user, *args, **kwargs)

    return decorated

# Input validation function
def validate_bet(bet):
    try:
        bet = int(bet)
        if bet <= 0:
            return False, "Bet must be greater than zero"
        return True, bet
    except (ValueError, TypeError):
        traceback.print_exc()
        return False, "Bet must be a valid number"
    

# Game loop
async def game_loop():
    global timerInfo
    global crash_history
    global TenorTotalBet
    global Temp_TenorMultiplyCashout
    global TotalPlayerCashoutTenor
    while True:
        try:
            # Membaca data dari file JSON
            crash_point = 0
            
            
            # Membaca data dari file JSON
            with open("C:\\Users\\isakm\\OneDrive\\Desktop\\ArcCas\\Server\\dataManagement\\GameData\\crashPoint.json", "r") as x:
                # Memuat isi file JSON ke dalam dictionary
                data = json.load(x)
                
                # Memeriksa apakah nilai dari 'crashpoint' bukan bertipe string
                if not isinstance(data["crashpoint"], str):
                    crash_point = data["crashpoint"]
                    data["crashpoint"] = "s"  # Mengubah nilai 'crashpoint' menjadi string 's'
                else:
                    crash_point = generate_crash_point(TenorTotalBet)
                    

            # Reset multiply to 1.00
            game_state["GameStatus"][0]["Multiply"] = "1.00"
            game_state["GameStatus"][0]["Status"] = "Playing"
            
            
            # Loop until crash point
            current_multiply = 1.00
            print("Crash In " + str(crash_point))
            while current_multiply < crash_point:
                await asyncio.sleep(0.04)
                current_multiply += 0.01
                current_multiply = round(current_multiply, 2)
                game_state["GameStatus"][0]["Multiply"] = f"{current_multiply:.2f}"
                
                # Broadcast to all connections
                await broadcast_game_state()
            
            # Crash
            game_state["GameStatus"][0]["Status"] = "Crash"
            await broadcast_game_state()
            await asyncio.sleep(3)
                        # Buka file TenorData.json (untuk dibaca dan ditulis)
            with open("C:\\Users\\isakm\\OneDrive\\Desktop\\ArcCas\\Server\\dataManagement\\GameData\\TenorData.json", "r+") as tenor_file:
                tenor_data = json.load(tenor_file)


                # Buka file playerList.json
                with open("C:\\Users\\isakm\\OneDrive\\Desktop\\ArcCas\\Server\\dataManagement\\playerData\\playerList.json", "r") as player_file:
                    player_data = json.load(player_file)

                # Hitung total bet
                total_bet = sum(player.get("bet", 0) for player in player_data["PlayerList"])

                # Tambahkan ke TenorLastBetTotal (harus list)

                if total_bet > 0:
                    tenor_data["TotalPlayerCashout"].append(TotalPlayerCashoutTenor)
                    tenor_data["TenorLastBetTotal"].append(total_bet)
                    tenor_data["TenorProfit"].append(TenorTotalBet)
                    for i in Temp_TenorMultiplyCashout:
                        tenor_data["AvgMultiplyCashout"].append(i)

                tenor_data["crashHistory"].append(crash_point)
                
                TenorTotalBet = 0
                Temp_TenorMultiplyCashout = []
                TotalPlayerCashoutTenor = 0
                
                print(TenorTotalBet)
                # Kembali ke awal file, tulis ulang isi file
                tenor_file.seek(0)
                json.dump(tenor_data, tenor_file, indent=4)
                tenor_file.truncate()  # Hapus sisa isi file lama jika file baru lebih pendek
            
            # Reset player list at crash
            player_list_path = os.path.join(BASE_DIR, 'Server', 'dataManagement', "playerData", "playerList.json")
            empty_list = {"PlayerList": []}
            safe_write_json(empty_list, player_list_path)
            
            # Waiting period
            game_state["GameStatus"][0]["Status"] = "Waiting"
            
            await broadcast_game_state()
            
            timerInfo = 0
            while timerInfo <= 4:
                timerInfo += 1
                game_state["GameStatus"][0]["Status"] = f"Waiting {timerInfo}"
                await broadcast_game_state()
                await asyncio.sleep(1)
            timerInfo = 0
        except Exception as e:
            logger.error(f"Error in game loop: {e}")
            traceback.print_exc()
            await asyncio.sleep(3)

# Broadcast game state to all WebSocket connections
async def broadcast_game_state():
    game_status = game_state['GameStatus'][0]
    message = ""
    
    if "Playing" in str(game_status["Status"]):
        message = str(game_status["Multiply"])
    elif "Crash" in str(game_status["Status"]):
        message = f"{game_status['Multiply']}x"
    else:
        message = str(game_status["Status"])
    
    # Copy connections to prevent errors during iteration
    connections_copy = active_connections.copy()
    connections_to_remove = set()
    
    for ws in connections_copy:
        try:
            if ws and hasattr(ws, 'send'):
                ws.send(message)
            else:
                connections_to_remove.add(ws)
        except Exception as e:
            logger.error(f"Error sending to WebSocket: {e}")
            connections_to_remove.add(ws)
    
    # Remove invalid connections
    for ws in connections_to_remove:
        if ws in active_connections:
            active_connections.remove(ws)

# WebSocket route
@sock.route('/ws/game')
def game_socket(ws):
    logger.info("WebSocket connected")
    active_connections.add(ws)
    try:
        while True:
            # Receive message from client
            message = ws.receive()
            # Process message if needed
    except Exception as e:
        logger.error(f"WebSocket disconnected: {e}")
    finally:
        if ws in active_connections:
            active_connections.remove(ws)

def render_from_folder(folder, filename):
    return render_template(f'{folder}/{filename}')

# Flask routes
@app.route('/')
def home():
    return render_from_folder('homepage', 'main.html')

@app.route('/game/tenor')
def web1():
    return render_from_folder('games/Tenor', 'main.html')

@app.route('/game/limbo')
def limbo():
    return render_from_folder('games/limbo', 'main.html')

@app.route('/account')
def web3():
    return render_from_folder('homepage', 'LoginRegister.html')

@app.route('/TenorData')
def SendTenorData():
    return render_from_folder('homepage', 'LoginRegister.html')



@app.route('/Main1.css')
def serve_css():
    css_folder = os.path.join(app.static_folder)
    return send_from_directory(css_folder, 'Main1.css', mimetype='text/css')

@app.route('/TenorLastMultiply')
def GetTenorLastMultiply():
    with open("C:\\Users\\isakm\\OneDrive\\Desktop\\ArcCas\\Server\\dataManagement\\GameData\\TenorData.json","r") as dat:
        TenorLastMultiply = json.load(dat)
        return jsonify(TenorLastMultiply["crashHistory"])

# Secure music file serving
@app.route('/music/<path:filename>')
def serve_music(filename):
    # Sanitize filename to prevent path traversal
    safe_filename = os.path.basename(filename)
    music_folder = os.path.join(app.static_folder, 'Audio')
    return send_from_directory(music_folder, safe_filename)


@app.route('/play/tenor', methods=['POST'])
@token_required
def playTenor(current_user):
    global TenorTotalBet
    try:
        # Check if game is in waiting state
        game_status = game_state["GameStatus"][0]["Status"].split()
        if game_status[0] != "Waiting":
            return jsonify({
                "Status": "Failed",
                "Msg": "You cannot bet while the game is in progress"
            }), 400
        
        # Validate bet amount
        bet_data = request.get_json()
        if not bet_data:
            return jsonify({"Status": "Failed", "Msg": "bet Not Valid"}), 400
            
        is_valid, bet_result = validate_bet(bet_data.get("bet", 0))
        if not is_valid:
            return jsonify({"Status": "Failed", "Msg": bet_result}), 400
        
        bet = bet_result
        
        
        # Get user data path
        player_data_path = os.path.join(BASE_DIR, 'Server', 'dataManagement', "playerData", "userdat.json")
        player_list_path = os.path.join(BASE_DIR, 'Server', 'dataManagement', "playerData", "playerList.json")
        
        # Load user data
        with open(player_data_path, "r") as file:
            data = json.load(file)
        
        # Find user
        user = None
        for u in data["users"]:
            if u["username"] == current_user:
                user = u
                break
                
        if not user:
            return jsonify({"Status": "Failed", "Msg": "User not found"}), 404
        
        # Check if user has enough balance BEFORE deducting
        if int(user['Balance']) < bet:
            print("Infucent Balance")
            return jsonify({
                "Status": "Failed",
                "Msg": "Insufficient Balance"
            }), 400
            
        # Load player list
        try:
            with open(player_list_path, "r") as pl_file:
                player_list = json.load(pl_file)
        except FileNotFoundError:
            player_list = {"PlayerList": []}
        
        # Check if user already placed a bet
        for player in player_list["PlayerList"]:
            if player["name"]["username"] == current_user:
                return jsonify({
                    "Status": "Failed",
                    "Msg": "You can't bet twice"
                }), 409
        
        # Deduct bet from balance
        user['Balance'] -= bet
        TenorTotalBet += bet
        
        # Add player to player list
        new_player = {
            "name": user,
            "bet": bet
        }
        player_list["PlayerList"].append(new_player)
        
        # Save updated data
        safe_write_json(data, player_data_path)
        safe_write_json(player_list, player_list_path)

        return jsonify({
            "Status": "Success",
            "Balance": user['Balance']
        }), 200
            
    except Exception as e:
        logger.error(f"Error in play/tenor: {e}")
        traceback.print_exc()
        return jsonify({"Status": "Failed", "Msg": "Server error"}), 500

@app.route('/cashout/tenor', methods=['POST'])
@token_required
def CashoutTenor(current_user):
    global TenorTotalBet
    global Temp_TenorMultiplyCashout
    global TotalPlayerCashoutTenor
    try:
        # Get current multiply value
        current_multiply = float(game_state["GameStatus"][0]["Multiply"])
        # Check if game is in playing state
        if "Playing" not in game_state["GameStatus"][0]["Status"]:
            return jsonify({
                "Status": "Failed", 
                "Msg": "You can only cash out during an active game"
            }), 400
        # Get file paths
        player_data_path = os.path.join(BASE_DIR, 'Server', 'dataManagement', "playerData", "userdat.json")
        player_list_path = "C:\\Users\\isakm\\OneDrive\\Desktop\\ArcCas\\Server\\dataManagement\\playerData\\playerList.json"
        # Load user data
        with open(player_data_path, "r") as file:
            data = json.load(file)
        # Find user
        user = None
        for u in data["users"]:
            if u["username"] == current_user:
                user = u
                break
        if not user:
            return jsonify({"Status": "Failed", "Msg": "User not found"}), 404
        # Load player list
        try:
            with open(player_list_path, "r") as pl_file:
                player_list = json.load(pl_file)
        except FileNotFoundError:
            return jsonify({"Status": "Failed", "Msg": "No active bets"}), 400
        
        # Find player in list and process cashout
        player_index = None
        player_bet = 0
        
        for i, player in enumerate(player_list["PlayerList"]):
            if player["name"]["username"] == current_user:
                player_index = i
                player_bet = player["bet"]
                break
        if player_index is None:
            return jsonify({"Status": "Failed", "Msg": "No active bet found"}), 400
        # Calculate winnings
        winnings = int(player_bet * current_multiply)
        # Update user balance
        user['Balance'] += winnings
        TenorTotalBet -= winnings
        
        # Remove player from player list
        # Save updated data
        safe_write_json(data, player_data_path)
        safe_write_json(player_list, player_list_path)
        Temp_TenorMultiplyCashout.append(current_multiply)
        TotalPlayerCashoutTenor +=1

        return jsonify({
            "Status": "Success",
            "Balance": user['Balance'],
            "Winnings": winnings,
            "currentMultiply": current_multiply
        }), 200
        
    except Exception as e:
        logger.error(f"Error in cashout/tenor: {e}")
        traceback.print_exc()
        return jsonify({"Status": "Failed", "Msg": "Server error"}), 500



@app.route('/halfcashout/tenor', methods=['POST'])
@token_required
def halfcashoutTenor(current_user):
    try:
        # Get current multiply value
        current_multiply = float(game_state["GameStatus"][0]["Multiply"])
        # Check if game is in playing state
        if "Playing" not in game_state["GameStatus"][0]["Status"]:
            return jsonify({
                "Status": "Failed", 
                "Msg": "You can only cash out during an active game"
            }), 400
        # Get file paths
        player_data_path = os.path.join(BASE_DIR, 'Server', 'dataManagement', "playerData", "userdat.json")
        player_list_path = "C:\\Users\\isakm\\OneDrive\\Desktop\\ArcCas\\Server\\dataManagement\\playerData\\playerList.json"
        # Load user data
        with open(player_data_path, "r") as file:
            data = json.load(file)
        # Find user
        user = None
        for u in data["users"]:
            if u["username"] == current_user:
                user = u
                break
        if not user:
            return jsonify({"Status": "Failed", "Msg": "User not found"}), 404
        # Load player list
        try:
            with open(player_list_path, "r") as pl_file:
                player_list = json.load(pl_file)
        except FileNotFoundError:
            return jsonify({"Status": "Failed", "Msg": "No active bets"}), 400
        
        # Find player in list and process cashout
        player_index = None
        player_bet = 0
        
        for i, player in enumerate(player_list["PlayerList"]):
            if player["name"]["username"] == current_user:
                player_index = i
                player_bet = player["bet"]
                break
        if player_index is None:
            return jsonify({"Status": "Failed", "Msg": "No active bet found"}), 400
        # Calculate half of the original bet
        half_bet = player_bet / 2
        
        # Calculate winnings based on half the bet
        winnings = int(half_bet * current_multiply)
        
        # Update user balance
        user['Balance'] += winnings
        
        # Update player's bet in the player list (half of the original bet remains in play)
        player_list["PlayerList"][player_index]["bet"] = half_bet
        
        # Save updated data
        safe_write_json(data, player_data_path)
        safe_write_json(player_list, player_list_path)
        return jsonify({
            "Status": "Success",
            "Balance": user['Balance'],
            "Winnings": winnings,
            "currentMultiply": current_multiply
        }), 200
        
    except Exception as e:
        logger.error(f"Error in cashout/tenor: {e}")
        traceback.print_exc()
        return jsonify({"Status": "Failed", "Msg": "Server error"}), 500

@app.route('/login', methods=['POST'])
def login():
    try:
        # Get login data
        data = request.get_json()
        if not data:
            return jsonify({"message": "Invalid request data"}), 400
            
        username = data.get("username")
        password = data.get("password")
        
        if not username or not password:
            return jsonify({"message": "Username and password are required"}), 400
            
        # Load user data
        user_data_path = os.path.join(BASE_DIR, 'Server', 'dataManagement', "playerData", "userdat.json")
        with open(user_data_path, "r") as file:
            data = json.load(file)
        
        # Find and authenticate user
        for user in data["users"]:
            if user["username"] == username:
                # Check if password is stored as hash or plaintext (for backward compatibility)
                if "password_hash" in user:
                    # Check password hash
                    if not check_password_hash(user["password_hash"], password):
                        return jsonify({"message": "Invalid credentials"}), 401
                else:
                    # Legacy plaintext check - update to hash after successful login
                    if user["password"] != password:
                        return jsonify({"message": "Invalid credentials"}), 401
                    
                    # Update to password hash
                    user["password_hash"] = generate_password_hash(password)
                    # Optionally keep plaintext for backwards compatibility or remove it
                    # del user["password"]
                    safe_write_json(data, user_data_path)
                
                # Create JWT token
                payload = {
                    "username": username,
                    "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
                }
                token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
                
                return jsonify({"token": token}), 200
                
        return jsonify({"message": "User not found"}), 401
        
    except Exception as e:
        logger.error(f"Error in login: {e}")
        return jsonify({"message": "Server error"}), 500

@app.route('/register', methods=['POST'])
def register():
    try:
        # Get registration data
        data = request.get_json()
        if not data:
            return jsonify({"message": "Invalid request data"}), 400
            
        username = data.get("username")
        password = data.get("password")
        
        if not username or not password:
            return jsonify({"message": "Username and password are required"}), 400
            
        # Validate username and password
        if len(username) < 3:
            return jsonify({"message": "Username must be at least 3 characters"}), 400
            
        if len(password) < 6:
            return jsonify({"message": "Password must be at least 6 characters"}), 400
            
        # Load user data
        user_data_path = os.path.join(BASE_DIR, 'Server', 'dataManagement', "playerData", "userdat.json")
        with open(user_data_path, "r") as file:
            data = json.load(file)
            
        # Check if username already exists
        for user in data["users"]:
            if user["username"] == username:
                return jsonify({"message": "Username already exists"}), 409
                
        # Create new user with hashed password
        new_user = {
            "username": username,
            "password": password,  # Keep for backward compatibility
            "password_hash": generate_password_hash(password),
            "Balance": 1000  # Initial balance
        }
        
        # Add user to data
        data["users"].append(new_user)
        
        # Save updated data
        safe_write_json(data, user_data_path)
        
        return jsonify({"message": "Registration successful"}), 201
        
    except Exception as e:
        logger.error(f"Error in register: {e}")
        traceback.print_exc()
        return jsonify({"message": "Server error"}), 500

@app.route('/dashboard', methods=['GET'])
@token_required
def dashboard(current_user):
    try:
        # Load user data
        user_data_path = os.path.join(BASE_DIR, 'Server', 'dataManagement', "playerData", "userdat.json")
        with open(user_data_path, "r") as file:
            data = json.load(file)
        
        # Find user
        for user in data["users"]:
            if user["username"] == current_user:
                return jsonify({
                    "Status": "Success",
                    "Username": current_user,
                    "Balance": user['Balance']
                })
                
        return jsonify({"message": "User not found"}), 404
        
    except Exception as e:
        logger.error(f"Error in dashboard: {e}")
        traceback.print_exc()
        return jsonify({"message": "Server error"}), 500


# Add security headers to all responses with relaxed CSP
@app.after_request
def add_security_headers(response):
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; img-src 'self' data:; media-src 'self' https://assets.mixkit.co; connect-src 'self'"
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

# Initialize and run game loop in background
def start_game_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(game_loop())
    loop.run_forever()

if __name__ == '__main__':
    # Ensure data directories exist
    ensure_data_dirs()
    
    # Start game loop in separate thread
    game_thread = threading.Thread(target=start_game_loop, daemon=True)
    game_thread.start()
    
    # Run Flask server in production mode
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)