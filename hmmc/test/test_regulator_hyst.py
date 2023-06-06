import unittest
import inspect
import importlib.util
from math import pi, cos, atan
from hmmc.regulator.hyst import HystRegulatorBitSerial
from migen import run_simulation, passive, Module
from hmmc.output.deltasigma import DeltaSigma


# Constants
FCLK = 100E6
RESOLUTION = 10


# Signed [-1; 1[ to uint
def s2u(s_v):
    s_v = max(-0.9, min(0.9, (s_v + 1.0) * 0.5))
    return round(s_v * 2**RESOLUTION)


class Dut(Module):
    def __init__(self):
        self.submodules.reg = HystRegulatorBitSerial(RESOLUTION, 3)
        self.submodules.setpoint = DeltaSigma(RESOLUTION)
        self.submodules.adc_feedback = DeltaSigma(RESOLUTION)
        self.comb += [
            self.reg.feedback.eq(self.adc_feedback.output),
            self.reg.setpoint.eq(self.setpoint.output),
        ]


class TestRegulatorHyst(unittest.TestCase):
    @passive
    def lpf(self, dut):
        # Emulate the current in an inductor
        dut.I_int = 0.0
        I_l = 0.1
        R = 10
        L = 1e-3 * FCLK
        U = 400
        while True:
            u = U if (yield dut.reg.output) else -1 * U
            I_l += (u - R * I_l) / L
            dut.I_l = I_l
            yield dut.adc_feedback.input.eq(int(s2u(I_l)))
            yield
            dut.I_int += I_l

    def set_setpoint(self, dut, setpoint):
        yield
        yield dut.setpoint.input.eq(s2u(setpoint))

    def check_current(self, dut, setpoint, itegration_period, tolerance):
        itegration_period = int(itegration_period / 2)
        for _ in range(itegration_period):
            yield
        dut.I_int = 0.0  # reset the integrator so we only check the average final value
        for _ in range(itegration_period):
            yield
        current = dut.I_int / itegration_period
        self.assertGreaterEqual(setpoint + tolerance, current)
        self.assertGreaterEqual(current, setpoint - tolerance)

    def sine_setpoint(self, dut, fclk, amplitude, offset, frequency, sin_cycles):
        phase_speed = frequency / fclk * 2 * pi
        cycles = int(fclk * sin_cycles / frequency)
        for i in range(cycles):
            yield dut.setpoint.input.eq(int(s2u(amplitude * cos(phase_speed * i) + offset)))
            yield

    def check_fft(self, dut, fclk, amplitude, offset, frequency, sin_cycles, tolerance):
        from numpy.fft import fft
        import numpy as np

        cycles = int(fclk * sin_cycles / frequency)
        current = []
        for i in range(cycles):
            current += [dut.I_l]
            yield

        # Compute FFT
        freq = np.arange(cycles) * fclk / cycles

        # keep only the lower frequencies, the rest contains mostly discretization
        n_oneside = cycles // 2
        f_oneside = freq[:n_oneside]
        i_fft = fft(current)[:n_oneside]

        # For the DC component we should only take the real part. For the rest, we'll look at |fft|
        i_amplitudes = 2 / cycles * np.abs(i_fft)
        i_avg = i_fft.real[0] / cycles
        i_amplitudes[0] = i_avg
        # Find amplitude at setpoint frequency
        index_freq = np.where(f_oneside == frequency)[0][0]
        i_freq = i_amplitudes[index_freq]

        # calculate phase of the current at the setpoint frequency. Should be close to 0.
        phase_tolerance = 2 * pi * 20 / 360
        phase_freq = atan(i_fft.imag[index_freq] / i_fft.real[index_freq])
        self.assertGreaterEqual(abs(phase_freq) + phase_tolerance, i_freq)
        self.assertGreaterEqual(i_freq, abs(phase_freq) - phase_tolerance)

        self.assertEqual(index_freq, sin_cycles)
        self.assertGreaterEqual(amplitude + tolerance, i_freq)
        self.assertGreaterEqual(i_freq, amplitude - tolerance)
        self.assertGreaterEqual(offset + tolerance, i_avg)
        self.assertGreaterEqual(i_avg, offset - tolerance)

        try:
            import matplotlib.pyplot as plt
            plt.figure(figsize=(12, 10))
            plt.plot(current)
            plt.savefig("test_regulator_hyst_sin_current.png")
            plt.clf()

            plt.plot(f_oneside, np.abs(i_fft.real), 'b')
            # plt.plot(f_oneside, np.abs(i_fft.imag), 'r')
            plt.yscale('log')
            plt.xscale('log')
            plt.xlabel('Freq (Hz)')
            plt.ylabel('FFT Amplitude |X(freq)|')
            plt.suptitle('Current FFT')
            plt.title(f"setpoint: offset={offset} amplitude={amplitude};"
                      f" readback: {i_avg:0.4f} {i_freq:0.4f} phase {phase_freq:0.4f}")
            plt.savefig("test_regulator_hyst_sin_fft.png")
            plt.clf()
        except ImportError:
            pass

    def test_regulator_hyst_average(self):
        setpoint = 0.25
        itegration_period = 1000
        tolerance = 0.05
        dut = Dut()
        run_simulation(dut, [
            self.lpf(dut),
            self.set_setpoint(dut, setpoint),
            self.check_current(dut, setpoint, itegration_period, tolerance)],
            vcd_name=inspect.stack()[0][3] + ".vcd",
            clocks={"sys": 1e9 / FCLK})

    def test_regulator_hyst_sine(self):
        spam_spec = importlib.util.find_spec("numpy")
        if spam_spec is None:
            # Don't perform this test if numpy is installed, as it's quite slow and probably should
            # only be run in a dev environment.
            return

        amplitude = 0.25
        offset = 0.1
        frequency = 10e3
        fclk = frequency * 1024 * 8
        sin_cycles = 4
        tolerance = 0.01
        dut = Dut()
        run_simulation(dut, [
            self.lpf(dut),
            self.sine_setpoint(dut, fclk, amplitude, offset, frequency, sin_cycles),
            self.check_fft(dut, fclk, amplitude, offset, frequency, sin_cycles, tolerance)],
            vcd_name=inspect.stack()[0][3] + ".vcd",
            clocks={"sys": 1e9 / FCLK})
