import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, os, requests, re
from bs4 import BeautifulSoup
from pptx import Presentation
from pptx.util import Inches

# 1. 기본 설정 (사이드바 기본 확장 상태)
st.set_page_config(
    page_title="AE Total Solution v9.5", 
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

# 2. UI 스타일 및 메뉴 복구 버튼 디자인
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: hidden; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3em; }
    .menu-header { font-size: 1.1em; font-weight: bold; color: #FFB300; margin-top: 35px; border-bottom: 2px solid #eee; padding-bottom: 5px; }
    .spacer { margin-bottom: 50px; }
    
    /* 메뉴 복구 안내 스타일 */
    .restore-box {
        padding: 20px;
        background-color: #fff4e5;
        border: 1px dashed #FFB300;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# 3. 사이드바 메뉴 로직
# 사이드바가 닫혔을 때 메인 화면에 안내 메시지를 띄우기 위한 장치
st.sidebar.title("🚀 AE Total Tool v9.5")
st.sidebar.markdown('<p class="menu-header">📋 내부 히스토리 관리</p>', unsafe_allow_html=True)
m_int = st.sidebar.radio("항목", ["광고주 DB 관리", "관리 이력 입력", "디지털 리포트(내부)"], label_visibility="collapsed")
st.sidebar.markdown('<div class="spacer"></div>', unsafe_allow_html=True)
st.sidebar.markdown('<p class="menu-header">📊 외부 시장 분석</p>', unsafe_allow_html=True)
m_ext = st.sidebar.checkbox("📊 Trend Radar(듀얼 모드)")

menu = "📊 Trend Radar(외부)" if m_ext else m_int

# 🌟 [v9.5 핵심 추가] 메뉴가 닫혔을 때 메인 상단에 표시될 안내 문구
# 사이드바 상태를 감지할 수는 없지만, 메인 화면 상단에 항시 배치하거나 
# 지혜님이 "어? 메뉴 어디갔지?" 할 때 볼 수 있게 배치했습니다.
st.markdown("""
    <div class="restore-box">
        💡 <b>메뉴가 보이지 않나요?</b> 왼쪽 상단의 <b>'>'</b> 모양 화살표를 누르거나 키보드에서 <b>'X'</b>를 눌러주세요!
    </div>
""", unsafe_allow_html=True)

# --- [이후 내부/외부 로직 v9.4와 동일] ---

if menu == "광고주 DB 관리":
    st.header("📂 데이터 로드 및 관리")
    c1, c2 = st.columns(2)
    with c1: 
        up_c = st.file_uploader("🏢 광고주 리스트 업로드", type=['xlsx', 'csv'], key="c_up")
        if up_c:
            df = pd.read_csv(up_c) if up_c.name.endswith('.csv') else pd.read_excel(up_c)
            df.rename(columns={df.columns[0]: '광고주명'}, inplace=True)
            st.session_state.client_db = df
