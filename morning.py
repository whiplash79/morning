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
    
    # [지각기록] 시트 연결 및 헤더 설정
    log_sheet = doc.worksheet("지각기록")
    log_header = ["날짜", "학년", "반", "성명", "학생 전화번호", "학부모 전화번호"]
    
    # 시트가 비어있으면 헤더 작성 (오류 방지)
    if not log_sheet.get_all_values():
        log_sheet.append_row(log_header)

    if class_df.empty:
        st.warning(f"{target_grade}학년 {target_room}반 데이터가 없습니다.")
    else:
        # 1. 체크박스 영역
        late_list = []
        for index, row in class_df.iterrows():
            # 시트의 컬럼명과 정확히 일치해야 합니다.
            s_phone = row.get('학생 전화번호', '')
            p_phone = row.get('학부모 전화번호', '')
            
            # 화면 표시: 이름 (학부모 번호 뒷자리 등)
            label = f"👤 **{row['성명']}**"
            if p_phone: label += f" (P: {p_phone[-4:]})" # 보안상 뒷번호만 살짝 표시
            
            if st.checkbox(label, key=f"chk_{row['성명']}"):
                late_list.append({
                    '학년': row['학년'], '반': row['반'], '성명': row['성명'],
                    '학생 전화번호': s_phone, '학부모 전화번호': p_phone
                })

        st.divider()

        # 2. 저장 버튼 로직
        if st.button(f"🚀 {len(late_list)}명 지각 보고 및 저장", use_container_width=True):
            if not late_list:
                st.info("선택된 학생이 없습니다.")
            else:
                all_logs = log_sheet.get_all_values()
                current_log_df = pd.DataFrame(all_logs[1:], columns=all_logs[0]) if len(all_logs) > 1 else pd.DataFrame(columns=log_header)
                
                today_str = datetime.now().strftime("%Y-%m-%d")
                now_full = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                newly_added = []
                for s in late_list:
                    is_dup = False
                    if not current_log_df.empty:
                        match = current_log_df[(current_log_df['날짜'].str.contains(today_str)) & (current_log_df['성명'] == s['성명'])]
                        if not match.empty:
                            is_dup = True
                    
                    if not is_dup:
                        # 지정하신 명칭으로 데이터 기록
                        log_sheet.append_row([now_full, s['학년'], s['반'], s['성명'], s['학생 전화번호'], s['학부모 전화번호']])
                        newly_added.append(s['성명'])

                if newly_added:
                    st.toast(f"{len(newly_added)}명 기록 성공!", icon="✅")
                    st.success(f"저장 완료: {', '.join(newly_added)}")
                else:
                    st.info("새로 추가할 인원이 없습니다. (이미 기록됨)")

        st.divider()

        # 3. 오늘의 기록 확인 및 삭제
        st.subheader("📝 오늘의 기록 확인")
        fresh_logs = log_sheet.get_all_values()
        
        if len(fresh_logs) > 1:
            header_row = fresh_logs[0]
            display_df = pd.DataFrame(fresh_logs[1:], columns=header_row)
            today_str = datetime.now().strftime("%Y-%m-%d")
            mine = display_df[
                (display_df['날짜'].str.contains(today_str)) & 
                (display_df['학년'] == str(target_grade)) & 
                (display_df['반'] == str(target_room))
            ]

            if not mine.empty:
                for idx, row in mine.iterrows():
                    c1, c2 = st.columns([4, 1])
                    c1.write(f"· **{row['성명']}** (부: {row.get('학부모 전화번호', '-')})")
                    if c2.button("삭제", key=f"del_{idx}"):
                        log_sheet.delete_rows(int(idx) + 2)
                        st.rerun()
            else:
                st.write("오늘 기록된 학생이 없습니다.")
        else:
            st.write("장부가 비어있습니다.")

except Exception as e:
    st.error(f"⚠️ 시스템 오류: {e}")
    st.info("구글 시트의 제목줄에 '학생 전화번호', '학부모 전화번호'가 있는지 확인해 주세요.")
