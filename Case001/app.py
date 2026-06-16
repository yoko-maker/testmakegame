"""Case001 消えた研究者 — 探偵推理ゲーム。

著名な研究者・霧島博士が失踪。プレイヤーは探偵として現場を調査し、
4つの解析ミニゲームで証拠を集め、容疑者を絞り込み、真犯人を推理する。

  🧩 指紋照合       指紋一致探し   → 指紋証拠     （犯人＝佐倉／手段＝薬物）
  📹 防犯カメラ解析 スライドパズル → 容疑者映像   （犯人＝佐倉／B・Cはアリバイ）
  📱 スマホ解析     ヒット&ブロー  → メッセージ履歴（動機＝独占）
  🧪 研究データ解析 タイムライン矛盾発見 → 動機情報 （動機＝独占／偽証拠の存在）
  🔍 隠し解析       全証拠後に解放 → 隠し証拠     （Secret End条件）

真相: 犯人=佐倉(共同研究者) / 動機=研究成果の独占 / 手段=薬物を盛り昏睡させた

【作り込みメモ】
- 被害者: 霧島 玲（ノクサ研究機構ECHO計画の主任研究者）。失踪は組織で続く一連の
  研究者失踪の一つでもある。日記・メッセージ履歴で人物像と恨みの構図を描く。
- ミスリード: 「黒田の脅迫メモ」。素直に集めると黒田犯人だと誤認(Bad End)へ誘導する罠。
  実は佐倉が黒田を陥れるために仕込んだ偽証拠で、これを見抜くのがSecret Endの核心。
- 共通世界観: ノクサ研究機構 / プロジェクトECHO / 数字404 / 相次ぐ失踪
  （資料の隅に軽く触れる程度。各作品は単体で完結する）。
"""

import random

import streamlit as st

try:
    st.set_page_config(page_title="Case001 消えた研究者", page_icon="🕵️", layout="centered")
except Exception:
    pass  # ポータルに統合された場合は無視

# NOXA Universe（ポータル統合時のみ利用可能 / 単体起動では import 失敗を無視）
try:
    import noxa_core as _noxa
except Exception:
    _noxa = None

# 正解
SUSPECT_A = "佐倉（共同研究者）"
MOTIVE_ANS = "研究成果の独占"
METHOD_ANS = "薬物を盛り昏睡させた"

SUSPECTS = [SUSPECT_A, "黒田（元上司）", "高村（競合企業社員）"]
MOTIVES = ["研究成果の独占", "金銭トラブル", "私怨・逆恨み", "口封じ"]
METHODS = ["薬物を盛り昏睡させた", "凶器で襲撃した", "脅迫して連れ去った", "事故に見せかけた"]

# 証拠と手がかり
EVIDENCE_CLUE = {
    "指紋証拠": "現場のコーヒーカップから共同研究者・佐倉の指紋を検出。さらにカップから微量の睡眠導入剤が見つかった。",
    "容疑者映像": "事件当夜23:40、白衣の人物が研究室へ最後に入る映像。IDゲート記録は『佐倉』。黒田と高村は当夜の入館記録なし。"
                  "（解析担当注記: 22:08のロビー映像の隅に、赤い服の女が一瞬映り込んでいる。来訪記録に該当者なし。事件との関連は不明。）",
    "メッセージ履歴": "被害者・霧島玲のスマホのロックを解除。佐倉からのメッセージ『成果は私のものだ』に加え、"
                      "玲自身の日記下書き ―『ECHOの権利を独占したい人がいる。私を消したい人がいる。404号室の鍵は預けた』。"
                      "受信トレイの隅には差出人 amagi@noxa.jp の古い未読メール（件名『A.T.承認済 ― 共同研究の件』）も残っていた。",
    "動機情報": "研究データ解析で、ECHO計画の特許出願書類が佐倉の単独名義に書き換えられていたと判明。"
                "同じフォルダに、黒田を名指しした『脅迫メモ』の画像も保存されていた。",
    "脅迫メモ": "「成果を渡さなければ後悔するぞ ― 黒田」と署名された脅迫メモ。",
    "隠し証拠": "佐倉のPCを深掘り。脅迫メモの原本ファイルは事件当夜0:14に佐倉のアカウントで作成・署名されていた。"
                "黒田を陥れる偽証拠を仕込んだのは佐倉本人。単独犯を取り繕う工作の全貌が露わになった。",
}

# 被害者・霧島玲の人物像（日記／メッセージ抜粋）。動機推理の手がかり。
VICTIM_DIARY = [
    "4/02 ECHO計画、ようやく実証フェーズ。10年分の私の研究がここに結実する。",
    "4/09 佐倉が共同名義の比率にこだわり始めた。彼は『成果は等しく』と言うが、目が笑っていない。",
    "4/15 黒田さんが訪ねてきた。左遷の件で恨んでいると思ったが、ただ研究の行く末を案じていただけだった。和解。",
    "4/20 競合の高村氏から接触。データを売れと。丁重に断った。彼は外部の人間、施設には入れない。",
    "4/26 特許書類の控えが消えている。私を計画から外そうとしている人がいる。確信に近い。",
    "4/30 もし私に何かあれば ― 404号室の鍵を信頼できる者に預けた。真実はそこにある。",
]

