"""
ROLEX AI — Formula Library
==========================
A large, offline, searchable catalogue of mathematical, physical, financial
and engineering formulas. Each entry has a name, the formula, a description
and the variables it uses.

Used by the router to answer "what is the formula for ..." and by the math
engine to explain the steps behind a calculation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Formula:
    name: str
    expression: str
    description: str
    variables: str = ""
    category: str = "general"


FORMULAS: List[Formula] = [
    # --- Algebra ---
    Formula("Quadratic formula", "x = (-b ± √(b²-4ac)) / 2a",
            "Roots of ax² + bx + c = 0", "a, b, c", "algebra"),
    Formula("Discriminant", "Δ = b² - 4ac",
            "Determines the nature of quadratic roots", "a, b, c", "algebra"),
    Formula("Difference of squares", "a² - b² = (a+b)(a-b)",
            "Factorisation identity", "a, b", "algebra"),
    Formula("Binomial square", "(a+b)² = a² + 2ab + b²",
            "Perfect square expansion", "a, b", "algebra"),
    Formula("Arithmetic sequence nth term", "aₙ = a₁ + (n-1)d",
            "nth term of an arithmetic progression", "a₁, n, d", "algebra"),
    Formula("Geometric sequence nth term", "aₙ = a₁ · r^(n-1)",
            "nth term of a geometric progression", "a₁, n, r", "algebra"),
    Formula("Sum of arithmetic series", "Sₙ = n/2 · (2a₁ + (n-1)d)",
            "Sum of first n terms", "n, a₁, d", "algebra"),
    Formula("Logarithm product rule", "log(xy) = log x + log y",
            "Logarithm identity", "x, y", "algebra"),

    # --- Geometry ---
    Formula("Circle area", "A = πr²", "Area of a circle", "r", "geometry"),
    Formula("Circle circumference", "C = 2πr", "Circumference of a circle", "r", "geometry"),
    Formula("Triangle area", "A = ½ · b · h", "Area of a triangle", "b, h", "geometry"),
    Formula("Heron's formula", "A = √(s(s-a)(s-b)(s-c))",
            "Triangle area from sides; s = (a+b+c)/2", "a, b, c", "geometry"),
    Formula("Rectangle area", "A = l · w", "Area of a rectangle", "l, w", "geometry"),
    Formula("Trapezoid area", "A = ½(a+b)h", "Area of a trapezoid", "a, b, h", "geometry"),
    Formula("Sphere volume", "V = 4/3 πr³", "Volume of a sphere", "r", "geometry"),
    Formula("Sphere surface area", "A = 4πr²", "Surface area of a sphere", "r", "geometry"),
    Formula("Cylinder volume", "V = πr²h", "Volume of a cylinder", "r, h", "geometry"),
    Formula("Cone volume", "V = ⅓πr²h", "Volume of a cone", "r, h", "geometry"),
    Formula("Cube volume", "V = a³", "Volume of a cube", "a", "geometry"),
    Formula("Pythagoras theorem", "c² = a² + b²",
            "Right triangle hypotenuse", "a, b", "geometry"),
    Formula("Distance between points", "d = √((x₂-x₁)² + (y₂-y₁)²)",
            "Euclidean distance", "x₁, y₁, x₂, y₂", "geometry"),

    # --- Trigonometry ---
    Formula("Sine rule", "a/sin A = b/sin B = c/sin C",
            "Triangle side-angle relation", "a, b, c, A, B, C", "trigonometry"),
    Formula("Cosine rule", "c² = a² + b² - 2ab·cos C",
            "Triangle side from two sides and angle", "a, b, C", "trigonometry"),
    Formula("Pythagorean identity", "sin²θ + cos²θ = 1",
            "Fundamental trig identity", "θ", "trigonometry"),
    Formula("Double angle sine", "sin 2θ = 2 sin θ cos θ", "Double angle", "θ", "trigonometry"),

    # --- Physics ---
    Formula("Newton's second law", "F = m · a", "Force = mass × acceleration", "m, a", "physics"),
    Formula("Velocity", "v = u + at", "Final velocity", "u, a, t", "physics"),
    Formula("Displacement", "s = ut + ½at²", "Displacement under acceleration", "u, a, t", "physics"),
    Formula("Kinetic energy", "KE = ½mv²", "Kinetic energy", "m, v", "physics"),
    Formula("Potential energy", "PE = mgh", "Gravitational potential energy", "m, g, h", "physics"),
    Formula("Work", "W = F · d · cosθ", "Work done by a force", "F, d, θ", "physics"),
    Formula("Power", "P = W / t", "Power = work / time", "W, t", "physics"),
    Formula("Momentum", "p = m · v", "Linear momentum", "m, v", "physics"),
    Formula("Density", "ρ = m / V", "Density = mass / volume", "m, V", "physics"),
    Formula("Pressure", "P = F / A", "Pressure = force / area", "F, A", "physics"),
    Formula("Ohm's law", "V = I · R", "Voltage = current × resistance", "I, R", "physics"),
    Formula("Electrical power", "P = V · I = I²R = V²/R", "Electrical power", "V, I, R", "physics"),
    Formula("Wave speed", "v = f · λ", "Wave speed = frequency × wavelength", "f, λ", "physics"),
    Formula("Einstein mass-energy", "E = m c²", "Mass-energy equivalence", "m, c", "physics"),
    Formula("Gravitational force", "F = G·m₁m₂ / r²", "Newton's law of gravitation", "m₁, m₂, r", "physics"),

    # --- Finance ---
    Formula("Simple interest", "SI = P·R·T / 100", "Simple interest", "P, R, T", "finance"),
    Formula("Compound interest", "A = P(1 + R/(100n))^(nT)", "Compound amount", "P, R, n, T", "finance"),
    Formula("EMI", "EMI = P·r·(1+r)^n / ((1+r)^n - 1)",
            "Equated monthly instalment; r = annual rate/12/100", "P, r, n", "finance"),
    Formula("Profit percentage", "Profit% = (SP - CP)/CP × 100",
            "Profit as a percentage of cost", "SP, CP", "finance"),
    Formula("Discount", "Discount = MP - SP", "Marked price minus selling price", "MP, SP", "finance"),
    Formula("CAGR", "CAGR = (End/Start)^(1/n) - 1",
            "Compound annual growth rate", "End, Start, n", "finance"),
    Formula("Future value (SIP)", "FV = P·((1+r)^n - 1)/r × (1+r)",
            "Future value of a monthly SIP", "P, r, n", "finance"),
    Formula("Return on investment", "ROI = (Gain - Cost)/Cost × 100",
            "Return on investment", "Gain, Cost", "finance"),

    # --- Statistics ---
    Formula("Mean", "μ = Σx / n", "Arithmetic mean", "x, n", "statistics"),
    Formula("Variance", "σ² = Σ(x - μ)² / n", "Population variance", "x, μ, n", "statistics"),
    Formula("Standard deviation", "σ = √(Σ(x - μ)² / n)", "Population std deviation", "x, μ, n", "statistics"),
    Formula("Probability", "P(E) = favourable / total", "Classical probability", "E", "statistics"),
    Formula("Combination", "nCr = n! / (r!(n-r)!)", "Number of combinations", "n, r", "statistics"),
    Formula("Permutation", "nPr = n! / (n-r)!", "Number of permutations", "n, r", "statistics"),

    # --- Computer science ---
    Formula("Time complexity (binary search)", "O(log n)", "Binary search complexity", "n", "computing"),
    Formula("Time complexity (merge sort)", "O(n log n)", "Merge sort complexity", "n", "computing"),
    Formula("Storage size", "size = rows × columns × bytes_per_cell",
            "Estimate table storage", "rows, columns", "computing"),
]


def search(query: str, limit: int = 8) -> List[Formula]:
    """Keyword search across formula names, expressions and descriptions."""
    q = (query or "").lower().strip()
    if not q:
        return []
    terms = [t for t in q.split() if len(t) > 1]
    scored = []
    for f in FORMULAS:
        hay = f"{f.name} {f.expression} {f.description} {f.category}".lower()
        score = sum(1 for t in terms if t in hay)
        if score:
            scored.append((score, f))
    scored.sort(key=lambda x: -x[0])
    return [f for _, f in scored[:limit]]


def by_category(category: str) -> List[Formula]:
    c = (category or "").lower()
    return [f for f in FORMULAS if f.category == c]


def categories() -> List[str]:
    return sorted({f.category for f in FORMULAS})


def count() -> int:
    return len(FORMULAS)


def explain(query: str) -> Optional[str]:
    """Return a formatted explanation for the best matching formula."""
    matches = search(query, limit=3)
    if not matches:
        return None
    lines = []
    for f in matches:
        lines.append(f"• {f.name} [{f.category}]")
        lines.append(f"    {f.expression}")
        lines.append(f"    {f.description}")
        if f.variables:
            lines.append(f"    variables: {f.variables}")
    return "\n".join(lines)
