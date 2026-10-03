import discord
from discord import app_commands
from discord.ext import commands
import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("DISCORD_TOKEN")
api_key_lol = os.getenv("API_KEY_LOL")
api_key_TFT = os.getenv("API_KEY_TFT")

puuidDict_lol = {
    "": "ohBl_GZMIQzLndSsO22mFm7DTwZTMUZchKwBfIIWcoyEzVQbcF3u9lfPDdVD_SmiWUG9lrrJ-r8npg",#小胖
    "liu"   : "-6C1MuA4uwMu8HBS6fDPiKOioOZ6fmzDk8eCMbQBIbxXEJc0_P1ITdKKsrTwI0jHrrDnE36ZYj55sQ",
    "su"    : "-mNv0o_XfmjkE2vxmSWqaWkK7H_AkZylOXhkDT6CaZ1JpcLVBVOU_MloZbvi6GvO9VIAOCoK5ynB0w",
    "kuo"   : "TuB7UgTISq-FNjbEbCIACZ4sivw8pFW2z5Knlqjd9sk-r3AJR8EtWdTXvQNn4f6R3DNA0DNtmopQxw",
    "char"  : "IXK9GoHYngIETdVKaBNuGRwc5mBiii6UbfAyIuXxILESpB-rsrAXCjOu0ocnsb_7wfLq0RjsS8X2BA",
    "ryu"   : "X3SuYL5uufpXjCpxdZkys1B3O5EF27DR9JkkTdxhUapf_7B7gX43UAbcDOwD1PZG54EuLvE76U2vtQ",
    "yu"    : "_wmwrD9FBuVRb0VyEFdSRG1KJ_XCwrOFvumEMzXGmm0U0TWXgvwe-b67YlEEk7ecvzdEheDtY7kqEQ",
    "wei"   : "DlvziZF3FdB07g3jNpsJAe4-SCFU9EnjdqKWS1nkek4Ek0_xcCek__AyUTbS1AQAV287tzOHlzcC6w",
}

puuidDict_TFT = {
    "su"    : "3LMV8gzK6z5CHSlL4C0dZHxCnybF3WUZehNojvlpQGI-PmwHRshvqlLIBPqqh-x8lws7oQ63QZJu6Q",
    "yu"    : "Q7nquiLWHfe99O1HddcqSBQR6mjlM99h0xnJf96ia02IEe2PLJhJrmuuqA8Scmz59PINJjv3Esd0aw",
    "char"  : "dVMCq0inlQYVcfg4_jwHi1JftA82SSHjAgY2-6dnb-g-MmpFkdQgHo-vTOAtDO7MA4a0eSz2ItiQgA",
}

# 名稱對應表 (給 slash command 和 on_message 共用)
name_map = {
    "": "小胖",
    "liu": "強劉",
    "su": "QOQ",
    "kuo": "郭70",
    "char": "查爾斯",
    "ryu": "警官",
    "yu": "小吉"
}

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def get_ranked_embed(puuid, puuid_tft=None, player_name="某人"):
    # 1. 取得基本牌位資訊 (維持原樣，使用 tw2)
    getRankedInfo = "https://tw2.api.riotgames.com/lol/league/v4/entries/by-puuid/"
    getTFTRankedInfo = "https://tw2.api.riotgames.com/tft/league/v1/by-puuid/"
    
    getRankedInfo += puuid + "?api_key=" + api_key_lol
    
    json_lol = requests.get(getRankedInfo).json()
    json_tft = None
    
    if puuid_tft:
        getTFTRankedInfo += puuid_tft + "?api_key=" + api_key_TFT
        json_tft = requests.get(getTFTRankedInfo).json()

    # 創建 Embed
    embed = discord.Embed(
        title=f"{player_name} 的:",
        color=discord.Color.blue()
    )
    
    # --- 處理 LOL 牌位 ---
    if isinstance(json_lol, list): # 確保回傳是列表
        for data in json_lol:
            wins = data.get('wins', 0)
            losses = data.get('losses', 0)
            total_games = wins + losses
            win_rate = (wins / total_games * 100) if total_games > 0 else 0
            
            if data['queueType'] == "RANKED_SOLO_5x5":
                embed.add_field(
                    name="單雙",
                    value=f"**{data['tier']} {data['rank']}** - {data['leaguePoints']}分\n"
                          f"戰績: {wins}勝 {losses}敗 ({win_rate:.1f}%)",
                    inline=False
                )
            elif data['queueType'] == "RANKED_FLEX_SR":
                embed.add_field(
                    name="彈性", 
                    value=f"**{data['tier']} {data['rank']}** - {data['leaguePoints']}分\n"
                          f"戰績: {wins}勝 {losses}敗 ({win_rate:.1f}%)",
                    inline=False
                )

    # --- 處理 TFT 牌位與歷史戰績 ---
    if json_tft and isinstance(json_tft, list):
        # A. 顯示 TFT 牌位
        for data in json_tft:
            wins = data.get('wins', 0)
            losses = data.get('losses', 0)
            total_games = wins + losses
            win_rate = (wins / total_games * 100) if total_games > 0 else 0
            
            if data['queueType'] == "RANKED_TFT":
                embed.add_field(
                    name="戰棋", 
                    value=f"**{data['tier']} {data['rank']}** - {data['leaguePoints']}分\n"
                          f"前四: {wins} / {total_games} 場 ({win_rate:.1f}%)",
                    inline=False
                )

        # B. 顯示最近 5 場戰績 (這裡就是你要的新功能)
        # 注意：這裡使用 sea 區域
        try:
            match_ids_url = f"https://sea.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid_tft}/ids?start=0&count=5&api_key={api_key_TFT}"
            match_ids = requests.get(match_ids_url).json()
            
            if isinstance(match_ids, list) and len(match_ids) > 0:
                history_text = ""
                for index, m_id in enumerate(match_ids):
                    # 抓取單場詳細資料
                    detail_url = f"https://sea.api.riotgames.com/tft/match/v1/matches/{m_id}?api_key={api_key_TFT}"
                    detail_res = requests.get(detail_url)
                    
                    if detail_res.status_code == 200:
                        match_data = detail_res.json()
                        participants = match_data['info']['participants']
                        
                        # 找出該玩家的排名
                        for p in participants:
                            if p['puuid'] == puuid_tft:
                                rank = p['placement']
                                
                                if rank == 8:
                                    rank_display = "老8"
                                else:
                                    rank_display = f"第 {rank} 名"
                                
                                history_text += f"`Game {index+1}`: {rank_display}\n"
                                break


                if history_text:
                    embed.add_field(
                        name="最近 5 場戰棋排名",
                        value=history_text,
                        inline=False
                    )
            else:
                embed.add_field(name="最近戰績", value="查無近期比賽紀錄", inline=False)
                
        except Exception as e:
            print(f"抓取戰棋歷史失敗: {e}")
            embed.add_field(name="錯誤", value="無法讀取歷史戰績", inline=False)

    return embed