ANALYSES = [
    ("指紋照合", "🧩", "print", "指紋証拠", "指紋一致探し"),
    ("防犯カメラ解析", "📹", "slide", "容疑者映像", "スライドパズル"),
    ("スマホ解析", "📱", "pin", "メッセージ履歴", "ヒット&ブロー"),
    ("研究データ解析", "🧪", "timeline", "動機情報", "タイムライン矛盾発見"),
]

# 容疑者の証言（二段構え）。各段で異なる鍵証拠を突きつけて崩す。
INTERROGATION = {
    SUSPECT_A: {
        "verdict": "クロ",
        "stages": [
            {"claim": "事件当夜、私はずっと自宅にいました。研究室には近づいてもいません。",
             "key": "容疑者映像",
             "break": "防犯カメラには23:40、あなたのIDで研究室に入る姿が映っている。"
                      "『自宅にいた』という証言は崩れましたね。"},
            {"claim": "…確かに立ち寄った。だが博士とは良好な関係だ。私が手にかける理由などない。",
             "key": "メッセージ履歴",
             "break": "あなたが博士へ送ったメッセージ ―『成果は私のものだ』。"
                      "研究を独占しようとする強い動機があった。もう言い逃れはできない。"},
        ],
    },
    "黒田（元上司）": {
        "verdict": "シロ",
        "stages": [
            {"claim": "脅迫メモだと？ あんなものは書いていない。当夜は他県の学会だ。疑うなら記録を見ろ。",
             "key": "容疑者映像",
             "break": "入館記録にあなたの名はなく、学会出席も確認できた。当夜のアリバイは成立だ。"
                      "では“黒田名義の脅迫メモ”は一体誰が用意した？"},
            {"claim": "私と博士は揉めたきりだと思っているのか。それは違う。",
             "key": "メッセージ履歴",
             "break": "博士の手記に『黒田さんとは和解した』との記述。脅迫の動機そのものが存在しない。"
                      "あなたを名指しする脅迫メモは、誰かがあなたに罪を着せるための作り物だ。シロだ。"},
        ],
    },
    "高村（競合企業社員）": {
        "verdict": "シロ",
        "stages": [
            {"claim": "競合というだけで犯人扱いか。私はあの施設に、痕跡ひとつ残していないはずだ。",
             "key": "指紋証拠",
             "break": "現場から検出された指紋は佐倉のものだけ。あなたの物証は一つもない。"},
            {"claim": "では、私が研究データを欲しがって動いたとでも言うのか？",
             "key": "動機情報",
             "break": "特許を独占して利益を得たのは佐倉だ。あなたが実行犯である線は完全に消えた。シロだ。"},
        ],
    },
}
MAX_CREDIT = 5


# ==========================================================================
# 状態管理
# ==========================================================================
def init_state(key, value):
    if key not in st.session_state:
        st.session_state[key] = value


def init_game():
    init_state("case_started", False)
    init_state("case_view", "board")
    init_state("case_evidences", [])
    init_state("case_clues", [])
    init_state("case_verdicts", {})  # {容疑者: "クロ"/"シロ"}
    init_state("case_stage", {})     # {容疑者: 崩した証言の数}
    init_state("case_credit", MAX_CREDIT)  # 捜査信用度
    init_state("case_redherring", False)   # ミスリード「脅迫メモ」を発見したか
    init_state("case_saw_through", False)   # 偽証拠を見抜いたか（隠し解析の解放条件）
    init_state("case_memo_trust", False)    # 偽証拠を額面通り信じてしまったか
    init_state("case_ending", None)


def reset_game():
    for key in list(st.session_state.keys()):
        if key.startswith("case_") or key.startswith("rm_"):
            del st.session_state[key]
    init_game()


def gain_evidence(name):
    if name not in st.session_state.case_evidences:
        st.session_state.case_evidences.append(name)
        st.session_state.case_clues.append(EVIDENCE_CLUE[name])
        # 研究データ解析では、同時にミスリードの「脅迫メモ」も発見される。
        # これは正規の証拠リストには加えず、別管理で誤誘導の罠として機能させる。
        if name == "動機情報":
            st.session_state.case_redherring = True
            st.session_state.case_clues.append(EVIDENCE_CLUE["脅迫メモ"])


def has_evidence(name):
    return name in st.session_state.case_evidences


def goto(view):
    st.session_state.case_view = view
    st.rerun()


# ==========================================================================
# サイドバー（証拠ファイル）
# ==========================================================================
def render_sidebar():
    st.sidebar.title("🕵️ Case001")
    st.sidebar.caption("消えた研究者")

    if st.session_state.case_started and st.session_state.case_ending is None:
        st.sidebar.subheader("🗂️ 証拠ファイル")
        evs = st.session_state.case_evidences
        if not evs:
            st.sidebar.caption("まだ証拠はない")
        for e in evs:
            st.sidebar.write(f"✅ {e}")
        st.sidebar.caption(f"収集: {len(evs)} / 5")

        credit = st.session_state.case_credit
        st.sidebar.caption(f"🛡️ 捜査信用度: {'❤️' * credit}{'🖤' * (MAX_CREDIT - credit)}")

    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 最初から捜査し直す"):
        reset_game()
        st.rerun()


