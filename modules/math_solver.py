"""
ROLEX AI — Step-by-Step Math Solver
===================================
Offline symbolic + numeric solving with human-readable steps.

Capabilities:
  * Arithmetic with step-by-step evaluation (order of operations)
  * Linear equations (ax + b = c) and simple quadratics (ax^2 + bx + c = 0)
  * Systems of two linear equations
  * Percentages, ratios, proportions
  * GCD / LCM, prime factorisation
  * Statistics (mean, median, mode, variance, std dev)
  * Interest (simple + compound), profit/loss, discount
  * Geometry (area / perimeter / volume) via the formula library

Everything is pure-Python and works fully offline.
"""
from __future__ import annotations

import ast
import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from modules.logger import get_logger

log = get_logger("rolex.math.solver")


class SolveError(Exception):
    """Controlled solver error surfaced to the user."""


@dataclass
class Solution:
    answer: str
    steps: List[str] = field(default_factory=list)
    kind: str = "arithmetic"
    data: Dict = field(default_factory=dict)

    def render(self) -> str:
        out = []
        if self.steps:
            out.append("Step-by-step:")
            for i, s in enumerate(self.steps, 1):
                out.append(f"  {i}. {s}")
        out.append(f"Answer: {self.answer}")
        return "\n".join(out)


# ---------------------------------------------------------------------------
# Safe numeric evaluation (mirrors math_engine's sandbox)
# ---------------------------------------------------------------------------
_SAFE_FUNCS = {
    "sqrt": math.sqrt, "abs": abs, "round": round, "floor": math.floor,
    "ceil": math.ceil, "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "log": math.log, "log10": math.log10, "log2": math.log2, "exp": math.exp,
    "factorial": math.factorial, "degrees": math.degrees, "radians": math.radians,
    "hypot": math.hypot, "pow": pow, "min": min, "max": max,
}
_SAFE_CONSTS = {"pi": math.pi, "e": math.e, "tau": math.tau}


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise SolveError("Only numeric constants are allowed.")
    if isinstance(node, ast.BinOp):
        import operator
        ops = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
               ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
               ast.Mod: operator.mod, ast.Pow: operator.pow}
        op = ops.get(type(node.op))
        if op is None:
            raise SolveError("Unsupported operator.")
        l, r = _eval(node.left), _eval(node.right)
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and r == 0:
            raise SolveError("Division by zero is not allowed.")
        return op(l, r)
    if isinstance(node, ast.UnaryOp):
        import operator
        ops = {ast.UAdd: operator.pos, ast.USub: operator.neg}
        op = ops.get(type(node.op))
        if op is None:
            raise SolveError("Unsupported unary operator.")
        return op(_eval(node.operand))
    if isinstance(node, ast.Name):
        if node.id in _SAFE_CONSTS:
            return _SAFE_CONSTS[node.id]
        raise SolveError(f"Unknown symbol: {node.id}")
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _SAFE_FUNCS:
            raise SolveError("Unsupported function.")
        return _SAFE_FUNCS[node.func.id](*[_eval(a) for a in node.args])
    raise SolveError("Invalid expression.")


def _fmt(x) -> str:
    if isinstance(x, float) and x.is_integer():
        return str(int(x))
    if isinstance(x, float):
        return f"{x:.6g}"
    return str(x)


# ---------------------------------------------------------------------------
# Arithmetic with steps
# ---------------------------------------------------------------------------
def solve_arithmetic(expr: str) -> Solution:
    e = (expr.replace("×", "*").replace("÷", "/").replace("^", "**")
         .replace("−", "-").replace(",", "").strip())
    try:
        tree = ast.parse(e, mode="eval")
    except SyntaxError:
        raise SolveError("Invalid expression syntax.")
    result = _eval(tree)
    steps = _explain_arithmetic(tree.body)
    return Solution(answer=_fmt(result), steps=steps, kind="arithmetic",
                    data={"expression": e, "value": result})


