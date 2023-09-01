from oceanography_stations import oceanographic_list_us
import json, requests

river_stations = []
oceanography_stations = []
sea_stations = []

DATA_BASE_URL = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json?type="

TYPES = ["watertemp", "physocean", "tidepredictions", "currentpredictions", "currents", "waterlevel", "airpressure", "airtemperature", "windspeed", "wind"]



def load_stations_from_file(filename="noaa_stations.json"):
    with open(filename, "r") as file:
        stations = json.load(file)
    return stations

def categorize_stations():
    all_stations = load_stations_from_file()
    oceanographic_list_us_str = [str(station) for station in oceanographic_list_us]
    for station in all_stations:
        # print(station['id'])
        if station["type"] == "R":
            river_stations.append(station)
        if station["id"] in oceanographic_list_us_str:
            # print(f"Found oceanographic station: {station['id']}")
            print(f"Found oceanographic station: {station['type']}")
            oceanography_stations.append(station)
    
    print(f"Found {len(river_stations)} river stations and {len(oceanography_stations)} oceanography stations.")
    
print(f"Oceanographic List: {len(oceanographic_list_us)}\n")
categorize_stations()


