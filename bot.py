import discord
from discord import app_commands
from discord.ext import commands
import requests
import time
import os
import asyncio
import re
import unicodedata
import sqlite3
from urllib.parse import quote
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
    "": "vN9r5-fJWuzCHXE-OK2jiT5p_2U1D7FEATM_eZvybEpH5hnPRpTQV_bgBf9m63uM33v3HSMTSQpxPg",#小胖
    "liu"   : "FT9HpjQWcD1eXSrXI8rVFcWFxP82FIVgU2WBK0r7YKmKy-RJ7gATKXOfseo0-mX2f1IA73AO8KVHAg",
    "su"    : "3LMV8gzK6z5CHSlL4C0dZHxCnybF3WUZehNojvlpQGI-PmwHRshvqlLIBPqqh-x8lws7oQ63QZJu6Q",
    "kuo"   : "P4-_iHnZTud68GEpZJLvwiiH7MGItNN8CLVEpt1UT9vr9DVozC1zwh7C2ExgC52WrS_olju9q4V5hQ",
    "char"  : "dVMCq0inlQYVcfg4_jwHi1JftA82SSHjAgY2-6dnb-g-MmpFkdQgHo-vTOAtDO7MA4a0eSz2ItiQgA",
    "ryu"   : "h0F2CquJl5RMPd2TjACP-tQBQyPGYs5rbMYlWyEV7mSfs6FgxL2Z6um62x5n26F4dMxpARm4zBoPZQ",
    "yu"    : "Q7nquiLWHfe99O1HddcqSBQR6mjlM99h0xnJf96ia02IEe2PLJhJrmuuqA8Scmz59PINJjv3Esd0aw",
    "wei"   : "8IwVNRu5L07KihwDKwaeRWOKCxm-D2FnMJ4ZAt-qCI6uPSFt-N7hsszJ-8m020vUk6B9-l9lrbP_tg",
}

# 額外綁定的帳號 (小帳)：key -> [(顯示名稱, LoL puuid, TFT puuid)]
extra_accounts = {
    "su": [
        ("kyri#2000",
         "65fqETPUd0l9__nai2Kp0X5sqDBGakXSh6fyld1B95J3y-ggqHw1Ev4xKKgajxE2rbzvQNGCUw55cA",
         "2dNw-il8iPJEYANM51KMk8NlhkC6jo7eK2wn3VmGeBHODDARAywv8UBd31YyId0rm5X-wpGWHbe6DA"),
    ],
}

# 名稱對應表 (給 slash command 和 on_message 共用)
name_map = {
    "": "小胖",
    "liu": "強劉",
    "su": "QOQ",
    "kuo": "郭70",
    "char": "查爾斯",
    "ryu": "警官",
    "yu": "小吉",
    "wei": "不打LOL然後來玩這個",
}

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def get_account_by_riot_id(game_name, tag_line, api_key):
    # Account-V1 用區域路由 (台服屬於 asia)，PUUID 會依 API key 加密，所以 LoL / TFT 要各查一次
    url = (
        "https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/"
        f"{quote(game_name)}/{quote(tag_line)}?api_key={api_key}"
    )
    res = requests.get(url)
    if res.status_code != 200:
        return None
    return res.json()

# 偵測伺服器時的嘗試順序 (台服優先)，以及各伺服器對應的區域路由 (給 TFT match 用)
PLATFORMS = ["tw2", "kr", "jp1", "sg2", "na1", "euw1", "eun1", "oc1", "br1", "la1", "la2", "tr1", "ru", "vn2", "ph2", "th2"]
MATCH_ROUTING = {
    "tw2": "sea", "sg2": "sea", "vn2": "sea", "ph2": "sea", "th2": "sea", "oc1": "sea",
    "kr": "asia", "jp1": "asia",
    "na1": "americas", "br1": "americas", "la1": "americas", "la2": "americas",
    "euw1": "europe", "eun1": "europe", "tr1": "europe", "ru": "europe",
}

def fetch_entries(platform, kind, puuid, api_key):
    path = "lol/league/v4/entries/by-puuid" if kind == "lol" else "tft/league/v1/by-puuid"
    res = requests.get(f"https://{platform}.api.riotgames.com/{path}/{puuid}?api_key={api_key}")
    if res.status_code != 200:
        return None
    return res.json()

def detect_platform(puuid, puuid_tft=None):
    # 依序找出玩家有牌位資料的伺服器，回傳 (platform, json_lol, json_tft)
    for platform in PLATFORMS:
        json_lol = fetch_entries(platform, "lol", puuid, api_key_lol)
        json_tft = fetch_entries(platform, "tft", puuid_tft, api_key_TFT) if puuid_tft else None
        if json_lol or json_tft:
            return platform, json_lol or [], json_tft or []
    return "tw2", [], []

