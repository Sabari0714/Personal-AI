"""Unit tests for the math engine."""
import math
import unittest

from modules.math_engine import (
    evaluate, MathError, circle_area, circle_circumference, rectangle_area,
    triangle_area, sphere_volume, cylinder_volume, convert_units,
    ohms_law, electrical_power, energy_kwh, resistor_series, resistor_parallel,
    rpm_to_hz, hz_to_rpm, rpm_to_angular_velocity, linear_speed_from_rpm,
    gear_ratio, output_rpm, solve,
)


class TestBasicMath(unittest.TestCase):
    def test_addition(self):
        self.assertEqual(evaluate("2 + 3"), 5)

    def test_brackets(self):
        self.assertEqual(evaluate("(2 + 3) * 4"), 20)

    def test_multiplication_symbols(self):
        self.assertEqual(evaluate("25 × 4"), 100)

    def test_division(self):
        self.assertEqual(evaluate("10 / 4"), 2.5)

    def test_power(self):
        self.assertEqual(evaluate("2 ^ 10"), 1024)

    def test_sqrt(self):
        self.assertAlmostEqual(evaluate("sqrt(16)"), 4.0)

    def test_constants(self):
        self.assertAlmostEqual(evaluate("pi"), math.pi)

    def test_division_by_zero(self):
        with self.assertRaises(MathError):
            evaluate("5 / 0")

    def test_invalid_expression(self):
        with self.assertRaises(MathError):
            evaluate("2 +* 3")

    def test_empty(self):
        with self.assertRaises(MathError):
            evaluate("")

    def test_unsafe_code_blocked(self):
        with self.assertRaises(MathError):
            evaluate("__import__('os').system('ls')")


class TestGeometry(unittest.TestCase):
    def test_circle_area(self):
        self.assertAlmostEqual(circle_area(5), math.pi * 25)

    def test_circle_circumference(self):
        self.assertAlmostEqual(circle_circumference(5), 2 * math.pi * 5)

    def test_rectangle_area(self):
        self.assertEqual(rectangle_area(4, 5), 20)

    def test_triangle_area(self):
        self.assertEqual(triangle_area(10, 5), 25)

    def test_sphere_volume(self):
        self.assertAlmostEqual(sphere_volume(3), (4 / 3) * math.pi * 27)

    def test_cylinder_volume(self):
        self.assertAlmostEqual(cylinder_volume(2, 5), math.pi * 4 * 5)

    def test_negative_radius(self):
        with self.assertRaises(MathError):
            circle_area(-1)


class TestUnitConversion(unittest.TestCase):
    def test_length(self):
        self.assertAlmostEqual(convert_units(1, "km", "m"), 1000)

    def test_length_inches(self):
        self.assertAlmostEqual(convert_units(1, "in", "cm"), 2.54, places=2)

    def test_weight(self):
        self.assertAlmostEqual(convert_units(1, "kg", "g"), 1000)

    def test_temperature_c_to_f(self):
        self.assertAlmostEqual(convert_units(100, "c", "f"), 212)

    def test_temperature_f_to_c(self):
        self.assertAlmostEqual(convert_units(32, "f", "c"), 0)

    def test_temperature_kelvin(self):
        self.assertAlmostEqual(convert_units(0, "c", "k"), 273.15)

    def test_speed(self):
        self.assertAlmostEqual(convert_units(36, "km/h", "m/s"), 10, places=3)

    def test_unsupported(self):
        with self.assertRaises(MathError):
            convert_units(1, "banana", "apple")


class TestElectrical(unittest.TestCase):
    def test_ohms_law_voltage(self):
        r = ohms_law(current=2, resistance=5)
        self.assertEqual(r["voltage"], 10)

    def test_ohms_law_current(self):
        r = ohms_law(voltage=10, resistance=5)
        self.assertEqual(r["current"], 2)

    def test_ohms_law_resistance(self):
        r = ohms_law(voltage=10, current=2)
        self.assertEqual(r["resistance"], 5)

    def test_ohms_law_insufficient(self):
        with self.assertRaises(MathError):
            ohms_law(voltage=10)

    def test_power_vi(self):
        self.assertEqual(electrical_power(voltage=10, current=2)["power_watts"], 20)

    def test_power_i2r(self):
        self.assertEqual(electrical_power(current=2, resistance=5)["power_watts"], 20)

    def test_power_v2r(self):
        self.assertEqual(electrical_power(voltage=10, resistance=5)["power_watts"], 20)

    def test_energy(self):
        self.assertEqual(energy_kwh(1000, 2), 2.0)

    def test_resistor_series(self):
        self.assertEqual(resistor_series(10, 20, 30), 60)

    def test_resistor_parallel(self):
        self.assertAlmostEqual(resistor_parallel(10, 10), 5)


class TestRPM(unittest.TestCase):
    def test_rpm_to_hz(self):
        self.assertEqual(rpm_to_hz(60), 1)

    def test_hz_to_rpm(self):
        self.assertEqual(hz_to_rpm(1), 60)

    def test_angular_velocity(self):
        self.assertAlmostEqual(rpm_to_angular_velocity(60), 2 * math.pi)

    def test_linear_speed(self):
        self.assertAlmostEqual(linear_speed_from_rpm(60, 1), 2 * math.pi)

    def test_gear_ratio(self):
        self.assertEqual(gear_ratio(40, 20), 2)

    def test_output_rpm(self):
        self.assertEqual(output_rpm(100, 20, 40), 50)


class TestSolve(unittest.TestCase):
    def test_solve_ok(self):
        self.assertIn("Result", solve("2+2"))

    def test_solve_error(self):
        self.assertIn("error", solve("5/0").lower())


if __name__ == "__main__":
    unittest.main()
