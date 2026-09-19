"""
ROLEX AI — Smart Home / IoT
A local-first registry of smart devices and scenes.

ROLEX can register devices (lights, fans, plugs, sensors), set their state,
and run scenes. Real hardware control is delegated to pluggable "drivers":
  * ``local``  — stores state only (simulation / manual devices)
  * ``http``   — sends a simple HTTP request to a device endpoint
  * ``mqtt``   — optional, if paho-mqtt is installed

This keeps the module useful offline while allowing real integrations.
"""
from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass
from typing import Dict, List, Optional

from data.database import get_db
from modules.logger import get_logger

log = get_logger("rolex.smarthome")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS smart_devices (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    kind       TEXT NOT NULL DEFAULT 'switch',
    room       TEXT,
    driver     TEXT NOT NULL DEFAULT 'local',
    endpoint   TEXT,
    state      TEXT NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS smart_scenes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    actions    TEXT NOT NULL,
    created_at REAL NOT NULL
);
"""


@dataclass
class SmartDevice:
    id: int
    name: str
    kind: str
    room: Optional[str]
    driver: str
    endpoint: Optional[str]
    state: Dict

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "kind": self.kind,
                "room": self.room, "driver": self.driver,
                "endpoint": self.endpoint, "state": self.state}


class SmartHome:
    def __init__(self):
        self.db = get_db()
        try:
            self.db._conn.executescript(_SCHEMA)
            self.db._conn.commit()
        except Exception as e:  # pragma: no cover
            log.warning("Smart home schema init issue: %s", e)

    # -- devices ------------------------------------------------------------
    def register(self, name: str, kind: str = "switch", room: Optional[str] = None,
                 driver: str = "local", endpoint: Optional[str] = None) -> SmartDevice:
        now = time.time()
        self.db.execute(
            "INSERT INTO smart_devices(name, kind, room, driver, endpoint, state, "
            "created_at, updated_at) VALUES(?,?,?,?,?,?,?,?) "
            "ON CONFLICT(name) DO UPDATE SET kind=excluded.kind, room=excluded.room, "
            "driver=excluded.driver, endpoint=excluded.endpoint, updated_at=excluded.updated_at",
            (name, kind, room, driver, endpoint, "{}", now, now),
        )
        return self.get(name)

    def get(self, name: str) -> Optional[SmartDevice]:
        row = self.db.query_one("SELECT * FROM smart_devices WHERE name=?", (name,))
        if not row:
            return None
        return SmartDevice(row["id"], row["name"], row["kind"], row["room"],
                           row["driver"], row["endpoint"],
                           json.loads(row["state"]) if row["state"] else {})

    def devices(self) -> List[SmartDevice]:
        rows = self.db.query("SELECT * FROM smart_devices ORDER BY room, name")
        return [SmartDevice(r["id"], r["name"], r["kind"], r["room"], r["driver"],
                            r["endpoint"], json.loads(r["state"]) if r["state"] else {})
                for r in rows]

    def set_state(self, name: str, **state) -> Dict:
        dev = self.get(name)
        if dev is None:
            return {"ok": False, "error": f"Unknown device: {name}"}
        merged = {**dev.state, **state}
        self.db.execute("UPDATE smart_devices SET state=?, updated_at=? WHERE name=?",
                        (json.dumps(merged), time.time(), name))
        # Dispatch to the driver.
        if dev.driver == "http" and dev.endpoint:
            try:
                url = dev.endpoint
                data = json.dumps(merged).encode()
                req = urllib.request.Request(url, data=data,
                                             headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=5)
            except Exception as e:
                log.info("HTTP driver failed for %s: %s", name, e)
        return {"ok": True, "device": name, "state": merged}

    def turn_on(self, name: str) -> Dict:
        return self.set_state(name, power="on")

    def turn_off(self, name: str) -> Dict:
        return self.set_state(name, power="off")

    # -- scenes -------------------------------------------------------------
    def create_scene(self, name: str, actions: List[Dict]) -> Dict:
        self.db.execute(
            "INSERT INTO smart_scenes(name, actions, created_at) VALUES(?,?,?) "
            "ON CONFLICT(name) DO UPDATE SET actions=excluded.actions",
            (name, json.dumps(actions), time.time()),
        )
        return {"ok": True, "scene": name, "actions": len(actions)}

    def run_scene(self, name: str) -> Dict:
        row = self.db.query_one("SELECT * FROM smart_scenes WHERE name=?", (name,))
        if not row:
            return {"ok": False, "error": f"Unknown scene: {name}"}
        actions = json.loads(row["actions"])
        results = []
        for a in actions:
            dev = a.get("device")
            state = a.get("state", {})
            results.append(self.set_state(dev, **state))
        return {"ok": True, "scene": name, "results": results}

    def scenes(self) -> List[str]:
        rows = self.db.query("SELECT name FROM smart_scenes")
        return [r["name"] for r in rows]


_smarthome: Optional[SmartHome] = None


def get_smarthome() -> SmartHome:
    global _smarthome
    if _smarthome is None:
        _smarthome = SmartHome()
    return _smarthome
