import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. 앱 페이지 설정 ---
st.set_page_config(page_title="지각생 체크 시스템", layout="centered")

# --- 2. 구글 시트 연결 함수 ---
def get_gspread_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds)

# --- 3. 데이터 로드 함수 ---
def load_data():
    client = get_gspread_client()
    sheet_id = "1718siWh7O-He8KQ3Ae2lHhpRsNaENzGFk0i2pu8398Q" 
    doc = client.open_by_key(sheet_id)
    sheet = doc.worksheet("학생현황")
    all_values = sheet.get_all_values()
    
    # 제목줄 찾기
    header_idx = 0
    for i, row in enumerate(all_values):
        if '학년' in row and '성명' in row:
            header_idx = i
            break
    
    header = all_values[header_idx]
    data = all_values[header_idx + 1:]
    
    # 중복 제목 방지
    seen = {}
    new_header = []
    for h in header:
        if h in seen:
            seen[h] += 1
            new_header.append(f"{h}_{seen[h]}")
        else:
            seen[h] = 0
            new_header.append(h)
            
    return pd.DataFrame(data, columns=new_header), doc

# --- 4. 메인 화면 ---
st.title("☀️ 실시간 지각 체크 시스템")

try:
    df, doc = load_data()
    
    qp = st.query_params
    target_grade = qp.get("grade", "3") 
    target_room = qp.get("room", "1")

    st.subheader(f"📍 {target_grade}학년 {target_room}반")
    
    df['학년'] = df['학년'].astype(str)
    df['반'] = df['반'].astype(str)
    
    class_df = df[(df['학년'] == target_grade) & (df['반'] == target_room)]
    
    if class_df.empty:
        st.warning(f"{target_grade}학년 {target_room}반 데이터가 없습니다.")
    else:
        # 학생 체크박스 리스트
        late_list = []
        for index, row in class_df.iterrows():
            # 체크박스 상태는 버튼을 눌러도 유지됩니다.
            if st.checkbox(f"👤 {row['성명']}", key=f"chk_{row['성명']}"):
                late_list.append(row)

        st.divider()

        # 보고 및 저장 버튼
        if st.button(f"🚀 {len(late_list)}명 지각 보고 및 저장", use_container_width=True):
            if not late_list:
                st.info("선택된 학생이 없습니다.")
            else:
                log_sheet = doc.worksheet("지각기록")
                
                # 1. 시트의 현재 기록을 다시 읽어옴 (최신 중복 체크용)
                existing_logs = log_sheet.get_all_records()
                existing_df = pd.DataFrame(existing_logs)
                
                today_str = datetime.now().strftime("%Y-%m-%d")
                now_full = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                newly_added = []
                already_in = []
                
                for s in late_list:
                    is_duplicate = False
                    if not existing_df.empty:
                        # 날짜가 오늘이고 성명이 같은지 확인
                        match = existing_df[
                            (existing_df['날짜'].str.contains(today_str)) & 
                            (existing_df['성명'] == s['성명'])
                        ]
                        if not match.empty:
                            is_duplicate = True
                    
                    if not is_duplicate:
                        # [핵심] 중복이 아닌 학생만 추가
                        log_sheet.append_row([now_full, s['학년'], s['반'], s['성명'], s.get('학부모폰', '')])
                        newly_added.append(s['성명'])
                    else:
                        already_in.append(s['성명'])
                
                # 결과 보고 (사용자 피드백)
                if newly_added:
                    st.toast(f"{len(newly_added)}명 신규 기록 완료!", icon="✅")
                    st.success(f"새로 기록된 학생: {', '.join(newly_added)}")
                
                if already_in:
                    st.info(f"이미 기록되어 제외된 학생: {', '.join(already_in)}")
                
                if not newly_added and already_in:
                    st.warning("새로 추가된 인원이 없습니다. 모두 이미 기록된 학생들입니다.")

except Exception as e:
    st.error(f"⚠️ 오류 발생: {e}")
