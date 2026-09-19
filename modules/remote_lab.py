"""
ROLEX AI — Remote Lab (WebSocket architecture)
A lightweight remote-control bridge that lets a paired client (phone, laptop,
browser) send commands to ROLEX and receive responses.

The server uses only the standard library (http.server + a minimal WebSocket
handshake/frame codec) so it runs on Android/Termux without extra deps. It is
disabled by default and must be explicitly started with a shared token.
"""
from __future__ import annotations

import base64
import hashlib
import json
import socket
import struct
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from modules.logger import get_logger

log = get_logger("rolex.remote_lab")

_WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def _accept_key(client_key: str) -> str:
    sha = hashlib.sha1((client_key + _WS_MAGIC).encode()).digest()
    return base64.b64encode(sha).decode()


def _encode_frame(payload: bytes, opcode: int = 0x1) -> bytes:
    header = bytearray()
    header.append(0x80 | opcode)
    length = len(payload)
    if length < 126:
        header.append(length)
    elif length < 65536:
        header.append(126)
        header += struct.pack(">H", length)
    else:
        header.append(127)
        header += struct.pack(">Q", length)
    return bytes(header) + payload


def _read_frame(conn: socket.socket) -> Optional[bytes]:
    try:
        b1 = conn.recv(1)
        if not b1:
            return None
        b2 = conn.recv(1)
        if not b2:
            return None
        length = b2[0] & 0x7F
        if length == 126:
            length = struct.unpack(">H", conn.recv(2))[0]
        elif length == 127:
            length = struct.unpack(">Q", conn.recv(8))[0]
        mask = conn.recv(4) if (b2[0] & 0x80) else b""
        data = b""
        while len(data) < length:
            chunk = conn.recv(length - len(data))
            if not chunk:
                break
            data += chunk
        if mask:
            data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        return data
    except Exception:
        return None


@dataclass
class RemoteSession:
    peer: str
    connected_at: float
    messages: int = 0


class RemoteLab:
    """Minimal WebSocket command bridge."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765,
                 token: Optional[str] = None):
        self.host = host
        self.port = port
        self.token = token
        self._server: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._handler: Optional[Callable[[str], str]] = None
        self.sessions: List[RemoteSession] = []

    def set_handler(self, fn: Callable[[str], str]) -> None:
        """Set the function that turns an incoming command into a reply."""
        self._handler = fn

    # -- lifecycle ----------------------------------------------------------
    def start(self) -> Dict:
        if self._running:
            return {"ok": True, "already_running": True, "port": self.port}
        try:
            self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server.bind((self.host, self.port))
            self._server.listen(5)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        log.info("Remote Lab listening on %s:%s", self.host, self.port)
        return {"ok": True, "port": self.port}

    def stop(self) -> Dict:
        self._running = False
        try:
            if self._server:
                self._server.close()
        except Exception:
            pass
        return {"ok": True}

    def is_running(self) -> bool:
        return self._running

    # -- server loop --------------------------------------------------------
    def _serve(self) -> None:
        while self._running and self._server:
            try:
                conn, addr = self._server.accept()
            except OSError:
                break
            threading.Thread(target=self._handle, args=(conn, addr), daemon=True).start()

    def _handle(self, conn: socket.socket, addr) -> None:
        try:
            conn.settimeout(10)
            request = conn.recv(4096).decode("utf-8", "ignore")
            headers = {}
            for line in request.split("\r\n")[1:]:
                if ":" in line:
                    k, v = line.split(":", 1)
                    headers[k.strip().lower()] = v.strip()
            key = headers.get("sec-websocket-key")
            if not key:
                conn.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
                conn.close()
                return
            # Token check (query string ?token=...).
            if self.token and f"token={self.token}" not in request.split("\r\n")[0]:
                conn.sendall(b"HTTP/1.1 401 Unauthorized\r\n\r\n")
                conn.close()
                return
            accept = _accept_key(key)
            handshake = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
            )
            conn.sendall(handshake.encode())
            session = RemoteSession(str(addr), time.time())
            self.sessions.append(session)
            log.info("Remote Lab client connected: %s", addr)
            while self._running:
                data = _read_frame(conn)
                if data is None:
                    break
                try:
                    msg = json.loads(data.decode("utf-8", "ignore"))
                except Exception:
                    msg = {"command": data.decode("utf-8", "ignore")}
                command = msg.get("command", "")
                reply = self._handler(command) if self._handler else "no handler"
                session.messages += 1
                conn.sendall(_encode_frame(json.dumps({"reply": reply}).encode()))
        except Exception as e:
            log.debug("Remote Lab connection error: %s", e)
        finally:
            try:
                conn.close()
            except Exception:
                pass


_lab: Optional[RemoteLab] = None


def get_remote_lab() -> RemoteLab:
    global _lab
    if _lab is None:
        _lab = RemoteLab()
    return _lab
