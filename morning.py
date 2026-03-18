import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. 앱 설정 ---
st.set_page_config(page_title="지각생 체크 시스템", layout="centered")

# --- 2. 구글 시트 연결 ---
def get_gspread_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds)

# --- 3. 데이터 로드 ---
def load_data():
    client = get_gspread_client()
    sheet_id = "1718siWh7O-He8KQ3Ae2lHhpRsNaENzGFk0i2pu8398Q" 
    doc = client.open_by_key(sheet_id)
    
    # 학생현황 읽기
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
    
    # 지각기록 시트 준비
    log_sheet = doc.worksheet("지각기록")
    
    if class_df.empty:
        st.warning(f"{target_grade}학년 {target_room}반 데이터가 없습니다.")
    else:
        # 1. 체크박스 영역
        late_list = []
        for index, row in class_df.iterrows():
            if st.checkbox(f"👤 {row['성명']}", key=f"chk_{row['성명']}"):
                late_list.append(row)

        st.divider()

        # 2. 저장 버튼 영역
        if st.button(f"🚀 {len(late_list)}명 지각 보고 및 저장", use_container_width=True):
            if not late_list:
                st.info("선택된 학생이 없습니다.")
            else:
                existing_logs = log_sheet.get_all_records()
                existing_df = pd.DataFrame(existing_logs)
                
                # '날짜' 컬럼이 없는 비어있는 시트일 경우 대비
                if existing_df.empty or '날짜' not in existing_df.columns:
                    # 제목줄이 없다면 생성 (오류 방지 핵심)
                    if not existing_logs:
                        log_sheet.append_row(["날짜", "학년", "반", "성명", "학부모폰"])
                    existing_df = pd.DataFrame(columns=["날짜", "학년", "반", "성명", "학부모폰"])

                today_str = datetime.now().strftime("%Y-%m-%d")
                now_full = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                newly_added = []
                for s in late_list:
                    # 중복 체크
                    is_dup = False
                    if not existing_df.empty:
                        match = existing_df[(existing_df['날짜'].str.contains(today_str)) & (existing_df['성명'] == s['성명'])]
                        if not match.empty:
                            is_dup = True
                    
                    if not is_dup:
                        log_sheet.append_row([now_full, s['학년'], s['반'], s['성명'], s.get('학부모폰', '')])
                        newly_added.append(s['성명'])

                if newly_added:
                    st.toast(f"{len(newly_added)}명 신규 기록 완료!", icon="✅")
                    st.success(f"새로 기록됨: {', '.join(newly_added)}")
                else:
                    st.info("새로 추가할 인원이 없습니다. (이미 기록됨)")

        st.divider()

        # 3. [신규] 오늘의 기록 확인 및 삭제 영역
        st.subheader("📝 오늘의 기록 확인")
        # 다시 읽어오기
        latest_logs = log_sheet.get_all_values()
        if len(latest_logs) > 1:
            log_df = pd.DataFrame(latest_logs[1:], columns=latest_logs[0])
            today_str = datetime.now().strftime("%Y-%m-%d")
            
            # 오늘 + 우리 반 기록만 필터링
            today_class_logs = log_df[
                (log_df['날짜'].str.contains(today_str)) & 
                (log_df['학년'] == str(target_grade)) & 
                (log_df['반'] == str(target_room))
            ]

            if not today_class_logs.empty:
                for idx, row in today_class_logs.iterrows():
                    cols = st.columns([3, 1])
                    cols[0].write(f"· {row['성명']} ({row['날짜'].split(' ')[1]})")
                    # 삭제 버튼 (실제 시트의 행 번호는 idx + 2)
                    if cols[1].button("삭제", key=f"del_{idx}"):
                        log_sheet.delete_rows(int(idx) + 2)
                        st.rerun() # 화면 새로고침
            else:
                st.write("오늘 기록된 학생이 없습니다.")
        else:
            st.write("기록 장부가 비어있습니다.")

except Exception as e:
    st.error(f"⚠️ 오류 발생: {e}")
