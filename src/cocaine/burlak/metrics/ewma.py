"""Exponential Weighted Moving Avarage.

Links:
  https://en.wikipedia.org/wiki/Moving_average#Exponential_moving_average
  https://en.wikipedia.org/wiki/Exponential_smoothing#Background
"""
import math


class EWMA(object):
    """Exponential Weighted Moving Avarage."""

    def __init__(self, alpha=.7, init=0):
        """EWMA.

        :param alpha: degree of weighting decrease in interval [0, 1]
        :type alpha: float

        :param init: initial sequcne value, 0 is ok
        :type init: float | int | long
        """
        if alpha < 0. or alpha > 1.:
            raise ValueError(
                'incorrect `alpha` parameter: {}, should in [0, 1] range',
                alpha
            )

        self._alpha = alpha
        self._s = init

    def update(self, value):
        """Recalculate moving avarage."""
        self._s = self._alpha * value + (1 - self._alpha) * self._s

    @property
    def value(self):
        """Get current moving avarage."""
        return self._s

    @property
    def int_of_value(self):
        """Get current moving avarage as integer."""
        return int(self._s)

    @staticmethod
    def alpha(dt, tau):
        """Generate alpha time constant based on poll ranges.

        :param dt: - sampling interval
        :param tau: measurements interval
        :ptype dt: float | int | long
        :ptype tau: float | int | long

        Aka `decay constant`.
        All times are in seconds.

        alpha = 1 - e ^ (-dt/tau)

        Alpha describes a rate (smoothing weight) of sample to account
        withing whole measurements interval.

        Ensures: 1 - 1 / e ~= 63.2 %

        """
        if tau <= 0:
            raise ValueError("tau interval should be greater then zero!")

        if dt <= 0:
            raise ValueError("sampling interval should be greater then zero!")

        return -math.expm1(-dt / float(tau))
