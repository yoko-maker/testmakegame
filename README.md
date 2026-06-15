# 🎮 Streamlit ゲーム作品集

Streamlit で制作したゲーム作品をまとめたリポジトリです。各フォルダが独立した1つの作品で、
それぞれ `app.py` を `streamlit run` で起動できます。

## 🕹️ 統合ポータル（おすすめ）

ルートの `app.py` は、5作品を1つのサイトに統合した**ゲームポータル**です。
ホーム画面または左メニューから好きなゲームを選んで遊べます。

```bash
pip install -r requirements.txt   # streamlit / numpy / Pillow
streamlit run app.py              # ← これ1つで全作品にアクセス
```

## 📂 作品一覧

| フォルダ | 作品 | ジャンル | 状態 |
|---|---|---|---|
| [MiniGameArcade/](MiniGameArcade/) | 🎮 ミニゲームアーケード | ミニゲーム集（共通コイン経済・実績） | ✅ 完成 |
| [Project_ECHO/](Project_ECHO/) | 🧬 Project ECHO | AI研究所 脱出ゲーム | ✅ 完成 |
| [Case001/](Case001/) | 🕵️ 消えた研究者 | 推理アドベンチャー | ✅ 完成 |
| [LAST_30minute/](LAST_30minute/) | ☄️ LAST 30 MINUTES | タイムアタック | ✅ 完成 |
| [404_User_Not_Found/](404_User_Not_Found/) | 🛑 404 User Not Found | ARG／謎解きホラー | ✅ 完成 |

## 🎮 各作品の概要

### MiniGameArcade ― ミニゲームアーケード
数当て・じゃんけん・神経衰弱・クイズ・スロット・ハングマンの6種を収録。
全ゲームが**共通コイン経済**でつながり、レベルや実績を集められる。

### Project ECHO ― AI研究所脱出ゲーム
閉鎖された研究所から脱出する謎解きアドベンチャー。ランダム生成の認証コード、
符号化された手がかり、隠し研究室、マルチエンド（True / Normal / Bad）。

### Case001 ― 消えた研究者
探偵として証拠を集め真犯人を推理。4つの解析ミニゲーム、容疑者の**二段構えの矛盾追及**、
捜査信用度システム、4エンディング（Perfect / Good / Bad / Secret）。

### LAST 30 MINUTES ― 世界崩壊カウントダウン
隕石衝突までの**リアルタイム制限時間**内に5施設を復旧するタイムアタック。
復旧数で迎撃成功率が変わり、結末が分岐（True / Good / Normal / Bad）。

### 404 User Not Found ― ARG
「HELP」のメッセージから始まる失踪事件を追うARG／都市伝説ホラー。暗号・ミニゲーム・分岐エンド。
（演出に `numpy` / `Pillow` を使用）

## 🚀 起動方法

```bash
# 例: ミニゲームアーケードを起動
cd MiniGameArcade
pip install -r requirements.txt   # streamlit
streamlit run app.py
```

各作品フォルダで同様に `streamlit run app.py` を実行してください。
（依存は共通で `streamlit` のみ）

## 🔄 ゲームを更新するには（開発フロー）

基本は **①編集 → ②ローカル確認 → ③push** の3ステップ。`main` に push すると
Streamlit Community Cloud が**自動で再デプロイ**します。

### ① 編集
更新したいゲームのフォルダ内 `app.py` を直接編集する。

| ゲーム | 編集するファイル |
|---|---|
| ミニゲームアーケード | `MiniGameArcade/app.py` |
| Project ECHO | `Project_ECHO/app.py` |
| 消えた研究者 | `Case001/app.py` |
| LAST 30 MINUTES | `LAST_30minute/app.py` |
| 404 User Not Found | `404_User_Not_Found/app.py`（＋ `game/` 内） |

### ② ローカルで動作確認
```bash
streamlit run app.py     # ポータルから全ゲームを確認できる
```
ブラウザ `http://localhost:8501` で確認。ファイルを保存すると自動リロードされる。

### ③ コミットして push（= 自動デプロイ）
```bash
git add .
git commit -m "変更内容を簡潔に"
git push
```
push 後、数分でクラウドの公開URLに反映される（手動操作は不要）。

### 新しいライブラリを使ったとき
ルートの `requirements.txt` に追記してから push する。
（忘れるとクラウドでだけ `ModuleNotFoundError` になる）

### 新しいゲームを追加するとき
1. 新フォルダ＋ `app.py` を作成（先頭の `st.set_page_config` は既存ゲームに倣い `try/except` で包む）
2. ルート `app.py` の `GAMES` リストに1項目追加
   ```python
   {"path": "新フォルダ/app.py", "title": "...", "icon": "🎲", "url": "newgame",
    "genre": "...", "desc": "..."},
   ```
3. 通常ゲーム同様の「ポータルに戻る」を出すなら `RETURN_URLS` にも `"newgame"` を追加
4. push

### 安全に試したいとき（任意）
```bash
git checkout -b feature/xxx   # 作業ブランチ
# 編集・commit・push → GitHubでPull Request → 確認後mainにマージ
```

## ☁️ デプロイ

- **リポジトリ:** https://github.com/yoko-maker/testmakegame
- **ホスティング:** Streamlit Community Cloud（Main file path = `app.py` / Branch = `main`）
- 公開後は `main` への push で自動再ビルド。失敗時は「Manage app」のログを確認、必要なら「Reboot」。

## 🛠️ 技術メモ

- すべて Python + Streamlit 製。状態は `st.session_state` で管理。
- 各作品は `streamlit.testing.v1.AppTest` による自動プレイテストで主要フローを検証済み。
- 各ゲームの `set_page_config` は `try/except` で包み、単体起動とポータル統合の両対応。
- ポータルは `st.navigation(position="hidden")`＋ホームのギャラリーで遷移（各ゲームのサイドバーに干渉しない）。
