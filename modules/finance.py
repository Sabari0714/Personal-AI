"""
ROLEX AI — Finance, Business, Travel & Family
Offline financial calculators plus a personal ledger (spending, bills,
payments) and travel/family helpers.

Everything here works fully offline using standard formulas:
  * SIP / lump-sum mutual fund projections
  * EMI / loan amortisation
  * simple & compound interest
  * share-market P&L and break-even
  * daily spending tracker, monthly budget, bills
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from data.database import get_db
from modules.logger import get_logger

log = get_logger("rolex.finance")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS expenses (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    amount     REAL NOT NULL,
    category   TEXT NOT NULL DEFAULT 'general',
    note       TEXT,
    spent_at   REAL NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_expenses_spent ON expenses(spent_at);
CREATE TABLE IF NOT EXISTS bills (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    amount     REAL NOT NULL,
    due_date   REAL,
    recurring  TEXT,
    paid       INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
);
"""


# ---------------------------------------------------------------------------
# Pure calculators (no state)
# ---------------------------------------------------------------------------
def sip(monthly: float, annual_rate: float, years: float) -> Dict:
    """Future value of a monthly SIP (Systematic Investment Plan)."""
    r = annual_rate / 100.0 / 12.0
    n = int(years * 12)
    if r == 0:
        fv = monthly * n
    else:
        fv = monthly * (((1 + r) ** n - 1) / r) * (1 + r)
    invested = monthly * n
    return {"future_value": round(fv, 2), "invested": round(invested, 2),
            "gains": round(fv - invested, 2), "months": n}


def lumpsum(principal: float, annual_rate: float, years: float) -> Dict:
    """Future value of a one-time investment (compound growth)."""
    fv = principal * ((1 + annual_rate / 100.0) ** years)
    return {"future_value": round(fv, 2), "invested": round(principal, 2),
            "gains": round(fv - principal, 2)}


def emi(principal: float, annual_rate: float, years: float) -> Dict:
    """Equated Monthly Instalment for a loan."""
    r = annual_rate / 100.0 / 12.0
    n = int(years * 12)
    if r == 0:
        monthly = principal / n
    else:
        monthly = principal * r * ((1 + r) ** n) / (((1 + r) ** n) - 1)
    total = monthly * n
    return {"emi": round(monthly, 2), "months": n,
            "total_payment": round(total, 2),
            "total_interest": round(total - principal, 2)}


def amortisation(principal: float, annual_rate: float, years: float,
                 limit: int = 12) -> List[Dict]:
    """Return the first ``limit`` rows of a loan amortisation schedule."""
    r = annual_rate / 100.0 / 12.0
    n = int(years * 12)
    monthly = principal * r * ((1 + r) ** n) / (((1 + r) ** n) - 1) if r else principal / n
    balance = principal
    rows = []
    for i in range(1, min(limit, n) + 1):
        interest = balance * r
        principal_paid = monthly - interest
        balance -= principal_paid
        rows.append({"month": i, "emi": round(monthly, 2),
                     "interest": round(interest, 2),
                     "principal": round(principal_paid, 2),
                     "balance": round(max(balance, 0), 2)})
    return rows


def simple_interest(principal: float, rate: float, years: float) -> Dict:
    si = principal * rate * years / 100.0
    return {"interest": round(si, 2), "total": round(principal + si, 2)}


def compound_interest(principal: float, rate: float, years: float,
                      times_per_year: int = 1) -> Dict:
    amount = principal * ((1 + rate / 100.0 / times_per_year) ** (times_per_year * years))
    return {"interest": round(amount - principal, 2), "amount": round(amount, 2)}


def share_pnl(buy_price: float, sell_price: float, quantity: int,
              brokerage: float = 0.0) -> Dict:
    invested = buy_price * quantity
    proceeds = sell_price * quantity
    pnl = proceeds - invested - brokerage
    pct = (pnl / invested * 100.0) if invested else 0.0
    return {"invested": round(invested, 2), "proceeds": round(proceeds, 2),
            "pnl": round(pnl, 2), "pnl_percent": round(pct, 2),
            "profit": pnl >= 0}


