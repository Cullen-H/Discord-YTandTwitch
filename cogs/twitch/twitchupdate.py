import os
import json
import requests
from discord.ext import tasks, commands
from discord.utils import get
from botcfg import TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET

def get_oauth_token():
    body = {
            "client_id": TWITCH_CLIENT_ID,
            "client_secret": TWITCH_CLIENT_SECRET,
            "grant_type": "client_credentials"
            }
    response = requests.post("https://id.twitch.tv/oauth2/token", body)
    keys = response.json()
    return keys["access_token"]

def get_stream(user):
    url = "https://api.twitch.tv/helix/streams?user_login="+user
    token = get_oauth_token()

    HEADERS = {
            "Client-ID": client_id,
            "Authorization": "Bearer "+token
            }
    
    try:
        response = requests.get(url, headers=HEADERS).json()
        if len(response['data']) > 0:
            data = response["data"][0]
            return {"title": data["title"], "game_name": data["game_name"]}
    except Exception as e:
        print("Exception while getting stream: ", e)

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
            print(stream)
            if stream and data[streamer]["is_live"] == 0:
                print('New stream found for {}'.format(streamer))
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
