import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime
import os

# 1. 기본 설정
st.set_page_config(page_title="AE History Visualizer v5.6", layout="wide")

# 폰트 설정
FONT_NAME = "font.ttf"

# 세션 상태 초기화 (데이터 증발 방지용 임시 공간)
if 'client_db' not in st.session_state: st.session_state.client_db = pd.DataFrame()
if 'history_db' not in st.session_state: st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '핵심키워드'])

# 2. UI 디자인
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: hidden; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; border: none; height: 3em; }
    div[data-baseweb="select"] { border: 1px solid #FFB300; border-radius: 4px; }
    </style>
""", unsafe_allow_html=True)

st.title("📝 AE History Visualizer v5.6")

# 사이드바 메뉴
menu = st.sidebar.radio("📋 메뉴 이동", ["광고주 DB 관리", "관리 이력 입력", "디지털 리포트 생성"])

# --- 1. 광고주 DB 관리 ---
if menu == "광고주 DB 관리":
    st.header("📂 데이터 로드 및 백업")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🏢 광고주 리스트 업로드")
        uploaded_clients = st.file_uploader("광고주 엑셀/CSV", type=['xlsx', 'xls', 'csv'], key="clients")
    with col2:
        st.subheader("💾 히스토리 백업 로드")
        uploaded_history = st.file_uploader("이전 히스토리 엑셀", type=['xlsx'], key="history")
    
    if uploaded_clients:
        try:
            df = pd.read_csv(uploaded_clients) if uploaded_clients.name.endswith('.csv') else pd.read_excel(uploaded_clients)
            # 첫 번째 컬럼을 '광고주명'으로 강제 지정하여 에러 방지
            df.rename(columns={df.columns[0]: '광고주명'}, inplace=True)
            st.session_state.client_db = df
            st.success("✅ 광고주 리스트 로드 완료!")
        except Exception as e: st.error(f"파일 오류: {e}")

    if uploaded_history:
        try:
            h_df = pd.read_excel(uploaded_history)
            st.session_state.history_db = h_df
            st.success("✅ 이전 히스토리 복구 완료!")
        except Exception as e: st.error(f"백업 파일 오류: {e}")

    st.divider()
    st.dataframe(st.session_state.client_db, use_container_width=True, hide_index=True)

# --- 2. 관리 이력 입력 ---
elif menu == "관리 이력 입력":
    st.header("✍️ 소통 및 관리 이력 기록")
    if st.session_state.client_db.empty:
        st.warning("먼저 '광고주 DB 관리' 메뉴에서 광고주 리스트를 등록해주세요.")
    else:
        # 🌟 에러 방지를 위해 폼 시작
        with st.form("history_input_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                # 🌟 검색 가능한 선택창
                client_list = sorted(st.session_state.client_db['광고주명'].dropna().unique())
                client = st.selectbox("광고주 선택 (검색 가능)", client_list)
                log_date = st.date_input("기록 날짜", datetime.date.today())
            with c2:
                tags = st.text_input("핵심 키워드 (쉼표 구분)", placeholder="효율개선, ROAS상승")
            
            content = st.text_area("상세 관리 내용 (워드클라우드 분석용)", height=150)
            
            # 🌟 버튼이 반드시 폼 안에 있어야 함!
            submitted = st.form_submit_button("히스토리 저장하기")
            
            if submitted:
                if content.strip() == "":
                    st.error("내용을 입력해주세요!")
                else:
                    new_data = pd.DataFrame([[log_date, client, content, tags]], columns=['날짜', '광고주명', '소통내용', '핵심키워드'])
                    st.session_state.history_db = pd.concat([st.session_state.history_db, new_data], ignore_index=True)
                    st.success(f"✅ {client}의 이력이 저장되었습니다.")
        
        st.subheader("📊 현재 누적된 히스토리 (임시)")
        st.dataframe(st.session_state.history_db.sort_values(by='날짜', ascending=False), use_container_width=True)

# --- 3. 디지털 리포트 생성 ---
elif menu == "디지털 리포트 생성":
    st.header("📊 워드클라우드 분석 리포트")
    
    if st.session_state.history_db.empty:
        st.info("기록된 데이터가 없습니다.")
    else:
        target_client = st.selectbox("대상 광고주 선택", sorted(st.session_state.history_db['광고주명'].unique()))
        period_opt = st.select_slider("분석 기간", options=["7일", "15일", "한달", "분기"])
        
        days_delta = {"7일": 7, "15일": 15, "한달": 30, "