# ==========================================================================
# イントロ（現場調査）
# ==========================================================================
def page_intro():
    st.title("🕵️ Case001 ―『消えた研究者』")
    st.markdown(
        """
        次世代AIの第一人者、**霧島 玲（きりしま れい）博士**が研究室から忽然と姿を消した。
        争った形跡、飲みかけのコーヒー、そして消えた研究データ——。

        博士が率いていたのは、人間の記憶と意識をAIへ写し取る極秘プロジェクト **「ECHO」**。
        だが近頃、同じ機構では研究者が一人、また一人と姿を消しているという噂もある。

        あなたは私立探偵。現場に残された痕跡を **4つの解析** で読み解き、
        3人の容疑者から**真犯人**を、その**動機**と**犯行手段**まで突き止めろ。
        """
    )
    st.info("💡 各解析（ミニゲーム）をクリアすると証拠が手に入る。全て揃えば隠された真実に近づけるかも。")
    st.caption("⚠️ 証拠の中には、誰かが意図的に仕込んだ“都合のいい証拠”が紛れているかもしれない。鵜呑みは禁物だ。")
    if st.button("🔦 捜査を開始する", use_container_width=True):
        st.session_state.case_started = True
        st.session_state.case_view = "board"
        st.rerun()


# ==========================================================================
# 捜査ボード（証拠収集ハブ）
# ==========================================================================
def page_board():
    st.header("🗺️ 捜査ボード")
    st.write("解析したい対象を選べ。集めた証拠は左の証拠ファイルに記録される。")

    for name, icon, view, reward, gtype in ANALYSES:
        done = has_evidence(reward)
        label = f"{icon} {name}（{gtype}）" + ("　✅ 解析済み" if done else "")
        if st.button(label, key=f"go_{view}", use_container_width=True):
            goto(view)
        if done:
            st.caption(f"　└ 入手: **{reward}** ― {EVIDENCE_CLUE[reward]}")

    st.markdown("---")

    # ミスリードの見破り → これを経て隠し解析が解放される（Secret Endの核心）
    base4 = all(has_evidence(r) for _, _, _, r, _ in ANALYSES)
    if st.session_state.case_redherring and not st.session_state.get("case_saw_through"):
        st.write("📄 **黒田を名指しする『脅迫メモ』** が証拠として見つかっている。"
                 "この証拠をどう扱うか、あなたの判断は？")
        cse1, cse2 = st.columns(2)
        if cse1.button("✅ 脅迫メモをそのまま信じる", use_container_width=True):
            st.session_state.case_memo_trust = True
            st.rerun()
        if cse2.button("🧐 脅迫メモを疑ってみる", use_container_width=True):
            st.session_state.case_saw_through = True
            st.session_state.case_memo_trust = False
            st.rerun()

    if st.session_state.get("case_saw_through"):
        st.info("🧐 あなたは脅迫メモを疑った。本当に作為があるなら、メモを仕込んだ者の痕跡がどこかに残っているはずだ。")

    # 隠し解析（全4証拠 ＋ 偽証拠の見破りで解放）
    if base4 and st.session_state.get("case_saw_through") and not has_evidence("隠し証拠"):
        st.write("🔍 メモの出所を追うなら、佐倉のPCにまだ解析していない領域がある。")
        if st.button("🔍 佐倉のPCを深掘り解析する", use_container_width=True):
            gain_evidence("隠し証拠")
            st.rerun()
    elif has_evidence("隠し証拠"):
        st.success(f"📕 隠し証拠: {EVIDENCE_CLUE['隠し証拠']}")

    st.markdown("---")
    resolved = sum(1 for s in SUSPECTS if s in st.session_state.case_verdicts)
    main_ev = sum(1 for _, _, _, r, _ in ANALYSES if has_evidence(r))
    c1, c2 = st.columns(2)
    if c1.button("👤 容疑者ファイルを見る", use_container_width=True):
        goto("suspects")
    if c2.button(f"🔦 容疑者を追及する（{resolved}/3）", use_container_width=True):
        goto("interrogate")
    if st.button("🧠 推理を始める", use_container_width=True):
        goto("deduce")

    st.caption(f"進捗 ― 証拠 {main_ev}/4 ・ 追及 {resolved}/3。両方を終えると告発できる。")


