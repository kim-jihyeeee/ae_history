import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime
import os
import requests

# 1. 기본 설정
st.set_page_config(page_title="AE History Visualizer v6.4", layout="wide")

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

# 2. UI 디자인
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: hidden; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3em; }
    .emergency-save { background-color: #FF4B4B !important; color: white !important; border: 2px solid white !important; }
    </style>
""", unsafe_allow_html=True)

st.title("📝 AE History Visualizer v6.4")

# 사이드바 메뉴
menu = st.sidebar.radio("📋 메뉴 이동", ["광고주 DB 관리", "관리 이력 입력", "디지털 리포트 생성"])

# --- 1. 광고주 DB 관리 ---
if menu == "광고주 DB 관리":
    st.header("📂 데이터 복구 및 등록")
    st.info("💡 새로고침으로 데이터가 사라졌다면, 저장해둔 백업 파일을 아래에 올려주세요.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🏢 광고주 리스트 업로드")
        uploaded_clients = st.file_uploader("광고주 엑셀/CSV", type=['xlsx', 'csv'], key="clients")
    with col2:
        st.subheader("💾 히스토리 백업 로드")
        uploaded_history = st.file_uploader("백업 엑셀 파일 (.xlsx)", type=['xlsx'], key="history")
    
    if uploaded_clients:
        try:
            df = pd.read_csv(uploaded_clients) if uploaded_clients.name.endswith('.csv') else pd.read_excel(uploaded_clients)
            df.rename(columns={df.columns[0]: '광고주명'}, inplace=True)
            st.session_state.client_db = df
            st.success("✅ 광고주 리스트 로드 완료!")
        except: st.error("파일 오류")

    if uploaded_history:
        try:
            h_df = pd.read_excel(uploaded_history)
            st.session_state.history_db = h_df
            st.success("✅ 모든 히스토리가 복구되었습니다!")
        except: st.error("백업 파일 오류")

# --- 2. 관리 이력 입력 ---
elif menu == "관리 이력 입력":
    st.header("✍️ 소통 이력 기록")
    
    if st.session_state.client_db.empty:
        st.warning("먼저 '광고주 DB 관리' 메뉴에서 리스트를 등록해주세요.")
    else:
        # 실시간 백업 유도 알림
        if not st.session_state.history_db.empty:
            st.error("🚨 주의: 브라우저를 새로고침하면 아래 데이터가 사라집니다! 중간중간 [백업 파일 저장] 버튼을 눌러주세요.")
            xlsx_buf = BytesIO()
            st.session_state.history_db.to_excel(xlsx_buf, index=False)
            st.download_button("💾 지금 즉시 모든 데이터 백업(Excel)", data=xlsx_buf.getvalue(), file_name=f"AE_History_Backup_{datetime.date.today()}.xlsx", key="emergency")

        search_query = st.text_input("🔍 업체명 검색", placeholder="일부만 입력해도 필터링됩니다.")
        all_clients = sorted(st.session_state.client_db['광고주명'].dropna().unique())
        filtered_clients = [c for c in all_clients if search_query.lower() in str(c).lower()]
        
        # 키워드 추천 로직
        existing_keywords = []
        if not st.session_state.history_db.empty:
            all_tags = st.session_state.history_db['핵심키워드'].dropna().str.split(',').explode().str.strip()
            existing_keywords = sorted(all_tags.unique())

        with st.form("history_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                client = st.selectbox(f"광고주 선택 ({len(filtered_clients)}건)", filtered_clients)
                log_date = st.date_input("날짜", datetime.date.today())
            with c2:
                selected_hints = st.multiselect("🏷️ 자주 쓰는 키워드", options=existing_keywords)
                manual_tags = st.text_input("➕ 직접 입력 (쉼표 구분)")
            
            content = st.text_area("상세 내용", height=150)
            if st.form_submit_button("히스토리 저장"):
                combined_tags = list(set(selected_hints + [t.strip() for t in manual_tags.split(',') if t.strip()]))
                new_data = pd.DataFrame([[log_date, client, content, ", ".join(combined_tags)]], columns=['날짜', '광고주명', '소통내용', '핵심키워드'])
                st.session_state.history_db = pd.concat([st.session_state.history_db, new_data], ignore_index=True)
                st.rerun() # 즉시 화면 갱신

        st.dataframe(st.session_state.history_db.sort_values(by='날짜', ascending=False), use_container_width=True)

# --- 3. 디지털 리포트 생성 ---
elif menu == "디지털 리포트 생성":
    st.header("📊 워드클라우드 분석")
    if st.session_state.history_db.empty:
        st.info("기록된 데이터가 없습니다.")
    else:
        target_client = st.selectbox("대상 광고주", sorted(st.session_state.history_db['광고주명'].unique()))
        period_opt = st.select_slider("기간", options=["7일", "15일", "한달", "분기"])
        
        # 필터링 및 시각화 로직 (동일)
        days_delta = {"7일": 7, "15일": 15, "한달": 30, "분기": 90}[period_opt]
        filtered_df = st.session_state.history_db[(st.session_state.history_db['광고주명'] == target_client)]
        
        if not filtered_df.empty:
            text_data = (filtered_df['핵심키워드'].fillna('').str.cat(sep=' ') + " ") * 3 + filtered_df['소통내용'].fillna('').str.cat(sep=' ')
            wc = WordCloud(font_path=FONT_PATH, width=900, height=500, background_color='white', colormap='Dark2').generate(text_data)
            fig, ax = plt.subplots(); ax.imshow(wc); ax.axis('off')
            st.pyplot(fig)
            
            xlsx_buf = BytesIO()
            st.session_state.history_db.to_excel(xlsx_buf, index=False)
            st.download_button("💾 전체 히스토리 백업 저장", data=xlsx_buf.getvalue(), file_name="AE_History_Backup.xlsx")
