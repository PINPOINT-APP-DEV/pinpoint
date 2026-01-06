from __future__ import annotations

import os
import uuid
import math
import random
from datetime import datetime, timezone, timedelta, date
from typing import Optional

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, make_response, jsonify
from flask_sqlalchemy import SQLAlchemy
from PIL import Image
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

# -----------------------------
# Brand / Token
# -----------------------------
APP_NAME = "Pinpoint"
APP_TAGLINE = "Pin what’s hot. Verify what’s real."
TOKEN_NAME = "PINPOINT"
TOKEN_SYMBOL = "$PINPOINT"
TOKEN_SUPPLY = 1_000_000_000  # 1B total supply (planned)

# In-app points
POINTS_START = 1000

# Rewards
REWARD_SUBMIT = 10                 # author per submission
REWARD_LIKE_RECEIVED = 2           # author when their tip gets a like
REWARD_LIKE_GIVEN = 1              # voter when liking
REWARD_DISLIKE_GIVEN = 1           # voter when disliking

# Daily check-in (UTC)
CHECKIN_MIN = 1
CHECKIN_MAX = 50
CHECKIN_MAX_STREAK = 30

# Planned swap (placeholder; tune later)
POINTS_PER_TOKEN = 1000            # 1 PINPOINT token = 1,000 points

ALLOWED_LANGS = ["en", "ja", "zh", "kr"]

# Hot ranking params
HOT_HALF_LIFE_HOURS = 12.0         # time-decay half-life
HOT_LIKE_WEIGHT = 1.0
HOT_DISLIKE_WEIGHT = 1.25
HOT_BASE = 1.0

# -----------------------------
# i18n
# -----------------------------
def _base():
    return {
        "tagline": APP_TAGLINE,
        "headline": "A community-ranked radar for what’s trending right now.",
        "subhead": "Submit tips with evidence (links/images). The community votes and verifies. Rankings update live.",
        "disclaimer": f"{TOKEN_SYMBOL} Points are in-app utility credits (pin/participation), not an investment product.",
        "submit_tip": "Submit a tip",
        "title_ph": "Title (what’s trending?)",
        "link_ph": "Link URL (https://...)",
        "image_url_ph": "Image URL (optional, https://...)",
        "tags_ph": "Tags (comma-separated)",
        "note_ph": "Short note / evidence (optional)",
        "upload_title": "Upload image (optional)",
        "drop_here": "Drop image here",
        "choose_image": "Choose image",
        "remove": "Remove",
        "submit": "Submit",
        "need_title": "Please enter a title.",
        "need_link_or_image": "Please provide a link or an image.",
        "login_ph": "handle (no password)",
        "password_ph": "password (set on first login)",
        "login": "Login",
        "logout": "Logout",
        "token": "Token",
        "lang": "Language:",
        "utc": "UTC:",
        "points": f"{TOKEN_SYMBOL} Points",
        "likes": "Likes",
        "dislikes": "Dislikes",
        "by": "by",
        "like": "Like",
        "liked": "Liked",
        "dislike": "Dislike",
        "disliked": "Disliked",
        "toast_login_needed": "Login required.",
        "toast_self_vote": "You can't vote on your own tip.",
        "toast_liked_author": f"+{REWARD_LIKE_RECEIVED} points to the author.",
        "toast_voter_like": f"+{REWARD_LIKE_GIVEN} point to you.",
        "toast_voter_dislike": f"+{REWARD_DISLIKE_GIVEN} point to you.",
        "toast_unliked": "Removed like.",
        "toast_undisliked": "Removed dislike.",
        "how_chip1": "Trend / Hot",
        "how_chip2": "Tips + Evidence",
        "how_chip3": "Vote / Verify",
        "how_chip4": f"{TOKEN_SYMBOL} Utility",
        "how_line1": "Hot ranking = time decay + votes (MVP).",
        "how_line2": "Thumbnails are generated on upload for faster feed loading.",
        "how_line3": "Storage backend ready for Local / S3 (default Local).",
        "reward_rules": f"Rewards: +{REWARD_SUBMIT} per submission, author +{REWARD_LIKE_RECEIVED} per like, voters +{REWARD_LIKE_GIVEN}/{REWARD_DISLIKE_GIVEN}, check-in {CHECKIN_MIN}~{CHECKIN_MAX}.",
        "no_file": "No file",
        "link_label": "Link",
        "image_label": "Image URL",
        "no_image": "No image",
        "tab_hot": "Hot",
        "tab_new": "New",
        "checkin": "Check-in",
        "checked_in": "Checked in",
        "toast_checkin_done": "Check-in complete!",
        "toast_checkin_already": "Already checked in today.",
        "streak": "Streak",
        "token_title": f"{TOKEN_SYMBOL} Utility + Planned Swap",
        "token_p1": f"{TOKEN_SYMBOL} Points are earned via participation (submissions, votes, check-ins).",
        "token_p2": f"Planned token supply: {TOKEN_SUPPLY:,} {TOKEN_NAME} (fixed supply at genesis).",
        "token_p3": "Planned swap: Points → token at launch. Initial target ratio:",
        "token_ratio": f"1 {TOKEN_NAME} = {POINTS_PER_TOKEN:,} Points (subject to final launch policy).",
        "back_home": "Back to Home",
    }

