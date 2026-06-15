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
| [404_User_Not_Found/](404_User_Not_Found/) | 📩 404 User Not Found | ARG／謎解きホラー | 📄 仕様書 |

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

### 404 User Not Found ― ARG（仕様書のみ）
「HELP」のメッセージから始まる失踪事件を追うARG／都市伝説ホラー。

## 🚀 起動方法

```bash
# 例: ミニゲームアーケードを起動
cd MiniGameArcade
pip install -r requirements.txt   # streamlit
streamlit run app.py
```

各作品フォルダで同様に `streamlit run app.py` を実行してください。
（依存は共通で `streamlit` のみ）

## 🛠️ 技術メモ

- すべて Python + Streamlit 製。状態は `st.session_state` で管理。
- 各作品は `streamlit.testing.v1.AppTest` による自動プレイテストで主要フローを検証済み。
