import requests, json, argparse, math, pytz
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
from oceanography_stations import oceanographic_list_us

BASE_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"


##### ARGUMENTS #####
def parse_arguments():
    parser = argparse.ArgumentParser(description="Fetch NOAA data for given city and state")
    parser.add_argument("location", help="City and state in the format 'city, st'", type=str)
    parser.add_argument("-u", "--update", help="Update NOAA station list", action="store_true")
    
    
    return parser.parse_args()

args = parse_arguments()


##### GET NEW NOAA STATION LIST #####
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

def convert_utc_to_est(utc_dt):
    utc_dt = pytz.utc.localize(utc_dt)
    est_dt = utc_dt.astimezone(pytz.timezone('US/Eastern'))
    return est_dt

##### LOAD LOCAL NOAA STATION LIST #####
def load_stations_from_file(filename="noaa_stations.json"):
    with open(filename, "r") as file:
        stations = json.load(file)
    return stations

def get_station_by_id(station_id, stations):
    for station in stations:
        if station["id"] == station_id:
            return station
    return None


##### GET LAT/LONG FOR CITY, STATE ARGUMENT #####
city, state = map(str.strip, args.location.split(','))
print(f"Fetching tide data for {city}, {state}...")
print()

def fetch_lat_long_for_city(city, state):
    geolocator = Nominatim(user_agent="DiveBot")
    location = geolocator.geocode(f"{city}, {state}")
    
    if location:
        return (location.latitude, location.longitude)
    else:
        raise ValueError(f"Could not fetch coordinates for {city}, {state}")

def haversine_distance(lat1, lon1, lat2, lon2):
    try:
        # Convert all to float
        lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
    except ValueError:
        print(f"Error converting lat/lon to float: {lat1}, {lon1}, {lat2}, {lon2}")
        return float('inf')  # return "infinite" distance so this station is effectively ignored

    R = 6371  # Earth radius in kilometers

    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    a = math.sin(dLat/2) * math.sin(dLat/2) + math.sin(dLon/2) * math.sin(dLon/2) * math.cos(lat1) * math.cos(lat2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


# all_noaa_stations = get_all_noaa_stations()
def get_nearest_station(city, state, threshold_distance=50):
    all_noaa_stations = load_stations_from_file()
    print(f"Loaded {len(all_noaa_stations)} NOAA stations.")
    
    city_lat, city_long = fetch_lat_long_for_city(city, state)

    nearest_station_id = None
    nearest_distance = float('inf')
    
    # Lists to store oceanographic and other stations separately
    oceanographic_stations = []
    other_stations = []

    # Sort stations
    oceanographic_list_us_str = [str(id) for id in oceanographic_list_us]
    for station in all_noaa_stations:
        if station["id"] in oceanographic_list_us_str:
            oceanographic_stations.append(station)
        else:
            other_stations.append(station)
    print(f"\nFound {len(oceanographic_stations)} oceanographic stations and {len(other_stations)} other stations.")
    print(f"Total Oceanographic Stations: {len(oceanographic_list_us)}, Sample: {oceanographic_list_us[:5]}\n")
    sample_stations = [station['id'] for station in all_noaa_stations[:10]]
    print(f"Sample NOAA Station IDs: {sample_stations}\n")
    for station_id in sample_stations:
        if station_id in oceanographic_list_us:
            print(f"Match found for station ID: {station_id}\n")
    # First check oceanographic stations
    for station in oceanographic_stations:
        distance = haversine_distance(city_lat, city_long, station['lat'], station['lng'])
        if distance < nearest_distance:
            nearest_distance = distance
            nearest_station_id = station['id']

    # If no oceanographic station found within threshold_distance, check other stations
    if not nearest_station_id or nearest_distance > threshold_distance:
        for station in other_stations:
            distance = haversine_distance(city_lat, city_long, station['lat'], station['lng'])
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_station_id = station['id']

    nearest_station = get_station_by_id(nearest_station_id, all_noaa_stations)
    print(f"Nearest station: {nearest_station['name']}, ID: {nearest_station['id']}\nThe station is {round(nearest_distance)} miles from {city}.")
    return nearest_station_id



def fetch_tide_predictions(station_id):
    now = datetime.utcnow()
    end_date = now + timedelta(days=1)

    begin_date_str = now.strftime('%Y%m%d')
    end_date_str = end_date.strftime('%Y%m%d')

    params = {
        "begin_date": begin_date_str,
        "end_date": end_date_str,
        "station": station_id,
        "product": "predictions",
        "datum": "MLLW",
        "units": "english",
        "time_zone": "lst_ldt",
        "interval": "hilo",
        "format": "json"
    }

    response = requests.get(BASE_URL, params=params)
    data = response.json()

    return data

def fetch_water_temperature(station_id):
    url = f"https://tidesandcurrents.noaa.gov/api/datagetter?date=today&station={station_id}&product=water_temperature&units=english&time_zone=lst_ldt&format=json"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to fetch water temperature.")
        return None


def format_tide_data(tide_data, water_temp_data):
    now = datetime.utcnow()
    now_est = convert_utc_to_est(now)

    print(f"Last Updated: {now.strftime('%m/%d/%Y at %I:%M %p')} UTC\n ({now_est.strftime('%m/%d/%Y at %I:%M %p')} EST)\n")

    next_tide = None
    today_tides = []

    for prediction in tide_data['predictions']:
        tide_time = datetime.strptime(prediction['t'], '%Y-%m-%d %H:%M')
        if tide_time > now and not next_tide:
            next_tide = prediction

        if tide_time.date() == now.date():
            today_tides.append(prediction)

    if next_tide:
        formatted_time = datetime.strptime(next_tide['t'], '%Y-%m-%d %H:%M').strftime('%I:%M %p')
        print(f"Next Tide: {'High' if next_tide['type'] == 'H' else 'Low'} at {formatted_time} with a level of {next_tide['v']}ft\n")

    print("Today's Tides:")
    for tide in today_tides:
        formatted_time = datetime.strptime(tide['t'], '%Y-%m-%d %H:%M').strftime('%I:%M %p')
        print(f"- {'High' if tide['type'] == 'H' else 'Low'} at {formatted_time} with a level of {tide['v']}ft")
    
    if water_temp_data:
        water_temp = water_temp_data.get('data', [{}])[0].get('v', None)
        if water_temp:
            print(f"Water Temperature: {water_temp}°F")

if __name__ == "__main__":
    station_id = get_nearest_station(city, state)
    if not station_id:
        print(f"Could not find a nearby NOAA station for {city}, {state}.")
        exit(1)
    tide_data = fetch_tide_predictions(station_id)
    water_temp_data = fetch_water_temperature(station_id)
    format_tide_data(tide_data, water_temp_data)

