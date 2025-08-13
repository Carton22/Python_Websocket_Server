#!/usr/bin/env python3
"""
Simple WebSocket server.

Install dependencies:
    pip install websockets

Run:
    python websocket.py
"""

import asyncio
import websockets
import json
from datetime import datetime

class WebSocketServer:
    def __init__(self):
        self.clients = set()
        self.frame_count = 0
        self.last_print_time = datetime.now()
        
    async def handle_client(self, websocket):
        """Handle a client connection."""
        print(f"Client connected from {websocket.remote_address}")
        
        self.clients.add(websocket)
        
        try:
            async for message in websocket:
                await self.process_message(message, websocket)
        except websockets.exceptions.ConnectionClosed:
            print(f"Client disconnected from {websocket.remote_address}")
        finally:
            self.clients.remove(websocket)
    
    async def process_message(self, message, websocket):
        try:
            data = json.loads(message)
            self.frame_count += 1
                # Calculate and print FPS every second
            now = datetime.now()
            time_diff = (now - self.last_print_time).total_seconds()
            if time_diff >= 1.0:
                fps = self.frame_count / time_diff
                print(f"Receiving at {fps:.1f} Hz")
                self.frame_count = 0
                self.last_print_time = now

                
        except json.JSONDecodeError:
            print(f"Invalid JSON received: {message}")
        except Exception as e:
            print(f"Error processing message: {e}")
    
    async def broadcast(self, message):
        """Broadcast a message to all connected clients."""
        if self.clients:
            await asyncio.gather(
                *[client.send(message) for client in self.clients],
                return_exceptions=True
            )

async def main():
    """Start the WebSocket server on multiple ports."""   
    server = WebSocketServer()
    
    print("Starting WebSocket server on multiple ports:")
    print("  - ws://localhost:3000")
    print("  - ws://localhost:3001")
    print("Waiting for Vision Pro connections...")
    
    # Keep both servers alive
    async with websockets.serve(server.handle_client, "0.0.0.0", 3000), \
               websockets.serve(server.handle_client, "0.0.0.0", 3001):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped.")