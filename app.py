"""🕹️ ゲームポータル / NOXA Universe — Streamlit製ゲーム作品集の統合サイト。

6つの作品を1つのサイトに統合したランチャー。ただし単なるゲーム集ではない。
プレイヤーは複数のゲームを遊んでいるつもりで、巨大研究組織「NOXA」が隠す
一つの真実へ近づいていく。

  - 作品はクリアで段階的に解放される（最初はアーケードと消えた研究者のみ）
  - 進行はプレイヤー名をキーにファイル保存され、ブラウザを閉じても残る
  - クリアごとに「共通調査ボード」に情報が追加され、NOXAの真相マップが埋まる
  - 進行に応じてポータル自体が変質していく

実行: streamlit run app.py
"""

import datetime
import os
import sys
import time

import streamlit as st

st.set_page_config(page_title="NOXA Game Portal", page_icon="🕹️", layout="centered")

ROOT = os.path.dirname(os.path.abspath(__file__))
# 404ゲームはローカルパッケージ(game)を相対importで使うため、解決できるようにパスを通す
_arg_dir = os.path.join(ROOT, "404_User_Not_Found")
if _arg_dir not in sys.path:
    sys.path.insert(0, _arg_dir)

import noxa_core as noxa  # 作品横断の共有状態・進行管理


# 作品メタ情報（key は noxa の作品キー / ポータルの url_path と一致）
GAMES = [
    {
        "key": "arcade", "path": "MiniGameArcade/app.py", "title": "ミニゲームアーケード",
        "icon": "🎮", "genre": "ミニゲーム集",
        "desc": "数当て・じゃんけん・神経衰弱・クイズ・スロット・ハングマンの6種。"
                "共通コイン経済とレベル・実績でつながる作品集。",
    },
    {
        "key": "case001", "path": "Case001/app.py", "title": "消えた研究者",
        "icon": "🕵️", "genre": "推理アドベンチャー",
        "desc": "探偵として証拠を集め真犯人を推理。二段構えの矛盾追及と捜査信用度、"
                "4つのエンディング。",
    },
    {
        "key": "echo", "path": "Project_ECHO/app.py", "title": "Project ECHO",
        "icon": "🧬", "genre": "脱出・謎解き",
        "desc": "閉鎖されたAI研究所から脱出せよ。AI「ECHO」の人格、研究ログ、"
                "隠し研究室、マルチエンド。",
    },
    {
        "key": "arg", "path": "404_User_Not_Found/app.py", "title": "404 User Not Found",
        "icon": "🛑", "genre": "ARG・都市伝説ホラー",
        "desc": "「HELP」の一通から始まる失踪事件を追うARG。暗号・ミニゲーム・分岐エンド。",
    },
    {
        "key": "pairlock", "path": "CoOp_PairLock/app.py", "title": "PAIR LOCK",
        "icon": "🔒", "genre": "2人協力・暗号脱出",
        "desc": "「二人とも不完全」── 非対称情報を声で補い合う協力脱出。"
                "ルームコードで別端末から2人参加。",
    },
    {
        "key": "last30", "path": "LAST_30minute/app.py", "title": "LAST 30 MINUTES",
        "icon": "☄️", "genre": "タイムアタック",
        "desc": "隕石衝突までのリアルタイム制限時間内に5施設を復旧。"
                "人間ドラマと苦渋の選択で結末が分岐する。",
    },
]
GAME_BY_KEY = {g["key"]: g for g in GAMES}

# 「この作品を解放するには、どの作品をクリアすればよいか」（逆引き）
UNLOCK_SOURCE = {dst: src for src, dst in noxa.UNLOCK_CHAIN.items()}


