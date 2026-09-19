"""
ROLEX AI — Mathematics Engine
Scientific calculator, geometry, unit conversion, electrical calculations, RPM.
All local, offline, with controlled error handling.
"""
from __future__ import annotations

import ast
import math
import operator
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from modules.logger import get_logger

log = get_logger("rolex.math")


class MathError(Exception):
    """Controlled math error surfaced to the user."""


# ---------------------------------------------------------------------------
# Safe expression evaluator (AST-based, no eval of arbitrary code)
# ---------------------------------------------------------------------------
_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_ALLOWED_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}

_SAFE_FUNCS: Dict[str, object] = {
    "sqrt": math.sqrt, "cbrt": lambda x: math.copysign(abs(x) ** (1 / 3), x),
    "abs": abs, "round": round, "floor": math.floor, "ceil": math.ceil,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh,
    "log": math.log, "log10": math.log10, "log2": math.log2,
    "exp": math.exp, "factorial": math.factorial, "degrees": math.degrees,
    "radians": math.radians, "hypot": math.hypot, "pow": pow, "min": min, "max": max,
}
_SAFE_CONSTS = {"pi": math.pi, "e": math.e, "tau": math.tau, "inf": math.inf}


def _eval_node(node):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise MathError("Only numeric constants are allowed.")
    if isinstance(node, ast.BinOp):
        op = _ALLOWED_BINOPS.get(type(node.op))
        if op is None:
            raise MathError("Unsupported operator.")
        left, right = _eval_node(node.left), _eval_node(node.right)
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and right == 0:
            raise MathError("Division by zero is not allowed.")
        try:
            return op(left, right)
        except ZeroDivisionError:
            raise MathError("Division by zero is not allowed.")
        except (OverflowError, ValueError) as e:
            raise MathError(f"Math error: {e}")
    if isinstance(node, ast.UnaryOp):
        op = _ALLOWED_UNARY.get(type(node.op))
        if op is None:
            raise MathError("Unsupported unary operator.")
        return op(_eval_node(node.operand))
    if isinstance(node, ast.Name):
        if node.id in _SAFE_CONSTS:
            return _SAFE_CONSTS[node.id]
        raise MathError(f"Unknown symbol: {node.id}")
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _SAFE_FUNCS:
            raise MathError("Unsupported function.")
        if node.keywords:
            raise MathError("Keyword arguments are not supported.")
        args = [_eval_node(a) for a in node.args]
        try:
            return _SAFE_FUNCS[node.func.id](*args)
        except ZeroDivisionError:
            raise MathError("Division by zero is not allowed.")
        except (ValueError, OverflowError) as e:
            raise MathError(f"Math error: {e}")
    raise MathError("Invalid expression.")


def evaluate(expression: str) -> float:
    """Safely evaluate a mathematical expression string."""
    if expression is None or not str(expression).strip():
        raise MathError("Empty expression.")
    expr = str(expression).strip()
    # Normalize common symbols
    expr = (expr.replace("×", "*").replace("÷", "/").replace("^", "**")
            .replace("−", "-").replace(",", ""))
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        raise MathError("Invalid expression syntax.")
    result = _eval_node(tree)
    if isinstance(result, complex):
        raise MathError("Complex results are not supported.")
    return result


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------
def circle_area(radius: float) -> float:
    if radius < 0:
        raise MathError("Radius cannot be negative.")
    return math.pi * radius ** 2


def circle_circumference(radius: float) -> float:
    if radius < 0:
        raise MathError("Radius cannot be negative.")
    return 2 * math.pi * radius


def rectangle_area(length: float, width: float) -> float:
    if length < 0 or width < 0:
        raise MathError("Dimensions cannot be negative.")
    return length * width


def rectangle_perimeter(length: float, width: float) -> float:
    if length < 0 or width < 0:
        raise MathError("Dimensions cannot be negative.")
    return 2 * (length + width)


def triangle_area(base: float, height: float) -> float:
    if base < 0 or height < 0:
        raise MathError("Dimensions cannot be negative.")
    return 0.5 * base * height


def sphere_volume(radius: float) -> float:
    if radius < 0:
        raise MathError("Radius cannot be negative.")
    return (4 / 3) * math.pi * radius ** 3


def cylinder_volume(radius: float, height: float) -> float:
    if radius < 0 or height < 0:
        raise MathError("Dimensions cannot be negative.")
    return math.pi * radius ** 2 * height


