import re
import requests
import pandas as pd
import folium

from time import time
from math import pi, cos


def tic():
    # Homemade version of matlab tic and toc functions
    global startTime_for_tictoc
    startTime_for_tictoc = time()


def toc():
    if "startTime_for_tictoc" in globals():
        val = time() - startTime_for_tictoc
        print("Elapsed time is %f seconds." % val)
        # return val
    else:
        print("Toc: start time not set")
        # return None


def dms2dd(degrees, minutes, seconds, direction):
    dd = float(degrees) + float(minutes) / 60 + float(seconds) / (60 * 60)
    if direction == "S" or direction == "W":
        dd *= -1
    return dd


def dd2dms(deg):
    d = int(deg)
    md = abs(deg - d) * 60
    m = int(md)
    sd = (md - m) * 60
    return [d, m, sd]


def parse_dms(dms, rads=True):
    parts = re.split("[^\d\w]+", dms)
    lat = dms2dd(parts[0], parts[1], parts[2], parts[3])
    lng = dms2dd(parts[4], parts[5], parts[6], parts[7])

    if rads:
        return lat * pi / 180, lng * pi / 180
    return lat, lng


# @interact(n=(1,df.shape[0]))
def show_map(df, lat, lon, n=None):
    if n:
        df2 = df.sort_values(by=["distance"], ascending=False).head(n=n)
    else:
        df2 = df

    m = folium.Map(location=(lat, lon), zoom_start=8)

    # add marker one by one on the map
    for i in range(0, len(df2)):
        folium.Marker(
            location=[df2.iloc[i]["latitude"], df2.iloc[i]["longitude"]],
            popup=df2.iloc[i]["name"],
            icon=folium.Icon(color="blue", icon="ok-sign"),
        ).add_to(m)
    folium.Marker(
        location=[lat, lon],
        popup="Main location",
        icon=folium.Icon(color="red", icon="exclamation-sign"),
    ).add_to(m)
    return m


def get_location_meters(original_location, next_position):
    """
    Returns a LocationGlobal object containing the latitude/longitude `d_north` and `d_east` metres from the specified `original_location`.

    The algorithm is relatively accurate over small distances (10m within 1km) except close to the poles.
    """

    d_north, d_east = next_position
    _lat, _long = original_location

    earth_radius = 6378137.0  # Radius of "spherical" earth
    # Coordinate offsets in radians
    d_at = d_north / earth_radius
    d_lon = d_east / (earth_radius * cos(pi * _lat / 180))

    # New position in decimal degrees
    newlat = round(_lat + (d_at * 180 / pi), 6)
    newlon = round(_long + (d_lon * 180 / pi), 6)

    return (newlat, newlon)


def split_gps(a_location):
    """Separates the coordinates of the object in latitude and longitude"""
    _lat1, _long1 = a_location
    return _lat1, _long1


def saturate(value, minimum, maximum):
    """Limits the value variable"""
    value = min(value, maximum)
    value = max(value, minimum)
    return value
