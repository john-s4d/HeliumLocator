"""To implement the probabilistic map"""
from math import exp, pi
from threading import Semaphore
from numpy import (
    load as load_data,
    around,
    linspace,
    ones,
    zeros,
    sum as suma,
    ceil,
    where,
    amin,
    sqrt,
    array,
)

from src.utils import get_location_meters, split_gps, saturate


class CellMap:
    """This object represents the likelihood map"""

    def __init__(self, **kwarg):
        self.n_x = kwarg["cells_in_x"]
        self.n_y = kwarg["cells_in_y"]
        x_0 = kwarg["initial_cell_x"]
        y_0 = kwarg["initial_cell_y"]
        map_width = kwarg["map_width_in_mtrs"]
        map_long = kwarg["map_long_in_mtrs"]
        home_gps = kwarg["initial_coordinate"]
        #
        self.l_x = float(map_width) / self.n_x
        self.l_y = float(map_long) / self.n_y
        #
        dis2lim4 = (self.n_x - x_0 - 0.5) * self.l_x
        dis2lim3 = (self.n_y - y_0 - 0.5) * self.l_y
        dis2lim2 = (x_0 + 0.5) * self.l_x
        dis2lim1 = (y_0 + 0.5) * self.l_y
        #
        limit3, limit4 = get_location_meters(home_gps, (dis2lim3, dis2lim4))
        limit1, limit2 = get_location_meters(home_gps, (-dis2lim1, -dis2lim2))
        #
        y_lat = linspace(limit1, limit3, self.n_y + 1)
        x_lon = linspace(limit2, limit4, self.n_x + 1)
        #
        x_with = abs(x_lon[1] - x_lon[0])
        y_long = abs(y_lat[1] - y_lat[0])
        #
        self.x_lon = around(x_lon[:-1] + x_with / 2, 6)
        self.y_lat = around(y_lat[:-1] + y_long / 2, 6)
        #
        self.t_0 = 0
        #
        self.S_tl_t_k = ones((self.n_x, self.n_y)) / (self.n_x * self.n_y)
        self.S_accum = zeros((self.n_x, self.n_y))
        self.gamma = ones((self.n_x, self.n_y)) / (self.n_x * self.n_y)
        #
        self.measures = [
            zeros((self.n_x, self.n_y)),
            zeros((self.n_x, self.n_y)),
            zeros((self.n_x, self.n_y)),
            zeros((self.n_x, self.n_y)),
        ]
        self.beta = self.S_accum
        self.V = 0
        #
        self.semaphore = Semaphore(1)

    def set_sample(
        self, x_index: int, y_index: int, value: float, index: int = 0
    ) -> None:
        """Set the measured value in the corresponding cell"""
        self.measures[index][x_index, y_index] = value

    def update(
        self, x_j: int, y_j: int, t_k: int = 10, detection: bool = True
    ) -> None:
        """Build the source probability map based on one detection or
        nondetection event at time t_k"""

        self.semaphore.acquire()
        memory = 7
        if t_k - self.t_0 > memory:
            t_0 = t_k - memory
        else:
            t_0 = 0
        #
        v_x = 0
        v_y = 0
        s_x = 1.75
        s_y = 1.75
        mu = 0.95
        #
        wix = ceil(5 * sqrt(memory) * s_x)
        wiy = ceil(5 * sqrt(memory) * s_y)
        #
        M = self.l_x * self.l_y
        #
        # From the article:
        for x_i in range(0, self.n_x):
            for y_i in range(0, self.n_y):
                if abs(x_j - x_i - v_x) < wix and abs(y_j - y_i - v_y) < wiy:
                    #
                    self.S_tl_t_k[x_i, y_i] = M * (
                        (
                            exp(
                                -((x_j - x_i - v_x) ** 2)
                                / (2 * (memory) * s_x**2)
                            )
                            * exp(
                                -((y_j - y_i - v_y) ** 2)
                                / (2 * (memory) * s_y**2)
                            )
                        )
                        / (2 * pi * (t_k - self.t_0) * s_x * s_y)
                    )
                else:
                    self.S_tl_t_k[x_i, y_i] = 0

        #
        self.S_tl_t_k = self.S_tl_t_k / suma(self.S_tl_t_k)
        #
        if detection:
            self.S_accum = self.S_accum + self.S_tl_t_k
            self.beta = self.S_accum / t_k
            self.beta = self.beta / suma(self.beta)
        # else:
        # self.gamma = self.gamma * (1 - mu * self.S_tl_t_k)
        # self.gamma = self.gamma / suma(self.gamma)
        #
        self.semaphore.release()
        #

    def gps2cell(self, location):
        """Returns the `location` equivalent indices on the likelihood map"""

        lat, lon = split_gps(location)
        diff_y_lat = abs(self.y_lat - lat)
        diff_x_lon = abs(self.x_lon - lon)
        min_x_lon = where(diff_x_lon == amin(diff_x_lon))[0]
        min_y_lat = where(diff_y_lat == amin(diff_y_lat))[0]
        #
        if type(min_x_lon).__name__ == "ndarray":
            if type(min_y_lat).__name__ == "ndarray":
                aux_a = saturate(min_x_lon[0], 0, self.n_x - 1)
                aux_b = saturate(min_y_lat[0], 0, self.n_y - 1)
            else:
                aux_a = saturate(min_x_lon[0], 0, self.n_x - 1)
                aux_b = saturate(min_y_lat, 0, self.n_y - 1)
        elif type(min_y_lat).__name__ == "ndarray":
            aux_a = saturate(min_x_lon, 0, self.n_x - 1)
            aux_b = saturate(min_y_lat[0], 0, self.n_y - 1)
        else:
            aux_a = saturate(min_x_lon, 0, self.n_x - 1)
            aux_b = saturate(min_y_lat, 0, self.n_y - 1)
        return array([aux_a, aux_b])

    #

    def cell2gps(self, i, dtype="cell_indices"):
        """Returns the global position of grid center"""

        if dtype == "cell_indices":
            if len(i) == 2:
                return [
                    self.y_lat[min(self.n_x - 1, int(i[1]))],
                    self.x_lon[min(self.n_y - 1, int(i[0]))],
                ]
            print("The indices length must be 2")
        elif dtype == "longitude":
            return self.x_lon[int(i)]
        elif dtype == "latitude":
            return self.y_lat[int(i)]
        #
        print(
            "The `dtype` argument must be: cell_indices, longitude or latitude."
        )
        return None

    def size(self):
        """Returns the size of the map"""
        return (self.n_x - 1, self.n_y - 1)


if __name__ == "__main__":
    cell_parameters = {
        "cells_in_x": 100,
        "cells_in_y": 100,
        "initial_cell_x": 15,
        "initial_cell_y": 15,
        "map_width_in_mtrs": 1000,
        "map_long_in_mtrs": 1000,
        "initial_coordinate": (25.645656, -100.288479),
    }

    li_map = CellMap(**cell_parameters)
    print(li_map.gamma)