# ==========================================================================
# 容疑者ファイル
# ==========================================================================
def page_suspects():
    st.header("👤 容疑者ファイル")

    st.subheader("容疑者A ― 佐倉 透（さくら とおる／37）")
    st.write("**職業:** ECHO計画の共同研究者。霧島博士の右腕。")
    st.write("**動機:** 10年の研究成果を独占し、自分の名で発表したい野心。特許の単独名義化を画策。")
    st.write("**アリバイ:** 「当夜は自宅にいた」と主張。だが研究室のIDゲート記録が残っている。")
    st.write("**嘘:** 博士とは『良好な関係』だと言うが、独占を迫るメッセージを送っていた。")

    st.subheader("容疑者B ― 黒田 修三（くろだ しゅうぞう／58）")
    st.write("**職業:** 霧島博士の元上司。研究方針の対立で左遷された過去を持つ。")
    st.write("**動機:** 表向きは『恨み』。だが博士の日記によれば既に和解しており、利益も得ていない。")
    st.write("**アリバイ:** 当夜は他県の学会に出席。施設の入館記録なし。")
    st.write("**嘘:** 本人に嘘はない。ただし“黒田を名指しする脅迫メモ”が彼を犯人に見せかけている。")

    st.subheader("容疑者C ― 高村 蓮（たかむら れん／42）")
    st.write("**職業:** 競合企業の社員。ECHOの研究データを狙い、博士に接触していた。")
    st.write("**動機:** データの奪取。ただし外部の人間で施設へは入れず、実行の手段を欠く。")
    st.write("**アリバイ:** 当夜の施設入館記録は確認されていない。現場に物証も一切残っていない。")
    st.write("**嘘:** 『痕跡ひとつ残していない』と豪語 ― これは事実で、だからこそ実行犯ではあり得ない。")

    st.markdown("---")
    st.subheader("📔 被害者・霧島玲の手記（復元抜粋）")
    if has_evidence("メッセージ履歴"):
        for line in VICTIM_DIARY:
            st.caption(f"・{line}")
    else:
        st.caption("（被害者のスマホを復号すれば、本人の手記が読めるはず ― スマホ解析を進めよう）")

    st.markdown("---")
    if st.session_state.case_redherring:
        st.write("📄 黒田を名指しした『脅迫メモ』が証拠として見つかっている。")

    st.subheader("🔎 これまでに判明した手がかり")
    if st.session_state.case_clues:
        for cl in st.session_state.case_clues:
            st.write(f"- {cl}")
    else:
        st.caption("まだ手がかりがない。解析を進めよう。")

    st.markdown("---")
    c1, c2 = st.columns(2)
    if c1.button("🔦 容疑者を追及する", use_container_width=True):
        goto("interrogate")
    if c2.button("↩️ 捜査ボードに戻る", use_container_width=True):
        goto("board")


# ==========================================================================
# ミニゲーム1: 指紋一致探し → 指紋証拠
# ==========================================================================
# 8×（線の向き×渦の形）で見分けのつく指紋パターンを構成。
# 並んだ指紋の中から、現場指紋と完全に一致する1枚を目視で選ばせる。
PRINT_RIDGE = ["╱╲╱╲", "╲╱╲╱", "╳╳╳╳", "═══", "║║║║", "◌◌◌", "◍◍◍", "❨❨❨"]
PRINT_CORE = ["◉", "◎", "⊙", "●", "◐", "◑", "✸", "✦"]


def make_print(ridge, core):
    """指紋カードの見た目を生成（線の流れ＋中心の渦）。"""
    return f"{ridge}\n {core}{core}\n{ridge}"


def setup_print():
    # 8種の指紋パターンから現場指紋を1つ選び、残りは別パターンを並べる。
    patterns = list(zip(PRINT_RIDGE, PRINT_CORE))
    random.shuffle(patterns)
    target = patterns[0]
    # 並べる候補（現場指紋1枚＋紛らわしいダミー）。target を必ず1枚だけ含める。
    others = patterns[1:6]
    cards = others + [target]
    random.shuffle(cards)
    st.session_state.rm_print_target = target
    st.session_state.rm_print_cards = cards
    st.session_state.rm_print_miss = 0


def view_print():
    st.header("🧩 指紋照合（指紋一致探し）")
    st.caption("現場のコーヒーカップから採取した指紋と、ぴったり一致する1枚を候補から見つけ出せ。")

    if has_evidence("指紋証拠"):
        st.success("✅ 指紋証拠は照合済み。")
        if st.button("↩️ 捜査ボードに戻る"):
            goto("board")
        return

    if "rm_print_cards" not in st.session_state:
        setup_print()

    target = st.session_state.rm_print_target
    cards = st.session_state.rm_print_cards

    st.markdown("##### 🔬 現場で採取した指紋（照合の基準）")
    st.code(make_print(*target), language=None)

    st.markdown("##### 🗂️ 容疑者データベースの指紋候補")
    st.write("基準と完全に一致するものを1枚選べ。線の流れと中心の渦をよく見比べること。")

    for row in range(2):
        cols = st.columns(3)
        for c in range(3):
            idx = row * 3 + c
            card = cards[idx]
            cols[c].code(make_print(*card), language=None)
            if cols[c].button(f"この指紋を照合 (No.{idx + 1})", key=f"print_{idx}", use_container_width=True):
                if card == target:
                    gain_evidence("指紋証拠")
                else:
                    st.session_state.rm_print_miss += 1
                st.rerun()

    miss = st.session_state.rm_print_miss
    if miss:
        st.error(f"❌ 一致しない指紋だ。線の向きと中心の形をもう一度確認しよう。（誤照合 {miss} 回）")

    if st.button("↩️ 捜査ボードに戻る"):
        goto("board")


