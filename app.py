"""🕹️ ゲームポータル — Streamlit製ゲーム作品集の統合サイト。

5つの作品を1つのサイトに統合し、ホームから選んで遊べるランチャー。
各ゲームは個別フォルダの app.py をマルチページ（st.navigation / st.Page）として読み込む。

実行: streamlit run app.py
"""

import os
import sys

import streamlit as st

st.set_page_config(page_title="ゲームポータル", page_icon="🕹️", layout="centered")

ROOT = os.path.dirname(os.path.abspath(__file__))
# 404ゲームはローカルパッケージ(game)を相対importで使うため、解決できるようにパスを通す
_arg_dir = os.path.join(ROOT, "404_User_Not_Found")
if _arg_dir not in sys.path:
    sys.path.insert(0, _arg_dir)


# 作品メタ情報
GAMES = [
    {
        "path": "MiniGameArcade/app.py", "title": "ミニゲームアーケード", "icon": "🎮", "url": "arcade",
        "genre": "ミニゲーム集",
        "desc": "数当て・じゃんけん・神経衰弱・クイズ・スロット・ハングマンの6種。"
                "共通コイン経済とレベル・実績でつながる作品集。",
    },
    {
        "path": "Project_ECHO/app.py", "title": "Project ECHO", "icon": "🧬", "url": "echo",
        "genre": "脱出・謎解き",
        "desc": "閉鎖されたAI研究所から脱出せよ。ランダム認証コード、符号化された手がかり、"
                "隠し研究室、マルチエンド。",
    },
    {
        "path": "Case001/app.py", "title": "消えた研究者", "icon": "🕵️", "url": "case001",
        "genre": "推理アドベンチャー",
        "desc": "探偵として証拠を集め真犯人を推理。二段構えの矛盾追及と捜査信用度、"
                "4つのエンディング。",
    },
    {
        "path": "LAST_30minute/app.py", "title": "LAST 30 MINUTES", "icon": "☄️", "url": "last30",
        "genre": "タイムアタック",
        "desc": "隕石衝突までのリアルタイム制限時間内に5施設を復旧。迎撃成功率で結末が分岐する。",
    },
    {
        "path": "404_User_Not_Found/app.py", "title": "404 User Not Found", "icon": "🛑", "url": "arg",
        "genre": "ARG・都市伝説ホラー",
        "desc": "「HELP」の一通から始まる失踪事件を追うARG。暗号・ミニゲーム・分岐エンド。",
    },
]


# ==========================================================================
# ホーム（ギャラリー）
# ==========================================================================
def home():
    st.title("🕹️ ゲームポータル")
    st.write("遊びたい作品を選んでスタート。左のメニューからも切り替えられます。")
    st.markdown("---")

    for g in GAMES:
        with st.container(border=True):
            c1, c2 = st.columns([1, 4])
            c1.markdown(f"<div style='font-size:52px; text-align:center;'>{g['icon']}</div>",
                        unsafe_allow_html=True)
            with c2:
                st.subheader(f"{g['title']}")
                st.caption(f"ジャンル: {g['genre']}")
                st.write(g["desc"])
                if st.button(f"▶ {g['title']} を遊ぶ", key=f"play_{g['url']}", use_container_width=True):
                    st.switch_page(g["path"])

    st.markdown("---")
    st.caption("すべて Python + Streamlit 製。各作品は個別フォルダでも単体起動できます。")


# ==========================================================================
# ナビゲーション
# ==========================================================================
home_page = st.Page(home, title="ホーム", icon="🏠", default=True)
game_pages = [
    st.Page(g["path"], title=g["title"], icon=g["icon"], url_path=g["url"])
    for g in GAMES
]

# サイドバーへ自動で挿入されるポータルメニューは出さない。
# （各ゲーム、とくに404のARG用サイドバーに portal の表示が混ざるのを防ぐ）
nav = st.navigation([home_page] + game_pages, position="hidden")

# 各ゲームのサイドバー上部に、控えめな「ポータルに戻る」を出す。
RETURN_URLS = {"arcade", "echo", "case001", "last30", "arg"}
if getattr(nav, "url_path", "") in RETURN_URLS:
    with st.sidebar:
        if st.button("🏠 ポータルに戻る", use_container_width=True):
            st.switch_page(home_page)
        st.divider()

nav.run()
