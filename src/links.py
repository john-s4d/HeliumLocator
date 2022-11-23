from numpy import array, NaN, apply_along_axis, vstack, load, mean
from math import pi, acos, sin, cos, log10, sqrt

from pandas.core.frame import DataFrame
from pandas.core.series import Series
from pandas import read_csv, merge, concat

from src.cellmap import CellMap
from src.collect import get_challenges


def gps_distance(point1, point2):
    """
    point1 and point2 -> tuples with lat lon positions in rads
    """
    if isinstance(point1, DataFrame):
        Xt, Yt = point1[["latitude", "longitude"]].values[0] * pi / 180
    else:
        Xt, Yt = array(point1) * pi / 180

    if isinstance(point2, DataFrame):
        Xr, Yr = point2[["latitude", "longitude"]].values[0] * pi / 180
    else:
        Xr, Yr = array(point2) * pi / 180

    return 6371 * acos(sin(Xt) * sin(Xr) + cos(Xt) * cos(Xr) * cos(Yr - Yt))


def receive_signal(simulated_point, test_point, show=False):
    """"""
    # Distance
    link_distance = gps_distance(simulated_point, test_point)
    if link_distance < 1:
        return None

    # Effective Isotropically Radiated Power (EIRP)
    # Max EIRP in US = 36 [dBi]
    G_TdB = float(simulated_point.gain) / 10.0  # [dB]
    P_TdB = 27  # dBm -> transmitter power
    cable_loss = 0  # dB included on G_TdB
    EIRP = P_TdB - cable_loss + G_TdB

    # Path loss - Friis free-space loss equation
    c = 299_792_458  # Speed of Light
    #f = 904.7000122070312 * 1e6  # [Hz]
    f = 915 * 1e6  # [Hz]
    lambda_ = c / f  # [m]
    d_m = link_distance * 1000  # [m]

    L_dB = -20 * log10(lambda_) + 20 * log10(d_m) + 22

    # Receive Signal Level (RSL)
    # -30dBm: signal is strong.
    # -120dBm: signal is weak.
    G_RdB = float(test_point.gain) / 10.0  # [dB]
    RSL = EIRP - L_dB + G_RdB

    if show:
        print(f"Distance = {link_distance:.3f} [km]")
        print(f"EIRP = {EIRP:.2f} [dB]")
        print(f"Free space loss = {L_dB:.2f} [dB]")
        print(f"RSL = {RSL:.2f} dB")

    return RSL


# RF parameters
c = 299_792_458  # Speed of Light
#f = 904.7000122070312 * 1e6  # [Hz]
f = 915 * 1e6  # [Hz]
lambda_ = c / f  # [m]
log_lambda = log10(lambda_)


def receive_sig(data, rx_gain):
    G_TdB, link_distance = data

    if link_distance < 0.001:
        return NaN

    EIRP = 27 + G_TdB / 10.0
    L_dB = -20 * log_lambda + 20 * log10(link_distance * 1000) + 22

    G_RdB = float(rx_gain)  # [dB]

    return EIRP - L_dB + G_RdB


def link_predictions(point, gains, df):
    df["distance_km"] = apply_along_axis(
        gps_distance, 1, df[["latitude", "longitude"]].values, point
    )
    for gain in gains:
        df[f"g{gain}"] = apply_along_axis(
            receive_sig, 1, df[["gain", "distance_km"]].values, gain
        )


# Earth curvature influence
def earth_curvature_influence(D):
    earth_radius = 8504  # [Km]
    H = 1000 * D * D / (8 * earth_radius)  # [m]
    return H


def fresnel_radius(D):
    f_GHz = f * 1e-9  # [GHz]
    r = 8.657 * sqrt(0.6 * D / f_GHz)  # 60% [m]
    return r


