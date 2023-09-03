import os, requests, math, pytz, json, discord, re, interactions
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
from discord.ext import commands
from dotenv import load_dotenv
from weather import GetDiveWeather, UpdateStations
from discord_slash import SlashCommand, cog_ext
from discord_slash.utils.manage_components import create_button, create_actionrow
from discord_slash.model import ButtonStyle


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