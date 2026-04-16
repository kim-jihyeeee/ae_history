import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, os, requests, re
from bs4 import BeautifulSoup
from pptx import Presentation
from pptx.util import Inches

# 1. 페이지 설정 (메뉴 강제 확장 상태 유지)
st.set_page_config(
    page_title="AE Total Solution v9.7", 
    layout="wide",
    initial_sidebar_state="expanded" 
)

@st.cache_data
def load_font():
    try:
        url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf"
        res = requests.get(url)
        with open("nanum_font.ttf", "wb") as f: f.write(res.content)
        return "nanum_font.ttf"
    except: return None

FONT_PATH = load_font()

# 세션 초기화
if 'client_db' not in st.session_state: st.session_state.client_db = pd.DataFrame()
if 'history_db' not in st.session_state: st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '핵심키워드'])

# 2. UI 스타일 (안내 박스 제거 및 깔끔한 레이아웃)
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: hidden; }
    [data-testid="stSidebarNav"] { display: block !important; }
    [data-testid="collapsedControl"] { display: block !important; color: #FFB300 !important; }
    
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3em; }
    .menu-header { font-size: 1.1em; font-weight: bold; color: #FFB300; margin-top: 35px; border-bottom: 2px solid #eee; padding-bottom: 5px; }
    .spacer { margin-bottom: 50px; }
    </style>
""", unsafe_allow_html=True)

# 3. 사이드바 구성
st.sidebar.title("🚀 AE Total Tool v9.7")
st.sidebar.markdown('<p class="menu-header">📋 내부 히스토리 관리</p>', unsafe_allow_html=True)
m_int = st.sidebar.radio("항목", ["광고주 DB 관리", "관리 이력 입력", "디지털 리포트(내부)"], label_visibility="collapsed")
st.sidebar.markdown('<div class="spacer"></div>', unsafe_allow_html=True)
st.sidebar.markdown('<p class="menu-header">📊 외부 시장 분석</p>', unsafe_allow_html=True)
m_ext = st.sidebar.checkbox("📊 Trend Radar(듀얼 모드)")

menu = "📊 Trend Radar(외부)" if
