import math
import time

class LowPassFilter:
    def __init__(self, alpha, init_val=0):
        self.__y = self.s = init_val
        self.__alpha = alpha

    def filter(self, val, alpha=None):
        if alpha is not None:
            self.__alpha = alpha
        alpha = self.__alpha
        self.__y = alpha * val + (1.0 - alpha) * self.s
        self.s = self.__y
        return self.__y

    def last_value(self):
        return self.__y

class OneEuroFilter:
    def __init__(self, min_cutoff=1.0, beta=0.0, d_cutoff=1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.x_filter = LowPassFilter(1.0)
        self.dx_filter = LowPassFilter(1.0)
        self.t_prev = None

    def alpha(self, cutoff, te):
        if te <= 0:
            return 1.0
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / te)

    def __call__(self, x, t=None):
        if t is None:
            t = time.time()
            
        if self.t_prev is None:
            self.t_prev = t
            self.x_filter = LowPassFilter(1.0, x)
            self.dx_filter = LowPassFilter(1.0, 0)
            return x

        te = t - self.t_prev
        self.t_prev = t
        
        if te == 0:
            return self.x_filter.last_value()

        filtered_derivative = (x - self.x_filter.last_value()) / te
        ad = self.alpha(self.d_cutoff, te)
        dx = self.dx_filter.filter(filtered_derivative, alpha=ad)
        
        cutoff = self.min_cutoff + self.beta * abs(dx)
        a = self.alpha(cutoff, te)
        return self.x_filter.filter(x, alpha=a)
