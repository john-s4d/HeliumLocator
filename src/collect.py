import requests
import json

from numpy import array_split
from pandas import concat
from time import sleep


def get_nodes(lat, lon, distance):
    url = "https://api.helium.io/v1/hotspots/location/distance"
    cont = 1
    cursor = ""
    rows_list = []

    while cont < 100:
        response_API = requests.get(
            f"{url}?lat={lat}&lon={lon}&distance={distance}&cursor={cursor}"
        )
        print(f"status_code cursor {cont} = {response_API.status_code}")
        cont += 1
        parse_json = json.loads(response_API.text)

        try:
            for node in parse_json["data"]:
                data = {
                    "name": node["name"],
                    "longitude": node["lng"],
                    "latitude": node["lat"],
                    "distance": node["distance"],
                    "gain": node["gain"],
                    "elevation": node["elevation"],
                    "reward_scale": node["reward_scale"],
                    "address": node["address"],
                }
                rows_list.append(data)
        except:
            print(parse_json)
            return rows_list

        if len(parse_json) == 2:
            cursor = parse_json["cursor"]
        else:
            return rows_list


def get_elevation(df):
    elevation_url = "https://api.opentopodata.org/v1/test-dataset"
    n_of_batches = df.shape[0] // 101 + 1
    batchs = array_split(df, n_of_batches)

    for i, batch in enumerate(batchs):
        locations = ""
        for row in batch.itertuples():
            locations += f"{row.latitude},{row.longitude}|"

        response_elevation_API = requests.get(
            f"{elevation_url}?locations={locations}"
        )
        sleep(1)
        print(
            f"status_code {i+1} of {n_of_batches} = {response_elevation_API.status_code}"
        )

        parse_json_elevation = json.loads(response_elevation_API.text)

        altitudes = []
        try:
            for node in parse_json_elevation["results"]:
                altitudes.append(node["elevation"])
        except:
            print(parse_json_elevation)

        batch["altitude"] = altitudes

    return concat(batchs)


def get_challenges(address, type_: str = "challenges"):
    print(f"Getting {type_} for a Hotspot - ", end="")
    url = f"https://api.helium.io/v1/hotspots/{address}/{type_}"
    cont = 1
    cursor = ""
    rows_list = []

    while cont < 100:
        response_API = requests.get(url + f"?cursor={cursor}")
        sleep(1)
        print(f"status_code cursor {cont} = {response_API.status_code}")
        cont += 1
        parse_json = json.loads(response_API.text)

        try:
            for node in parse_json["data"]:
                rows_list.append(node)
        except:
            print(parse_json)
            return rows_list

        if len(parse_json) == 2:
            cursor = parse_json["cursor"]
        else:
            return rows_list