# ==========================================================================
# ミニゲーム2: スライドパズル → 容疑者映像
# ==========================================================================
GOAL = [1, 2, 3, 4, 5, 6, 7, 8, 0]


def slide_neighbors(i):
    r, c = divmod(i, 3)
    res = []
    if r > 0:
        res.append(i - 3)
    if r < 2:
        res.append(i + 3)
    if c > 0:
        res.append(i - 1)
    if c < 2:
        res.append(i + 1)
    return res


def setup_slide():
    tiles = GOAL[:]
    blank = 8
    for _ in range(80):
        swap = random.choice(slide_neighbors(blank))
        tiles[blank], tiles[swap] = tiles[swap], tiles[blank]
        blank = swap
    st.session_state.rm_slide = tiles
    st.session_state.rm_slide_moves = 0


def view_slide():
    st.header("📹 防犯カメラ解析（スライドパズル）")
    st.caption("乱れた映像フレームを 1〜8 の順に並べ替えると、当夜の映像が復元される。")

    if has_evidence("容疑者映像"):
        st.success("✅ 容疑者映像は復元済み。")
        if st.button("↩️ 捜査ボードに戻る"):
            goto("board")
        return

    if "rm_slide" not in st.session_state:
        setup_slide()

    tiles = st.session_state.rm_slide
    blank = tiles.index(0)
    cleared = tiles == GOAL
    if cleared:
        gain_evidence("容疑者映像")

    for row in range(3):
        cols = st.columns(3)
        for c in range(3):
            idx = row * 3 + c
            val = tiles[idx]
            if val == 0:
                cols[c].button("　", key=f"sl_{idx}", use_container_width=True, disabled=True)
            else:
                movable = idx in slide_neighbors(blank) and not cleared
                if cols[c].button(str(val), key=f"sl_{idx}", use_container_width=True, disabled=not movable):
                    tiles[blank], tiles[idx] = tiles[idx], tiles[blank]
                    st.session_state.rm_slide_moves += 1
                    st.rerun()

    st.metric("手数", st.session_state.rm_slide_moves)
    if cleared:
        st.balloons()
        st.success("🎉 映像を復元！ **容疑者映像** を入手した。")
    else:
        if st.button("🔀 並べ直す（シャッフル）"):
            setup_slide()
            st.rerun()

    if st.button("↩️ 捜査ボードに戻る"):
        goto("board")


# ==========================================================================
# ミニゲーム3: ヒット&ブロー（暗証推理） → メッセージ履歴
# ==========================================================================
# 被害者スマホのロックは4桁の暗証番号（数字は重複なし）。
# 毎回の入力に対し「ヒット＝数字も位置も一致」「ブロー＝数字はあるが位置違い」を返す。
def setup_pin():
    digits = random.sample("0123456789", 4)
    st.session_state.rm_pin_code = "".join(digits)
    st.session_state.rm_pin_history = []  # [(guess, hit, blow), ...]


def pin_judge(secret, guess):
    hit = sum(1 for a, b in zip(secret, guess) if a == b)
    blow = sum(1 for g in guess if g in secret) - hit
    return hit, blow


def view_pin():
    st.header("📱 スマホ解析（ヒット&ブロー）")
    st.caption("被害者のスマホのロックは4桁の暗証番号（0〜9、数字の重複なし）。"
               "推理して入力すると、ヒント（ヒット/ブロー）が返る。")

    if has_evidence("メッセージ履歴"):
        st.success("✅ メッセージ履歴は解除済み。")
        if st.button("↩️ 捜査ボードに戻る"):
            goto("board")
        return

    if "rm_pin_code" not in st.session_state:
        setup_pin()

    secret = st.session_state.rm_pin_code
    history = st.session_state.rm_pin_history

    st.info("💡 **ヒット** = 数字も位置も合っている桁数　/　"
            "**ブロー** = 数字は暗証番号に含まれるが位置が違う桁数。"
            "4ヒットで解除。")

    ans = st.text_input("暗証番号を入力（4桁・数字は重複しない）", max_chars=4, placeholder="例: 0123")

    if st.button("🔓 入力して照合"):
        g = ans.strip()
        if len(g) != 4 or not g.isdigit():
            st.error("❌ 4桁の数字を入力してください。")
        elif len(set(g)) != 4:
            st.error("❌ 暗証番号に同じ数字は使われていない。重複のない4桁で。")
        else:
            hit, blow = pin_judge(secret, g)
            history.append((g, hit, blow))
            if hit == 4:
                gain_evidence("メッセージ履歴")
            st.rerun()

    if history:
        st.markdown("##### 📋 これまでの試行")
        for i, (g, hit, blow) in enumerate(reversed(history), 1):
            no = len(history) - i + 1
            st.write(f"`{no:2}`　**{g}**　→　🎯 ヒット {hit}　・　🔵 ブロー {blow}")
        st.caption(f"試行回数: {len(history)}")

    if st.button("↩️ 捜査ボードに戻る"):
        goto("board")


