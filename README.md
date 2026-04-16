import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime
import os

# 1. 기본 설정
st.set_page_config(page_title="AE History Visualizer v5.3", layout="wide")

# 🌟 폰트 파일명을 font.ttf로 고정했습니다.
FONT_NAME = "font.ttf"

# 세션 상태 초기화
if 'client_db' not in st.session_state: st.session_state.client_db = pd.DataFrame(columns=['광고주명', '담당자', '업종'])
if 'history_db' not in st.session_state: st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '핵심키워드'])

# 2. UI 디자인 (지혜 AE님의 감각적인 리포트 스타일)
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: hidden; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; border: none; height: 3em; }
    div[data-testid="stExpander"] { border: 1px solid #FFB300; border-radius: 8px; }
    .stDataFrame { border-radius: 8px; overflow: hidden; }
    </style>
""", unsafe_allow_html=True)

st.title("📝 AE History Visualizer v5.3")
st.caption("광고주 히스토리 데이터 시각화 리포트 시스템")

# 사이드바 메뉴
menu = st.sidebar.radio("📋 메뉴 이동", ["광고주 DB 관리", "관리 이력 입력", "디지털 리포트 생성"])

# --- 1. 광고주 DB 관리 ---
if menu == "광고주 DB 관리":
    st.header("📂 광고주 리스트 등록")
    uploaded_file = st.file_uploader("Excel 또는 CSV 파일을 업로드하세요", type=['xlsx', 'csv'])
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            st.session_state.client_db = df
            st.success("✅ 광고주 리스트를 성공적으로 불러왔습니다!")
        except Exception as e:
            st.error(f"데이터 로드 중 오류가 발생했습니다: {e}")
    
    st.subheader("현재 등록된 광고주 목록")
    st.dataframe(st.session_state.client_db, use_container_width=True, hide_index=True)

# --- 2. 관리 이력 입력 ---
elif menu == "관리 이력 입력":
    st.header("✍️ 소통 및 관리 이력 기록")
    if st.session_state.client_db.empty:
        st.warning("먼저 '광고주 DB 관리' 메뉴에서 리스트를 등록해주세요.")
    else:
        with st.form("log_entry_form"):
            col1, col2 = st.columns(2)
            with col1:
                client = st.selectbox("광고주 선택", st.session_state.client_db['광고주명'].unique())
                date = st.date_input("기록 날짜", datetime.date.today())
            with col2:
                tags = st.text_input("핵심 키워드 (쉼표로 구분)", placeholder="효율개선, ROAS상승, GFA세팅")
            
            content = st.text_area("상세 관리 내용 (워드클라우드 분석용)", height=150)
            
            if st.form_submit_button("히스토리 저장하기"):
                new_data = pd.DataFrame([[date, client, content, tags]], 
                                      columns=['날짜', '광고주명', '소통내용', '핵심키워드'])
                st.session_state.history_db = pd.concat([st.session_state.history_