MY_GUILD = discord.Object(id=668344492541083648)

@bot.event
async def on_ready():
    print(f"目前登入身份 --> {bot.user}")
    # 同步 slash commands 到指定伺服器 (立即生效)
    try:
        synced = await bot.tree.sync(guild=MY_GUILD)
        print(f"已同步 {len(synced)} 個 slash commands 到伺服器")
    except Exception as e:
        print(f"同步指令失敗: {e}")

# ========== Slash Commands ==========

@bot.tree.command(name="rank", description="查詢玩家的 LoL 和 TFT 牌位")
@app_commands.describe(player="選擇要查詢的玩家")
@app_commands.choices(player=[
    app_commands.Choice(name="小胖", value=""),
    app_commands.Choice(name="強劉", value="liu"),
    app_commands.Choice(name="QOQ", value="su"),
    app_commands.Choice(name="郭70", value="kuo"),
    app_commands.Choice(name="查爾斯", value="char"),
    app_commands.Choice(name="警官", value="ryu"),
    app_commands.Choice(name="小吉", value="yu"),
    app_commands.Choice(name="我", value="wei"),
])
async def rank_command(interaction: discord.Interaction, player: app_commands.Choice[str]):
    target_key = player.value
    
    if target_key in puuidDict_lol:
        p_lol = puuidDict_lol[target_key]
        p_tft = puuidDict_TFT.get(target_key)
        p_name = name_map.get(target_key, target_key)
        
        # 先回應「正在查詢」
        await interaction.response.defer()
        
        embed = get_ranked_embed(p_lol, p_tft, player_name=p_name)
        await interaction.followup.send(embed=embed)
    else:
        await interaction.response.send_message("找不到該玩家的資料", ephemeral=True)

@bot.tree.command(name="help", description="顯示所有可用指令")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📖 指令說明",
        description="以下是所有可用的指令：",
        color=discord.Color.green()
    )
    
    # Slash Commands
    embed.add_field(
        name="🔹 Slash Commands (斜線指令)",
        value=(
            "**/rank [玩家]** - 查詢玩家的 LoL 和 TFT 牌位\n"
            "**/help** - 顯示此說明訊息"
        ),
        inline=False
    )
    
    # 文字指令
    player_list = "、".join([name_map[k] if k else "小胖" for k in puuidDict_lol.keys()])
    embed.add_field(
        name="🔹 文字指令",
        value=(
            f"**幾分了[名字]** - 查詢玩家牌位\n"
            f"例如：`幾分了su`、`幾分了liu`\n\n"
            f"**可查詢玩家：** {player_list}"
        ),
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

# ========== Message Listener (保留原本功能) ==========

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # 去除空格並轉小寫，方便比對
    msg = message.content.replace(" ", "").lower()

    # 檢查指令是否包含 "幾分了" 並且後面有接名字
    if msg.startswith("幾分了"):
        target_key = msg.replace("幾分了", "") # 取得名字部分 (如 su, liu)
        
        if target_key in puuidDict_lol:
            # 準備參數
            p_lol = puuidDict_lol[target_key]
            p_tft = puuidDict_TFT.get(target_key) # 如果字典裡沒有這個人(如 liu)會回傳 None
            p_name = name_map.get(target_key, target_key)
            
            # 發送正在查詢的訊息 (因為抓歷史紀錄會花個 1-2 秒)
            temp_msg = await message.channel.send(f"正在查詢 {p_name} 的資料與戰棋歷史，請稍等...")
            
            embed = get_ranked_embed(p_lol, p_tft, player_name=p_name)
            
            await temp_msg.delete() # 刪除提示訊息
            await message.channel.send(embed=embed)

bot.run(token)