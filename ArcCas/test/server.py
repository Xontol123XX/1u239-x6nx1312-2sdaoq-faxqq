import asyncio
import websockets

x = 0  # deklarasi di luar sebagai global

async def handler(websocket):
    print("Klien terhubung")
    global x
    try:
        while True:
            x += 1
            await asyncio.sleep(1)
            await websocket.send(str(x))  # pastikan dikirim sebagai string
    except Exception as e:
        print(f"Klien terputus: {e}")

async def main():
    async with websockets.serve(handler, "localhost", 6789):
        print("WebSocket Server jalan di ws://localhost:6789")
        await asyncio.Future()

asyncio.run(main())