def _explain_arithmetic(node) -> List[str]:
    """Produce a light-weight order-of-operations explanation."""
    steps: List[str] = []
    try:
        # Show the normalised expression first.
        steps.append("Evaluate using BODMAS/PEMDAS order.")
        # Recursively describe nested operations.
        def walk(n):
            if isinstance(n, ast.BinOp):
                walk(n.left)
                walk(n.right)
                sym = {ast.Add: "+", ast.Sub: "-", ast.Mult: "×",
                       ast.Div: "÷", ast.FloorDiv: "//", ast.Mod: "%",
                       ast.Pow: "^"}.get(type(n.op), "?")
                try:
                    lv, rv = _eval(n.left), _eval(n.right)
                    steps.append(f"{_fmt(lv)} {sym} {_fmt(rv)} = {_fmt(_eval(n))}")
                except Exception:
                    pass
            elif isinstance(n, ast.UnaryOp):
                walk(n.operand)
        walk(node)
    except Exception:
        pass
    return steps


# ---------------------------------------------------------------------------
# Linear equations:  ax + b = c   (single variable x)
# ---------------------------------------------------------------------------
def solve_linear(equation: str) -> Solution:
    """Solve a one-variable linear equation like '2x + 3 = 11'."""
    if "=" not in equation:
        raise SolveError("An equation must contain '='.")
    lhs, rhs = equation.split("=", 1)
    # Move everything to the left: lhs - rhs = 0
    expr = f"({lhs}) - ({rhs})"
    a, b = _linear_coeffs(expr)
    if abs(a) < 1e-12:
        if abs(b) < 1e-12:
            return Solution("Infinite solutions (identity).", kind="linear")
        return Solution("No solution (contradiction).", kind="linear")
    x = -b / a
    steps = [
        f"Start: {equation.strip()}",
        f"Bring all terms to one side: {a:g}x + {b:g} = 0",
        f"Move constant: {a:g}x = {-b:g}",
        f"Divide by {a:g}: x = {-b:g} / {a:g}",
    ]
    return Solution(f"x = {_fmt(x)}", steps, kind="linear", data={"x": x})


def _linear_coeffs(expr: str) -> Tuple[float, float]:
    """Return (a, b) for a linear expression a*x + b using two sample points."""
    f0 = _eval_var(expr, 0.0)
    f1 = _eval_var(expr, 1.0)
    a = f1 - f0
    b = f0
    return a, b


def _normalize(expr: str) -> str:
    """Normalise unicode operators and insert explicit multiplication."""
    e = (expr.replace("×", "*").replace("÷", "/").replace("^", "**")
         .replace("−", "-").replace("–", "-").replace(",", ""))
    # Insert '*' for implicit multiplication: 2(  ->  2*(  and  )(  ->  )*(
    e = re.sub(r"(\d)\s*\(", r"\1*(", e)
    e = re.sub(r"\)\s*\(", ")*(", e)
    return e


def _subst_var(e: str, name: str, value: float) -> str:
    """Replace a standalone variable with its numeric value, keeping
    implicit multiplication valid (2x -> 2*(value))."""
    e = re.sub(rf"(?<=[\d\)])\s*{name}(?![A-Za-z_])", f"*({value})", e)
    e = re.sub(rf"(?<![A-Za-z_]){name}(?![A-Za-z_])", f"({value})", e)
    return e


def _eval_var(expr: str, x: float) -> float:
    """Evaluate an expression containing the variable x."""
    e = _normalize(expr)
    e = _subst_var(e, "x", x)
    tree = ast.parse(e, mode="eval")
    return _eval(tree)


