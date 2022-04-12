import discord
from discord.ext import commands, tasks
import json
import requests
import re
import os

class YtUpdate(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.update_videos.start()

    @commands.command(aliases=['setchannel', 'SetChannel'])
    @commands.has_permissions(administrator=True)
    async def set_channel(self, ctx, channel_url_extension, *, upload_message=None):
        """
        Sets the current text channel up for notifications for a given youtube channel. 
        Optional Second paramater for roles to ping eg. @everyone (input as 'everyone')
        Also accepts a custom message as a second paramater. (without this it will remain blank)
        """
        
        with open("data/ytdata.json", "r") as f:
            data = json.load(f)

        for channel in data:
            if channel == "channel_url_extension":
                data[channel]["discord_channel_id"] = ctx.channel.id
                data[channel]["message"] = upload_message if upload_message is not None else data[channel]["message"]
                try:
                    channel_url = f"https://www.youtube.com/channel/{channel}"
                    response = requests.get(channel_url+"/videos").text
                    latest_video_url = "https://www.youtube.com/watch?v=" + re.search('(?<="videoId":").*?(?=")', response).group()
                except:
                    print(f"failed to get latest video from {channel}.")
                    latest_video_url = ""
                data[channel]["latest_video_url"] = latest_video_url
                with open("data/ytdata.json", "w") as f:
                    json.dump(data, f)
                    await ctx.send(f"Updated {channel}")
                return

        try:
            channel_url = f"https://www.youtube.com/channel/{channel_url_extension}"
            response = requests.get(channel_url+"/videos").text
            latest_video_url = "https://www.youtube.com/watch?v=" + re.search('(?<="videoId":").*?(?=")', response).group()
            discord_channel_id = ctx.channel.id
            discord_server_id = ctx.guild.id
        except Exception as e:
            print(f"failed to get latest video from {channel_url_extension}.")
            print(e)
            latest_video_url = ""

        message = upload_message if upload_message else ""

        data[channel_url_extension] = {
                "latest_video_url": latest_video_url, 
                "message": message, 
                "discord_channel_id": discord_channel_id,
                "discord_server_id": discord_server_id
                }

        with open("data/ytdata.json", "w") as f:
            json.dump(data, f)
            await ctx.send(f"Added {channel_url_extension}")

    @tasks.loop(seconds=30.0, minutes=0, hours=0, count=None)
    async def update_videos(self):
        """
        Checks all youtube channels for updates every 30 seconds and posts notifications whenever a new video has released.
        """

        with open("data/ytdata.json", "r") as f:
            data = json.load(f)

        for channel in data:
            try:
                channel_url = f"https://www.youtube.com/channel/{channel}"
                response = requests.get(channel_url+"/videos").text
            except Exception as e:
                print(f"failed to retrieve data for {channel}")
                print(e)
            try:
                if not str(data[channel]["latest_video_url"]) == latest_video_url:
                    data[str(channel)]["latest_video_url"] = latest_video_url
                    with open("data/ytdata.json", "w") as f:
                        json.dump(data, f)

                    discord_channel = self.client.get_guild(int(data[channel]["discord_server_id"])).get_channel(int(data[channel]["discord_channel_id"]))
                    allowed_mentions = discord.AllowedMentions(everyone=True)

                    await discord_channel.send(content=data[channel]["message"], allowed_mentions=allowed_mentions)
            except Exception as e:
                print(f"failed to display new video")
                print(e)

def setup(client):
    client.add_cog(YtUpdate(client))
