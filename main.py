api_key = "RGAPI-075db9c0-e2a7-41c6-9d2c-c87e0da3bf02"
puuid = "M94cRgHLx2dzGy9wFWjL_b0srRmlDZZv5shiV-EK1Z7VcmWXt7RoDnLdqReDRTX0DPDEEf_0aUZ9hg" #小胖的puuid
import requests

getSummonerBypuuid = "https://tw2.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/"
getSummonerBypuuid += puuid + "?api_key=" + api_key
sumid = requests.get(getSummonerBypuuid).json()["id"]
getEntriesBySumid = "https://tw2.api.riotgames.com/lol/league/v4/entries/by-summoner/"
getEntriesBySumid += sumid + "?api_key=" + api_key

data = requests.get(getEntriesBySumid).json()[1]


print(f"{data["tier"]}-{data["rank"]}")