# ---------------------------------------------------------------------------
# Quadratic equations:  ax^2 + bx + c = 0
# ---------------------------------------------------------------------------
def solve_quadratic(equation: str) -> Solution:
    if "=" not in equation:
        raise SolveError("An equation must contain '='.")
    lhs, rhs = equation.split("=", 1)
    expr = f"({lhs}) - ({rhs})"
    a, b, c = _quad_coeffs(expr)
    if abs(a) < 1e-12:
        return solve_linear(equation)
    disc = b * b - 4 * a * c
    steps = [
        f"Standard form: {a:g}x² + {b:g}x + {c:g} = 0",
        f"Discriminant Δ = b² − 4ac = ({b:g})² − 4·({a:g})·({c:g}) = {_fmt(disc)}",
    ]
    if disc > 0:
        r1 = (-b + math.sqrt(disc)) / (2 * a)
        r2 = (-b - math.sqrt(disc)) / (2 * a)
        steps.append(f"Δ > 0 → two real roots")
        steps.append(f"x = (−b ± √Δ) / 2a")
        steps.append(f"x₁ = {_fmt(r1)},  x₂ = {_fmt(r2)}")
        return Solution(f"x₁ = {_fmt(r1)}, x₂ = {_fmt(r2)}", steps, kind="quadratic",
                        data={"roots": [r1, r2], "discriminant": disc})
    if abs(disc) < 1e-12:
        r = -b / (2 * a)
        steps.append("Δ = 0 → one repeated real root")
        steps.append(f"x = −b / 2a = {_fmt(r)}")
        return Solution(f"x = {_fmt(r)} (double root)", steps, kind="quadratic",
                        data={"roots": [r], "discriminant": 0})
    real = -b / (2 * a)
    imag = math.sqrt(-disc) / (2 * a)
    steps.append("Δ < 0 → two complex roots")
    steps.append(f"x = {_fmt(real)} ± {_fmt(abs(imag))}i")
    return Solution(f"x = {_fmt(real)} ± {_fmt(abs(imag))}i", steps, kind="quadratic",
                    data={"real": real, "imag": imag, "discriminant": disc})


def _quad_coeffs(expr: str) -> Tuple[float, float, float]:
    f0 = _eval_var(expr, 0.0)
    f1 = _eval_var(expr, 1.0)
    fm1 = _eval_var(expr, -1.0)
    f2 = _eval_var(expr, 2.0)
    # Solve for a,b,c from samples: c=f0; a+b=f1-c; a-b=fm1-c
    c = f0
    a_plus_b = f1 - c
    a_minus_b = fm1 - c
    a = (a_plus_b + a_minus_b) / 2
    b = (a_plus_b - a_minus_b) / 2
    return a, b, c


# ---------------------------------------------------------------------------
# Systems of two linear equations
# ---------------------------------------------------------------------------
def solve_system(eq1: str, eq2: str) -> Solution:
    """Solve a 2x2 linear system using Cramer's rule."""
    a1, b1, c1 = _two_var_coeffs(eq1)
    a2, b2, c2 = _two_var_coeffs(eq2)
    det = a1 * b2 - a2 * b1
    if abs(det) < 1e-12:
        return Solution("No unique solution (lines are parallel or identical).",
                        kind="system")
    x = (c1 * b2 - c2 * b1) / det
    y = (a1 * c2 - a2 * c1) / det
    steps = [
        f"Equation 1: {a1:g}x + {b1:g}y = {c1:g}",
        f"Equation 2: {a2:g}x + {b2:g}y = {c2:g}",
        f"Determinant D = a₁b₂ − a₂b₁ = {_fmt(det)}",
        f"x = (c₁b₂ − c₂b₁) / D = {_fmt(x)}",
        f"y = (a₁c₂ − a₂c₁) / D = {_fmt(y)}",
    ]
    return Solution(f"x = {_fmt(x)}, y = {_fmt(y)}", steps, kind="system",
                    data={"x": x, "y": y})


def _two_var_coeffs(eq: str) -> Tuple[float, float, float]:
    """Parse 'ax + by = c' into (a, b, c)."""
    if "=" not in eq:
        raise SolveError("Each equation must contain '='.")
    lhs, rhs = eq.split("=", 1)
    expr = f"({lhs}) - ({rhs})"
    # Sample to recover coefficients of x and y.
    f00 = _eval_xy(expr, 0, 0)
    f10 = _eval_xy(expr, 1, 0)
    f01 = _eval_xy(expr, 0, 1)
    a = f10 - f00
    b = f01 - f00
    c = -f00
    return a, b, c