def get_ranked_embed(puuid, puuid_tft=None, player_name="某人", platform=None):
    if platform:
        json_lol = fetch_entries(platform, "lol", puuid, api_key_lol) or []
        json_tft = (fetch_entries(platform, "tft", puuid_tft, api_key_TFT) or []) if puuid_tft else None
    else:
        platform, json_lol, json_tft = detect_platform(puuid, puuid_tft)
    match_region = MATCH_ROUTING.get(platform, "sea")

    # 創建 Embed
    embed = discord.Embed(
        title=f"{player_name} 的:" + ("" if platform == "tw2" else f" ({platform})"),
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
        # 區域路由依玩家伺服器決定
        try:
            match_ids_url = f"https://{match_region}.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid_tft}/ids?start=0&count=5&api_key={api_key_TFT}"
            match_ids = requests.get(match_ids_url).json()
            
            if isinstance(match_ids, list) and len(match_ids) > 0:
                history_text = ""
                for index, m_id in enumerate(match_ids):
                    # 抓取單場詳細資料
                    detail_url = f"https://{match_region}.api.riotgames.com/tft/match/v1/matches/{m_id}?api_key={api_key_TFT}"
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

    if not embed.fields:
        embed.description = "查無排位資料 (可能還沒打排位，或不在支援的伺服器)"

    return embed

FAKER_ID = ("Hide on bush", "KR1")
_faker_cache = {"games": None, "time": 0}

def count_ranked_games(puuid, platform=None):
    # LoL 排位 (單雙 + 彈性) 總場數
    if platform:
        entries = fetch_entries(platform, "lol", puuid, api_key_lol) or []
    else:
        _, entries, _ = detect_platform(puuid)
    return sum(e.get("wins", 0) + e.get("losses", 0) for e in entries)

def get_faker_games():
    # Faker 在韓服，快取 10 分鐘避免一直打 API
    if _faker_cache["games"] is None or time.time() - _faker_cache["time"] > 600:
        account = get_account_by_riot_id(*FAKER_ID, api_key_lol)
        if not account:
            return None
        _faker_cache["games"] = count_ranked_games(account["puuid"], "kr")
        _faker_cache["time"] = time.time()
    return _faker_cache["games"]

def get_faker_compare_embed(target_key):
    p_name = name_map.get(target_key, target_key)
    total = count_ranked_games(puuidDict_lol[target_key])
    for _, alt_lol, _ in extra_accounts.get(target_key, []):
        total += count_ranked_games(alt_lol)
    faker = get_faker_games()
    if not faker:
        return None
    return discord.Embed(
        title="🆚 對比 Faker",
        description=f"{p_name} 排位總場數 **{total}** 場 (所有帳號、單雙+彈性)\n"
                    f"Faker 排位總場數 **{faker}** 場\n"
                    f"→ 是 Faker 的 **{total / faker * 100:.1f}%**",
        color=discord.Color.gold(),
    )

def get_player_embeds(target_key):
    # 主帳號 + 額外綁定的帳號，各一個 embed
    p_name = name_map.get(target_key, target_key)
    embeds = [get_ranked_embed(puuidDict_lol[target_key], puuidDict_TFT.get(target_key), player_name=p_name)]
    for alt_name, alt_lol, alt_tft in extra_accounts.get(target_key, []):
        embeds.append(get_ranked_embed(alt_lol, alt_tft, player_name=f"{p_name} ({alt_name})"))
    if target_key == "su":
        try:
            compare = get_faker_compare_embed(target_key)
            if compare:
                embeds.append(compare)
        except Exception as e:
            print(f"計算 Faker 對比失敗: {e}")
    return embeds

# ========== GG 統計 ==========

GG_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gg_counts.db")
# 單獨出現的 gg (不含 egg 這種英文字中間)，前後是中文也算
GG_PATTERN = re.compile(r"(?<![a-z0-9_])gg+(?:wp|ez|s)?(?![a-z0-9_])", re.IGNORECASE)
# 不算數的內容：程式碼、網址、<@提及> / <:自訂表情:>、:表情名稱:
GG_IGNORE = re.compile(r"```.*?```|`[^`]*`|https?://\S+|<[^>]*>|:[a-z0-9_]+:", re.IGNORECASE | re.DOTALL)

# NFKC 搞不定的 G 變體：區域指示符 🇬、小型大寫 ɢ、方塊字母 🅶
GG_EXTRA_MAP = str.maketrans({"\U0001F1EC": "g", "\u0262": "g", "\U0001F176": "g", "\U0001F136": "g"})

def normalize_gg_text(text):
    # NFKC：全形 ＧＧ、圓圈 ⓖ、數學花體 𝓖𝓖 等都會轉成一般字母
    text = unicodedata.normalize("NFKC", text).translate(GG_EXTRA_MAP)
    # 去掉零寬字元等不可見的格式字元 (g​g 這種藏字)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Cf")
    return text.casefold()

def count_gg(text):
    # 每個分開的 GG 各算一次，連在一起的 GGGG 算一次，沒有上限
    return len(GG_PATTERN.findall(GG_IGNORE.sub(" ", normalize_gg_text(text))))

def gg_db():
    conn = sqlite3.connect(GG_DB)
    conn.execute("CREATE TABLE IF NOT EXISTS gg (guild_id INTEGER, user_id INTEGER, count INTEGER, PRIMARY KEY (guild_id, user_id))")
    # 已經觸發過的彩蛋，每個數字只觸發一次 (刪訊息掉回去再衝上來也不會重複)
    conn.execute("CREATE TABLE IF NOT EXISTS gg_milestones (guild_id INTEGER, number INTEGER, user_id INTEGER, PRIMARY KEY (guild_id, number))")
    return conn

def add_gg(guild_id, user_id, n=1):
    # n 可以是負的 (訊息被刪或被改)，次數最低到 0
    with gg_db() as conn:
        conn.execute(
            "INSERT INTO gg VALUES (?, ?, MAX(?, 0)) ON CONFLICT(guild_id, user_id) DO UPDATE SET count = MAX(count + ?, 0)",
            (guild_id, user_id, n, n),
        )

def get_gg_ranking(guild_id):
    with gg_db() as conn:
        return conn.execute("SELECT user_id, count FROM gg WHERE guild_id = ? ORDER BY count DESC", (guild_id,)).fetchall()

def get_gg_total(guild_id):
    with gg_db() as conn:
        return conn.execute("SELECT COALESCE(SUM(count), 0) FROM gg WHERE guild_id = ?", (guild_id,)).fetchone()[0]

def build_gg_ranking_embed(guild_id):
    ranking = get_gg_ranking(guild_id)
    if not ranking:
        return None
    total = sum(c for _, c in ranking)
    lines = [f"**{i}.** <@{uid}> - {c} 次" for i, (uid, c) in enumerate(ranking[:10], 1)]
    return discord.Embed(
        title="🏳️ GG 次數排行",
        description="\n".join(lines) + f"\n\n全 server 共 **{total}** 次",
        color=discord.Color.orange(),
    )

# ========== GG 彩蛋 (全 server 總次數跨過特別數字時觸發) ==========

GG_SPECIAL = {
    87: "很87",
    520: "我愛GG",
    666: "666",
    777: "中獎",
    888: "發",
    1314: "一生一世",
    2486: "二四八六",
}

def gg_milestone_text(n):
    # 特別數字回傳附註 (可能是空字串)，不是特別數字回傳 None
    if n in GG_SPECIAL:
        return GG_SPECIAL[n]
    digits = str(n)
    if n == 100 or n % 1000 == 0:
        return ""
    if n >= 111 and len(set(digits)) == 1:
        return ""
    if n >= 123 and "123456789".startswith(digits):
        return ""
    return None

def claim_gg_milestones(guild_id, user_id, before, after):
    # 找出這次從 before 跨到 after 經過的特別數字，記下來並回傳還沒觸發過的
    hits = [(n, t) for n in range(before + 1, after + 1) if (t := gg_milestone_text(n)) is not None]
    claimed = []
    with gg_db() as conn:
        for n, t in hits:
            cur = conn.execute("INSERT OR IGNORE INTO gg_milestones VALUES (?, ?, ?)", (guild_id, n, user_id))
            if cur.rowcount:
                claimed.append((n, t))
    return claimed

async def record_gg(message, n):
    # 加 GG 次數；跨過特別數字就講一聲 + 自動貼 /gg 排行
    guild_id = message.guild.id
    before = get_gg_total(guild_id)
    add_gg(guild_id, message.author.id, n)
    if n <= 0:
        return
    claimed = claim_gg_milestones(guild_id, message.author.id, before, get_gg_total(guild_id))
    if not claimed:
        return
    # 一次跨好幾個只講最後一個
    num, text = claimed[-1]
    msg = f"第 {num} 次 GG 了" + (f"，{text}" if text else "") + f"（{message.author.display_name} 打的）"
    ranking = build_gg_ranking_embed(guild_id)
    await message.channel.send(msg, embed=ranking, allowed_mentions=discord.AllowedMentions.none())

MY_GUILD = discord.Object(id=668344492541083648)

@bot.event
async def on_ready():
    print(f"目前登入身份 --> {bot.user}")
    # 同步 slash commands 到指定伺服器 (立即生效)
    try:
        # 指令是用 @bot.tree.command 註冊的全域指令，要先複製到伺服器，sync(guild=...) 才會帶上它們
        bot.tree.copy_global_to(guild=MY_GUILD)
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
    app_commands.Choice(name="不打LOL然後來玩這個", value="wei"),
])
async def rank_command(interaction: discord.Interaction, player: app_commands.Choice[str]):
    target_key = player.value
    
    if target_key in puuidDict_lol:
        # 先回應「正在查詢」
        await interaction.response.defer()
        
        embeds = await asyncio.to_thread(get_player_embeds, target_key)
        await interaction.followup.send(embeds=embeds)
    else:
        await interaction.response.send_message("找不到該玩家的資料", ephemeral=True)

