"""ターミナル / グリッチ調のビジュアルテーマ。"""

import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=VT323&display=swap');

:root {
    --term-green: #39ff14;
    --term-dim: #1f8a10;
    --term-bg: #050805;
    --term-red: #ff003c;
    --term-amber: #ffb000;
}

.stApp {
    background:
        radial-gradient(circle at 50% 0%, rgba(57,255,20,0.05), transparent 60%),
        #050805;
    color: var(--term-green);
    font-family: 'Share Tech Mono', monospace;
}

/* 走査線 + ちらつき */
.stApp::before {
    content: "";
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: repeating-linear-gradient(
        0deg, rgba(0,0,0,0.22) 0px, rgba(0,0,0,0.22) 1px,
        transparent 1px, transparent 3px);
    pointer-events: none;
    z-index: 9999;
    animation: flicker 4.5s infinite steps(60);
}
@keyframes flicker {
    0%, 92%, 100% { opacity: 1; }
    93% { opacity: 0.65; }
    94% { opacity: 1; }
    96% { opacity: 0.4; }
    97% { opacity: 1; }
}

/* 暗いビネット (四隅から侵食する闇) */
.stApp::after {
    content: "";
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: radial-gradient(ellipse at center,
        transparent 38%, rgba(0,0,0,0.55) 88%, rgba(20,0,0,0.85) 100%);
    pointer-events: none;
    z-index: 9998;
}

h1, h2, h3, h4 {
    font-family: 'VT323', monospace !important;
    color: var(--term-green) !important;
    text-shadow: 0 0 6px rgba(57,255,20,0.6);
    letter-spacing: 2px;
}

p, li, label, .stMarkdown { color: #c8ffc0 !important; }

code, pre {
    background: #0a140a !important;
    color: var(--term-amber) !important;
    border: 1px solid var(--term-dim);
}

/* ボタン */
.stButton > button {
    background: transparent;
    color: var(--term-green);
    border: 1px solid var(--term-green);
    border-radius: 0;
    font-family: 'Share Tech Mono', monospace;
    transition: all 0.15s ease;
}
.stButton > button:hover {
    background: var(--term-green);
    color: #050805;
    box-shadow: 0 0 12px var(--term-green);
}

/* 入力欄 */
.stTextInput input, .stTextArea textarea {
    background: #0a140a !important;
    color: var(--term-green) !important;
    border: 1px solid var(--term-dim) !important;
    font-family: 'Share Tech Mono', monospace !important;
}

.term-box {
    border: 1px solid var(--term-dim);
    background: rgba(10,20,10,0.6);
    padding: 1rem 1.2rem;
    margin: 0.6rem 0;
    box-shadow: inset 0 0 18px rgba(57,255,20,0.06);
}

.glitch {
    color: var(--term-red);
    font-family: 'VT323', monospace;
    font-size: 2.4rem;
    text-shadow: 2px 0 var(--term-green), -2px 0 #00b3ff;
    animation: glitch 0.35s infinite;
}
@keyframes glitch {
    0% { transform: translate(0); }
    20% { transform: translate(-2px, 1px); }
    40% { transform: translate(2px, -1px); }
    60% { transform: translate(-1px, -1px); }
    80% { transform: translate(1px, 1px); }
    100% { transform: translate(0); }
}

.blink { animation: blink 1s step-start infinite; }
@keyframes blink { 50% { opacity: 0; } }

.email-head {
    border-left: 3px solid var(--term-amber);
    padding-left: 0.8rem;
    color: var(--term-amber) !important;
}

/* 囁き: 暗がりからにじむ赤いテキスト */
.whisper {
    color: #b5102a;
    font-family: 'VT323', monospace;
    font-size: 1.5rem;
    letter-spacing: 1px;
    text-shadow: 0 0 8px rgba(181,16,42,0.8);
    opacity: 0.85;
    animation: breathe 3s ease-in-out infinite;
}
@keyframes breathe { 0%,100% { opacity: 0.45; } 50% { opacity: 0.95; } }

/* 全画面の赤フラッシュ (ジャンプスケア風) */
.jumpscare {
    position: fixed; inset: 0; z-index: 10000;
    background: radial-gradient(circle at center,
        rgba(255,0,30,0.0) 30%, rgba(120,0,0,0.9) 100%);
    pointer-events: none;
    animation: flash 0.9s ease-out forwards;
}
@keyframes flash {
    0% { opacity: 0; }
    8% { opacity: 1; }
    100% { opacity: 0; }
}

.corrupt {
    color: #ff003c;
    font-family: 'VT323', monospace;
    text-shadow: 1px 0 #00b3ff, -1px 0 #39ff14;
}
</style>
"""


def inject():
    st.markdown(CSS, unsafe_allow_html=True)


def boxed(text: str):
    st.markdown(f'<div class="term-box">{text}</div>', unsafe_allow_html=True)


def glitch_text(text: str):
    st.markdown(f'<div class="glitch">{text}</div>', unsafe_allow_html=True)


def whisper(text: str):
    st.markdown(f'<div class="whisper">{text}</div>', unsafe_allow_html=True)


def jumpscare():
    """全画面の赤フラッシュを一瞬だけ重ねる。"""
    st.markdown('<div class="jumpscare"></div>', unsafe_allow_html=True)
