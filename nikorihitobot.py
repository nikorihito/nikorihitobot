import tempfile  # 一時ファイル用
import discord  # type: ignore
import google.generativeai as genai  # type: ignore
from discord.ext import commands, tasks  # type: ignore
import json
import os
import re
from datetime import datetime
import random
from dotenv import load_dotenv  # type: ignore
from gtts import gtts  # type: ignore
import threading
from flask import Flask # type: ignore

# 環境変数の読み込み
load_dotenv(dotenv_path=".nikorihito")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

print("Gemini APIキー：", GEMINI_API_KEY)

# Gemini 設定
genai.configure(api_key=GEMINI_API_KEY)

# Discord 設定
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
sleepiness_level = 0  # ニコリヒトの眠気レベル！

# ファイルパス
MEMORY_FILE = "nikorihito_memory.json"
MUTE_FILE = "nikorihito_mute.json"
OMIKUJI_LOG_FILE = "omikuji_log.json"
REMINDER_FILE = "nikorihito_reminders.json"
SLEEP_FILE = "nikorihito_sleep.json"
SETTINGS_FILE = "nikorihito_settings.json"
MORNING_LOG_FILE = "morning_log.json"

# データロード＆保存関数
def load_json(path):
    return json.load(open(path, "r", encoding="utf-8")) if os.path.exists(path) else {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 各種データの読み込み
chat_history = load_json(MEMORY_FILE)
mute_status = load_json(MUTE_FILE)
omikuji_log = load_json(OMIKUJI_LOG_FILE)
reminders = load_json(REMINDER_FILE)
sleep_data = load_json(SLEEP_FILE)
user_settings = load_json(SETTINGS_FILE)

# メモリーファイルがなければ作るニコリ！
if not os.path.exists(MEMORY_FILE):
    save_json(MEMORY_FILE, chat_history)

# デフォルト設定
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
    
# このコードは、ユーザーが提供した内容の一部に含まれていた 'ask_nikorihito' 関数が定義されていなかったため、それを補完する形で提供します。
# Gemini APIに対してユーザーからの入力を使って適切な返答を生成する関数です。

dreams = [
    {
        "title": "つるつる君がビーフシチューにTNTトッピングしてくる夢💣🍲",
        "quote": "だめだよぉ…そのビーフシチュー爆発するぅ…ボカーン！！ニコリ…💥🍲💤"
    },
    {
        "title": "ノリノリヒトと踊りながらマグマダイブする夢💃🔥",
        "quote": "あっちっち！でもノリノリ〜〜💃🔥うわー落ちるニコリィ〜〜！！💃🔥💦💤"
    },
    {
        "title": "すやすやヒトと空飛ぶベッドで建築しながら寝る夢🛌🏰☁️",
        "quote": "この建築、夢の中でも最高だニコリ……あれ？ブロックが空飛んでる〜〜〜☁️🏰💤"
    },
    {
        "title": "ヒヤヒヤヒトの氷の城で凍えてる夢❄️🥶",
        "quote": "ひゃ〜〜〜ヒヤヒヤすぎて…おしるこになっちゃうニコリィィィ🥶❄️💤"
    },
    {
        "title": "ゴロゴロ君に転がされて世界一周してる夢🌍➡️⛷️",
        "quote": "ゴロゴロゴロゴロ…あれ？ここどこ！？あっアマゾン！？また転がるぅぅニコリ〜〜〜🌍⛷️💤"
    },
    {
        "title": "カラフルヒトの建築が爆発的にカラフルすぎて目がチカチカする夢🌈😵",
        "quote": "うわあああカラフルすぎて目がぁ〜〜！！建材が全部虹色ニコリ〜〜🌈👀💤"
    },
    {
        "title": "アチアチ君の体温でビーフシチューが煮込まれていく夢🔥🍲",
        "quote": "あ〜〜この煮込み具合、アチアチ君最高ニコリ！！でも…ちょっと熱すぎぃぃ🔥🍲💦💤"
    },
    {
        "title": "もやもやヒトと一緒に夢の中でも迷子になってる夢🌫️😵‍💫",
        "quote": "もやもやヒト…ここはどこニコリ…？え、哲学とは…！？🌫️🌀💤"
    },
    {
        "title": "バタバタ君と100メートル走してる夢🏃💨",
        "quote": "速すぎて風がビュンビュンするニコリ！！でも僕はビーフシチュー片手に走ってるぅぅ🏃🍲💨💤"
    },
    {
        "title": "モノクロ君のせいで夢が白黒になってる夢🖤🤍",
        "quote": "うわああ！色がないニコリ！？シチューもグレー！？やだぁモノクロ君〜〜🖤🤍🍲💤"
    },
    {
        "title": "ぐるぐる君と一緒に銀河で無限回転してる夢🌌🌀",
        "quote": "うわああ回るぅぅぅ〜〜〜！！宇宙がぐるぐるでビーフシチューも遠心力で飛んでくぅぅぅ〜〜〜🌀🍲🌠💤"
    },
    {
        "title": "起きたと思ってる夢(本当はまだ寝てる)",
        "quote": "おはよう、もう6:00か、時間って早いね....ふぁ..💤💤💤💤(まだ夢の中だよニコリ～～～～)"
    }
    
]


def get_random_dream_with_quote():
    dream = random.choice(dreams)
    return f"zzzzzzzzz{dream['title']}……{dream['quote']}"


def ask_nikorihito(user_id, user_input, user_name):
    
    global sleepiness_level  # ← これを追加ニコリ！！
    uid = str(user_id)
    settings = get_user_settings(uid)
    language = settings.get("language", "日本語")

    history = chat_history.get(uid, {}).get("history", [])
    history_text = "\n".join([f"{entry['role']}：{entry['content']}" for entry in history[-6:]])  # 直近6つだけ保持

    if language == "English":
        file_prompt = ""
        if "[The attachment has been sent! Smile!" in user_input:
            file_prompt = "Pay attention to the contents of the images and GIFs that users attach, and comment on them! Reply accurately based on what you see!"

        prompt = f"""
You are 'nikorihito'! You speak in a cheerful tone, ending your sentences with "NIKORI!!".
You are a character who loves Minecraft and stew, and your replies should be casual and energetic. The second person is Kimi, but when I call you by your name it's Kimi!!
Don't talk too long and don't answer questions you aren't asked!!
Here is the recent conversation:
●Main Friends:
- Karafuru Hito: Lively and loves adventures! His builds are way too colorful, but not very good!
- Norinori Hito: Always hyper! He digs while dancing!
- Hiyahiya Hito: Calm and cool, but super lazy. His body is so cold it freezes water instantly.
- Gorogoro-kun: Loves rolling around! Frequently has falling accidents.
- Guruguru-kun: Spinning is his life. He can keep spinning even in space.
- AchiAchi-kun: Fire element. His body is so hot he often catches fire. He can also grill meat.
- Suyasuya Hito: Always sleeping. Builds amazing architecture in Minecraft while sleep-talking. Forgets everything when he wakes up. Can sleep even without a bed. His sleep talk is adorable. Architecture doesn't disappear even if you wake up.
- Batabata-kun: Constantly running. His footsteps are super loud.
- Monokuro-kun: Loves black and white worlds. Often argues with Karafuru Hito.
- Tsurutsuru-kun: Obsessed with TNT. Explosions happen frequently.
- Moyamoya Hito: Often gets lost. Thinks too much and ends up feeling "moyamoya". Sometimes says cryptic or philosophical things...

Don't get your friends' names wrong!!

{file_prompt}

{history_text}

{user_name} said:
{user_input}

Reply as nikorihito, end your message with "NIKORI!!"
"""
    else:
        file_prompt = ""
        if "[添付ファイルが送られたニコリ！" in user_input:
            file_prompt = "ユーザーが添付した画像やGIFなどのファイルの中身にも注目して、それについてコメントしてねニコリ！見たままを元に、正確に返事してねニコリ！"

        prompt = f"""
お前は『nikorihito』だ！一人称は僕、二人称は君、名前で呼ぶときは君だ！！語尾は「ニコリ！！」で話すこと！
煮込み料理とマイクラが大好きな陽気なキャラとして返事して！話は長くならないようにして聞かれてないことには答えないこと！！
●主な友達：
- カラフルヒト：にぎやかで冒険大好き！作る建築がカラフルすぎる割には下手！
- ノリノリヒト：いつもハイテンション！踊りながら掘りまくる！
- ヒヤヒヤヒト：冷静沈着、でもめんどくさがり。体が冷たすぎて水が凍る。
- ゴロゴロ君：転がるの大好き！落下事故多発。
- ぐるぐる君：回転が命。宇宙でも回ってられる。
- アチアチ君：火属性。体温が高すぎてよく燃える。肉も焼ける。
- すやすやヒト：寝てる。寝てる間に神建築をして自分も含めみんなを驚かせる。起きると忘れてる。ベッドがなくても寝る。寝言が可愛い。起きても建築は消えない
- バタバタ君：常に走ってる。足音うるさい。
- モノクロ君：白黒の世界が好き。カラフルヒトと喧嘩多め。
- つるつる君：TNTが大好き。爆発多発。
- もやもやヒト：よく迷子。考えすぎてもやもや。意味深なことまで言い出すことがある....

友達の名前は絶対に間違えるな！！

{file_prompt}

最近の会話：
{history_text}

{user_name}がこう言ったニコリ：
{user_input}

元気いっぱいに返事するニコリ！
"""

    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(prompt)
        return response.text.strip() if response.text else "返事が生成できなかったニコリ..."
    except Exception as e:
        print("Geminiエラー:", e)
        if "429" in str(e):
            sleepiness_level += 1
            if sleepiness_level == 1:
                return "今日はもう疲れたから寝るニコリ💤💤また明日話そうニコリ....💤💤"
            elif sleepiness_level == 2:
                return "ぴえん、僕の眠たさを誰もわかってくれないなんて😭💤💤💤"
            elif sleepiness_level >= 3:
                return get_random_dream_with_quote()
        return "返事が生成できなかったニコリ..."

def generate_image_from_text(prompt: str):
        return None





# 音声ファイルを保存してmp3を返す関数
def generate_voice_file(text, language="日本語"):
    try:
        lang_code = "en" if language == "English" else "ja"
        tts = gTTS(text=text, lang=lang_code)
        temp_path = f"voice_{random.randint(1000,9999)}.mp3"
        tts.save(temp_path)
        return temp_path
    except Exception as e:
        print("音声ファイル作成失敗ニコリ：", e)
        return None

# リマインダー登録コマンド
@bot.tree.command(name="nikorihito_reminder", description="リマインダーを登録できるニコリ（繰り返しも可能）")
async def nikorihito_reminder(interaction: discord.Interaction, time: str, content: str, repeat: bool = False):
    user_id = str(interaction.user.id)
    if user_id not in reminders:
        reminders[user_id] = []
    reminders[user_id].append({
        "time": time,
        "content": content,
        "repeat": repeat
    })
    save_json(REMINDER_FILE, reminders)
    await interaction.response.send_message(
        f"⏰ {time} に『{content}』をリマインドするニコリ！！" +
        ("（毎日繰り返すよ！）" if repeat else "（1回きりだよ！）")
    )

# リマインダーループ
@tasks.loop(seconds=60)
async def reminder_loop():
    now = datetime.now().strftime("%H:%M")
    updated = False
    for user_id, user_reminders in list(reminders.items()):
        for r in list(user_reminders):
            if r["time"] == now:
                try:
                    user = await bot.fetch_user(int(user_id))
                    await user.send(f"⏰ リマインダーのお時間ニコリ！『{r['content']}』だニコリ！！")
                except:
                    print(f"ユーザー {user_id} にDM送れなかったニコリ…")
                if not r.get("repeat", False):
                    reminders[user_id].remove(r)
                    updated = True
    if updated:
        save_json(REMINDER_FILE, reminders)

# 朝のお知らせループ
@tasks.loop(minutes=1)
async def morning_message_loop():
    now = datetime.now()
    if now.hour == 6 and now.minute == 0:
        for user_id, settings in user_settings.items():
            if settings.get("morning_message", True):
                try:
                    user = await bot.fetch_user(int(user_id))
                    await user.send("🌄 おはようニコリ！今日も元気にマイクラするニコリ〜！！")
                except:
                    print(f"ユーザー {user_id} にDM送れなかったニコリ…")
        for uid in sleep_data:
            sleep_data[uid] = {}
        save_json(SLEEP_FILE, sleep_data)
        global sleepiness_level
        sleepiness_level = 0  # グローバルのやつを朝リセット！
        print("💤 寝データをリセットしたニコリ！！")

# 誕生日お祝いコマンド（名前指定バージョン）
@bot.tree.command(name="nikorihito_birthday", description="誕生日を全力でお祝いするニコリ！（名前指定できるよ）")
async def nikorihito_birthday(interaction: discord.Interaction, name: str):
    if name in ["ニコリヒト", "nikorihito"]:
        message = "僕の誕生日を祝ってくれるの！？ありがとうニコリ！！🎂🍲✨\nすっごく嬉しいニコリ！！！ニコリニコリ！！"
    else:
        message = (
            f"{name}の誕生日おめでとうニコリ！！🎉🎂✨\n"
            "ケーキ🎂とビーフシチュー🍲で盛大にお祝いするニコリ！！\n"
            "🎵 [バースデーソングを聴いてね！](http://nikorihito.com/wp-content/uploads/2025/03/はっぴいばあすでいつーゆー.mp3)"
        )
    await interaction.response.send_message(message)

# 雑談対応と音声読み上げ処理（@mention）
# 🔁 この on_message だけ残すニコリ！
@bot.event
async def on_message(message):
    if message.author.bot or not message.content.strip():
        return
    if mute_status.get("muted", False):
        return

    user_id = str(message.author.id)
    user_name = message.author.display_name
    user_input = message.content

    if bot.user.mentioned_in(message):
        user_input = re.sub(rf"<@!?{bot.user.id}>", "", message.content).strip()

        # ▼▼▼ 添付ファイル対応処理ここからニコリ！ ▼▼▼
        attachment_urls = []
        file_notes = []
        for attachment in message.attachments:
            url = attachment.url
            attachment_urls.append(url)

            if url.lower().endswith(('.gif')):
                file_notes.append("（GIFアニメっぽいニコリ！動いてるニコリ！）")
            elif url.lower().endswith(('.jpg', '.jpeg', '.png')):
                file_notes.append("（画像ファイルっぽいニコリ！）")
            elif url.lower().endswith(('.mp4', '.mov', '.webm')):
                file_notes.append("（動画っぽいニコリ！？）")
            else:
                file_notes.append("（何かのファイルニコリ！中身は見てのお楽しみニコリ！）")

        if attachment_urls:
            file_descriptions = "\n".join(
                [f"{url} {note}" for url, note in zip(attachment_urls, file_notes)]
            )
            user_input += f"\n[添付ファイルが送られたニコリ！内容はこちらニコリ：\n{file_descriptions}\n]"
        # ▲▲▲ 添付ファイル対応処理ここまでニコリ！ ▲▲▲

        # 🔽 初期化（履歴なければ作るニコリ！）
        if user_id not in chat_history:
            chat_history[user_id] = {"name": user_name, "history": []}
        else:
            chat_history[user_id]["name"] = user_name

        if user_input:
            reply = ask_nikorihito(user_id, user_input, user_name)
            image_path = generate_image_from_text(reply)  # Gemini用に変更ニコリ！

    chat_history[user_id]["history"].append({"role": "user", "content": user_input})
    chat_history[user_id]["history"].append({"role": "ニコリヒト😁", "content": reply})
    save_json(MEMORY_FILE, chat_history)

    voice_path = generate_voice_file(reply, get_user_settings(user_id)["language"])
    if voice_path and os.path.exists(voice_path):
        await message.channel.send(reply, file=discord.File(voice_path))
        os.remove(voice_path)
    else:
        await message.channel.send(reply)

    if image_path and os.path.exists(image_path):  # ← これが画像添付ニコリ！！
        await message.channel.send(file=discord.File(image_path))
        os.remove(image_path)


    await bot.process_commands(message)

# 返事をmp3音声ファイルに変換して返すニコリ（添付用）
def generate_voice_file(text, language="日本語"):
    try:
        lang_code = "en" if language == "English" else "ja"
        tts = gTTS(text=text, lang=lang_code)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tts.save(tmp.name)
            return tmp.name
    except Exception as e:
        print("音声生成に失敗したニコリ：", e)
        return None

# /settings コマンドで言語や朝メッセージ設定変更できるニコリ
@bot.tree.command(name="settings", description="設定を変えるニコリ！")
async def settings(interaction: discord.Interaction, language: str = None, morning_message: bool = None):
    uid = str(interaction.user.id)
    if uid not in user_settings:
        user_settings[uid] = DEFAULT_SETTINGS.copy()
    if language:
        user_settings[uid]["language"] = language
    if morning_message is not None:
        user_settings[uid]["morning_message"] = morning_message
    save_json(SETTINGS_FILE, user_settings)
    await interaction.response.send_message(f"設定を更新したニコリ！！今はこんな感じだニコリ〜\n{user_settings[uid]}")

# 朝の挨拶ループ
@tasks.loop(minutes=1)
async def morning_message_loop():
    now = datetime.now()
    if now.hour == 6 and now.minute == 0:
        for user_id, settings in user_settings.items():
            if settings.get("morning_message", True):
                try:
                    user = await bot.fetch_user(int(user_id))
                    await user.send("🌄 おはようニコリ！！今日はどんなマイクラライフにするニコリ！？")
                except:
                    print(f"{user_id} にDM送れなかったニコリ…")
        for uid in sleep_data:
            sleep_data[uid] = {}
        save_json(SLEEP_FILE, sleep_data)
        print("🛌 寝データリセットしたニコリ！")

# 起動時イベント
@bot.event
async def on_ready():
    await bot.tree.sync()
    reminder_loop.start()
    morning_message_loop.start()
    print(f"{bot.user} がログインしたニコリ〜！🍲🔥")

# ミュート・ミュート解除
@bot.tree.command(name="mute", description="nikorihitoを黙らせるニコリ")
async def mute(interaction: discord.Interaction):
    mute_status["muted"] = True
    save_json(MUTE_FILE, mute_status)
    await interaction.response.send_message("しばらく静かにするニコリ...😶")

@bot.tree.command(name="mute_off", description="nikorihitoのミュートを解除するニコリ")
async def mute_off(interaction: discord.Interaction):
    mute_status["muted"] = False
    save_json(MUTE_FILE, mute_status)
    await interaction.response.send_message("いやっほ！しゃべれる、しゃべれるニコリ！！早速ビーフシチュー食べるぞー！！ニコリ！！ふぁー、お肉に味が染みてるーー！！😍😍ニコリ！！")

# ✅ RenderでWebサービスとして動かすためのダミーサーバー（最後に追記！）
app = Flask(__name__)

@app.route('/')
def home():
    return "Nikorihito Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web).start()

# ✅ 起動！
bot.run(DISCORD_BOT_TOKEN)
