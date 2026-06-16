"""Case001 消えた研究者 — 探偵推理ゲーム。

著名な研究者・霧島博士が失踪。プレイヤーは探偵として現場を調査し、
4つの解析ミニゲームで証拠を集め、容疑者を絞り込み、真犯人を推理する。

  🧩 指紋照合       神経衰弱      → 指紋証拠     （犯人＝佐倉／手段＝薬物）
  📹 防犯カメラ解析 スライドパズル → 容疑者映像   （犯人＝佐倉／B・Cはアリバイ）
  📱 スマホ解析     暗号解読      → メッセージ履歴（動機＝独占）
  🧪 研究データ解析 クイズ        → 動機情報     （動機＝独占／偽証拠の存在）
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
    "容疑者映像": "事件当夜23:40、白衣の人物が研究室へ最後に入る映像。IDゲート記録は『佐倉』。黒田と高村は当夜の入館記録なし。",
    "メッセージ履歴": "被害者・霧島玲のスマホを復号。佐倉からの暗号メッセージ『MINE（成果は私のものだ）』に加え、"
                      "玲自身の日記下書き ―『ECHOの権利を独占したい人がいる。私を消したい人がいる。404号室の鍵は預けた』。",
    "動機情報": "研究データ解析で、ECHO計画の特許出願書類が佐倉の単独名義に書き換えられていたと判明。"
                "同じフォルダに、黒田を名指しした『脅迫メモ』の画像も保存されていた。",
    "脅迫メモ": "「成果を渡さなければ後悔するぞ ― 黒田」と署名された脅迫メモ。一見、黒田が真犯人に見える有力証拠。",
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
    ("指紋照合", "🧩", "mem", "指紋証拠", "神経衰弱"),
    ("防犯カメラ解析", "📹", "slide", "容疑者映像", "スライドパズル"),
    ("スマホ解析", "📱", "cipher", "メッセージ履歴", "暗号解読"),
    ("研究データ解析", "🧪", "quiz", "動機情報", "クイズ"),
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
             "break": "あなたが博士へ送った暗号メッセージ ―『MINE（成果は私のものだ）』。"
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
        st.error("📄 **黒田を名指しする『脅迫メモ』** が見つかっている。"
                 "素直に読めば黒田が犯人だ ― だが被害者の手記では黒田とは“和解済み”。何かがおかしい。")
        cse1, cse2 = st.columns(2)
        if cse1.button("✅ 脅迫メモを“額面通り”受け取る", use_container_width=True):
            st.session_state.case_memo_trust = True
            st.rerun()
        if cse2.button("🧐 脅迫メモを“偽証拠”と疑う", use_container_width=True):
            st.session_state.case_saw_through = True
            st.session_state.case_memo_trust = False
            st.rerun()
        if st.session_state.get("case_memo_trust"):
            st.warning("…黒田が怪しいと結論づけかけている。だが本当にそれでいいのか？ もう一度、メモの整合性を疑ってみよう。")

    if st.session_state.get("case_saw_through"):
        st.info("🧐 あなたは脅迫メモを偽証拠と見抜いた。本物なら、メモを仕込んだ“真犯人の痕跡”がどこかに残っているはずだ。")

    # 隠し解析（全4証拠 ＋ 偽証拠の見破りで解放）
    if base4 and st.session_state.get("case_saw_through") and not has_evidence("隠し証拠"):
        st.warning("🔍 偽証拠の出所を追え。佐倉のPCにまだ解析していない領域がある。")
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
    st.write("**嘘:** 博士とは『良好な関係』だと言うが、独占を迫る暗号メッセージを送っていた。")

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
        st.info("📕 手記が示す構図: 黒田とは“和解済み”、高村は“施設に入れない外部者”。"
                "そして『特許から私を外そうとする者』― 内部にいて成果を独占したい人物こそが鍵だ。")
    else:
        st.caption("（被害者のスマホを復号すれば、本人の手記が読めるはず ― スマホ解析を進めよう）")

    st.markdown("---")
    if st.session_state.case_redherring:
        st.error("📄 **要注意の証拠** ― 黒田を名指しした『脅迫メモ』が見つかっている。"
                 "一見すると黒田が犯人のようだが…日記の和解の記述と食い違う。誰かの作為では？")

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
# ミニゲーム1: 神経衰弱 → 指紋証拠
# ==========================================================================
PRINT_EMOJIS = ["🔍", "🧪", "🩸", "🔑", "📱", "💊", "🗝️", "📄"]


def setup_mem():
    deck = PRINT_EMOJIS * 2
    random.shuffle(deck)
    st.session_state.rm_mem_deck = deck
    st.session_state.rm_mem_revealed = [False] * len(deck)
    st.session_state.rm_mem_matched = [False] * len(deck)
    st.session_state.rm_mem_moves = 0
    st.session_state.rm_mem_pending = None


def view_mem():
    st.header("🧩 指紋照合（神経衰弱）")
    st.caption("同じ指紋マーカーのペアを全て揃えると、指紋証拠が照合できる。")

    if has_evidence("指紋証拠"):
        st.success("✅ 指紋証拠は照合済み。")
        if st.button("↩️ 捜査ボードに戻る"):
            goto("board")
        return

    if "rm_mem_deck" not in st.session_state:
        setup_mem()

    deck = st.session_state.rm_mem_deck
    revealed = st.session_state.rm_mem_revealed
    matched = st.session_state.rm_mem_matched

    pending = [i for i in range(len(deck)) if revealed[i] and not matched[i]]
    if len(pending) == 2:
        i, j = pending
        if deck[i] == deck[j]:
            matched[i] = matched[j] = True
        st.session_state.rm_mem_pending = pending

    cleared = all(matched)
    if cleared:
        gain_evidence("指紋証拠")

    for row in range(4):
        cols = st.columns(4)
        for c in range(4):
            idx = row * 4 + c
            face = deck[idx] if (revealed[idx] or matched[idx]) else "❓"
            disabled = revealed[idx] or matched[idx] or cleared
            if cols[c].button(face, key=f"mem_{idx}", use_container_width=True, disabled=disabled):
                pend = st.session_state.rm_mem_pending
                if pend:
                    for p in pend:
                        if not matched[p]:
                            revealed[p] = False
                    st.session_state.rm_mem_pending = None
                revealed[idx] = True
                st.session_state.rm_mem_moves += 1
                st.rerun()

    st.metric("手数", st.session_state.rm_mem_moves)
    if cleared:
        st.balloons()
        st.success("🎉 全ペア一致！ **指紋証拠** を入手した。")

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
# ミニゲーム3: 暗号解読 → メッセージ履歴
# ==========================================================================
def setup_cipher():
    shift = random.randint(3, 23)
    plain = "MINE"
    cipher = "".join(chr((ord(ch) - 65 + shift) % 26 + 65) for ch in plain)
    st.session_state.rm_cipher_shift = shift
    st.session_state.rm_cipher_text = cipher
    st.session_state.rm_cipher_plain = plain
    st.session_state.rm_cipher_miss = 0


def view_cipher():
    st.header("📱 スマホ解析（暗号解読）")
    st.caption("被害者のスマホに残る暗号メッセージを復号せよ。")

    if has_evidence("メッセージ履歴"):
        st.success("✅ メッセージ履歴は復号済み。")
        if st.button("↩️ 捜査ボードに戻る"):
            goto("board")
        return

    if "rm_cipher_text" not in st.session_state:
        setup_cipher()

    shift = st.session_state.rm_cipher_shift
    cipher = st.session_state.rm_cipher_text

    st.code(f"暗号文:  {' '.join(cipher)}", language=None)
    st.info(f"💡 各アルファベットを **+{shift} 文字ずらして** 暗号化されている。元の英単語に戻せ。")
    ans = st.text_input("復号した英単語", placeholder="例: WORD")

    if st.button("🔓 復号"):
        if ans.strip().upper().replace(" ", "") == st.session_state.rm_cipher_plain:
            gain_evidence("メッセージ履歴")
            st.rerun()
        else:
            st.session_state.rm_cipher_miss += 1
            st.error(f"❌ 復号失敗。各文字を {shift} 戻す（A→Zを跨ぐ）と意味の通る英単語になる。")

    if st.session_state.rm_cipher_miss >= 2:
        ex = cipher[0]
        dec = chr((ord(ex) - 65 - shift) % 26 + 65)
        st.caption(f"（ヒント: 先頭 {ex} → {dec}。意味は『私のもの』）")

    if st.button("↩️ 捜査ボードに戻る"):
        goto("board")


# ==========================================================================
# ミニゲーム4: クイズ → 動機情報
# ==========================================================================
CASE_QUIZ = [
    {"q": "霧島博士が率いていた極秘プロジェクトの名は？",
     "choices": ["ECHO計画", "MIRROR計画", "ORACLE計画", "PHOENIX計画"], "answer": 0},
    {"q": "事件後、ECHOの特許出願書類はどう変わっていた？",
     "choices": ["破棄されていた", "佐倉の単独名義に書換", "黒田の名義に変更", "変化なし"], "answer": 1},
    {"q": "佐倉が事件後に取ろうとした行動は？",
     "choices": ["警察へ自首", "論文の単独発表", "海外へ逃亡", "研究の中止"], "answer": 1},
    {"q": "同じフォルダで見つかった、黒田を名指しする文書は？",
     "choices": ["推薦状", "脅迫メモ", "辞表", "領収書"], "answer": 1},
]


def view_quiz():
    st.header("🧪 研究データ解析（クイズ）")
    st.caption("回収した研究データに関する設問。全問正解で動機情報が得られる。")

    if has_evidence("動機情報"):
        st.success("✅ 動機情報は解析済み。")
        if st.button("↩️ 捜査ボードに戻る"):
            goto("board")
        return

    init_state("rm_quiz_idx", 0)
    init_state("rm_quiz_correct", 0)
    init_state("rm_quiz_answered", False)

    idx = st.session_state.rm_quiz_idx
    item = CASE_QUIZ[idx]
    st.progress(idx / len(CASE_QUIZ), text=f"第 {idx + 1} 問 / {len(CASE_QUIZ)}")
    st.subheader(item["q"])

    if not st.session_state.rm_quiz_answered:
        for i, ch in enumerate(item["choices"]):
            if st.button(ch, key=f"qz_{idx}_{i}", use_container_width=True):
                st.session_state.rm_quiz_answered = True
                st.session_state.rm_quiz_last = (i == item["answer"])
                if st.session_state.rm_quiz_last:
                    st.session_state.rm_quiz_correct += 1
                st.rerun()
    else:
        if st.session_state.rm_quiz_last:
            st.success("⭕ 正解！")
        else:
            st.error(f"❌ 不正解… 正解は「{item['choices'][item['answer']]}」")
        last = idx + 1 == len(CASE_QUIZ)
        if st.button("結果を見る" if last else "次の問題へ", key=f"qz_next_{idx}"):
            st.session_state.rm_quiz_answered = False
            if last:
                if st.session_state.rm_quiz_correct == len(CASE_QUIZ):
                    gain_evidence("動機情報")
                else:
                    st.session_state.rm_quiz_idx = 0
                    st.session_state.rm_quiz_correct = 0
                    st.session_state.rm_quiz_failed = True
            else:
                st.session_state.rm_quiz_idx += 1
            st.rerun()

    if st.session_state.get("rm_quiz_failed"):
        st.warning("⚠️ 全問正解が必要だ。最初から解析し直そう。")

    if st.button("↩️ 捜査ボードに戻る"):
        goto("board")


# ==========================================================================
# 容疑者の追及（矛盾追及パート）
# ==========================================================================
def page_interrogate():
    st.header("🔦 容疑者の追及")
    st.write("容疑者の証言に、集めた**証拠を突きつけて**矛盾を暴け。証言は二段構え、各段で鍵となる証拠は異なる。")

    credit = st.session_state.case_credit
    st.markdown(f"**🛡️ 捜査信用度:** {'❤️' * credit}{'🖤' * (MAX_CREDIT - credit)}")
    st.caption("誤った証拠を突きつけると信用度が下がる。0になると捜査から外される。")

    evs = list(st.session_state.case_evidences)
    if not evs:
        st.warning("まだ証拠がない。先に解析を進めよう。")
        if st.button("↩️ 捜査ボードに戻る"):
            goto("board")
        return

    sel = st.radio("追及する容疑者", SUSPECTS, key="itg_sel")
    data = INTERROGATION[sel]
    stages = data["stages"]
    s_idx = SUSPECTS.index(sel)
    verdicts = st.session_state.case_verdicts
    stage_idx = st.session_state.case_stage.get(sel, 0)
    resolved = sel in verdicts

    st.markdown(f"##### 🗣️ {sel} の追及")

    # すでに崩した証言を表示
    for i in range(stage_idx):
        st.success(f"✅ 「{stages[i]['claim']}」\n\n→ {stages[i]['break']}")

    if resolved:
        badge = "🔴 クロ（容疑濃厚）" if verdicts[sel] == "クロ" else "🟢 シロ（容疑圏外）"
        st.markdown(f"### 追及完了 ― {badge}")
    else:
        cur = stages[stage_idx]
        st.info(f"証言 {stage_idx + 1}/{len(stages)}：「{cur['claim']}」")
        st.write("どの証拠を突きつける？")
        for ev in evs:
            if st.button(f"📎 {ev} を突きつける", key=f"itg_{s_idx}_{stage_idx}_{ev}", use_container_width=True):
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
                        f"《{ev}》を突きつけたが、{sel.split('（')[0]}は動じない。"
                        "「それが何の関係が？」― 決定打にならず、信用度が下がった。",
                    )
                st.rerun()

        react = st.session_state.get("itg_reaction")
        if react and react[0] == sel and react[1] == stage_idx:
            st.warning(react[2])

    st.markdown("---")
    resolved_n = sum(1 for s in SUSPECTS if s in verdicts)
    st.caption(f"追及の進捗: {resolved_n}/3")
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
        "mem": view_mem,
        "slide": view_slide,
        "cipher": view_cipher,
        "quiz": view_quiz,
    }
    VIEW_DISPATCH[st.session_state.case_view]()