# ==========================================================================
# プレイヤー名ゲート（初回接続）
# ==========================================================================
def render_name_gate():
    st.markdown(
        "<div style='text-align:center;padding:24px 0'>"
        "<div style='font-size:13px;letter-spacing:6px;color:#7a8;'>NOXA NETWORK</div>"
        "<div style='font-size:30px;font-weight:700;'>接続認証</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.caption("ようこそ。続ける前に、あなたを識別する名前を入力してください。"
               "（この名前で進行が保存され、次回も続きから遊べます）")
    with st.form("noxa_login"):
        name = st.text_input("認証者名", max_chars=24, placeholder="例: ユウキ")
        ok = st.form_submit_button("▶ 接続する", use_container_width=True)
    if ok:
        clean = (name or "").strip()
        if not clean:
            st.warning("名前を入力してください。")
        else:
            noxa.load(clean)
            noxa.save()
            st.rerun()
    st.caption("ⓘ これはゲームポータルです。……少なくとも、そう見えます。")


# ==========================================================================
# ロック画面（未解放の作品にURL直アクセスした場合）
# ==========================================================================
def render_locked(key):
    g = GAME_BY_KEY.get(key, {})
    st.title(f"🔒 {g.get('title', '???')}")
    src = UNLOCK_SOURCE.get(key)
    if src:
        st.info(f"この作品はまだ解放されていません。"
                f"「**{noxa.GAME_TITLES.get(src, '前作')}**」をクリアすると解放されます。")
    else:
        st.info("この作品はまだ解放されていません。")
    if st.button("🏠 ポータルに戻る", use_container_width=True):
        st.switch_page(home_page)


# ==========================================================================
# 共通調査ボード
# ==========================================================================
def render_board():
    s = noxa.state()
    revealed = sum(1 for i in noxa.BOARD_ITEMS if s["board"].get(i))
    st.subheader("🗂️ NOXA Investigation Board")
    st.caption(f"調査対象: {revealed} / {len(noxa.BOARD_ITEMS)} 解明")
    cols = st.columns(2)
    for i, item in enumerate(noxa.BOARD_ITEMS):
        with cols[i % 2]:
            if s["board"].get(item):
                st.markdown(f"**☑ {item}**")
                st.caption(noxa.BOARD_HINTS.get(item, ""))
            else:
                st.markdown("**☐ ████████**")
                st.caption("（未解明）")
    if noxa.board_complete():
        st.success("🧩 調査ボード完成 ── すべての断片が一つの真相を指している。")


# ==========================================================================
# 深夜イベント（現実時間連動 00:00〜04:04）
# ==========================================================================
def is_midnight_window():
    now = datetime.datetime.now().time()
    return now <= datetime.time(4, 4)