# ==========================================================================
# ミニゲーム4: タイムライン矛盾発見 → 動機情報
# ==========================================================================
# 佐倉が提出したアリバイ時刻表。一見筋が通っているが、1項目だけ辻褄が合わない。
# その矛盾した1項目を見抜くと、供述の嘘＝動機の核心（独占）に辿り着く。
TIMELINE = [
    {"time": "21:30", "text": "研究棟を出て帰宅したと供述。", "ok": True},
    {"time": "22:00", "text": "自宅に到着し、夕食をとったと供述。", "ok": True},
    {"time": "23:40", "text": "自宅で就寝したと供述。", "ok": False,
     "why": "防犯カメラには23:40に佐倉のIDで研究室へ入る姿が記録されている。"
            "『自宅で就寝』とは両立しない ― ここに供述の嘘がある。"},
    {"time": "翌0:30", "text": "物音で一度目を覚ましたが、すぐ眠ったと供述。", "ok": True},
    {"time": "翌7:00", "text": "起床し、いつも通り出勤したと供述。", "ok": True},
]


def view_timeline():
    st.header("🧪 研究データ解析（タイムライン矛盾発見）")
    st.caption("佐倉が提出したアリバイ時刻表。集めた証拠と突き合わせ、辻褄の合わない1項目を見抜け。")

    if has_evidence("動機情報"):
        st.success("✅ 動機情報は解析済み。")
        if st.button("↩️ 捜査ボードに戻る"):
            goto("board")
        return

    init_state("rm_timeline_miss", 0)

    st.markdown("##### 🕰️ 佐倉のアリバイ供述（時系列）")
    if has_evidence("容疑者映像"):
        st.caption("（防犯カメラ解析の記録と照合できる。矛盾する供述があるはずだ。）")
    else:
        st.caption("（先に防犯カメラ解析を進めると、矛盾を裏づけやすい。）")

    for idx, item in enumerate(TIMELINE):
        cols = st.columns([1, 4])
        cols[0].markdown(f"**{item['time']}**")
        cols[1].write(item["text"])
        if cols[1].button("この供述は矛盾している", key=f"tl_{idx}", use_container_width=True):
            if not item["ok"]:
                st.session_state.rm_timeline_found = item["why"]
                gain_evidence("動機情報")
            else:
                st.session_state.rm_timeline_miss += 1
                st.session_state.rm_timeline_found = None
            st.rerun()

    found = st.session_state.get("rm_timeline_found")
    if found:
        st.success(f"🎯 矛盾を発見！ {found}")
        st.info("供述の嘘が割れたことで、特許を単独名義に書き換えた事実 ― **独占の動機** が浮かび上がった。"
                "同じフォルダには黒田を名指しした『脅迫メモ』の画像も保存されていた。")
    elif st.session_state.rm_timeline_miss:
        st.error(f"❌ その供述に矛盾はない。他の証拠と突き合わせて考え直そう。（誤り {st.session_state.rm_timeline_miss} 回）")

    if st.button("↩️ 捜査ボードに戻る"):
        goto("board")


