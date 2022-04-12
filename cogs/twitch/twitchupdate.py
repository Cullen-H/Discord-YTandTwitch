import os
import json
import requests
from discord.ext import tasks, commands
from twitchAPI.twitch import Twitch
from discord.utils import get

from botcfg import TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET

twitch = Twitch(TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET)
twitch.authenticate_app([])
TWITCH_STREAM_API_ENDPOINT_V5 = "https://api.twitch.tv/kraken/streams/{}"
API_HEADERS = {
        'Client-ID': TWITCH_CLIENT_ID,
        'Accept': 'application/vnd.twitchtv.v5+json'
        }

def get_stream(user):
    try:
        userid = twitch.get_users(logins=[user])['data'][0]['id']
        url = TWITCH_STREAM_API_ENDPOINT_V5.format(userid)
        try:
            response = requests.Session().get(url, headers=API_HEADERS).json()
            if 'stream' in response:
                return response["stream"]
            return None
        except Exception as e:
            print(f"Failed to get user data for {user}. Exception: {e}")
            return None
    except IndexError:
        return None

def init_startup_json():
    with open("data/twitchdata.json", "r") as f:
        data = json.load(f)

    for streamer in data:
        data[streamer]["is_live"] = 0 if data[streamer]["is_live"] else 1

    with open("data/twitchdata.json", "w") as f:
        json.dump(data, f)

class TwitchUpdate(commands.Cog):
    def __init__(self, client):
        self.client = client
        init_startup_json()
        self.update_streams.start()

    @commands.command(aliases=['setstreamer', 'SetStreamer'])
    @commands.has_permissions(administrator=True)
    async def set_streamer(self, ctx, twitch_name, stream_url, discord_channel_id, role_to_mention):
        with open("data/twitchdata.json", "r") as f:
            data = json.load(f)

        for streamer in data:
            if streamer == twitch_name:
                data[twitch_name]["discord_channel_id"] = discord_channel_id
                data[twitch_name]["role_to_mention"] = role_to_mention
                data[twitch_name]["stream_url"] = stream_url
                try:
                    with open("data/twitchdata.json", "r") as f:
                        json.dump(data, f)
                except Exception as e:
                    print("failed to update twitchdata.json. Exception: ", e)
                return
        discord_server_id = ctx.guild.id
        data[twitch_name] = {
                "discord_channel_id": discord_channel_id,
                "discord_server_id": discord_server_id,
                "role_to_mention": role_to_mention,
                "stream_url": stream_url,
                "is_live": 0
                }

        with open("data/twitchdata.json", "w") as f:
            json.dump(data, f)
            await ctx.send(f"Added {twitch_name}")
    
    @tasks.loop(seconds=30.0, minutes=0, hours=0, count=None)
    async def update_streams(self):
        with open("data/twitchdata.json", "r") as f:
            data = json.load(f)

        for streamer in data:
            stream = get_stream(streamer)
            if stream:
                discord_server = self.client.get_guild(data[streamer]["discord_server_id"])
                discord_channel = discord_server.get_channel(int(data[streamer]["discord_channel_id"]))
                if not data[streamer]["is_live"]:
                    data[streamer]["is_live"] = 1
                    allowed_mentions = discord.AllowedMentions(everyone=True)
                    await discord_channel.send(content=f'''Hey @{data[streamer]["role_to_mention"]} {streamer} is live on Twitch!
                            {stream["title"]} 
                            - {stream["game_name"]}
                            {data[streamer]["stream_url"]}''', 
                            allowed_mentions=allowed_mentions)
            else:
                # set is_live to 0 if it is 1
                if data[streamer]["is_live"]:
                    data[streamer]["is_live"] = 0 
        with open("data/twitchdata.json", "w") as f:
            json.dump(data, f)

def setup(client):
    client.add_cog(TwitchUpdate(client))