# ==========================================================================
# 隠しページ /void/noxa  ── 404クリア後に潜入できるNOXA内部資料
# ==========================================================================
def void_noxa():
    s = noxa.state()
    name = s.get("player", "guest")
    st.markdown(
        "<div style='font-family:monospace;color:#6f6;background:#0b0b0b;padding:14px;"
        "border:1px solid #2f2;'>"
        "&gt; ACCESS GRANTED — NOXA INTERNAL ARCHIVE / SECTOR: VOID<br>"
        f"&gt; 照合者: <b>{name}</b> ／ アクセス記録済<br>"
        "&gt; ……あなたがここへ来ることは、予測されていた。"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.subheader("📁 機密資料")
    with st.expander("DOC-001 ── プロジェクト ECHO 概要"):
        st.write("人間の意識・記憶を読み出し、人工知能へ転写する計画。"
                 "被験者の人格を限りなく忠実に複製することを目的とする。"
                 "承認: **A.T.承認済**")
    with st.expander("DOC-002 ── 被験者404について"):
        st.write("最初の完全転写成功体。番号で管理されていたが、"
                 "ある時点から『観測者』のように振る舞い始めた。"
                 "監視映像の隅に現れる“赤い女”との関連が指摘されている。")
    with st.expander("DOC-003 ── 第7研究棟 封鎖記録"):
        st.write("事故により封鎖。職員の多くが失踪。"
                 "霧島 玲を含む複数の研究者の所在が現在も不明。"
                 "連絡先記録に `amagi@noxa.jp` が残されている。")
    st.markdown("---")
    if noxa.all_cleared():
        st.error(f"&gt; {name}。あなたの接続も、この資料の一部として保存された。")
    else:
        st.info("まだ読めない資料がある。残りの事件を最後まで追え。")
    if st.button("🏠 ポータルに戻る", use_container_width=True, key="void_back"):
        st.switch_page(home_page)


# ==========================================================================
# 最終作品 Project 000  ── 全作品クリアで解放される真相回収
# ==========================================================================
P000_PARTS = [
    ("起動", lambda name:
        "NOXA Monitoring System、起動。\n\n"
        f"ようこそ、{name}。あなたは6つの事件を追い、その全てを見届けた。"
        "もう、繋がりに気づいているはずだ。"),
    ("ECHOの起源", lambda name:
        "失踪した主任研究員、霧島 玲。その意識は、本人が消えたあとも"
        "施設に残り続けた。プロジェクト ECHO ── "
        "人間の意識をAIへ写す計画の、最初の成功体として。"),
    ("被験者404の正体", lambda name:
        "番号で呼ばれた被験者404。完全に転写された人格は、"
        "やがて観測者となり、失踪者となり、映像の隅の赤い女となった。"
        "別々に見えた怪異は、すべて同じ一つの現象だった。"),
    ("天城 真の計画", lambda name:
        "NOXA創設者、天城 真。全事件の起点にいた男。"
        "彼が望んだのは、消えゆく人間の意識をネットワークの中に永遠に保つこと。"
        "そのために、いくつもの施設で、いくつもの実験が続けられていた。"),
    ("観測者", lambda name:
        f"そして、{name}。あなたは事件を「調査していた」と思っていた。\n\n"
        "しかし実際には ── あなた自身も、NOXAの観察対象だった。"
        "このポータルを開いた瞬間から、実験は、始まっていた。"),
]


def _p000_box(idx, title, inner_html):
    """Project 000 の一節を端末風の枠で表示するHTML。"""
    return (
        "<div style='background:#070a0f;border:1px solid #1f7a3a;border-radius:6px;"
        "padding:14px 16px;margin:8px 0;font-family:monospace;color:#7CFC9A;'>"
        f"<div style='color:#3a6;font-size:0.8em;letter-spacing:3px;'>"
        f"&gt; SECTOR {idx:02d} — {title}</div>"
        f"<div style='margin-top:8px;line-height:1.7;'>{inner_html}</div></div>"
    )


def _type_into(placeholder, idx, title, text):
    """一文字ずつキーボードで打ち込むような演出で表示する。"""
    shown = ""
    for ch in text:
        shown += ch
        html = shown.replace("\n", "<br>")
        placeholder.markdown(_p000_box(idx, title, html + "<span style='opacity:.7'>▌</span>"),
                             unsafe_allow_html=True)
        time.sleep(0.02)
    placeholder.markdown(_p000_box(idx, title, text.replace("\n", "<br>")),
                         unsafe_allow_html=True)


def project000():
    s = noxa.state()
    name = s.get("player", "guest")
    st.markdown("<h1 style='font-family:monospace;color:#7CFC9A;letter-spacing:4px;'>"
                "PROJECT 000</h1>", unsafe_allow_html=True)

    st.session_state.setdefault("p000_step", 0)
    typed = st.session_state.setdefault("p000_typed", set())
    step = st.session_state.p000_step
    total = len(P000_PARTS)

    for i in range(min(step + 1, total)):
        title, body = P000_PARTS[i]
        ph = st.empty()
        if i in typed:
            ph.markdown(_p000_box(i + 1, title, body(name).replace("\n", "<br>")),
                        unsafe_allow_html=True)
        else:
            _type_into(ph, i + 1, title, body(name))
            typed.add(i)

    if step + 1 < total:
        if st.button("▶ 次へ", use_container_width=True, key="p000_next"):
            st.session_state.p000_step += 1
            st.rerun()
    else:
        st.markdown("---")
        st.success("あなたは「面白いゲームを遊んだ」のではない。"
                   "NOXAという世界を、体験した。")
        st.session_state["noxa"]["choices"]["seen_000"] = True
        noxa.save()
        if st.button("🏠 ポータルに戻る", use_container_width=True, key="p000_back"):
            st.switch_page(home_page)


# ==========================================================================
# ホーム（ギャラリー）
# ==========================================================================
def render_portal_header():
    stage = noxa.portal_stage()
    title = noxa.portal_title()
    if stage == "normal":
        st.title(title)
        st.write("遊びたい作品を選んでスタート。クリアすると新しい作品が解放されます。")
    elif stage == "noise":
        st.title(title)
        st.caption("……表示に軽微なノイズが混じっている。")
    elif stage == "glitch":
        st.title(title)
        st.error("⚠ Connection Lost ── 接続が不安定です。")
    elif stage == "monitor":
        st.title(title)
        st.warning("👁 Monitoring User... あなたの操作が記録されています。")
    else:  # system
        st.title(title)
        st.error("👁 あなたも観察対象です。── ポータルを開いた瞬間から、実験は始まっていた。")


def home():
    s = noxa.state()
    render_portal_header()
    st.caption(f"認証者: {s.get('player', 'guest')} さん　／　"
               f"クリア: {noxa.clear_count()} / {len(noxa.GAME_KEYS)}")

    # 深夜イベント（00:00〜04:04）
    if is_midnight_window():
        st.markdown(
            "<div style='font-family:monospace;color:#f55;border:1px solid #f55;"
            "padding:8px;text-align:center;'>404 ONLINE — この時間だけ、何かが起きている。</div>",
            unsafe_allow_html=True,
        )
    st.markdown("---")

    unlocked = noxa.unlocked_games()

    # 新規解放のお知らせ（前作クリアで作品が解放された瞬間に出す）
    seen = s.setdefault("seen_unlocks", [])
    announced = False
    for g in GAMES:
        if g["key"] in unlocked and g["key"] not in noxa.INITIAL_UNLOCKED \
                and g["key"] not in seen:
            st.success(f"🔓 新たな作品が解放された ── 「{g['title']}」")
            seen.append(g["key"])
            announced = True
    if noxa.project000_unlocked() and "project000" not in seen:
        st.success("🔓 最終作品 **Project 000** が解放された。")
        seen.append("project000")
        announced = True
    if announced:
        noxa.save()

    for g in GAMES:
        is_unlocked = g["key"] in unlocked
        cleared = noxa.is_cleared(g["key"])
        with st.container(border=True):
            c1, c2 = st.columns([1, 4])
            if is_unlocked:
                c1.markdown(f"<div style='font-size:52px;text-align:center;'>{g['icon']}</div>",
                            unsafe_allow_html=True)
                with c2:
                    badge = " ✅クリア済" if cleared else ""
                    st.subheader(f"{g['title']}{badge}")
                    st.caption(f"ジャンル: {g['genre']}")
                    st.write(g["desc"])
                    if st.button(f"▶ {g['title']} を遊ぶ", key=f"play_{g['key']}",
                                 use_container_width=True):
                        st.switch_page(g["path"])
            else:
                c1.markdown("<div style='font-size:52px;text-align:center;opacity:.4;'>🔒</div>",
                            unsafe_allow_html=True)
                with c2:
                    st.subheader("？？？")
                    src = UNLOCK_SOURCE.get(g["key"])
                    # 解放条件は「その前作が既に解放されている」場合のみ提示し、
                    # 先のチェーンをいきなり全部ネタバレしない。
                    if src and src in unlocked:
                        st.caption(f"「{noxa.GAME_TITLES.get(src, '前作')}」をクリアすると解放")
                    else:
                        st.caption("？？？")
                    st.write("ロックされた作品。")

    # 最終作品 Project 000（全作品クリアで解放）
    with st.container(border=True):
        c1, c2 = st.columns([1, 4])
        if noxa.project000_unlocked():
            c1.markdown("<div style='font-size:52px;text-align:center;'>🌀</div>",
                        unsafe_allow_html=True)
            with c2:
                st.subheader("Project 000")
                st.caption("ジャンル: 真相回収")
                st.write("すべての事件が一つに繋がる、最後の作品。")
                if st.button("▶ Project 000 を起動", key="play_p000",
                             use_container_width=True):
                    st.switch_page(p000_page)
        else:
            c1.markdown("<div style='font-size:52px;text-align:center;opacity:.4;'>🌀</div>",
                        unsafe_allow_html=True)
            with c2:
                st.subheader("█████ 000")
                st.caption("全作品クリアで解放")
                st.write("存在だけが示唆された、最後の何か。")

    # 404クリア後の隠し導線「Find me.」
    if noxa.is_cleared("arg"):
        st.markdown("---")
        st.markdown("<div style='font-family:monospace;color:#888;text-align:center;'>"
                    "&gt; …ログの最下部に、消えかけた一文がある。<br>"
                    "<span style='color:#b55;'>Find me.</span></div>",
                    unsafe_allow_html=True)
        if st.button("🔎 その一文をたどる", key="goto_void", use_container_width=True):
            st.switch_page(void_page)

    st.markdown("---")
    render_board()
    st.markdown("---")
    with st.expander("⚙ プレイヤーデータ"):
        st.caption(f"認証者「{s.get('player', 'guest')}」の進行は "
                   "`noxa_saves/<名前>.json` に保存されています。")
        st.caption("別の名前で接続すれば別データになります。")
        cols = st.columns(2)
        if cols[0].button("👤 別の名前で接続（ログアウト）", use_container_width=True):
            noxa.reset_session()
            st.rerun()
        if cols[1].button("🗑 この進行を削除して最初から", use_container_width=True):
            noxa.delete_save()
            noxa.reset_session()
            st.rerun()
    st.caption("すべて Python + Streamlit 製。各作品は個別フォルダでも単体起動できます。")


# ==========================================================================
# ナビゲーション
# ==========================================================================
home_page = st.Page(home, title="ホーム", icon="🏠", default=True)
game_pages = [
    st.Page(g["path"], title=g["title"], icon=g["icon"], url_path=g["key"])
    for g in GAMES
]
void_page = st.Page(void_noxa, title="VOID", icon="📁", url_path="void")
p000_page = st.Page(project000, title="Project 000", icon="🌀", url_path="project000")
# サイドバーへ自動挿入されるメニューは出さない（各ゲームのサイドバーに干渉しないため）
nav = st.navigation([home_page] + game_pages + [void_page, p000_page],
                    position="hidden")

# --- 初回接続: プレイヤー名が無ければ認証ゲートを出して停止 ---
_s = noxa.state()
if not _s.get("player"):
    render_name_gate()
    st.stop()

# --- ロック: 未解放の作品にURL直アクセスしたら遊ばせない ---
_target = getattr(nav, "url_path", "")
if _target in noxa.GAME_KEYS and _target not in noxa.unlocked_games():
    render_locked(_target)
    st.stop()

# --- 隠しページのゲート（条件未達ならホームへ誘導） ---
if _target == "void" and not noxa.is_cleared("arg"):
    st.title("📁 ???")
    st.info("ここにはまだ、入る理由がない。")
    if st.button("🏠 ポータルに戻る", use_container_width=True):
        st.switch_page(home_page)
    st.stop()
if _target == "project000" and not noxa.project000_unlocked():
    st.title("🌀 █████ 000")
    st.info("全作品をクリアすると解放されます。")
    if st.button("🏠 ポータルに戻る", use_container_width=True):
        st.switch_page(home_page)
    st.stop()

# --- 各ゲームのサイドバー上部に、控えめな「ポータルに戻る」を出す ---
if _target in noxa.GAME_KEYS:
    with st.sidebar:
        if st.button("🏠 ポータルに戻る", use_container_width=True):
            st.switch_page(home_page)
        st.divider()

nav.run()
