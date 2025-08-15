#!/usr/bin/env python3
"""
Simple, robust WebSocket server for iOS clients.

Install:
    pip install websockets

Run:
    python websocket.py
"""

import asyncio
import json
from datetime import datetime
import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError


class WebSocketServer:
    def __init__(self, app_heartbeat=True, heartbeat_interval=20.0):
        self.clients: set[websockets.WebSocketServerProtocol] = set()
        self.frame_count = 0
        self.last_print_time = datetime.now()
        self.app_heartbeat = app_heartbeat
        self.heartbeat_interval = heartbeat_interval

    async def handle_client(self, websocket):
        """Register a client and handle its incoming messages."""
        print(f"Client connected from {websocket.remote_address}")
        self.clients.add(websocket)

        try:
            async for message in websocket:
                # Optional: parse to compute FPS / validate JSON
                self._bump_fps()
                # If you need to inspect the payload:
                # self._safe_parse_json(message)

                await self.broadcast(message)
                # For visibility (truncate long frames):
                log_sample = message if isinstance(message, str) else f"<{len(message)} bytes>"
                if isinstance(log_sample, str) and len(log_sample) > 120:
                    log_sample = log_sample[:120] + "…"
                print(f"Received message from {websocket.remote_address}: {log_sample}")

        except (ConnectionClosedOK, ConnectionClosedError) as e:
            print(f"Client {websocket.remote_address} disconnected: {e}")
        except Exception as e:
            print(f"Error with client {websocket.remote_address}: {e}")
        finally:
            self.clients.discard(websocket)
            print(f"Remaining clients: {len(self.clients)}")

    async def broadcast(self, message):
        """Broadcast a message to all currently connected clients."""
        if not self.clients:
            return

        to_remove = set()
        # Send concurrently, collect failures
        tasks = []
        for client in self.clients:
            tasks.append(asyncio.create_task(self._safe_send(client, message, to_remove)))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Drop any clients that errored during send
        if to_remove:
            self.clients -= to_remove
            print(f"Removed {len(to_remove)} disconnected clients during broadcast")

    async def _safe_send(self, client, message, to_remove: set):
        try:
            await client.send(message)
        except Exception as e:
            print(f"Send error to {client.remote_address}: {e}")
            to_remove.add(client)

    def _bump_fps(self):
        """Compute and log receive rate ~once per second."""
        self.frame_count += 1
        now = datetime.now()
        dt = (now - self.last_print_time).total_seconds()
        if dt >= 1.0:
            fps = self.frame_count / dt
            print(f"Receiving at {fps:.1f} Hz from all clients")
            self.frame_count = 0
            self.last_print_time = now

    def _safe_parse_json(self, message):
        """Optional: validate JSON and surface errors nicely."""
        if isinstance(message, (bytes, bytearray)):
            try:
                message = message.decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                print("Received non-UTF8 binary frame (skipping JSON parse).")
                return
        try:
            json.loads(message)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON received: {e}")

    async def app_heartbeat_task(self):
        """Optional app-level heartbeat (separate from WebSocket ping/pong)."""
        while True:
            try:
                if self.clients:
                    heartbeat_msg = json.dumps({
                        "type": "heartbeat",
                        "timestamp": datetime.now().isoformat(),
                        "client_count": len(self.clients),
                    })
                    await self.broadcast(heartbeat_msg)
                await asyncio.sleep(self.heartbeat_interval)
            except Exception as e:
                print(f"Error in heartbeat task: {e}")
                await asyncio.sleep(5)


async def main():
    server = WebSocketServer(app_heartbeat=True, heartbeat_interval=20.0)

    print("Starting WebSocket server on multiple ports:")
    print("  - ws://localhost:3000")
    print("  - ws://localhost:3001")
    print("Waiting for client connections…")

    # Use built-in ping/pong; relax size/queue limits while debugging meshes.
    serve_kwargs = dict(
        ping_interval=20,   # server sends control ping every 20s
        ping_timeout=20,    # close if no pong within 20s
        max_size=None,      # allow large frames (meshes)
        max_queue=None,     # don't drop messages if slow consumer (debug)
    )

    # Start optional app-level heartbeat
    if server.app_heartbeat:
        asyncio.create_task(server.app_heartbeat_task())

    async with websockets.serve(server.handle_client, "0.0.0.0", 3000, **serve_kwargs), \
               websockets.serve(server.handle_client, "0.0.0.0", 3001, **serve_kwargs):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped.")