class HeliumLink(object):
    """Main class to check links"""

    def __init__(self, df, cell_parameters):
        self.df = df
        self.reference_map = CellMap(**cell_parameters)

        new_references = apply_along_axis(
            func1d=self.reference_map.gps2cell,
            axis=1,
            arr=df[["latitude", "longitude"]].values,
        )

        self.df["x"] = new_references[:, 0]
        self.df["y"] = new_references[:, 1]

        self.buildings = {
            "urban": 10,  # [m]
            "suburban": 5,  # [m]
            "rural": 0,  # [m]
        }
        self.location_type = "rural"

    scale = 1000

    def _get_altitude(self, data):
        lat, lon = self.reference_map.cell2gps(data)
        alt = self.r_altirudes[data[0], data[1]]

        if alt > -5000:
            return alt

        geometry = self.ee.Geometry.Point(lon, lat)
        lat = (
            self.elv.sample(geometry, scale)
            .first()
            .get("elevation")
            .getInfo()
        )

        self.r_altirudes[data[0], data[1]] = lat

        return lat

    def set_location_type(self, location_type: str):
        if location_type in self.buildings.keys():
            self.location_type = location_type
            print(f"The location type is {location_type}")
        else:
            print("Type only 'urban', 'suburban', or 'rural'.")

    def check(self, **kwargs):
        point = [kwargs["latitude"], kwargs["longitude"]]
        gains = kwargs["gains"]
        elevations = kwargs["elevations"]
        self.ee = kwargs["Google_Earth_Auntentificator"]
        self.elv = kwargs["Google_Earth_Elevation_Image"]
        df = self.df

        link_responses = df.loc[:, ["name"]]

        # Distances to the simulated point
        link_responses["dist_km"] = apply_along_axis(
            gps_distance, 1, df[["latitude", "longitude"]].values, point
        )
        df["sim_dist_km"] = link_responses["dist_km"]
        #
        for gain in gains:
            link_responses[f"rssi_g{gain}"] = apply_along_axis(
                receive_sig,
                1,
                vstack([df.gain, link_responses.dist_km]).T,
                gain,
            )

        r_nodes = df[["x", "y"]]
        r_point = self.reference_map.gps2cell(point)

        path = "./databases/altitudes_map.npy"
        self.r_altirudes = load(path)

        # Getting the map coordinates of the midpoints
        r_mid_points = (r_point + (r_nodes - r_point) / 2).astype(int)

        r_mid_points["altitude"] = apply_along_axis(
            self._get_altitude,
            1,
            r_mid_points[["x", "y"]].values,
        )

        df["altitude"] = apply_along_axis(
            self._get_altitude,
            1,
            r_nodes.values,
        )

        r_mid_points["dsit_km"] = link_responses["dist_km"]
        r_mid_points["destination"] = link_responses.loc[:, ["name"]]
        r_mid_points["Fresnel_r"] = link_responses["dist_km"].apply(
            fresnel_radius
        )
        # Earth curvature influence
        r_mid_points["Earth_H"] = apply_along_axis(
            earth_curvature_influence, 0, link_responses["dist_km"].values
        ).round(decimals=1)

        point_alt = self.r_altirudes[r_point[0], r_point[1]]

        for elevation in elevations:
            alt_reference = (df["altitude"] + df["elevation"]).apply(
                lambda x, y: min(x, y) + abs(x - y) / 2.0,
                args=(elevation + point_alt,),
            )
            Obstruction_H = (
                r_mid_points["altitude"]
                + r_mid_points["Earth_H"]
                + self.buildings[self.location_type]
            )

            r_mid_points[f"link_h{elevation}"] = (
                alt_reference - Obstruction_H > r_mid_points["Fresnel_r"]
            )

        self.by_gain = link_responses
        self.by_Fresnel = r_mid_points

        resp = DataFrame(columns=["gain", "elevation", "earnings", "nodes"])
        for i in gains:
            for j in elevations:
                print(f"gain {i}, elevaion {j}")
                dict_resp = {
                    "gain": i,
                    "elevation": j,
                    "nodes": [
                        df[
                            (link_responses[f"rssi_g{i}"] > -120)
                            & r_mid_points[f"link_h{j}"]
                        ].name.to_list()
                    ],
                }

                dict_resp["earnings"] = self._get_earnings(dict_resp["nodes"][0])

                resp = concat([resp, DataFrame(dict_resp)], ignore_index=True)
        return resp

    def _get_earnings(self, nodes):
        df = self.df
        final_points = (
            df[df.name.isin(nodes)].dropna().sort_values("sim_dist_km")
        )
        A = min(14, final_points.shape[0])
        final_points = final_points.head(A)

        B = sum(final_points.reward_scale)

        prev_C = [
            min(14, len(get_challenges(address=N, type_="witnesses")))
            for N in final_points.address.values
        ]

        C = mean(prev_C)

        return A * B * (15 - C)
