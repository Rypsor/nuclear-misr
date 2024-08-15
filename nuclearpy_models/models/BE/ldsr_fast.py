####
# SR guided for correction of the binding energy
from typing import Any, List
import numpy as np
from .semf import semf_be


class LDSR:
    def __init__(self) -> None:
        self.exprs_list = [
            "(np.exp((h ** -1.514328570392646) - (P / (h ** -1.8592375329438713))))",
            "(((Z * (np.square(h - 0.736416622256365) ** 0.6957266745395214)) ** 0.8106014764774799) - np.square(1.4710769103505243))",
            "(((0.6891128763572738 ** (P + x)) + (np.square(S) / (-0.4401292167790589 + P))) * K)",
            "((np.exp(x / A) * -1.0380675417759826e-5) / (2.0820449870191298 + P))",
            "((((np.square(P) / (P ** P)) + np.log(N)) - 4.758719114044408) * h)",
        ]

    @staticmethod
    def get_features(Z, N):
        z_magic_numbers = [2, 8, 20, 28, 50, 82, 126]
        n_magic_numbers = [2, 8, 20, 28, 50, 82, 126, 184]
        clossest_z = min(z_magic_numbers, key=lambda x: abs(x - Z))
        clossest_n = min(n_magic_numbers, key=lambda x: abs(x - N))
        vp = abs(Z - clossest_z)
        vn = abs(N - clossest_n)
        P = (vp * vn) / (vp + vn + 1e-6)
        A = Z + N
        ee = int(Z % 2 == 0 and N % 2 == 0)
        eo = int(Z % 2 == 0 and N % 2 != 0)
        oe = int(Z % 2 != 0 and N % 2 == 0)
        oo = int(Z % 2 != 0 and N % 2 != 0)
        d = ee - oo
        x = (N - Z) ** 2
        ax = np.sqrt(x)
        h = Z / N
        K = A ** (1 / 3)
        S = (N - Z) / A
        t = A ** (2 / 3)
        return {
            "Z": Z,
            "A": A,
            "N": N,
            "x": x,
            "ax": ax,
            "ee": ee,
            "eo": eo,
            "oe": oe,
            "oo": oo,
            "t": t,
            "h": h,
            "P": P,
            "K": K,
            "S": S,
            "d": d,
        }

    def predict_be(self, Z: int, N: int, expression: str):
        """Predict the binding energy of a nucleus using the given expression"""
        features = self.get_features(Z, N)
        return eval(expression, None, features) + semf_be(Z, N)

    def predict_sp(self, Z: int, N: int, f: callable):
        pred_be_this = f(Z, N)
        pred_be_up = f(Z + 1, N)
        return pred_be_up - pred_be_this

    def predict_sn(self, Z: int, N: int, f: callable):
        pred_be_this = f(Z, N)
        pred_be_up = f(Z, N - 1)
        return pred_be_up - pred_be_this

    def get_expression(self, max_index):
        return " + ".join(self.exprs_list[:max_index])

    def get_model(self, max_index):
        st = self.get_expression(max_index).replace("x", "(N - Z) ** 2")
        st = st.replace("h", "Z / N")
        st = st.replace("K", "A ** (1 / 3)")
        st = st.replace("S", "(N - Z) / A")
        st = st.replace("t", "A ** (2 / 3)")
        return st

    def __call__(self, Z, N, index=-1):
        expression = self.get_expression(index)
        pred = self.predict_be(Z, N, expression)
        return pred, 0.0


ld_sr = LDSR()
