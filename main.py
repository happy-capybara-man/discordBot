token = "MTI3NTUxNTA2NjA3MDA3NzUxMA.GwiLgq.nOFnXOaQM_KVmtvhTdVTZ0NtymAZN-Zyo4XSqg"
api_key = "RGAPI-0072949e-14e7-4eb4-96ea-577d2e6b1bb3"
puuid = "ohBl_GZMIQzLndSsO22mFm7DTwZTMUZchKwBfIIWcoyEzVQbcF3u9lfPDdVD_SmiWUG9lrrJ-r8npg" #小胖的puuid

import discord
import requests

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents = intents)

@client.event

async def on_ready():
    print(f"目前登入身份 --> {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.content == "幾分了":
        getSummonerBypuuid = "https://tw2.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/"
        getSummonerBypuuid += puuid + "?api_key=" + api_key
        sumid = requests.get(getSummonerBypuuid).json()["id"]
        getEntriesBySumid = "https://tw2.api.riotgames.com/lol/league/v4/entries/by-summoner/"
        getEntriesBySumid += sumid + "?api_key=" + api_key
        json = requests.get(getEntriesBySumid).json()
        for data in json:
            if data['queueType'] == "RANKED_SOLO_5x5":
                await message.channel.send(f"單雙:{data['tier']}-{data['rank']:<4} {data['leaguePoints']:2d}分 wins:{data['wins']:2d} losses:{data['losses']:2d}")
            if data['queueType'] == "RANKED_FLEX_SR":
                await message.channel.send(f"彈性:{data['tier']}-{data['rank']:<4} {data['leaguePoints']:2d}分 wins:{data['wins']:2d} losses:{data['losses']:2d}")

client.run(token)