def _eval_xy(expr: str, x: float, y: float) -> float:
    e = _normalize(expr)
    e = _subst_var(e, "x", x)
    e = _subst_var(e, "y", y)
    return _eval(ast.parse(e, mode="eval"))


# ---------------------------------------------------------------------------
# Number theory
# ---------------------------------------------------------------------------
def gcd_lcm(a: int, b: int) -> Solution:
    g = math.gcd(a, b)
    l = abs(a * b) // g if g else 0
    steps = [f"GCD({a}, {b}) = {g}", f"LCM({a}, {b}) = |a·b| / GCD = {l}"]
    return Solution(f"GCD = {g}, LCM = {l}", steps, kind="number_theory",
                    data={"gcd": g, "lcm": l})


def prime_factors(n: int) -> Solution:
    if n < 2:
        return Solution(f"{n} has no prime factors.", kind="number_theory")
    original = n
    factors = []
    d = 2
    while d * d <= n:
        while n % d == 0:
            factors.append(d)
            n //= d
        d += 1
    if n > 1:
        factors.append(n)
    steps = [f"Factorise {original} by trial division."]
    steps.append(" × ".join(str(f) for f in factors) + f" = {original}")
    return Solution(" × ".join(str(f) for f in factors), steps,
                    kind="number_theory", data={"factors": factors})


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------
def statistics_summary(numbers: List[float]) -> Solution:
    if not numbers:
        raise SolveError("Provide at least one number.")
    n = len(numbers)
    s = sorted(numbers)
    mean = sum(numbers) / n
    median = (s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2)
    var = sum((x - mean) ** 2 for x in numbers) / n
    std = math.sqrt(var)
    # mode
    from collections import Counter
    counts = Counter(numbers)
    maxc = max(counts.values())
    modes = [k for k, v in counts.items() if v == maxc] if maxc > 1 else []
    steps = [
        f"Count n = {n}",
        f"Sum = {_fmt(sum(numbers))}",
        f"Mean = Sum / n = {_fmt(mean)}",
        f"Median (sorted middle) = {_fmt(median)}",
        f"Variance = Σ(x−μ)² / n = {_fmt(var)}",
        f"Standard deviation = √variance = {_fmt(std)}",
    ]
    if modes:
        steps.append("Mode = " + ", ".join(_fmt(m) for m in modes))
    return Solution(
        f"mean={_fmt(mean)}, median={_fmt(median)}, std={_fmt(std)}",
        steps, kind="statistics",
        data={"mean": mean, "median": median, "variance": var, "std": std,
              "modes": modes, "min": min(numbers), "max": max(numbers)})


# ---------------------------------------------------------------------------
# Finance helpers
# ---------------------------------------------------------------------------
def simple_interest(principal: float, rate: float, years: float) -> Solution:
    si = principal * rate * years / 100.0
    total = principal + si
    steps = [
        f"Simple Interest = P·R·T / 100",
        f"= {principal:g} × {rate:g} × {years:g} / 100",
        f"Interest = {_fmt(si)}",
        f"Total amount = P + SI = {_fmt(total)}",
    ]
    return Solution(f"Interest = {_fmt(si)}, Total = {_fmt(total)}", steps,
                    kind="finance", data={"interest": si, "total": total})


def compound_interest(principal: float, rate: float, years: float,
                      n: int = 1) -> Solution:
    amount = principal * (1 + rate / (100.0 * n)) ** (n * years)
    ci = amount - principal
    steps = [
        f"Compound Interest = P(1 + R/(100n))^(nT) − P",
        f"= {principal:g}(1 + {rate:g}/(100·{n}))^({n}·{years:g})",
        f"Amount = {_fmt(amount)}",
        f"Interest = Amount − P = {_fmt(ci)}",
    ]
    return Solution(f"Interest = {_fmt(ci)}, Amount = {_fmt(amount)}", steps,
                    kind="finance", data={"interest": ci, "amount": amount})


