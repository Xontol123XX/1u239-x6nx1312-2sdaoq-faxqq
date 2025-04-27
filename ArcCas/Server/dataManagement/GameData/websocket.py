import asyncio
import websockets
import json
import sys

async def connect_to_spaceman():
    uri = "ws://localhost:6789"  # Changed port to match your server
    while True:  # Persistent connection attempt
        try:
            print("Attempting to connect...")
            async with websockets.connect(uri) as websocket:
                print("Connected to Spaceman WebSocket server")
                
                while True:
                    try:
                        # Receive game state
                        message = await websocket.recv()
                        game_state = json.loads(message)
                        
                        # Print game state from the GameStatus list
                        game_status = game_state['GameStatus'][0]
                        print(f"Status: {game_status['Status']}, "
                              f"Multiply: {game_status['Multiply']}")
                        
                    except websockets.ConnectionClosed:
                        print("Connection to server closed")
                        break
        
        except Exception as e:
            print(f"Error connecting to server: {e}")
            await asyncio.sleep(2)  # Wait before retry

async def main():
    await connect_to_spaceman()

if __name__ == "__main__":
    asyncio.run(main())