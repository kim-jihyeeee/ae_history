import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime
import os
import requests

# 1. 기본 설정
st.set_page_config(page_title="AE History Visualizer v7.1", layout="wide")

# 폰트 자동 로드
@st.cache_data
def load_font():
    try:
        font_url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf"
        font_res = requests.get(font_url)
        with open("nanum_font.ttf", "wb") as f: f.write(font_res.content)
        return "nanum_font.ttf"
    except: return None

FONT_PATH = load_font()

# 세션 상태 초기화
if 'client_db' not in st.session_state: st.session_state.client_db = pd.DataFrame()
if 'history_db' not in st.session_state: st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '핵심키워드'])

# 2. UI 디자인 (디자인 복구 및 눈금 가시성 강화)
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: hidden; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3em; }
    
    /* 슬라이더 디자인 복구 (v6.9 스타일) */
    div[data-testid="stSlider"] { padding-top: 20px; }
    
    /* 슬라이더 빨간색 포인트와 선 두께 조절 */
    div[role="slider"] {
        background-color: #FF4B4B !important;
        border: 2px solid white !important;
        width: 14px !important;
        height: 14px !important;
    }
    
    /* 🌟 핵심: 슬라이더 아래 글자(7일, 15일 등) 정렬 및 강조 */
    div[data-testid="stSliderTickBar"] > div {
        font-weight: bold !important;
        color: #FF4B4B !important;
        font-size: 13px !important;
        margin-