I18N = {
    "en": _base(),
    "ja": {
        **_base(),
        "tagline": "熱いものをピン留め。真実を検証。",
        "headline": "いま話題のものを、コミュニティでランキング。",
        "subhead": "リンク/画像の証拠付きで投稿。投票と検証でランキングが更新されます。",
        "disclaimer": f"{TOKEN_SYMBOL}ポイントはアプリ内ユーティリティ(固定/参加)であり、投資商品ではありません。",
        "submit_tip": "投稿する",
        "title_ph": "タイトル（何が流行？）",
        "link_ph": "リンクURL (https://...)",
        "image_url_ph": "画像URL（任意, https://...)",
        "tags_ph": "タグ（カンマ区切り）",
        "note_ph": "メモ / 根拠（任意）",
        "upload_title": "画像アップロード（任意）",
        "drop_here": "ここにドロップ",
        "choose_image": "画像を選択",
        "remove": "削除",
        "submit": "送信",
        "need_title": "タイトルを入力してください。",
        "need_link_or_image": "リンクまたは画像を追加してください。",
        "login_ph": "ハンドル（パスワード不要）",
        "password_ph": "パスワード（初回で設定）",
        "login": "ログイン",
        "logout": "ログアウト",
        "token": "トークン",
        "lang": "言語:",
        "points": f"{TOKEN_SYMBOL}ポイント",
        "likes": "いいね",
        "dislikes": "よくないね",
        "by": "投稿者",
        "like": "いいね",
        "liked": "いいね済み",
        "dislike": "よくないね",
        "disliked": "押下済み",
        "toast_login_needed": "ログインが必要です。",
        "toast_self_vote": "自分の投稿には投票できません。",
        "toast_liked_author": f"作者に +{REWARD_LIKE_RECEIVED} ポイント。",
        "toast_voter_like": f"あなたに +{REWARD_LIKE_GIVEN} ポイント。",
        "toast_voter_dislike": f"あなたに +{REWARD_DISLIKE_GIVEN} ポイント。",
        "toast_unliked": "取り消しました。",
        "toast_undisliked": "取り消しました。",
        "tab_hot": "人気",
        "tab_new": "新着",
        "checkin": "チェックイン",
        "checked_in": "完了",
        "toast_checkin_done": "チェックイン完了！",
        "toast_checkin_already": "本日は完了しています。",
        "streak": "連続",
    },
    "zh": {
        **_base(),
        "tagline": "置顶热点，验证真实。",
        "headline": "一个由社区排名的当下热度雷达。",
        "subhead": "提交带证据(链接/图片)的线索。社区投票与验证，排名实时更新。",
        "disclaimer": f"{TOKEN_SYMBOL} 积分是站内用途积分（置顶/参与），不是投资产品。",
        "submit_tip": "提交线索",
        "title_ph": "标题（什么在火？）",
        "link_ph": "链接 URL (https://...)",
        "image_url_ph": "图片 URL（可选, https://...)",
        "tags_ph": "标签（逗号分隔）",
        "note_ph": "备注/证据（可选）",
        "upload_title": "上传图片（可选）",
        "drop_here": "拖拽到这里",
        "choose_image": "选择图片",
        "remove": "移除",
        "submit": "提交",
        "need_title": "请输入标题。",
        "need_link_or_image": "请提供链接或图片。",
        "login_ph": "昵称（无需密码）",
        "password_ph": "密码（首次登录设置）",
        "login": "登录",
        "logout": "退出",
        "token": "代币",
        "lang": "语言:",
        "points": f"{TOKEN_SYMBOL} 积分",
        "likes": "点赞",
        "dislikes": "点踩",
        "by": "来自",
        "like": "点赞",
        "liked": "已赞",
        "dislike": "点踩",
        "disliked": "已踩",
        "toast_login_needed": "需要登录。",
        "toast_self_vote": "不能给自己的帖子投票。",
        "toast_liked_author": f"作者获得 +{REWARD_LIKE_RECEIVED} 积分。",
        "toast_voter_like": f"你获得 +{REWARD_LIKE_GIVEN} 积分。",
        "toast_voter_dislike": f"你获得 +{REWARD_DISLIKE_GIVEN} 积分。",
        "toast_unliked": "已取消点赞。",
        "toast_undisliked": "已取消点踩。",
        "tab_hot": "热门",
        "tab_new": "最新",
        "checkin": "签到",
        "checked_in": "已签",
        "toast_checkin_done": "签到成功！",
        "toast_checkin_already": "今天已签到。",
        "streak": "连续",
    },
    "kr": {
        "tagline": "핫한 것을 고정하고, 진짜를 검증한다.",
        "headline": "지금 뜨는 것을 커뮤니티가 랭킹으로 만든다.",
        "subhead": "링크/이미지 근거와 함께 제보. 커뮤니티가 투표/검증하며 랭킹이 갱신됩니다.",
        "disclaimer": f"{TOKEN_SYMBOL} 포인트는 사이트 내 유틸리티(고정/참여)이며 투자상품이 아닙니다.",
        "submit_tip": "제보 올리기",
        "title_ph": "제목 (뭐가 뜨고 있어?)",
        "link_ph": "링크 URL (https://...)",
        "image_url_ph": "이미지 URL (선택, https://...)",
        "tags_ph": "태그 (콤마로)",
        "note_ph": "메모 / 근거 (선택)",
        "upload_title": "이미지 업로드 (선택)",
        "drop_here": "여기에 드롭",
        "choose_image": "이미지 선택",
        "remove": "삭제",
        "submit": "등록",
        "need_title": "제목을 입력해줘.",
        "need_link_or_image": "링크 또는 이미지를 추가해줘.",
        "login_ph": "핸들 (비번 없음)",
        "password_ph": "비밀번호 (첫 로그인 설정)",
        "login": "로그인",
        "logout": "로그아웃",
        "token": "토큰",
        "lang": "언어:",
        "utc": "UTC:",
        "points": f"{TOKEN_SYMBOL} 포인트",
        "likes": "좋아요",
        "dislikes": "싫어요",
        "by": "작성자",
        "like": "좋아요",
        "liked": "좋아요됨",
        "dislike": "싫어요",
        "disliked": "싫어요됨",
        "toast_login_needed": "로그인이 필요합니다.",
        "toast_self_vote": "내 글에는 투표할 수 없습니다.",
        "toast_liked_author": f"작성자에게 +{REWARD_LIKE_RECEIVED} 포인트 지급.",
        "toast_voter_like": f"나에게 +{REWARD_LIKE_GIVEN} 포인트.",
        "toast_voter_dislike": f"나에게 +{REWARD_DISLIKE_GIVEN} 포인트.",
        "toast_unliked": "좋아요 취소.",
        "toast_undisliked": "싫어요 취소.",
        "how_chip1": "트렌드/핫",
        "how_chip2": "제보+근거",
        "how_chip3": "투표/검증",
        "how_chip4": f"{TOKEN_SYMBOL} 유틸리티",
        "how_line1": "핫 랭킹 = 시간 감쇠 + 투표(MVP).",
        "how_line2": "업로드 시 자동 썸네일 생성.",
        "how_line3": "저장소(Local/S3) 구조 준비됨 (기본 Local).",
        "reward_rules": f"보상: 제보 +{REWARD_SUBMIT}, 좋아요(작성자 +{REWARD_LIKE_RECEIVED}), 투표자 +{REWARD_LIKE_GIVEN}/{REWARD_DISLIKE_GIVEN}, 출석 랜덤 {CHECKIN_MIN}~{CHECKIN_MAX}.",
        "no_file": "선택된 파일 없음",
        "link_label": "링크",
        "image_label": "이미지URL",
        "no_image": "이미지 없음",
        "tab_hot": "핫",
        "tab_new": "최신",
        "checkin": "출석",
        "checked_in": "완료",
        "toast_checkin_done": "출석 완료!",
        "toast_checkin_already": "오늘은 이미 출석했어.",
        "streak": "연속",
        "token_title": f"{TOKEN_SYMBOL} 유틸리티 + 스왑 예정",
        "token_p1": f"{TOKEN_SYMBOL} 포인트는 참여(제보/투표/출석)로 획득합니다.",
        "token_p2": f"토큰 총발행량(예정): {TOKEN_SUPPLY:,} {TOKEN_NAME} (제네시스 고정).",
        "token_p3": "런칭 시 포인트→토큰 스왑을 진행할 예정입니다. 초기 목표 비율:",
        "token_ratio": f"1 {TOKEN_NAME} = {POINTS_PER_TOKEN:,} 포인트 (최종 정책에 따라 조정).",
        "back_home": "홈으로",
    },
}

