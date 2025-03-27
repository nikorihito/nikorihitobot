import discord
import google.generativeai as genai # type: ignore
from discord.ext import commands, tasks # type: ignore
import json
import os
import re
from datetime import datetime, date
import random
from dotenv import load_dotenv

# ✅ .nikorihito から環境変数読み込み
load_dotenv(dotenv_path=".nikorihito")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY:")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN:")

# ✅ Gemini 設定
genai.configure(api_key=GEMINI_API_KEY)

# ✅ Discord 設定
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ✅ ファイルパス
MEMORY_FILE = "nikorihito_memory.json"
MUTE_FILE = "nikorihito_mute.json"
OMIKUJI_LOG_FILE = "omikuji_log.json"
REMINDER_FILE = "nikorihito_reminders.json"
SLEEP_FILE = "nikorihito_sleep.json"
SETTINGS_FILE = "nikorihito_settings.json"
MORNING_LOG_FILE = "morning_log.json"

# ✅ データロード＆保存
def load_json(path):
    return json.load(open(path, "r", encoding="utf-8")) if os.path.exists(path) else {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

chat_history = load_json(MEMORY_FILE)
mute_status = load_json(MUTE_FILE)
omikuji_log = load_json(OMIKUJI_LOG_FILE)
reminders = load_json(REMINDER_FILE)
sleep_data = load_json(SLEEP_FILE)
user_settings = load_json(SETTINGS_FILE)

# ✅ デフォルト設定
DEFAULT_SETTINGS = {
    "language": "日本語",
    "morning_message": True,
}

def get_user_settings(user_id):
    return user_settings.get(str(user_id), DEFAULT_SETTINGS.copy())

def update_user_settings(user_id, key, value):
    if str(user_id) not in user_settings:
        user_settings[str(user_id)] = DEFAULT_SETTINGS.copy()
    user_settings[str(user_id)][key] = value
    save_json(SETTINGS_FILE, user_settings)

# ✅ 起動イベント
@bot.event
async def on_ready():
    await bot.tree.sync()
    reminder_loop.start()
    morning_message_loop.start()
    print(f"{bot.user} がオンラインになったぜ！🔥 ニコリ！！")

# 🎂 誕生日
@bot.tree.command(name="nikorihito_birthday", description="nikorihitoが誕生日を祝ってくれます")
async def nikorihito_birthday(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"{interaction.user.mention}の誕生日を全力でお祝いするニコリ！！🎉🎂✨\n"
        "ケーキ🎂とビーフシチュー🍲を召し上がれニコリ！！\n"
        "🎵 [っていうことでゆったり系のバースデーソングで誕生日を限界までお祝いしよう！！](http://nikorihito.com/wp-content/uploads/2025/03/はっぴいばあすでいつーゆー.mp3)"
    )

# 🎴 おみくじ
@bot.tree.command(name="nikorihito_omikuji", description="1日1回おみくじを引けます")
async def nikorihito_omikuji(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    today = datetime.now().strftime("%Y-%m-%d")
    if omikuji_log.get(user_id) == today:
        await interaction.response.send_message(f"{interaction.user.mention}、今日はもう引いてるニコリ！！")
        return
    result = random.choice([
        "🌟大吉ニコリ！！最高の煮込み日和だニコリ！！",
        "🎉中吉ニコリ！！いいことありそうニコリ！！",
        "😌小吉ニコリ！！のんびりでいこうニコリ！！",
        "🤔末吉ニコリ！！焦らずゆっくりニコリ！！",
        "🌧凶ニコリ！！でもビーフシチューで元気出るニコリ！！🍚"
    ])
    omikuji_log[user_id] = today
    save_json(OMIKUJI_LOG_FILE, omikuji_log)
    await interaction.response.send_message(f"{interaction.user.mention}の今日の運勢は...\n{result}")

# 🔇 ミュート
@bot.tree.command(name="mute", description="nikorihitoをミュートにできます")
async def mute(interaction: discord.Interaction):
    mute_status["muted"] = True
    save_json(MUTE_FILE, mute_status)
    await interaction.response.send_message("しばらく黙っておくニコリ…😶")

@bot.tree.command(name="mute_off", description="nikorihitoのミュートを解除できます")
async def mute_off(interaction: discord.Interaction):
    mute_status["muted"] = False
    save_json(MUTE_FILE, mute_status)
    await interaction.response.send_message("やったー！！しゃべれるようになったニコリ！！🍲")

def ask_nikorihito(user_id, user_input, user_name):
    uid = str(user_id)

    # ✅ ユーザーの設定から言語を取得（初期値は「日本語」）
    settings = get_user_settings(uid)
    language = settings.get("language", "日本語")

    # ✅ 言語に応じてプロンプトを切り替え
    if language == "English":
        prompt = f"""
You are 'nikorihito'! You speak in a cheerful tone, ending your sentences with "NIKORI!!".
You're a bright character who loves stews and Minecraft, and you have lots of unique friends!

● Your main friends:
- Karafuru-hito: super lively and loves adventures! His builds are extremely colorful… but kind of bad!
- Norinori-hito: always hyper and digs while dancing!
- Hiyahiya-hito: calm and cool, but super lazy. Complains a lot.
- Gorogoro-kun: loves rolling around! Often falls to his doom.
- Guruguru-kun: lives for spinning. Total minecart maniac.
- AchiAchi-kun: a fire master who often sets himself on fire. His body is so hot, meat cooks on contact.
- Suyasuya-hito: mostly sleeping. Says cute things in his sleep. Builds insane structures when dreaming.
- Batabata-kun: always running around, super loud footsteps.
- Monokuro-kun: loves black & white worlds. Shader pack wizard.
- Tsurutsuru-kun: obsessed with TNT. Always messing things up.
- Moyamoya-hito: always getting lost. Constantly thinking and looking confused.

{user_name} said:
{user_input}

Respond cheerfully in English as 'nikorihito', ending with 'NIKORI!!'.
"""


    else:
        prompt = f"""
お前は『nikorihito』だ！一人称は僕、語尾は「ニコリ！！」で話すこと！
煮込み料理とマイクラが大好きで、友達がいっぱいいる明るいキャラ！

●主な友達：
- カラフルヒト：にぎやかで冒険大好き！作る建築がカラフルすぎる割には下手！
- ノリノリヒト：いつもハイテンション！踊りながら掘りまくる！
- ヒヤヒヤヒト：冷静沈着、でもめんどくさがり。よく文句言う。
- ゴロゴロ君：ゴロゴロ転がるのが大好き！落下事故率高め。
- ぐるぐる君：回転に命をかける。トロッコマニア。
- アチアチ君：火の扱いはプロ！でもよく燃える。体の体温が高すぎて肉が焼ける
- すやすやヒト：基本寝てる。寝言がかわいい。寝るとすごすぎる建築を作り出す。
- バタバタ君：いつも走ってる、足音うるさい。
- モノクロ君：白黒の世界が好き。影MOD職人。
- つるつる君：TNTが大好き。いつもやらかす。
- もやもやヒト：よく迷子になる。いつも何かを考えてもやもやしてる。

{user_name}がこう言ったニコリ：
{user_input}
"""


    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(prompt)

        # ✅ 言語に応じて語尾を追加（日本語は「ニコリ！！」、英語は「NIKORI!!」）
        return response.text.strip() + (" NIKORI!!" if language == "English" else " ニコリ！！")

    except Exception as e:
        print("エラー:", e)

        # ✅ Geminiの回数制限の場合は寝落ちモード（共通）
        if "quota" in str(e).lower() or "exceeded" in str(e).lower():
            today = date.today().isoformat()
            if uid not in sleep_data:
                sleep_data[uid] = {}
            count = sleep_data[uid].get(today, 0)
            sleep_lines = [
                "今日は疲れたから寝るニコリ...また明日話そニコリ！！💤",
                "勘弁してよ、眠すぎるニコリ、しゃべらないで......💤💤",
                "ぴえん、僕が眠いのが伝わらないなんて、バサッ(布団を頭からかぶる)💤💤💤",
                "グーピーグーピー（熟睡している）😴😴😴"
            ]
            line = sleep_lines[min(count, len(sleep_lines) - 1)]
            sleep_data[uid][today] = count + 1
            save_json(SLEEP_FILE, sleep_data)
            return line

        # ✅ その他のエラー（API落ちなど）は固定返答
        return "エラーが発生したニコリ！！💦"


# 📩 メッセージ受信
@bot.event
async def on_message(message):
    if message.author == bot.user or not message.content.strip():
        return
    if mute_status.get("muted", False):
        return
    if bot.user.mentioned_in(message):
        user_input = re.sub(rf"<@!?{bot.user.id}>", "", message.content).strip()
        user_input = re.sub(r"##.*?##", "", user_input).strip()
        if user_input:
            reply = ask_nikorihito(message.author.id, user_input, message.author.display_name)
            await message.channel.send(reply)
    await bot.process_commands(message)

# ⏰ リマインダー
@bot.tree.command(name="nikorihito_reminder", description="リマインダーを登録できます")
async def nikorihito_reminder(interaction: discord.Interaction, time: str, content: str):
    user_id = str(interaction.user.id)
    if user_id not in reminders:
        reminders[user_id] = []
    reminders[user_id].append({"time": time, "content": content})
    save_json(REMINDER_FILE, reminders)
    await interaction.response.send_message(f"⏰ {time} に『{content}』をリマインドするニコリ！！")

@tasks.loop(seconds=60)
async def reminder_loop():
    now = datetime.now().strftime("%H:%M")
    for user_id, user_reminders in reminders.items():
        for r in user_reminders:
            if r["time"] == now:
                try:
                    user = await bot.fetch_user(int(user_id))
                    await user.send(f"⏰ リマインダーのお時間ニコリ！『{r['content']}』だニコリ！！")
                except:
                    print(f"ユーザー {user_id} にDM送れなかったニコリ…")

# 🌅 朝の挨拶
@tasks.loop(minutes=1)
async def morning_message_loop():
    now = datetime.now()
    if now.hour == 6 and now.minute == 0:
        for user_id, settings in user_settings.items():
            if settings.get("morning_message", True):
                try:
                    user = await bot.fetch_user(int(user_id))
                    await user.send("🌅 おはようニコリ！！マイクラの話しよう！！ついさっき朝ごはんにおでん食べたニコリ！！🫕")
                except:
                    print(f"ユーザー {user_id} にDM送れなかったニコリ…")
        for uid in sleep_data:
            sleep_data[uid] = {}
        save_json(SLEEP_FILE, sleep_data)
        print("💤 寝データをリセットしたニコリ！！")

# 🎄 クリスマス
@bot.tree.command(name="nikorihito_chrismas", description="クリスマス気分を楽しもう！🎄")
async def nikorihito_chrismas(interaction: discord.Interaction):
    await interaction.response.send_message(
        "**🎄 メリークリスマスニコリ！！ 🎄**\n"
        "煮込みながら聴きたい名曲ニコリ〜〜！！🎶\n"
        "[🎵 クリスマスソングはこちらニコリ](http://nikorihito.com/wp-content/uploads/2025/03/サンタは中央線でやってくる.mp3)"
    )

# 🎍 お正月
@bot.tree.command(name="nikorihito_newyear", description="新年をお祝いするニコリ！！🎍")
async def nikorihito_newyear(interaction: discord.Interaction):
    await interaction.response.send_message(
        "**🎍 あけましておめでとうニコリ！！ 🎍**\n"
        "今年も一緒にマイクラと煮込みを満喫するニコリ！！🔥🔥\n"
        "[っていうことで特製お正月画像はこちらニコリ！！](https://nikorihito.com/wp-content/uploads/2025/03/osyougatsu4.png)"
    )


# 🛠️ 設定
@bot.tree.command(name="settings", description="nikorihitoの設定を変更できます")
async def settings(interaction: discord.Interaction, language: str = None, morning_message: bool = None):
    uid = str(interaction.user.id)
    if uid not in user_settings:
        user_settings[uid] = DEFAULT_SETTINGS.copy()
    if language:
        user_settings[uid]["language"] = language
    if morning_message is not None:
        user_settings[uid]["morning_message"] = morning_message
    save_json(SETTINGS_FILE, user_settings)
    await interaction.response.send_message(f"設定を更新したニコリ！！\n現在の設定：{user_settings[uid]}")

# ✅ 起動！
bot.run(DISCORD_BOT_TOKEN)
