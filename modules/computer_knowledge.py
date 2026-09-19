"""
ROLEX AI — Computer Knowledge
A curated, offline knowledge base about computers, operating systems,
networking, security and troubleshooting.

Provides quick, accurate answers to common "how do I..." computer questions
without needing the internet.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from modules.logger import get_logger

log = get_logger("rolex.computer_knowledge")

_KB: Dict[str, Dict] = {
    "ram": {
        "title": "RAM (Random Access Memory)",
        "body": "RAM is fast, volatile memory that holds data the CPU is actively "
                "using. More RAM lets you run more apps at once. It is cleared "
                "when power is lost.",
    },
    "ssd": {
        "title": "SSD vs HDD",
        "body": "An SSD stores data on flash memory (fast, silent, shock-resistant). "
                "An HDD uses spinning magnetic disks (cheaper per GB, slower). "
                "SSDs dramatically speed up boot and app loading.",
    },
    "cpu": {
        "title": "CPU (Central Processing Unit)",
        "body": "The CPU executes instructions. Cores let it run tasks in parallel; "
                "clock speed (GHz) is how fast each core works. More cores help "
                "multitasking and heavy workloads.",
    },
    "ip address": {
        "title": "IP Address",
        "body": "An IP address identifies a device on a network. IPv4 looks like "
                "192.168.1.10; IPv6 is longer. Private ranges (192.168.x.x, "
                "10.x.x.x) are used inside home/office networks.",
    },
    "dns": {
        "title": "DNS (Domain Name System)",
        "body": "DNS translates human names (example.com) into IP addresses. "
                "If websites won't load but the internet works, try changing your "
                "DNS to 8.8.8.8 (Google) or 1.1.1.1 (Cloudflare).",
    },
    "vpn": {
        "title": "VPN (Virtual Private Network)",
        "body": "A VPN encrypts your traffic and routes it through a server, hiding "
                "your IP and protecting data on public Wi-Fi. It does not make you "
                "anonymous by itself.",
    },
    "firewall": {
        "title": "Firewall",
        "body": "A firewall filters network traffic based on rules, blocking "
                "unwanted connections while allowing trusted ones. Keep it enabled.",
    },
    "malware": {
        "title": "Malware",
        "body": "Malware is malicious software (viruses, trojans, ransomware, "
                "spyware). Protect yourself: keep systems updated, avoid unknown "
                "downloads, use reputable antivirus, and back up data.",
    },
    "backup": {
        "title": "Backups (3-2-1 rule)",
        "body": "Keep 3 copies of important data, on 2 different media, with 1 copy "
                "off-site. Test restores regularly — an untested backup is not a backup.",
    },
    "wifi slow": {
        "title": "Slow Wi-Fi troubleshooting",
        "body": "1) Move closer to the router. 2) Switch to 5 GHz if available. "
                "3) Restart the router. 4) Reduce interference (microwave, walls). "
                "5) Update router firmware. 6) Limit connected devices.",
    },
    "blue screen": {
        "title": "Blue Screen of Death (Windows)",
        "body": "A BSOD is a fatal system error. Note the stop code, then: update "
                "drivers, run memory/disk checks, check recent hardware/software "
                "changes, and boot into safe mode to isolate the cause.",
    },
    "bios": {
        "title": "BIOS / UEFI",
        "body": "BIOS/UEFI initialises hardware and boots the OS. UEFI is the modern "
                "replacement with faster boot, larger disk support and Secure Boot.",
    },
    "port": {
        "title": "Network Ports",
        "body": "Ports identify services on a host. Common: 80 (HTTP), 443 (HTTPS), "
                "22 (SSH), 25 (SMTP), 3306 (MySQL). 'Open port' = a service is "
                "listening; close unused ports for security.",
    },
    "https": {
        "title": "HTTPS / TLS",
        "body": "HTTPS encrypts web traffic using TLS. The padlock means the "
                "connection is encrypted and the certificate is valid. Never enter "
                "passwords on sites without HTTPS.",
    },
    "password": {
        "title": "Strong Passwords",
        "body": "Use long passphrases (12+ chars), unique per site, stored in a "
                "password manager, with two-factor authentication (2FA) enabled.",
    },
}


class ComputerKnowledge:
    def lookup(self, query: str) -> Dict:
        q = (query or "").lower().strip()
        if not q:
            return {"ok": False, "error": "Empty query."}
        # Exact / substring match first.
        for key, info in _KB.items():
            if key in q or q in key:
                return {"ok": True, "topic": key, **info}
        # Keyword overlap.
        words = set(q.split())
        best, best_score = None, 0
        for key, info in _KB.items():
            score = len(words & set(key.split()))
            if score > best_score:
                best, best_score = info, score
        if best:
            return {"ok": True, **best}
        return {"ok": False, "error": f"No computer knowledge found for '{query}'.",
                "topics": list(_KB.keys())}

    def topics(self) -> List[str]:
        return list(_KB.keys())


_ck: Optional[ComputerKnowledge] = None


def get_computer_knowledge() -> ComputerKnowledge:
    global _ck
    if _ck is None:
        _ck = ComputerKnowledge()
    return _ck
