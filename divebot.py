import discord, os, requests, math
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
SECRET = os.getenv('CLIENT_SECRET')
# WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
NOAA_BASE_URL = "https://api.tidesandcurrents.noaa.gov"

BASE_NWS_URL = "https://api.weather.gov"
HEADERS = {
    'User-Agent': 'YourBotName',  # The NWS API requires a User-Agent header
    'Accept': 'application/geo+json'
}

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

async def get_noaa_station(lat, lon):
    url = f"{NOAA_BASE_URL}/mdapi/prod/webapi/stations.json?type=tidepredictions&lat={lat}&lon={lon}"
    response = requests.get(url).json()
    if not response.get('stations'):
        return None
    return response['stations'][0]['id']

async def get_tide_data(station_id):
    url = f"{NOAA_BASE_URL}/api/prod/datagetter?begin_date=now&range=24&station={station_id}&product=predictions&datum=MLLW&time_zone=lst_ldt&units=english&interval=hilo&format=json"
    response = requests.get(url).json()
    if not response.get('predictions'):
        return None
    return response['predictions']

async def get_lat_lon_from_city(location):
    # Try splitting by comma first; if that doesn't work, split by space.
    if ',' in location:
        city, state = [part.strip() for part in location.split(",")]
    else:
        city, state = location.split() if len(location.split()) == 2 else (None, None)

    if not city or not state:
        return None, None

    url = f"https://nominatim.openstreetmap.org/search?city={city}&state={state}&country=US&format=json"
    response = requests.get(url).json()

    if not response:
        return None, None

    return response[0]['lat'], response[0]['lon']

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

async def get_noaa_station(lat, lon):
    url = f"{NOAA_BASE_URL}/mdapi/prod/webapi/stations.json?type=tidepredictions&lat={lat}&lon={lon}&radius=50"
    response = requests.get(url).json()

    if not response.get('stations'):
        return None

    try:
        # Find the nearest station by computing the haversine distance
        nearest_station = min(response['stations'], key=lambda s: haversine_distance(lat, lon, s['lat'], s['lng']))
    except Exception as e:
        print(f"Error computing nearest station: {e}")
        return None

    return nearest_station['id']


@bot.command(name='guide', help='Request a guided dive at a location')
async def guide(ctx, *, location):
    user = ctx.author
    channel = bot.get_channel(1146846581874770011)
    await channel.send(f'{user} would like to dive at {location}')



@bot.command(name='weather', help='Get the weather and sea data for a specified location (city, state)')
async def weather(ctx, *, location):
    lat, lon = await get_lat_lon_from_city(location)
    if not lat or not lon:
        await ctx.send(f"Couldn't find the location: {location}. Please ensure it's in the format 'City, State' or 'City State'.")
        return

    # Fetching Weather Information
    points_url = f"{BASE_NWS_URL}/points/{lat},{lon}"
    response = requests.get(points_url, headers=HEADERS).json()
    
    forecast_url = response['properties']['forecast']
    forecast_data = requests.get(forecast_url, headers=HEADERS).json()
    
    today_forecast = forecast_data['properties']['periods'][0]
    
    weather_msg = (f"Weather for {location}:\n"
                   f"Condition: {today_forecast['shortForecast']}\n"
                   f"Air Temperature: {today_forecast['temperature']}°{today_forecast['temperatureUnit']}\n"
                   f"Wind: {today_forecast['windSpeed']} from {today_forecast['windDirection']}")

    await ctx.send(weather_msg)

    # Fetching NOAA Sea Data Information
    station_id = await get_noaa_station(lat, lon)
    if not station_id:
        await ctx.send(f"Note: Couldn't find a NOAA station near {location} for sea data.")
        return
    
    tide_data = await get_tide_data(station_id)
    if not tide_data:
        await ctx.send(f"Note: Couldn't fetch tide data for {location}.")
        return

    tides_info = "\n".join([f"{entry['t']} - {entry['type']}" for entry in tide_data])
    sea_data_msg = (f"\nTide Predictions for {location}:\n{tides_info}")
    await ctx.send(sea_data_msg)



bot.run(TOKEN)