@bot.tree.command(name="search", description="用 Riot ID (名稱#標籤) 查詢任意玩家的牌位")
@app_commands.describe(riot_id="例如：Hide on bush#KR1")
async def search_command(interaction: discord.Interaction, riot_id: str):
    riot_id = riot_id.strip().replace("＃", "#")
    if "#" not in riot_id:
        await interaction.response.send_message("格式錯誤，請輸入 `名稱#標籤`，例如 `Hide on bush#KR1`", ephemeral=True)
        return

    game_name, tag_line = (s.strip() for s in riot_id.rsplit("#", 1))
    if not game_name or not tag_line:
        await interaction.response.send_message("格式錯誤，請輸入 `名稱#標籤`，例如 `Hide on bush#KR1`", ephemeral=True)
        return

    await interaction.response.defer()

    account_lol = get_account_by_riot_id(game_name, tag_line, api_key_lol)
    if not account_lol:
        await interaction.followup.send(f"找不到 `{game_name}#{tag_line}` 這個玩家")
        return

    account_tft = get_account_by_riot_id(game_name, tag_line, api_key_TFT) if api_key_TFT else None
    p_tft = account_tft["puuid"] if account_tft else None
    p_name = f"{account_lol['gameName']}#{account_lol['tagLine']}"

    embed = await asyncio.to_thread(get_ranked_embed, account_lol["puuid"], p_tft, p_name)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="gg", description="查看 server 裡講 GG 的次數排行")
