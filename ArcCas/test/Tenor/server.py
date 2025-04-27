import asyncio
import websockets
import random
import json
import tkinter as tk
from tkinter import StringVar
import threading

# Nilai awal untuk game state
game_state = {
    "GameStatus": [
        {
            "Status": "Playing",
            "Multiply": "1.00"
        }
    ]
}
timerInfo = 0

async def game_loop():
    global timerInfo
    while True:
        # Generate angka acak antara 1.00 sampai 1.5 (2 angka dibelakang koma)
        crash_point = round(random.uniform(1.00, 1.5), 2)
        print(f"Crash point baru: {crash_point}")
        
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
        
        # Crash
        game_state["GameStatus"][0]["Status"] = "Crash"
        print(f"Game crash pada multiply: {current_multiply}")
        await asyncio.sleep(3)  # Tunggu 3 detik
        
        # Waiting
        game_state["GameStatus"][0]["Status"] = "Waiting"
        print("Status:"+game_state["GameStatus"][0]["Status"])
        while timerInfo <= 4:
            timerInfo += 1
            game_state["GameStatus"][0]["Status"] = "Waiting" + " " + str(timerInfo)
            print("Status:" + game_state["GameStatus"][0]["Status"])
            await asyncio.sleep(1)  # Tunggu 1 detik
        timerInfo = 0

async def handler(websocket):
    print("Klien terhubung")
    try:
        # Kirim update game state ke klien secara terus menerus
        while True:
            game_status = game_state['GameStatus'][0]
            if str(game_state["GameStatus"][0]["Status"]) in "Playing":
                await websocket.send(str(game_status["Multiply"]))
            elif str(game_state["GameStatus"][0]["Status"]) in "Crash":
                await websocket.send(str(game_status["Multiply"] + "x"))
            else:
                await websocket.send(str(game_state["GameStatus"][0]["Status"]))
                
            await asyncio.sleep(0.01)  # Refresh rate 10x per detik
    except Exception as e:
        print(f"Klien terputus: {e}")

async def main():
    # Mulai game loop di background
    asyncio.create_task(game_loop())
    
    # Mulai WebSocket server
    async with websockets.serve(handler, "localhost", 6789):
        print("WebSocket Server jalan di ws://localhost:6789")
        await asyncio.Future()  # Berjalan selamanya

# Tkinter UI untuk menampilkan data JSON
class GameUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Game State UI")
        self.geometry("300x200")
        
        # Variabel untuk memperbarui data JSON
        self.status_var = StringVar(value=game_state["GameStatus"][0]["Status"])
        self.multiply_var = StringVar(value=game_state["GameStatus"][0]["Multiply"])
        
        # Label untuk menampilkan status
        self.status_label = tk.Label(self, text="Status: ", font=("Arial", 14))
        self.status_label.pack(pady=10)
        
        self.status_value = tk.Label(self, textvariable=self.status_var, font=("Arial", 14))
        self.status_value.pack(pady=5)
        
        # Label untuk menampilkan multiply
        self.multiply_label = tk.Label(self, text="Multiply: ", font=("Arial", 14))
        self.multiply_label.pack(pady=10)
        
        self.multiply_value = tk.Label(self, textvariable=self.multiply_var, font=("Arial", 14))
        self.multiply_value.pack(pady=5)
        
        # Update UI secara teratur untuk menampilkan data terbaru
        self.update_ui()

    def update_ui(self):
        self.status_var.set(game_state["GameStatus"][0]["Status"])
        self.multiply_var.set(game_state["GameStatus"][0]["Multiply"])
        self.after(100, self.update_ui)  # Update setiap 100 ms

def run_asyncio():
    asyncio.run(main())  # Menjalankan main() di thread background

# Main program
if __name__ == "__main__":
    # Jalankan asyncio di thread terpisah
    asyncio_thread = threading.Thread(target=run_asyncio)
    asyncio_thread.start()
    
    # Jalankan UI Tkinter
    app = GameUI()
    app.mainloop()