def cone_volume(radius: float, height: float) -> float:
    if radius < 0 or height < 0:
        raise MathError("Dimensions cannot be negative.")
    return (1 / 3) * math.pi * radius ** 2 * height


def cube_volume(side: float) -> float:
    if side < 0:
        raise MathError("Side cannot be negative.")
    return side ** 3


# ---------------------------------------------------------------------------
# Unit conversion
# ---------------------------------------------------------------------------
_LENGTH = {  # to meters
    "mm": 0.001, "cm": 0.01, "m": 1.0, "km": 1000.0,
    "in": 0.0254, "inch": 0.0254, "inches": 0.0254, "ft": 0.3048, "foot": 0.3048,
    "feet": 0.3048, "yd": 0.9144, "yard": 0.9144, "yards": 0.9144,
    "mile": 1609.344, "miles": 1609.344, "mi": 1609.344,
}
_WEIGHT = {  # to kilograms
    "mg": 1e-6, "g": 0.001, "kg": 1.0, "tonne": 1000.0, "t": 1000.0,
    "oz": 0.0283495, "ounce": 0.0283495, "ounces": 0.0283495,
    "lb": 0.453592, "lbs": 0.453592, "pound": 0.453592, "pounds": 0.453592,
}
_TIME = {  # to seconds
    "ms": 0.001, "s": 1.0, "sec": 1.0, "secs": 1.0, "second": 1.0, "seconds": 1.0,
    "min": 60.0, "minute": 60.0, "minutes": 60.0,
    "h": 3600.0, "hr": 3600.0, "hour": 3600.0, "hours": 3600.0,
    "day": 86400.0, "days": 86400.0, "week": 604800.0, "weeks": 604800.0,
}
_SPEED = {  # to m/s
    "m/s": 1.0, "km/h": 1 / 3.6, "kph": 1 / 3.6, "mph": 0.44704, "knot": 0.514444,
}
_AREA = {  # to m^2
    "mm2": 1e-6, "cm2": 1e-4, "m2": 1.0, "km2": 1e6,
    "in2": 0.00064516, "ft2": 0.092903, "acre": 4046.8564224, "hectare": 10000.0,
}
_VOLUME = {  # to liters
    "ml": 0.001, "l": 1.0, "litre": 1.0, "liter": 1.0, "litres": 1.0, "liters": 1.0,
    "m3": 1000.0, "gal": 3.785411784, "gallon": 3.785411784, "gallons": 3.785411784,
    "cup": 0.236588, "cups": 0.236588,
}
_DATA = {  # to bytes
    "b": 1.0, "kb": 1024.0, "mb": 1024.0 ** 2, "gb": 1024.0 ** 3, "tb": 1024.0 ** 4,
}

_UNIT_TABLES = {
    "length": _LENGTH, "weight": _WEIGHT, "mass": _WEIGHT, "time": _TIME,
    "speed": _SPEED, "area": _AREA, "volume": _VOLUME, "data": _DATA,
}


def convert_units(value: float, from_unit: str, to_unit: str) -> float:
    from_unit = from_unit.strip().lower()
    to_unit = to_unit.strip().lower()

    # Temperature special-case
    temp_units = {"c", "celsius", "f", "fahrenheit", "k", "kelvin"}
    if from_unit in temp_units and to_unit in temp_units:
        return _convert_temperature(value, from_unit, to_unit)

    for name, table in _UNIT_TABLES.items():
        if from_unit in table and to_unit in table:
            return value * table[from_unit] / table[to_unit]
    raise MathError(f"Unsupported unit conversion: {from_unit} -> {to_unit}")


def _convert_temperature(value: float, frm: str, to: str) -> float:
    # Normalize to Celsius
    if frm in ("c", "celsius"):
        c = value
    elif frm in ("f", "fahrenheit"):
        c = (value - 32) * 5 / 9
    else:  # kelvin
        c = value - 273.15
    if c < -273.15:
        raise MathError("Temperature below absolute zero.")
    if to in ("c", "celsius"):
        return c
    if to in ("f", "fahrenheit"):
        return c * 9 / 5 + 32
    return c + 273.15