async def gg_command(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("這個指令只能在 server 使用", ephemeral=True)
        return
    embed = build_gg_ranking_embed(interaction.guild.id)
    if not embed:
        await interaction.response.send_message("還沒有人講過 GG")
        return
    await interaction.response.send_message(embed=embed, allowed_mentions=discord.AllowedMentions.none())

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
            "**/search [名稱#標籤]** - 用 Riot ID 查詢任意玩家的牌位\n"
            "**/gg** - 查看講 GG 的次數排行 (全 server 次數到特別數字會觸發彩蛋 🥚)\n"
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

# ========== GG 計數 (編輯訊息只加不減，刪除訊息不扣) ==========

# 每則訊息目前算過幾次，避免同一則訊息改來改去重複加分 (只留最近 5000 則)
_gg_counted = {}

def remember_gg(message_id, n):
    _gg_counted[message_id] = n
    if len(_gg_counted) > 5000:
        _gg_counted.pop(next(iter(_gg_counted)))

@bot.event
async def on_message_edit(before, after):
    # 只有 bot 快取裡的訊息 (bot 上線後收到的最近 1000 則) 會觸發
    if after.guild and not after.author.bot:
        counted = _gg_counted.get(after.id, count_gg(before.content))
        now = count_gg(after.content)
        if now > counted:
            await record_gg(after, now - counted)
            remember_gg(after.id, now)

# ========== Message Listener (保留原本功能) ==========

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # 統計 GG (機器人不算)
    if message.guild and not message.author.bot:
        gg_count = count_gg(message.content)
        if gg_count:
            await record_gg(message, gg_count)
            remember_gg(message.id, gg_count)
    
    # 去除空格並轉小寫，方便比對
    msg = message.content.replace(" ", "").lower()

    # 檢查指令是否包含 "幾分了" 並且後面有接名字
    if msg.startswith("幾分了"):
        target_key = msg.replace("幾分了", "") # 取得名字部分 (如 su, liu)
        
        if target_key in puuidDict_lol:
            p_name = name_map.get(target_key, target_key)
            
            # 發送正在查詢的訊息 (因為抓歷史紀錄會花個 1-2 秒)
            temp_msg = await message.channel.send(f"正在查詢 {p_name} 的資料與戰棋歷史，請稍等...")
            
            embeds = await asyncio.to_thread(get_player_embeds, target_key)
            
            await temp_msg.delete() # 刪除提示訊息
            await message.channel.send(embeds=embeds)

bot.run(token)