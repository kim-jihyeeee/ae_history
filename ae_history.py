import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime
import os
import requests

# 1. 기본 설정
st.set_page_config(page_title="AE History Visualizer v6.2", layout="wide")

# 🌟 폰트 해결: 나눔고딕 폰트를 인터넷에서 직접 가져옵니다.
@st.cache_data
def load_font():
    font_url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf"
    font_res = requests.get(font_url)
    with open("nanum_font.ttf", "wb") as f:
        f.write(font_res.content)
    return "nanum_font.ttf"

try:
    FONT_PATH = load_font()
except:
    FONT_PATH = None # 실패 시 기본 폰트 사용

# 세션 상태 초기화
if 'client_db' not in st.session_state: st.session_state.client_db = pd.DataFrame()
if 'history_db' not in st.session_state: st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '핵심키워드'])

# 2. UI 디자인
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: hidden; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; border: none; height: 3em; }
    div[data-testid="stTextInput"] input { border: 2px solid #FFB300 !important; }
    </style>
""", unsafe_allow_html=True)

st.title("📝 AE History Visualizer v6.2")

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
    if not st.session_state.client_db.empty:
        st.dataframe(st.session_state.client_db, use_container_width=True, hide_index=True)

# --- 2. 관리 이력 입력 ---
elif menu == "관리 이력 입력":
    st.header("✍️ 소통 및 관리 이력 기록")
    if st.session_state.client_db.empty:
        st.warning("먼저 '광고주 DB 관리' 메뉴에서 리스트를 등록해주세요.")
    else:
        search_query = st.text_input("🔍 업체명 검색 (일부만 입력해도 필터링됩니다)", placeholder="예: 삼다 또는 water")
        all_clients = sorted(st.session_state.client_db['광고주명'].dropna().unique())
        filtered_clients = [c for c in all_clients if search_query.lower() in str(c).lower()]
        
        if not filtered_clients:
            st.error("검색 결과가 없습니다.")
        else:
            with st.form("history_input_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    client = st.selectbox(f"광고주 선택 ({len(filtered_clients)}건 검색됨)", filtered_clients)
                    log_date = st.date_input("기록 날짜", datetime.date.today())
                with c2:
                    tags = st.text_input("핵심 키워드 (쉼표 구분)", placeholder="효율개선, ROAS상승")
                content = st.text_area("상세 관리 내용 (워드클라우드 분석용)", height=150)
                submitted = st.form_submit_button("히스토리 저장하기")
                
                if submitted:
                    if content.strip() == "":
                        st.error("내용을 입력해주세요!")
                    else:
                        new_data = pd.DataFrame([[log_date, client, content, tags]], columns=['날짜', '광고주명', '소통내용', '핵심키워드'])
                        st.session_state.history_db = pd.concat([st.session_state.history_db, new_data], ignore_index=True)
                        st.success(f"✅ {client}의 이력이 저장되었습니다.")
        
        st.subheader("📊 현재 누적된 히스토리")
        st.dataframe(st.session_state.history_db.sort_values(by='날짜', ascending=False), use_container_width=True)

# --- 3. 디지털 리포트 생성 ---
elif menu == "디지털 리포트 생성":
    st.header("📊 워드클라우드 분석 리포트")
    if st.session_state.history_db.empty:
        st.info("기록된 데이터가 없습니다.")
    else:
        search_rep = st.text_input("🔍 대상 업체 검색", key="rep_search")
        all_rep_clients = sorted(st.session_state.history_db['광고주명'].unique())
        filtered_rep = [c for c in all_rep_clients if search_rep.lower() in str(c).lower()]
        
        if filtered_rep:
            target_client = st.selectbox("대상 광고주 선택", filtered_rep)
            period_opt = st.select_slider("분석 기간", options=["7일", "15일", "한달", "분기"])
            
            days_delta = {"7일": 7, "15일": 15, "한달": 30, "분기": 90}[period_opt]
            start_date = datetime.date.today() - datetime.timedelta(days=days_delta)
            
            filtered_df = st.session_state.history_db[
                (st.session_state.history_db['광고주명'] == target_client) &
                (pd.to_datetime(st.session_state.history_db['날짜']).dt.date >= start_date)
            ]
            
            if not filtered_df.empty:
                text_data = (filtered_df['핵심키워드'].fillna('').str.cat(sep=' ') + " ") * 3 + filtered_df['소통내용'].fillna('').str.cat(sep=' ')
                try:
                    # 🌟 폰트가 없으면 시스템 기본 폰트라도 쓰도록 설정
                    wc = WordCloud(
                        font_path=FONT_PATH, 
                        width=900, height=500, 
                        background_color='white', 
                        colormap='Dark2', 
                        regexp=r"[\w\xA1-\xFE]+"
                    ).generate(text_data)
                    
                    fig, ax = plt.subplots(figsize=(10, 6))
                    ax.imshow(wc, interpolation='bilinear'); ax.axis('off')
                    st.pyplot(fig)
                    
                    c1, c2 = st.columns(2)
                    img_buf = BytesIO()
                    fig.savefig(img_buf, format="png", dpi=300, bbox_inches='tight')
                    c1.download_button(label="📥 리포트 이미지 저장", data=img_buf.getvalue(), file_name=f"Report_{target_client}.png", mime="image/png")
                    
                    xlsx_buf = BytesIO()
                    st.session_state.history_db.to_excel(xlsx_buf, index=False)
                    c2.download_button(label="💾 히스토리 백업 저장", data=xlsx_buf.getvalue(), file_name=f"AE_History_Backup.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                except Exception as e:
                    st.error(f"워드클라우드 생성 중 오류: {e}")
            else:
                st.warning("데이터가 없습니다.")
        else:
            st.error("검색된 업체가 없습니다.")
