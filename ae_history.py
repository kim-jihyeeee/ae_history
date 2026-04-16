import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime
import os
import requests

# 1. 기본 설정
st.set_page_config(page_title="AE History Visualizer v6.8", layout="wide")

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
    .stDataEditor { border: 2px solid #FFB300; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

st.title("📝 AE History Visualizer v6.8")

# 사이드바 메뉴
menu = st.sidebar.radio("📋 메뉴 이동", ["광고주 DB 관리", "관리 이력 입력", "디지털 리포트 생성"])

# --- 1. 광고주 DB 관리 ---
if menu == "광고주 DB 관리":
    st.header("📂 데이터 로드 및 관리")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🏢 광고주 리스트 업로드")
        uploaded_clients = st.file_uploader("광고주 리스트 (엑셀/CSV)", type=['xlsx', 'csv'], key="clients")
    with col2:
        st.subheader("💾 히스토리 백업 로드")
        uploaded_history = st.file_uploader("백업 엑셀 파일", type=['xlsx'], key="history")
    
    if uploaded_clients:
        try:
            df = pd.read_csv(uploaded_clients) if uploaded_clients.name.endswith('.csv') else pd.read_excel(uploaded_clients)
            df.rename(columns={df.columns[0]: '광고주명'}, inplace=True)
            st.session_state.client_db = df
            st.success("✅ 광고주 리스트 로드 완료!")
        except: st.error("파일 확인 필요")

    if uploaded_history:
        try:
            h_df = pd.read_excel(uploaded_history)
            if '날짜' in h_df.columns: h_df['날짜'] = pd.to_datetime(h_df['날짜']).dt.date
            st.session_state.history_db = h_df
            st.success("✅ 히스토리 복구 완료!")
        except: st.error("백업 파일 로드 실패")

# --- 2. 관리 이력 입력 ---
elif menu == "관리 이력 입력":
    st.header("✍️ 소통 이력 기록 및 실시간 수정")
    if st.session_state.client_db.empty:
        st.warning("먼저 '광고주 DB 관리' 메뉴에서 리스트를 등록해주세요.")
    else:
        # 입력 폼 영역
        search_query = st.text_input("🔍 업체명 검색", placeholder="일부만 입력해도 필터링됩니다.")
        all_clients = sorted(st.session_state.client_db['광고주명'].dropna().unique())
        filtered_clients = [c for c in all_clients if search_query.lower() in str(c).lower()]
        
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
                st.success("저장되었습니다! 아래 표에서 바로 수정도 가능합니다.")
                st.rerun()

        st.divider()

        # 🌟 지혜님이 요청하신 기능: 입력 페이지에서 바로 수정하는 편집기
        if not st.session_state.history_db.empty:
            st.subheader("🛠️ 전체 히스토리 편집기")
            st.caption("내용을 클릭해서 수정하거나, 행을 선택해 삭제할 수 있습니다. 수정 후 반드시 아래 버튼을 눌러주세요.")
            
            # 전체 히스토리를 편집할 수 있는 데이터 에디터
            updated_history = st.data_editor(
                st.session_state.history_db,
                use_container_width=True,
                num_rows="dynamic", # 행 추가/삭제 가능
                hide_index=True,
                column_config={
                    "날짜": st.column_config.DateColumn("날짜"),
                    "광고주명": st.column_config.TextColumn("광고주명"),
                    "소통내용": st.column_config.TextColumn("소통내용", width="large"),
                    "핵심키워드": st.column_config.TextColumn("핵심키워드", width="medium")
                }
            )
            
            if st.button("✅ 수정/삭제사항 최종 반영하기"):
                st.session_state.history_db = updated_history
                st.success("수정사항이 완벽하게 반영되었습니다!")
                st.rerun()
        else:
            st.info("아직 기록된 히스토리가 없습니다.")

# --- 3. 디지털 리포트 생성 ---
elif menu == "디지털 리포트 생성":
    st.header("📊 워드클라우드 분석 리포트")
    if st.session_state.history_db.empty:
        st.info("기록된 데이터가 없습니다.")
    else:
        target_client = st.selectbox("대상 광고주 선택", sorted(st.session_state.history_db['광고주명'].unique()))
        period_opt = st.select_slider("기간", options=["7일", "15일", "한달", "분기"])
        
        days_delta = {"7일": 7, "15일": 15, "한달": 30, "분기": 90}[period_opt]
        filtered_df = st.session_state.history_db[(st.session_state.history_db['광고주명'] == target_client)]
        
        if not filtered_df.empty:
            text_data = (filtered_df['핵심키워드'].fillna('').str.cat(sep=' ') + " ") * 3 + filtered_df['소통내용'].fillna('').str.cat(sep=' ')
            wc = WordCloud(font_path=FONT_PATH, width=900, height=500, background_color='white', colormap='Dark2').generate(text_data)
            fig, ax = plt.subplots(figsize=(10, 5)); ax.imshow(wc); ax.axis('off')
            st.pyplot(fig)
            
            col1, col2 = st.columns(2)
            img_buf = BytesIO()
            fig.savefig(img_buf, format="png", dpi=300, bbox_inches='tight')
            col1.download_button(label="📥 리포트 이미지 저장", data=img_buf.getvalue(), file_name=f"Report_{target_client}.png", mime="image/png")
            
            xlsx_buf = BytesIO()
            st.session_state.history_db.to_excel(xlsx_buf, index=False)
            col2.download_button(label="💾 전체 백업 저장 (유실방지용)", data=xlsx_buf.getvalue(), file_name="AE_History_Backup.xlsx")
