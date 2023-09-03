import os, requests, math, pytz, json, discord, re, interactions
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
from discord.ext import commands
from dotenv import load_dotenv
from weather import GetDiveWeather, UpdateStations
# from discord.interactions import SlashCommand, cog_ext
# from discord.interactions import create_button, create_actionrow
# from discord.interactions import ButtonStyle
from discord.interactions import SlashCommand, cog_ext


load_dotenv()

#### INIT Weather Class ####
w = GetDiveWeather()
wu = UpdateStations()


TOKEN = os.getenv('DISCORD_TOKEN')
SECRET = os.getenv('CLIENT_SECRET')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)
slash = SlashCommand(bot, sync_commands=True)

##### GUIDE COMMAND #####
def parse_location_time(input_str):
    location, _, time = input_str.rpartition(' ')
    return location, time

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


@bot.command(name='weather', help='Fetch tide, weather, and water temperature data for a location')
async def tide(ctx, *, location: str):
    try:
        city, state = w.parse_location(location)
    except ValueError as e:
        await ctx.send(str(e))
        return

    station_id = w.get_nearest_station(city, state)
    if not station_id:
        await ctx.send(f"Could not find a nearby NOAA station for {city}, {state}.")
        return

    tide_data = w.fetch_tide_predictions(station_id)
    water_temp_data = w.fetch_water_temperature(station_id)
    tide_message = w.format_tide_data(tide_data, water_temp_data, city, state)

    await ctx.send(tide_message)

@cog_ext.cog_slash(name="guide", description="Request a guided dive at a location")
async def guide(ctx, input_str: str):
    location, time = parse_location_time(input_str)
    user = ctx.author
    channel = bot.get_channel(1146846581874770011)
    
    yes_button = create_button(style=ButtonStyle.green, label="Yes")
    no_button = create_button(style=ButtonStyle.red, label="No")
    action_row = create_actionrow(yes_button, no_button)

    
    await ctx.send(
    content=f"{ctx.author.mention} has requested a guided dive at {location} on {time}! Guides: None",
    components=[action_row]
)


    # Store the message ID somewhere for later reference (for example in a dictionary or database)


# @bot.command(name='guide', help='Request a guided dive at a location')
# async def guide(ctx, *, location):
#     user = ctx.author
#     channel = bot.get_channel(1146846581874770011)
#     await channel.send(f"{user.mention} has requested a guided dive at {location}!")

bot.run(TOKEN)