# ==========================================================================
# 容疑者の追及（矛盾追及パート）
# ==========================================================================
def page_interrogate():
    st.header("🔦 容疑者の追及")
    st.markdown(
        "**進め方:**　①追及する容疑者を選ぶ　→　②今出ている証言を読む　→　"
        "③その証言を崩せる証拠を1つ選んで突きつける。\n\n"
        "証言は**二段構え**。各段で“鍵となる証拠”は異なる。正しい証拠を順に突きつけると、その容疑者の白黒が確定する。"
    )

    credit = st.session_state.case_credit
    st.markdown(f"**🛡️ 捜査信用度:** {'❤️' * credit}{'🖤' * (MAX_CREDIT - credit)}")
    st.caption("⚠️ 見当違いの証拠を突きつけると信用度が1減る。0になると捜査失格(Bad End)。")

    evs = list(st.session_state.case_evidences)
    if not evs:
        st.warning("まだ証拠がない。先に解析を進めよう。")
        if st.button("↩️ 捜査ボードに戻る"):
            goto("board")
        return

    verdicts = st.session_state.case_verdicts

    # 容疑者ごとの進捗を一覧で示す（誰が未着手・進行中・完了か一目で分かるように）
    st.markdown("##### 👥 容疑者ごとの追及状況")
    for s in SUSPECTS:
        st_idx = st.session_state.case_stage.get(s, 0)
        total = len(INTERROGATION[s]["stages"])
        if s in verdicts:
            mark = "🔴 クロ（容疑濃厚）" if verdicts[s] == "クロ" else "🟢 シロ（容疑圏外）"
            st.caption(f"・{s}　― ✅ 追及完了：{mark}")
        elif st_idx > 0:
            st.caption(f"・{s}　― ⏳ 追及中（第{st_idx + 1}段／全{total}段）")
        else:
            st.caption(f"・{s}　― ⬜ 未着手（全{total}段）")

    st.markdown("---")
    sel = st.radio("① 追及する容疑者を選ぶ", SUSPECTS, key="itg_sel")
    data = INTERROGATION[sel]
    stages = data["stages"]
    s_idx = SUSPECTS.index(sel)
    stage_idx = st.session_state.case_stage.get(sel, 0)
    resolved = sel in verdicts

    short = sel.split("（")[0]
    st.markdown(f"##### 🗣️ {sel} の追及（全{len(stages)}段）")

    # すでに崩した証言を表示
    for i in range(stage_idx):
        st.success(f"✅ 第{i + 1}段クリア　「{stages[i]['claim']}」\n\n→ {stages[i]['break']}")

    if resolved:
        badge = "🔴 クロ（容疑濃厚）" if verdicts[sel] == "クロ" else "🟢 シロ（容疑圏外）"
        st.markdown(f"### 🎯 {short} の追及完了 ― {badge}")
    else:
        cur = stages[stage_idx]
        st.info(f"② 現在の証言【第{stage_idx + 1}段／全{len(stages)}段】\n\n"
                f"🗨️ {short}:「{cur['claim']}」")
        st.markdown("③ **この証言を崩せる証拠を1つ選んで突きつけろ:**")
        for ev in evs:
            if st.button(f"📎 「{ev}」を突きつける", key=f"itg_{s_idx}_{stage_idx}_{ev}", use_container_width=True):
                if ev == cur["key"]:
                    st.session_state.case_stage[sel] = stage_idx + 1
                    if stage_idx + 1 >= len(stages):
                        verdicts[sel] = data["verdict"]
                    st.session_state.itg_reaction = None
                else:
                    st.session_state.case_credit -= 1
                    if st.session_state.case_credit <= 0:
                        st.session_state.case_ending = "blunder"
                    st.session_state.itg_reaction = (
                        sel, stage_idx,
                        f"《{ev}》を突きつけたが、{short}は動じない。"
                        "「それが何の関係が？」― 決定打にならず、信用度が下がった。",
                    )
                st.rerun()

        react = st.session_state.get("itg_reaction")
        if react and react[0] == sel and react[1] == stage_idx:
            st.warning(react[2])

    st.markdown("---")
    resolved_n = sum(1 for s in SUSPECTS if s in verdicts)
    st.caption(f"追及の進捗: 完了 {resolved_n}/3")
    if resolved_n == len(SUSPECTS):
        kuro = [s for s in SUSPECTS if verdicts[s] == "クロ"]
        st.success("✅ 全員の追及が完了。アリバイが崩れたのは ― " + ("、".join(kuro) if kuro else "誰もいない…？"))

    if st.button("↩️ 捜査ボードに戻る"):
        st.session_state.itg_reaction = None
        goto("board")


# ==========================================================================
# 最終推理
# ==========================================================================
def page_deduce():
    st.header("🧠 最終推理")
    st.write("集めた証拠から、**犯人・動機・犯行手段** を結論づけよ。一度の告発で決まる。")

    # --- 証拠不足時の推理制限 ---
    main_ev = sum(1 for _, _, _, r, _ in ANALYSES if has_evidence(r))
    resolved = sum(1 for s in SUSPECTS if s in st.session_state.case_verdicts)
    ready = (main_ev == 4) and (resolved == len(SUSPECTS))

    if not ready:
        st.error("⚠️ 告発するには準備が足りない。確証なき告発は誤認逮捕を招く。")
        st.write(f"- 証拠の収集: **{main_ev} / 4**" + ("　✅" if main_ev == 4 else "　← 解析が未完了"))
        st.write(f"- 容疑者の追及: **{resolved} / 3**" + ("　✅" if resolved == 3 else "　← 全員を追及せよ"))

    st.markdown("##### 🔎 手がかりの確認")
    if st.session_state.case_clues:
        for cl in st.session_state.case_clues:
            st.caption(f"・{cl}")
    else:
        st.caption("（証拠がない…当てずっぽうになる）")

    if st.session_state.case_verdicts:
        st.markdown("##### ⚖️ 追及の結果")
        for s in SUSPECTS:
            v = st.session_state.case_verdicts.get(s)
            if v:
                st.caption(f"・{s}: {'🔴 クロ' if v == 'クロ' else '🟢 シロ'}")

    if st.session_state.case_redherring:
        if st.session_state.get("case_saw_through"):
            st.caption("🧐 脅迫メモは佐倉が黒田を陥れるための偽証拠だと見抜いた。黒田への告発は誤り。")
        elif st.session_state.get("case_memo_trust"):
            st.warning("⚠️ 黒田名義の脅迫メモを真に受けている。だが手記では博士と黒田は和解済み ― 本当に黒田が犯人か？")

    st.markdown("---")
    crim = st.radio("犯人は誰だ？", SUSPECTS)
    motive = st.radio("その動機は？", MOTIVES)
    method = st.radio("犯行手段は？", METHODS)

    c1, c2 = st.columns(2)
    if c1.button("↩️ 捜査に戻る", use_container_width=True):
        goto("board")
    if c2.button("⚖️ この推理で告発する", use_container_width=True, disabled=not ready):
        if crim != SUSPECT_A:
            st.session_state.case_ending = "bad"
        elif motive == MOTIVE_ANS and method == METHOD_ANS:
            if has_evidence("隠し証拠"):
                st.session_state.case_ending = "secret"
            else:
                st.session_state.case_ending = "perfect"
        else:
            st.session_state.case_ending = "good"
        st.rerun()