# ---------------------------------------------------------------------------
# Electrical calculations
# ---------------------------------------------------------------------------
def ohms_law(voltage: Optional[float] = None, current: Optional[float] = None,
             resistance: Optional[float] = None) -> Dict[str, float]:
    """Solve Ohm's law V = I * R given any two of the three values."""
    provided = [v for v in (voltage, current, resistance) if v is not None]
    if len(provided) < 2:
        raise MathError("Provide at least two of voltage, current, resistance.")
    if voltage is None:
        voltage = current * resistance
    elif current is None:
        if resistance == 0:
            raise MathError("Resistance cannot be zero.")
        current = voltage / resistance
    else:
        if current == 0:
            raise MathError("Current cannot be zero.")
        resistance = voltage / current
    return {"voltage": voltage, "current": current, "resistance": resistance}


def electrical_power(voltage: Optional[float] = None, current: Optional[float] = None,
                     resistance: Optional[float] = None) -> Dict[str, float]:
    """Compute power P = V*I = I^2*R = V^2/R."""
    if voltage is not None and current is not None:
        p = voltage * current
    elif current is not None and resistance is not None:
        p = current ** 2 * resistance
    elif voltage is not None and resistance is not None:
        if resistance == 0:
            raise MathError("Resistance cannot be zero.")
        p = voltage ** 2 / resistance
    else:
        raise MathError("Provide two of voltage, current, resistance.")
    return {"power_watts": p, "power_kw": p / 1000.0}


def energy_kwh(power_watts: float, hours: float) -> float:
    if power_watts < 0 or hours < 0:
        raise MathError("Power and hours must be non-negative.")
    return power_watts * hours / 1000.0


def resistor_series(*values: float) -> float:
    if not values:
        raise MathError("Provide at least one resistor value.")
    if any(v < 0 for v in values):
        raise MathError("Resistance cannot be negative.")
    return sum(values)


def resistor_parallel(*values: float) -> float:
    if not values:
        raise MathError("Provide at least one resistor value.")
    if any(v <= 0 for v in values):
        raise MathError("Parallel resistances must be positive.")
    return 1.0 / sum(1.0 / v for v in values)


def capacitor_energy(capacitance_farads: float, voltage: float) -> float:
    if capacitance_farads < 0:
        raise MathError("Capacitance cannot be negative.")
    return 0.5 * capacitance_farads * voltage ** 2


# ---------------------------------------------------------------------------
# RPM / rotational
# ---------------------------------------------------------------------------
def rpm_to_hz(rpm: float) -> float:
    return rpm / 60.0


def hz_to_rpm(hz: float) -> float:
    return hz * 60.0


def rpm_to_angular_velocity(rpm: float) -> float:
    """Return angular velocity in rad/s."""
    return rpm * 2 * math.pi / 60.0


def angular_velocity_to_rpm(omega: float) -> float:
    return omega * 60.0 / (2 * math.pi)


def linear_speed_from_rpm(rpm: float, radius: float) -> float:
    """Tangential speed (m/s) given rpm and radius (m)."""
    if radius < 0:
        raise MathError("Radius cannot be negative.")
    return rpm_to_angular_velocity(rpm) * radius


def gear_ratio(driven_teeth: float, driver_teeth: float) -> float:
    if driver_teeth == 0:
        raise MathError("Driver teeth cannot be zero.")
    return driven_teeth / driver_teeth


def output_rpm(input_rpm: float, driver_teeth: float, driven_teeth: float) -> float:
    if driven_teeth == 0:
        raise MathError("Driven teeth cannot be zero.")
    return input_rpm * driver_teeth / driven_teeth


# ---------------------------------------------------------------------------
# High-level natural-language math handler
# ---------------------------------------------------------------------------
def solve(expression: str, steps: bool = True) -> str:
    """
    Best-effort natural language math solver. Returns a human string.

    When ``steps`` is True, tries the step-by-step solver first (equations,
    statistics, finance, number theory) and falls back to plain evaluation.
    """
    expr = (expression or "").strip()
    if not expr:
        return "Math error: empty expression."

    if steps:
        try:
            from modules.math_solver import solve_auto, solve_arithmetic, SolveError
            auto = solve_auto(expr)
            if auto is not None:
                return auto.render()
            # Plain arithmetic with an explanation.
            if re.search(r"[0-9]", expr) and re.search(r"[+\-*/^%×÷]", expr):
                try:
                    sol = solve_arithmetic(expr)
                    return sol.render()
                except SolveError:
                    pass
        except Exception as e:
            log.debug("Step solver skipped: %s", e)

    try:
        result = evaluate(expr)
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return f"Result: {result}"
    except MathError as e:
        return f"Math error: {e}"
    except Exception as e:  # never crash
        log.error("Unexpected math error: %s", e)
        return "Math error: could not evaluate the expression."