def percentage(part: float, whole: float) -> Solution:
    if whole == 0:
        raise SolveError("Whole cannot be zero.")
    pct = part / whole * 100
    steps = [f"Percentage = (part / whole) × 100",
             f"= ({part:g} / {whole:g}) × 100 = {_fmt(pct)}%"]
    return Solution(f"{_fmt(pct)}%", steps, kind="percentage", data={"percent": pct})


def profit_loss(cost: float, selling: float) -> Solution:
    diff = selling - cost
    pct = (diff / cost * 100) if cost else 0
    if diff >= 0:
        steps = [f"Profit = SP − CP = {selling:g} − {cost:g} = {_fmt(diff)}",
                 f"Profit % = (Profit / CP) × 100 = {_fmt(pct)}%"]
        return Solution(f"Profit = {_fmt(diff)} ({_fmt(pct)}%)", steps,
                        kind="finance", data={"profit": diff, "percent": pct})
    steps = [f"Loss = CP − SP = {cost:g} − {selling:g} = {_fmt(-diff)}",
             f"Loss % = (Loss / CP) × 100 = {_fmt(-pct)}%"]
    return Solution(f"Loss = {_fmt(-diff)} ({_fmt(-pct)}%)", steps,
                    kind="finance", data={"loss": -diff, "percent": -pct})


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------
def solve_auto(text: str) -> Optional[Solution]:
    """
    Try to detect and solve a math problem from natural language.
    Returns None if it is not recognised as a solvable problem.
    """
    t = (text or "").strip()
    low = t.lower()

    # Statistics: "mean of 1,2,3"
    m = re.search(r"(mean|median|mode|average|std|standard deviation|variance)\s*(?:of)?\s*([\d\.,\s]+)", low)
    if m:
        nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", m.group(2))]
        if nums:
            return statistics_summary(nums)

    # GCD / LCM
    m = re.search(r"(gcd|lcm|hcf)\D*(\d+)\D+(\d+)", low)
    if m:
        return gcd_lcm(int(m.group(2)), int(m.group(3)))

    # Prime factors
    m = re.search(r"(prime factor|factorise|factorize)\D*(\d+)", low)
    if m:
        return prime_factors(int(m.group(2)))

    # Simple interest
    m = re.search(r"simple interest.*?(\d+(?:\.\d+)?)\D+(\d+(?:\.\d+)?)\D+(\d+(?:\.\d+)?)", low)
    if m:
        return simple_interest(float(m.group(1)), float(m.group(2)), float(m.group(3)))

    # Compound interest
    m = re.search(r"compound interest.*?(\d+(?:\.\d+)?)\D+(\d+(?:\.\d+)?)\D+(\d+(?:\.\d+)?)", low)
    if m:
        return compound_interest(float(m.group(1)), float(m.group(2)), float(m.group(3)))

    # Percentage: "what is 20% of 50"
    m = re.search(r"(\d+(?:\.\d+)?)\s*%\s*of\s*(\d+(?:\.\d+)?)", low)
    if m:
        part = float(m.group(1)) / 100 * float(m.group(2))
        return Solution(f"{_fmt(part)}", [f"{m.group(1)}% of {m.group(2)} = {m.group(1)}/100 × {m.group(2)} = {_fmt(part)}"],
                        kind="percentage", data={"value": part})

    # Profit / loss
    m = re.search(r"(profit|loss).*?cost\D*(\d+(?:\.\d+)?)\D+.*?(?:sell\w*|sp)\D*(\d+(?:\.\d+)?)", low)
    if m:
        return profit_loss(float(m.group(2)), float(m.group(3)))

    # Quadratic
    if re.search(r"x\s*\^?\s*2|x²", low) and "=" in t:
        try:
            return solve_quadratic(t)
        except SolveError:
            pass

    # Linear equation with a variable
    if "=" in t and re.search(r"(?<![A-Za-z_])x(?![A-Za-z_])", t):
        try:
            return solve_linear(t)
        except SolveError:
            pass

    return None