# ==========================================================================
# エンディング
# ==========================================================================
def page_ending():
    ending = st.session_state.case_ending
    if _noxa:
        _noxa.report_clear("case001")

    if ending == "perfect":
        st.balloons()
        st.title("🏆 Perfect End ―『完全解決』")
        st.markdown(
            """
            犯人は **佐倉**。動機は **研究成果の独占**、手段は **薬物を盛っての昏睡**。

            コーヒーに混入した睡眠導入剤、書き換えられた特許、そして本人のメッセージ。
            証拠の全てが彼を指していた。観念した佐倉は犯行を自供し、博士は無事に保護された。

            名探偵の推理が、消えた研究者を救い出した。
            """
        )
        st.info("💡 ただし黒田を名指しした『脅迫メモ』の出所までは詰め切れなかった。"
                "あの偽証拠を見抜き、佐倉のPCを深掘りすれば ― 隠された真相(Secret End)に辿り着けるはずだ。")
    elif ending == "secret":
        st.balloons()
        st.title("🌟 Secret End ―『仕組まれた罠』")
        st.markdown(
            """
            犯人 **佐倉**、動機 **研究成果の独占**、手段 **薬物による昏睡** ――全て的中。
            だが、あなたが暴いた最大の真実は別にあった。

            黒田を名指しした**脅迫メモ**。誰もが彼を疑う、あまりに“都合のいい証拠”。
            あなたはそれを鵜呑みにせず、被害者の手記との矛盾から **偽証拠** だと見抜いた。

            佐倉のPCを深掘りすれば原本ファイルが残っていた ―
            脅迫メモは事件当夜0:14、佐倉自身のアカウントで作成・署名されたもの。
            無実の黒田に罪を着せ、単独犯を取り繕うための工作だったのだ。

            そして手記の片隅に記された **「404号室の鍵」** ― そこに眠るECHO計画の真実は、
            やがてノクサ研究機構を揺るがすことになる。だが、それはまた別の物語だ。

            真犯人の仕掛けた罠ごと見抜いた、完璧な解決。
            """
        )
    elif ending == "good":
        st.title("🙂 Good End ―『一応の解決』")
        st.markdown(
            """
            犯人 **佐倉** の特定は正しかった。彼の身柄は確保された。

            しかし動機か手段の見立てに誤りがあり、事件の全容解明には至らなかった。
            それでも、博士の行方を追う手がかりは確かに前進した。
            """
        )
        st.info("💡 Perfect End には、動機と犯行手段の両方を正しく突き止める必要がある。")
    elif ending == "blunder":
        st.title("💀 Bad End ―『捜査失格』")
        st.markdown(
            """
            見当違いの証拠を容疑者に突きつけ続け、あなたの **捜査信用度は地に落ちた**。

            「この探偵は当てずっぽうで人を疑う」――そんな評判が広まり、
            あなたは事件から外された。真相は、別の誰かの手に委ねられる。
            """
        )
        st.caption("💡 証言の二段構えを、正しい鍵証拠で順に崩していこう。")
    elif ending == "bad":
        st.title("💀 Bad End ―『誤認逮捕』")
        accused_kuroda = st.session_state.get("case_memo_trust") and not st.session_state.get("case_saw_through")
        if accused_kuroda:
            st.markdown(
                """
                あなたは『脅迫メモ』を額面通り信じ、**黒田** を犯人と告発した。
                だがそれこそ真犯人の狙いだった ― メモは無実の黒田を陥れる**偽証拠**。

                罠にまんまと嵌まったあなたが視線を逸らしている間に、
                本当の犯人は全ての痕跡を消して姿を消した。
                消えた研究者の行方は、永遠に闇の中へ——。
                """
            )
        else:
            st.markdown(
                """
                あなたは真犯人を取り違えた。無実の人物を告発してしまったのだ。

                その隙に、本当の犯人は全ての痕跡を消して姿を消した。
                消えた研究者の行方は、永遠に闇の中へ——。
                """
            )
        st.caption(f"（真犯人は {SUSPECT_A} だった…）")
        st.caption("💡 “都合のよすぎる証拠”は疑え。被害者の手記との矛盾が罠を見破る鍵だ。")

    st.markdown("---")
    if st.button("🔄 もう一度挑戦する", use_container_width=True):
        reset_game()
        st.rerun()


# ==========================================================================
# メイン
# ==========================================================================
init_game()
render_sidebar()

if st.session_state.case_ending is not None:
    page_ending()
elif not st.session_state.case_started:
    page_intro()
else:
    VIEW_DISPATCH = {
        "board": page_board,
        "suspects": page_suspects,
        "interrogate": page_interrogate,
        "deduce": page_deduce,
        "print": view_print,
        "slide": view_slide,
        "pin": view_pin,
        "timeline": view_timeline,
    }
    VIEW_DISPATCH[st.session_state.case_view]()
