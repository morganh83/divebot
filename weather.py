import requests, json, math, pytz
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim

state_abbreviations = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming"
}

NOAA_BASE_URL = "https://api.tidesandcurrents.noaa.gov"

BASE_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
BASE_NWS_URL = "https://api.weather.gov"
HEADERS = {
    'User-Agent': 'DiveBot', 
    'Accept': 'application/geo+json'
}

##### GET NEW NOAA STATION LIST #####
class UpdateStations:
    def __init__(self):
        self.DATA_BASE_URL = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json?type="
        self.TYPES = ["watertemp", "physocean", "tidepredictions", "currentpredictions", "currents", "waterlevels"]
    
    def update_stations_file(self):
        for station_type in self.TYPES:
            response = requests.get(self.DATA_BASE_URL + station_type)
            print(f"Station: {station_type}  Response: {response.status_code}")
            
            if response.status_code == 200: 
                data = response.json()
                with open(f"noaa_stations_{station_type}.json", "w") as f:
                    json.dump(data["stations"], f, indent=4)
            else:
                print(f"Failed to fetch data for {station_type}. HTTP Status: {response.status_code}")

class GetDiveWeather:
    def convert_utc_to_est(self, utc_dt):
        utc_dt = pytz.utc.localize(utc_dt)
        est_dt = utc_dt.astimezone(pytz.timezone('US/Eastern'))
        return est_dt

    ##### LOAD LOCAL NOAA STATION LIST #####
    def load_stations_from_file(self, filename="noaa_stations_tidepredictions.json"):
        with open(filename, "r") as file:
            t_stations = json.load(file)
        return t_stations

    def load__oceanographic_stations_from_file(self, filename="noaa_stations_physocean.json"):
        with open(filename, "r") as file:
            o_stations = json.load(file)
        return o_stations

    def get_station_by_id(self, station_id, stations):
        for station in stations:
            if station["id"] == station_id:
                return station
        return None

    def fetch_lat_long_for_city(self, city, state):
        geolocator = Nominatim(user_agent="DiveBot")
        location = geolocator.geocode(f"{city}, {state}")
        
        if location:
            return (location.latitude, location.longitude)
        else:
            raise ValueError(f"Could not fetch coordinates for {city}, {state}")

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        try:
            lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
        except ValueError:
            print(f"Error converting lat/lon to float: {lat1}, {lon1}, {lat2}, {lon2}")
            return float('inf')  

        R = 6371  # Earth radius in kilometers

        dLat = math.radians(lat2 - lat1)
        dLon = math.radians(lon2 - lon1)
        lat1 = math.radians(lat1)
        lat2 = math.radians(lat2)

        a = math.sin(dLat/2) * math.sin(dLat/2) + math.sin(dLon/2) * math.sin(dLon/2) * math.cos(lat1) * math.cos(lat2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c


    def get_nearest_station(self, city, state, threshold_distance=50):
        all_noaa_stations = self.load_stations_from_file()
        all_physocean_stations = self.load__oceanographic_stations_from_file()
        
        city_lat, city_long = self.fetch_lat_long_for_city(city, state)

        nearest_station_id = None
        nearest_distance = float('inf')
        
        for station in all_physocean_stations:
            distance = self.haversine_distance(city_lat, city_long, station['lat'], station['lng'])
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_station_id = station['id']

        # If no oceanographic station found within threshold_distance, check other stations
        if not nearest_station_id or nearest_distance > threshold_distance:
            for station in all_noaa_stations:
                distance = self.haversine_distance(city_lat, city_long, station['lat'], station['lng'])
                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest_station_id = station['id']

        nearest_station = self.get_station_by_id(nearest_station_id, all_noaa_stations)
        print(f"Nearest NOAA station: {nearest_station['name']}, ID: {nearest_station['id']}\nThe station is {round(nearest_distance)} miles from {city}.")
        return nearest_station_id

    ##### FETCH TIDE DATA #####
    def fetch_tide_predictions(self, station_id):
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

    def fetch_water_temperature(self, station_id):
        url = f"https://tidesandcurrents.noaa.gov/api/datagetter?date=today&station={station_id}&product=water_temperature&units=english&time_zone=lst_ldt&format=json"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            print("Failed to fetch water temperature.")
            return None

    # def parse_location(input_str):
    #     words = input_str.split()
        
    #     for i in range(1, len(words)):
    #         potential_state = " ".join(words[i:]).upper() # Try joining multiple words for state names like New York
    #         if potential_state in state_abbreviations:
    #             city = " ".join(words[:i])
    #             state = state_abbreviations[potential_state]
    #             return city, state
    #         elif potential_state in state_abbreviations.values():
    #             city = " ".join(words[:i])
    #             state = potential_state
    #             return city, state

    #     # If function hasn't returned by now, then the format wasn't recognized
    #     raise ValueError("Could not parse location string. Please use a recognized format.")
    def parse_location(self, input_str):
        words = input_str.split()

        # If we find two words and the second word matches a state abbreviation,
        # return immediately as city and state.
        if len(words) == 2 and words[1].upper() in state_abbreviations:
            return words[0], state_abbreviations[words[1].upper()]

        # If we don't find a match using the above, then we iterate through the words.
        # This loop checks for a match against full state names like "New York" or "New Mexico".
        for i in range(1, len(words)):
            potential_state = " ".join(words[i:]).upper()
            
            if potential_state in state_abbreviations:
                city = " ".join(words[:i])
                state = state_abbreviations[potential_state]
                return city, state
            elif potential_state in state_abbreviations.values():
                city = " ".join(words[:i])
                state = potential_state
                return city, state

        # If function hasn't returned by now, then the format wasn't recognized
        raise ValueError("Could not parse location string. Please use a recognized format.")


    def format_tide_data(self, tide_data, water_temp_data, city, state):
        now = datetime.utcnow()
        now_est = self.convert_utc_to_est(now)
        output = [f"DiveBot Weather Report for {city}, {state} as of {now_est.strftime('%m/%d/%Y at %I:%M %p')}"]
        # output = [f"Last Updated: {now_est.strftime('%m/%d/%Y at %I:%M %p')} EST\n"]
        # print(f"Station: {tide_data['metadata']['name']}\n")

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
            output.append(f"Next Tide: {'High' if next_tide['type'] == 'H' else 'Low'} at {formatted_time} with a level of {next_tide['v']}ft\n")

        if water_temp_data:
            water_temp = water_temp_data.get('data', [{}])[0].get('v', None)
            if water_temp:
                output.append(f"Water Temperature: {water_temp}°F\n")

        output.append("Today's Tides:")
        for tide in today_tides:
            formatted_time = datetime.strptime(tide['t'], '%Y-%m-%d %H:%M').strftime('%I:%M %p')
            output.append(f"- {'High' if tide['type'] == 'H' else 'Low'} at {formatted_time} with a level of {tide['v']}ft")
        
        return "\n".join(output)

    def convert_state_to_full_name(self, state):
        """Convert state abbreviation to full name if needed"""
        return state_abbreviations.get(state.upper(), state)

