import os, requests, math, pytz, json, re #discord
from interactions import ButtonStyle, Button, ActionRow, slash_command, SlashContext, Client, Intents, listen, OptionType, slash_option
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
from discord.ext import commands
from dotenv import load_dotenv
from weather import GetDiveWeather, UpdateStations
from asyncio import TimeoutError
import asyncio
from interactions.api.events import Component

load_dotenv()

#### INIT Weather Class ####
w = GetDiveWeather()
wu = UpdateStations()


TOKEN = os.getenv('DISCORD_TOKEN')
SECRET = os.getenv('CLIENT_SECRET')

# bot = commands.Bot(command_prefix='!', intents=intents)
bot = Client(intents=Intents.DEFAULT)
# slash = SlashCommand(bot, sync_commands=True)

##### GUIDE COMMAND #####
# def parse_location_time(input_str):
#     location, _, time = input_str.rpartition(' ')
#     return location, time

async def on_component(ctx):
    if ctx.component_type == 2:
        guide = ctx.author
        original_message = await ctx.origin_message()
        
        # Extract current guides from the message content
        prefix = f"{guide.mention} has requested a guided dive"
        suffix = "! Guides: "
        guides_str_start = original_message.content.index(suffix) + len(suffix)
        current_guides_str = original_message.content[guides_str_start:]

        current_guides = [guide.strip() for guide in current_guides_str.split(",")]

        # If guide is already listed, remove them; otherwise, add them
        if str(guide.mention) in current_guides:
            current_guides.remove(str(guide.mention))
        else:
            current_guides.append(str(guide.mention))

        # Update the message content
        new_content = original_message.content[:guides_str_start] + ", ".join(current_guides)
        await original_message.edit(content=new_content)
        
        # If there's any significant change (like the first guide signing up),
        # you can send the RSVP to the general channel here
        if len(current_guides) == 1:
            general_channel = bot.get_channel(1146672917892051028)
            await general_channel.send(f"RSVP for a dive led by {', '.join(current_guides)}!")

@slash_command(
    name='weather', 
    description='Fetch tide, weather, and water temperature data for a location', 
    options=[
        {
            "name": "city",
            "description": "City",
            "type": OptionType.STRING,
            "required": True
        },
        {
            "name": "state",
            "description": "State",
            "type": OptionType.STRING,
            "required": True
        }, 
    ]
)
async def weather(ctx, *, city: str, state: str):
    await ctx.defer()
    station_id = int(w.get_nearest_station(city, state)[0])
    if not station_id:
        await ctx.send(f"Could not find a nearby NOAA station for {city}, {state}.")
        return

    tide_data = w.fetch_tide_predictions(station_id)
    water_temp_data = w.fetch_water_temperature(station_id)
    # air_temp_data = w.weather(city, state)
    tide_message = w.format_tide_data(tide_data, water_temp_data, city, state)
    
    await ctx.send(tide_message)

@slash_command(
    name='guide', 
    description='Request a guided dive at a location (OPTIONAL: Add a date and time)', 
    options=[
        {
            "name": "location",
            "description": "Location and optional time for the dive",
            "type": OptionType.STRING,
            "required": True
        },
        {
            "name": "date",
            "description": "Requested time for the dive (optional). e.g. 10am or 1700",
            "type": OptionType.STRING,
            "required": False
        }, 
        {
            "name": "time",
            "description": "Requested time for the dive (optional). e.g. 10am or 1700",
            "type": OptionType.STRING,
            "required": False
        }, 
    ]
)
async def guide(ctx: SlashContext, location: str, date: str = None, time: str = None):
    user = ctx.author.nickname
    channel = bot.get_channel(1146846581874770011)
    
    yes_button = Button(style=ButtonStyle.GREEN, label="Accept", custom_id="guide_yes")
    no_button = Button(style=ButtonStyle.RED, label="Decline", custom_id="guide_no")
    
    action_row = ActionRow(yes_button, no_button)
    
    if time is None:
        await channel.send(
            content=f"{ctx.author} has requested a guided dive at {location}!",
            components=[action_row]
            )
    else:
        await channel.send(
            content=f"{user} has requested a guided dive at {location} at {date} - {time}!",
            components=[action_row]
            )

@listen()
async def on_component(event: Component):
    ctx = event.ctx
    match ctx.custom_id:
        case "guide_yes":
            await ctx.send(f"{ctx.author.mention} has volunteered to guide this dive!")
            # Disable the buttons
            print("YES")
            # await ctx.send(f"{ctx.author.mention} has volunteered to guide this dive!")        
        case "guide_no":
            await ctx.send(f"{ctx.author.mention} has declined to guide this dive.")
            print("NO")

@listen()
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print()
    print(f'{bot.user} is connected to the following guilds:')
    for guild in bot.guilds:
        print(f'    {guild.name}(id: {guild.id})')

bot.start(TOKEN)
