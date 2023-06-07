import unittest
from hmmc.math.fixedpoint import FloatFixedConverter


class TestMathFixedPoint(unittest.TestCase):
    def test_conversion_ok(self):
        res = 10
        bit_res = 1.0 / (2**res >> 1) * 4
        values_float = [-1.0, -0.75, -0.5, -1.0 * bit_res, 0.0, bit_res, 0.5, 0.75]
        converter = FloatFixedConverter(resolution=res, saturate=True)
        converter4 = FloatFixedConverter(resolution=res, amplitude=4.0, saturate=True)

        self.assertEqual(converter.convert_float([-1.0, 1.0, 0.0]),
            [2**(res - 1), 2**(res - 1) - 1, 0])

        self.assertEqual(converter4.convert_float(-4.0), 2**(res - 1))
        self.assertEqual(converter4.convert_float(4.0), 2**(res - 1) - 1)
        self.assertEqual(converter4.convert_float(0.0), 0)

        values_int = [converter.convert_float(val) for val in values_float]
        values_reconverted = [converter.convert_int(val) for val in values_int]
        self.assertEqual(values_float, values_reconverted)

    def test_conversion_error(self):
        converter = FloatFixedConverter(10)
        self.assertRaises(ValueError, converter.convert_float, -2.0)
        self.assertRaises(ValueError, converter.convert_float, 2.0)

        converter = FloatFixedConverter(10, signed=False)
        self.assertRaises(ValueError, converter.convert_float, -0.1)
