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

# --- 3. 데이터 로드 및 전처리 함수 ---
def load_data():
    client = get_gspread_client()
    sheet_id = "1718siWh7O-He8KQ3Ae2lHhpRsNaENzGFk0i2pu8398Q" 
    doc = client.open_by_key(sheet_id)
    sheet = doc.worksheet("학생현황")
    all_values = sheet.get_all_values()
    
    header_idx = 0
    for i, row in enumerate(all_values):
        if '학년' in row and '성명' in row:
            header_idx = i
            break
    
    header = all_values[header_idx]
    data = all_values[header_idx + 1:]
    
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

# --- 4. 메인 화면 구성 ---
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
        late_list = []
        for index, row in class_df.iterrows():
            if st.checkbox(f"👤 {row['성명']}", key=index):
                late_list.append(row)

        st.divider()

        # --- [수정된 버튼 로직] ---
        if st.button(f"🚀 {len(late_list)}명 지각 보고 및 저장", use_container_width=True):
            if not late_list:
                st.info("선택된 학생이 없습니다.")
            else:
                log_sheet = doc.worksheet("지각기록")
                
                # 1. 이미 기록된 데이터 가져오기 (중복 체크용)
                existing_logs = log_sheet.get_all_records()
                existing_df = pd.DataFrame(existing_logs)
                
                today_str = datetime.now().strftime("%Y-%m-%d")
                now_full = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                new_count = 0
                already_count = 0
                
                for s in late_list:
                    # 중복 조건: 오늘 날짜에 해당 학생 이름이 이미 있는지 확인
                    is_duplicate = False
                    if not existing_df.empty:
                        # '날짜' 컬럼에서 오늘 날짜를 포함하고, '성명'이 같은지 확인
                        match = existing_df[
                            (existing_df['날짜'].str.contains(today_str)) & 
                            (existing_df['성명'] == s['성명'])
                        ]
                        if not match.empty:
                            is_duplicate = True
                    
                    if not is_duplicate:
                        # 중복이 아닐 때만 기록
                        log_sheet.append_row([now_full, s['학년'], s['반'], s['성명'], s.get('학부모폰', '')])
                        new_count += 1
                    else:
                        already_count += 1
                
                # 결과 알림
                if new_count > 0:
                    st.toast(f"{new_count}명 신규 기록 완료!", icon="✅")
                if already_count > 0:
                    st.warning(f"{already_count}명은 이미 오늘 기록되었습니다.")
                
                if new_count > 0:
                    st.success("구글 시트에 성공적으로 저장되었습니다.")
                
                # 다운로드용 세션 저장
                st.session_state['last_late'] = late_list

        if 'last_late' in st.session_state:
            late_df = pd.DataFrame(st.session_state['last_late'])
            csv = late_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 하이에듀 업로드용 CSV 다운로드", data=csv, file_name=f"late_{datetime.now().strftime('%m%d')}.csv")

except Exception as e:
    st.error(f"⚠️ 오류 발생: {e}")