def break_even(buy_price: float, quantity: int, brokerage: float = 0.0) -> Dict:
    invested = buy_price * quantity
    be = (invested + brokerage) / quantity if quantity else 0
    return {"break_even_price": round(be, 2)}


# ---------------------------------------------------------------------------
# Stateful ledger
# ---------------------------------------------------------------------------
@dataclass
class Expense:
    id: int
    amount: float
    category: str
    note: Optional[str]
    spent_at: float

    def to_dict(self) -> dict:
        return {"id": self.id, "amount": self.amount, "category": self.category,
                "note": self.note, "spent_at": self.spent_at}


class FinanceManager:
    def __init__(self):
        self.db = get_db()
        try:
            self.db._conn.executescript(_SCHEMA)
            self.db._conn.commit()
        except Exception as e:  # pragma: no cover
            log.warning("Finance schema init issue: %s", e)

    # -- expenses -----------------------------------------------------------
    def add_expense(self, amount: float, category: str = "general",
                    note: Optional[str] = None) -> Expense:
        now = time.time()
        cur = self.db.execute(
            "INSERT INTO expenses(amount, category, note, spent_at, created_at) "
            "VALUES(?,?,?,?,?)", (float(amount), category, note, now, now))
        return Expense(cur.lastrowid, float(amount), category, note, now)

    def expenses(self, limit: int = 100) -> List[Expense]:
        rows = self.db.query("SELECT * FROM expenses ORDER BY id DESC LIMIT ?", (limit,))
        return [Expense(r["id"], r["amount"], r["category"], r["note"], r["spent_at"])
                for r in rows]

    def spending_summary(self, days: int = 30) -> Dict:
        since = time.time() - days * 86400
        rows = self.db.query(
            "SELECT category, SUM(amount) AS total FROM expenses WHERE spent_at>=? "
            "GROUP BY category ORDER BY total DESC", (since,))
        total = sum(r["total"] for r in rows)
        return {"days": days, "total": round(total, 2),
                "by_category": {r["category"]: round(r["total"], 2) for r in rows}}

    def daily_spending(self, days: int = 7) -> List[Dict]:
        out = []
        for d in range(days):
            start = time.time() - (d + 1) * 86400
            end = time.time() - d * 86400
            row = self.db.query_one(
                "SELECT SUM(amount) AS total FROM expenses WHERE spent_at>=? AND spent_at<?",
                (start, end))
            out.append({"day_offset": d, "total": round(row["total"] or 0, 2)})
        return out

    # -- bills --------------------------------------------------------------
    def add_bill(self, name: str, amount: float, due_date: Optional[float] = None,
                 recurring: Optional[str] = None) -> int:
        cur = self.db.execute(
            "INSERT INTO bills(name, amount, due_date, recurring, paid, created_at) "
            "VALUES(?,?,?,?,?,?)", (name, float(amount), due_date, recurring, 0, time.time()))
        return cur.lastrowid

    def bills(self, unpaid_only: bool = False) -> List[Dict]:
        if unpaid_only:
            rows = self.db.query("SELECT * FROM bills WHERE paid=0 ORDER BY due_date")
        else:
            rows = self.db.query("SELECT * FROM bills ORDER BY due_date")
        return [dict(r) for r in rows]

    def pay_bill(self, bill_id: int) -> bool:
        cur = self.db.execute("UPDATE bills SET paid=1 WHERE id=?", (bill_id,))
        return cur.rowcount > 0

    def monthly_payment_total(self) -> float:
        row = self.db.query_one("SELECT SUM(amount) AS total FROM bills WHERE paid=0")
        return round(row["total"] or 0, 2)


_finance: Optional[FinanceManager] = None


def get_finance() -> FinanceManager:
    global _finance
    if _finance is None:
        _finance = FinanceManager()
    return _finance
