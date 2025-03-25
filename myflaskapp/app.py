import re
import requests
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'wjtmxm0810'

# DB 설정 (이미 있다면 중복 안 생김)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 유저 테이블
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

# 유저가 저장한 유튜브 채널
class Channel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    channel_name = db.Column(db.String(200))
    channel_url = db.Column(db.String(300))


# DB 생성
with app.app_context():
    db.create_all()

# ---------------- 유튜브 영상 불러오기 함수들 ----------------

def get_channel_id_from_handle(handle):
    """@핸들로 채널 ID 추출하기"""
    url = f"https://www.youtube.com/@{handle}"
    response = requests.get(url)
    match = re.search(r'"channelId":"(UC[-_A-Za-z0-9]{21}[AQgw])"', response.text)
    if match:
        return match.group(1)
    return None

def get_latest_videos(channel_id, max_results=5):
    YOUTUBE_API_KEY = "AIzaSyC8CraXfnWHyMd0-2OaTKzBJUjifSHaLuY"  # ← 너의 유튜브 API 키를 여기에 넣어!
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "key": YOUTUBE_API_KEY,
        "channelId": channel_id,
        "part": "snippet",
        "order": "date",
        "maxResults": max_results
    }
    response = requests.get(url, params=params)
    data = response.json()
    videos = []
    for item in data.get("items", []):
        if item["id"]["kind"] == "youtube#video":
            videos.append({
                "title": item["snippet"]["title"],
                "videoId": item["id"]["videoId"],
                "publishedAt": item["snippet"]["publishedAt"]
            })
    return videos

# ---------------- 라우팅 ----------------

@app.route("/videos", methods=["GET", "POST"])
def videos():
    videos = []
    raw_input = ""

    if request.method == "POST":
        raw_input = request.form["channel_id"].strip()
    elif request.method == "GET":
        raw_input = request.args.get("channel_id", "").strip()

    channel_id = None
    if raw_input.startswith("UC"):
        channel_id = raw_input
    elif "@" in raw_input:
        handle = raw_input.split("@")[-1]
        channel_id = get_channel_id_from_handle(handle)
    elif "youtube.com/channel/" in raw_input:
        match = re.search(r"(UC[-_A-Za-z0-9]{21}[AQgw])", raw_input)
        if match:
            channel_id = match.group(1)

    if channel_id:
        videos = get_latest_videos(channel_id)
    elif raw_input:
        return "<h3>채널 ID를 찾을 수 없습니다. 입력을 확인해주세요.</h3>"

    return render_template("videos.html", videos=videos)


# ---------------- 로그인/회원가입 기본 라우팅 (생략 가능) ----------------
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session["user_id"] = user.id
            session["username"] = user.username
            return redirect(url_for("dashboard"))
        else:
            return "<h3>로그인 실패. 아이디나 비밀번호가 잘못되었습니다.</h3><a href='/login'>다시 시도</a>"

    return render_template("login.html")



@app.route("/register")
def register():
    return render_template("register.html")


# 라우터 수정
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    username = session["username"]

    if request.method == "POST":
        name = request.form["channel_name"]
        url = request.form["channel_url"]
        new_channel = Channel(user_id=user_id, channel_name=name, channel_url=url)
        db.session.add(new_channel)
        db.session.commit()
        return redirect(url_for("dashboard"))

    channels = Channel.query.filter_by(user_id=user_id).all()
    return render_template("dashboard.html", username=username, channels=channels)




if __name__ == "__main__":
    app.run(debug=True)