# -----------------------------
# App / DB
# -----------------------------
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///trendfuel.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024
db = SQLAlchemy(app)

UPLOAD_DIR = os.path.join(app.root_path, "static", "uploads")
THUMB_DIR = os.path.join(app.root_path, "static", "thumbs")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(THUMB_DIR, exist_ok=True)

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def utc_day_str(dt: datetime | None = None) -> str:
    return (dt or now_utc()).date().isoformat()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    handle = db.Column(db.String(48), unique=True, nullable=False)
    points = db.Column(db.Integer, default=POINTS_START)
    created_at = db.Column(db.DateTime, default=now_utc)
    password_hash = db.Column(db.String(255), default="")

    checkin_streak = db.Column(db.Integer, default=0)
    last_checkin_day = db.Column(db.String(10), default="")  # YYYY-MM-DD

class Tip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    link_url = db.Column(db.String(500), default="")
    image_url = db.Column(db.String(500), default="")
    upload_path = db.Column(db.String(260), default="")
    thumb_path = db.Column(db.String(260), default="")
    tags = db.Column(db.String(200), default="")
    note = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=now_utc)

    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    author = db.relationship("User", backref="tips")

    likes_count = db.Column(db.Integer, default=0)
    dislikes_count = db.Column(db.Integer, default=0)

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tip_id = db.Column(db.Integer, db.ForeignKey("tip.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=now_utc)
    __table_args__ = (db.UniqueConstraint("tip_id", "user_id", name="uq_like_tip_user"),)

class Dislike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tip_id = db.Column(db.Integer, db.ForeignKey("tip.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=now_utc)
    __table_args__ = (db.UniqueConstraint("tip_id", "user_id", name="uq_dislike_tip_user"),)


class VoteReward(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tip_id = db.Column(db.Integer, db.ForeignKey("tip.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    kind = db.Column(db.String(8), nullable=False)  # "like" or "dislike"
    created_at = db.Column(db.DateTime, default=now_utc)
    __table_args__ = (db.UniqueConstraint("tip_id", "user_id", "kind", name="uq_reward_tip_user_kind"),)

def ensure_schema():
    db.create_all()
    try:
        cols = [r[1] for r in db.session.execute(db.text('PRAGMA table_info("user")')).fetchall()]
        if "password_hash" not in cols:
            db.session.execute(db.text('ALTER TABLE "user" ADD COLUMN password_hash VARCHAR(255) DEFAULT ""'))
            db.session.commit()
    except Exception:
        db.session.rollback()

with app.app_context():
    ensure_schema()

# -----------------------------
# Helpers
# -----------------------------
def get_lang() -> str:
    q = (request.args.get("lang") or "").lower().strip()
    if q in ALLOWED_LANGS:
        return q
    c = (request.cookies.get("lang") or "").lower().strip()
    if c in ALLOWED_LANGS:
        return c
    return "en"

def get_user() -> Optional[User]:
    handle = (request.cookies.get("handle") or "").strip()
    if not handle:
        return None
    return User.query.filter_by(handle=handle).first()

def get_or_create_user(handle: str) -> User:
    handle = handle.strip()
    u = User.query.filter_by(handle=handle).first()
    if u:
        return u
    u = User(handle=handle, points=POINTS_START)
    db.session.add(u)
    db.session.commit()
    return u

def safe_filename(original: str) -> str:
    ext = os.path.splitext(original)[1].lower()
    if ext not in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
        ext = ".png"
    return f"{uuid.uuid4().hex}{ext}"

def make_thumb(src_abs: str, thumb_abs: str, max_side: int = 480) -> None:
    with Image.open(src_abs) as im:
        im = im.convert("RGB")
        w, h = im.size
        scale = min(max_side / max(w, h), 1.0)
        nw, nh = int(w * scale), int(h * scale)
        if (nw, nh) != (w, h):
            im = im.resize((nw, nh))
        im.save(thumb_abs, "JPEG", quality=85, optimize=True)

def hot_score(tip: Tip) -> float:
    age = max((now_utc().replace(tzinfo=None) - tip.created_at).total_seconds(), 0.0)

    age_hours = age / 3600.0
    decay = 0.5 ** (age_hours / HOT_HALF_LIFE_HOURS)  # half-life decay
    votes = (tip.likes_count * HOT_LIKE_WEIGHT) - (tip.dislikes_count * HOT_DISLIKE_WEIGHT)
    base = HOT_BASE + votes
    return base * decay

# -----------------------------
# Routes
# -----------------------------
@app.get("/")
def home():
    lang = get_lang()
    tab = (request.args.get("tab") or "hot").lower()
    if tab not in ["hot", "new"]:
        tab = "hot"

    me = get_user()

    tips = Tip.query.order_by(Tip.created_at.desc()).limit(200).all()
    tips_sorted = tips if tab == "new" else sorted(tips, key=hot_score, reverse=True)
    tips_sorted = tips_sorted[:50]

    my_likes = set()
    my_dislikes = set()
    if me:
        my_likes = {r.tip_id for r in Like.query.filter_by(user_id=me.id).all()}
        my_dislikes = {r.tip_id for r in Dislike.query.filter_by(user_id=me.id).all()}

    resp = make_response(render_template(
        "index.html",
        APP_NAME=APP_NAME,
        TOKEN_SYMBOL=TOKEN_SYMBOL,
        TOKEN_NAME=TOKEN_NAME,
        T=I18N[lang],
        lang=lang,
        tab=tab,
        me=me,
        tips=tips_sorted,
        my_likes=my_likes,
        my_dislikes=my_dislikes,
        POINTS_PER_TOKEN=POINTS_PER_TOKEN,
        TOKEN_SUPPLY=TOKEN_SUPPLY,
        REWARD_SUBMIT=REWARD_SUBMIT,
        REWARD_LIKE_RECEIVED=REWARD_LIKE_RECEIVED,
        REWARD_LIKE_GIVEN=REWARD_LIKE_GIVEN,
        REWARD_DISLIKE_GIVEN=REWARD_DISLIKE_GIVEN,
        CHECKIN_MAX_STREAK=CHECKIN_MAX_STREAK,
    ))
    resp.set_cookie("lang", lang, max_age=60 * 60 * 24 * 365, samesite="Lax")
    return resp

@app.post("/login")
def login():
    lang = get_lang()
    tab = (request.args.get("tab") or "hot").lower()
    handle = (request.form.get("handle") or "").strip()
    password = (request.form.get("password") or "").strip()
    if not handle or not password:
        return redirect(url_for("home", lang=lang, tab=tab))

    u = User.query.filter_by(handle=handle).first()
    if not u:
        u = User(handle=handle, points=POINTS_START, password_hash=generate_password_hash(password))
        db.session.add(u)
        db.session.commit()
    else:
        if not (u.password_hash or "").strip():
            u.password_hash = generate_password_hash(password)
            db.session.commit()
        elif not check_password_hash(u.password_hash, password):
            return redirect(url_for("home", lang=lang, tab=tab, bad_login=1))

    resp = make_response(redirect(url_for("home", lang=lang, tab=tab)))
    resp.set_cookie("handle", u.handle, max_age=60 * 60 * 24 * 365, samesite="Lax")
    return resp

@app.post("/logout")
def logout():
    lang = get_lang()
    resp = make_response(redirect(url_for("home", lang=lang)))
    resp.delete_cookie("handle")
    return resp

@app.post("/submit")
def submit():
    lang = get_lang()
    tab = (request.args.get("tab") or "hot").lower()
    me = get_user()
    if not me:
        return redirect(url_for("home", lang=lang, tab=tab))

    title = (request.form.get("title") or "").strip()
    link_url = (request.form.get("link_url") or "").strip()
    image_url = (request.form.get("image_url") or "").strip()
    tags = (request.form.get("tags") or "").strip()
    note = (request.form.get("note") or "").strip()

    upload_path = ""
    thumb_path = ""

    f = request.files.get("image_file")
    if f and f.filename:
        fn = safe_filename(f.filename)
        abs_up = os.path.join(UPLOAD_DIR, fn)
        f.save(abs_up)
        upload_path = f"uploads/{fn}"

        thumb_fn = f"{os.path.splitext(fn)[0]}.jpg"
        abs_th = os.path.join(THUMB_DIR, thumb_fn)
        try:
            make_thumb(abs_up, abs_th)
            thumb_path = f"thumbs/{thumb_fn}"
        except Exception:
            thumb_path = ""

    if not title:
        return redirect(url_for("home", lang=lang, tab=tab))
    if not link_url and not image_url and not upload_path:
        return redirect(url_for("home", lang=lang, tab=tab))

    tip = Tip(
        title=title,
        link_url=link_url,
        image_url=image_url,
        upload_path=upload_path,
        thumb_path=thumb_path,
        tags=tags,
        note=note,
        author_id=me.id,
    )
    db.session.add(tip)

    me.points += REWARD_SUBMIT
    db.session.commit()

    return redirect(url_for("home", lang=lang, tab=tab))

@app.post("/api/vote")
def api_vote():
    me = get_user()
    if not me:
        return jsonify({"ok": False, "code": "LOGIN_REQUIRED"}), 401

    tip_id = int(request.form.get("tip_id") or 0)
    kind = (request.form.get("kind") or "").lower()  # "like" or "dislike"
    if kind not in ["like", "dislike"]:
        return jsonify({"ok": False, "code": "BAD_KIND"}), 400

    tip = Tip.query.get(tip_id)
    if not tip:
        return jsonify({"ok": False, "code": "NOT_FOUND"}), 404

    if tip.author_id == me.id:
        return jsonify({"ok": False, "code": "SELF_VOTE"}), 400

    existing_like = Like.query.filter_by(tip_id=tip.id, user_id=me.id).first()
    existing_dislike = Dislike.query.filter_by(tip_id=tip.id, user_id=me.id).first()

    delta_me = 0
    delta_author = 0
    removed = None
    added = None

    def reward_once(k: str) -> bool:
        # Returns True if this is the first time this user ever gets reward for this tip+kind
        r = VoteReward.query.filter_by(tip_id=tip.id, user_id=me.id, kind=k).first()
        if r:
            return False
        db.session.add(VoteReward(tip_id=tip.id, user_id=me.id, kind=k))
        return True

    if kind == "like":
        if existing_like:
            # toggle off (no extra points)
            db.session.delete(existing_like)
            tip.likes_count = max(tip.likes_count - 1, 0)
            removed = "like"
        else:
            # switch off dislike if exists
            if existing_dislike:
                db.session.delete(existing_dislike)
                tip.dislikes_count = max(tip.dislikes_count - 1, 0)
                removed = "dislike"

            db.session.add(Like(tip_id=tip.id, user_id=me.id))
            tip.likes_count += 1
            added = "like"

            # reward ONLY once per user per tip for "like"
            if reward_once("like"):
                delta_me += REWARD_LIKE_GIVEN
                delta_author += REWARD_LIKE_RECEIVED

    else:  # dislike
        if existing_dislike:
            db.session.delete(existing_dislike)
            tip.dislikes_count = max(tip.dislikes_count - 1, 0)
            removed = "dislike"
        else:
            # switch off like if exists (do not refund points; just counts)
            if existing_like:
                db.session.delete(existing_like)
                tip.likes_count = max(tip.likes_count - 1, 0)
                removed = "like"

            db.session.add(Dislike(tip_id=tip.id, user_id=me.id))
            tip.dislikes_count += 1
            added = "dislike"

            # reward ONLY once per user per tip for "dislike"
            if reward_once("dislike"):
                delta_me += REWARD_DISLIKE_GIVEN

    author = User.query.get(tip.author_id)
    if author and delta_author:
        author.points = max(author.points + delta_author, 0)
    if delta_me:
        me.points = max(me.points + delta_me, 0)

    db.session.commit()

    return jsonify({
        "ok": True,
        "added": added,
        "removed": removed,
        "likes": tip.likes_count,
        "dislikes": tip.dislikes_count,
        "me_points": me.points,
    })

@app.post("/api/delete")
def api_delete():
    me = get_user()
    if not me:
        return jsonify({"ok": False, "message": "Login required."}), 401
    try:
        tip_id = int(request.args.get("tip_id") or "0")
    except Exception:
        tip_id = 0
    if not tip_id:
        return jsonify({"ok": False, "message": "Bad tip id."}), 400
    tip = Tip.query.filter_by(id=tip_id).first()
    if not tip:
        return jsonify({"ok": False, "message": "Not found."}), 404
    if tip.author_id != me.id:
        return jsonify({"ok": False, "message": "Only the author can delete."}), 403
    db.session.delete(tip)
    db.session.commit()
    return jsonify({"ok": True})

@app.post("/api/checkin")
def api_checkin():
    me = get_user()
    if not me:
        return jsonify({"ok": False, "code": "LOGIN_REQUIRED"}), 401

    today = utc_day_str()
    if me.last_checkin_day == today:
        return jsonify({"ok": False, "code": "ALREADY"}), 200

    if me.last_checkin_day:
        try:
            last = date.fromisoformat(me.last_checkin_day)
            if last == (date.fromisoformat(today) - timedelta(days=1)):
                me.checkin_streak = min(me.checkin_streak + 1, CHECKIN_MAX_STREAK)
            else:
                me.checkin_streak = 1
        except Exception:
            me.checkin_streak = 1
    else:
        me.checkin_streak = 1

    me.last_checkin_day = today
    reward = random.randint(CHECKIN_MIN, CHECKIN_MAX)
    me.points += reward
    db.session.commit()

    return jsonify({"ok": True, "reward": reward, "streak": me.checkin_streak, "me_points": me.points})

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5050"))
    app.run(host="0.0.0.0", port=port, debug=True)


def _init_visits():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS visits (
        day TEXT,
        ip TEXT
    )
    """)
    conn.commit()
    conn.close()

def track_visit():
    try:
        _init_visits()
        ip = request.remote_addr or "0.0.0.0"
        day = datetime.utcnow().date().isoformat()
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("INSERT INTO visits(day, ip) VALUES (?,?)", (day, ip))
        conn.commit()
        conn.close()
    except:
        pass

def get_visitors():
    _init_visits()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    day = datetime.utcnow().date().isoformat()
    cur.execute("SELECT COUNT(DISTINCT ip) FROM visits WHERE day=?", (day,))
    daily = cur.fetchone()[0] or 0
    cur.execute("SELECT COUNT(DISTINCT ip) FROM visits")
    total = cur.fetchone()[0] or 0
    conn.close()
    return daily, total

LAST_POST_TS = {}