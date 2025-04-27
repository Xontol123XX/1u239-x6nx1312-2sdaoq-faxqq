import time
import random
import json
import asyncio
import websockets

# Path ke file JSON
data_file = r"C:\\Users\\isakm\\OneDrive\\Desktop\\ArcCas\\Server\\dataManagement\\GameData\\Tenor.json"

clients = set()

def load_data():
    """Membaca data dari file JSON."""
    try:
        with open(data_file, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"GameStatus": [{"Status": "Waiting", "Multiply": "0.00"}]}

def save_data(status, multiply):
    """Menyimpan game state ke file JSON."""
    game_data = {"GameStatus": [{"Status": status, "Multiply": f"{multiply:.2f}"}]}
    with open(data_file, "w") as file:
        json.dump(game_data, file, indent=4)
    return game_data  # Return data agar bisa langsung dikirim ke klien

async def notify_clients(data):
    """Mengirim update ke semua klien yang terhubung."""
    if clients:
        message = json.dumps(data)
        await asyncio.gather(
            *[client.send(message) for client in clients],
            return_exceptions=True
        )

async def spaceman_simulation():
    """Simulasi game dan update data secara real-time."""


async def handle_client(websocket):
    """Menangani koneksi klien WebSocket."""
    clients.add(websocket)
    try:
        # Kirim data awal ke klien
        await websocket.send(json.dumps(load_data()))
        await websocket.wait_closed()  # Tunggu sampai klien disconnect
    finally:
        clients.remove(websocket)

async def main():
    server = await websockets.serve(handle_client, "localhost", 6789)
    print("WebSocket server running on ws://localhost:6789")
    
    # Jalankan simulasi secara async
    simulation_task = asyncio.create_task(spaceman_simulation())
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())