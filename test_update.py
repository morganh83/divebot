import requests, json, argparse

def parse_arguments():
    parser = argparse.ArgumentParser(description="Fetch NOAA data for given city and state")
    parser.add_argument("-u", "--update", help="Update NOAA station list", action="store_true")
    
    return parser.parse_args()

def update_stations_file():
    DATA_BASE_URL = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json?type="
    TYPES = ["watertemp", "physocean", "tidepredictions", "currentpredictions", "currents", "waterlevels"]
    
    for station_type in TYPES:
        response = requests.get(DATA_BASE_URL + station_type)
        print(f"Station: {station_type}  Response: {response.status_code}")
        
        if response.status_code == 200:  # check if request was successful
            data = response.json()
            with open(f"noaa_stations_{station_type}.json", "w") as f:
                # Directly dump the stations data into the file
                json.dump(data["stations"], f, indent=4)
        else:
            print(f"Failed to fetch data for {station_type}. HTTP Status: {response.status_code}")

args = parse_arguments()
if args.update:
    update_stations_file()
    exit(0)