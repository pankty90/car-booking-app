import streamlit as st
import pandas as pd
from datetime import datetime, date, time
from streamlit_calendar import calendar
import requests

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="ระบบตารางจอง Boom-Lift,X-Lift", layout="wide")

st.markdown("""
<style>
    .main-title { font-family: 'Sarabun', sans-serif; color: #1e293b; font-weight: 700; }
    .card-container { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 16px; padding: 25px; text-align: center; }
    td.fc-day-sat, td.fc-day-sat .fc-daygrid-day-frame, .fc-timegrid-col.fc-day-sat { background-color: #cbd5e1 !important; }
    td.fc-day-sun, td.fc-day-sun .fc-daygrid-day-frame, .fc-timegrid-col.fc-day-sun { background-color: #fca5a5 !important; }
    .fc .fc-col-header-cell.fc-day-sun .fc-col-header-cell-cushion { color: #991b1b !important; font-weight: bold; }
    .fc .fc-col-header-cell.fc-day-sat .fc-col-header-cell-cushion { color: #1e293b !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">📅 ระบบตารางจองBoom-Lift,X-Lift (Car Booking Dashboard)</h1>', unsafe_allow_html=True)

# 🛑 จุดแก้ไขที่ 1: ลิงก์ดึงข้อมูลจาก Google Sheet ของคุณ
SHEET_URL = "https://docs.google.com/spreadsheets/d/1edm4HlYEnvlKE5ZOeinEeoJyFbWvwkS4nWjPiU673V0/edit?gid=0#gid=0"

# 🛑 จุดแก้ไขที่ 2: วางลิงก์ Google Form Response ที่เปลี่ยนท้ายคำเป็น /formResponse แล้ว
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSegBTNB3BtvVvBwUfgGrFxayPur5lBzcXUGDWv3ZTbvFtKnCA/formResponse"

# แปลงลิงก์สำหรับดึงข้อมูลไฟล์มาอ่าน
if "/edit" in SHEET_URL:
    DATA_URL = SHEET_URL.split("/edit")[0] + "/export?format=csv"
else:
    DATA_URL = SHEET_URL

CAR_LIST = ["Boom-Lift", "X-Lift"]
LOCATION_LIST = ["F1", "F2", "WH-Center", "WH-CKD", "POD"]

def load_sheet_data(url):
    try:
        st.cache_data.clear()
        df_sheet = pd.read_csv(url)
        df_sheet.columns = df_sheet.columns.astype(str).str.strip()
        
        if 'Car' in df_sheet.columns and not df_sheet.empty:
            df_sheet = df_sheet.dropna(subset=['Car', 'No'])
            df_sheet['No'] = df_sheet['No'].astype(int)
            df_sheet['Start_Date'] = pd.to_datetime(df_sheet['Start_Date'], errors='coerce')
            df_sheet['Finish_Date'] = pd.to_datetime(df_sheet['Finish_Date'], errors='coerce')
            df_sheet = df_sheet.dropna(subset=['Start_Date', 'Finish_Date'])
            
            # 🔥 ลอจิกสำคัญ: เอาเฉพาะแถวล่าสุดของแต่ละ Job No (ถ้ายกเลิก ข้อมูลใหม่จะมาทับ)
            df_sheet = df_sheet.sort_index().drop_duplicates(subset=['No'], keep='last')
            
            # กรองเอาพวกที่ไม่ได้โดนยกเลิกออกไป (คัดกรองคำว่า [CANCELLED] ในช่อง User)
            df_sheet = df_sheet[~df_sheet['User'].astype(str).str.startswith('[CANCELLED]')]
            
            return df_sheet
        return pd.DataFrame(columns=['No', 'Car', 'Start_Date', 'Finish_Date', 'Location', 'User', 'Purpose'])
    except Exception as e:
        return pd.DataFrame(columns=['No', 'Car', 'Start_Date', 'Finish_Date', 'Location', 'User', 'Purpose'])

df = load_sheet_data(DATA_URL)

# ส่วนการกรองและการแสดงผลปฏิทิน
unique_cars_for_view = ["ทั้งหมด (All Vehicles)"] + CAR_LIST
selected_car = st.selectbox("🚗 คัดกรองประเภทรถสำหรับแสดงบนปฏิทิน", unique_cars_for_view, index=0)

filtered_df = df.copy()
if selected_car != "ทั้งหมด (All Vehicles)" and not filtered_df.empty:
    filtered_df = filtered_df[filtered_df['Car'] == selected_car]

calendar_events = []
if not filtered_df.empty:
    for _, row in filtered_df.iterrows():
        is_boom = "boom" in str(row['Car']).lower()
        bg_color = "#5bc0de" if is_boom else "#f0ad4e"
        border_color = "#46b8da" if is_boom else "#eea236"
        
        loc_info = f" @ {row['Location']}" if 'Location' in row and pd.notna(row['Location']) else ""
        user_info = f" [By: {row['User']}]" if 'User' in row and pd.notna(row['User']) else ""
        job_no = int(row['No'])
        
        # ดึงข้อมูลวัตถุประสงค์การใช้งานมาแสดงผล (ถ้าไม่มีข้อความ ให้แสดงว่าไม่ได้ระบุ)
        purpose_info = row['Purpose'] if 'Purpose' in row and pd.notna(row['Purpose']) else "ไม่ได้ระบุ"
        
        start_str = row['Start_Date'].strftime('%d/%m/%Y %H:%M')
        finish_str = row['Finish_Date'].strftime('%d/%m/%Y %H:%M')
        
        # รวมข้อความทั้งหมดรวมถึงวัตถุประสงค์ และใช้ \n ขึ้นบรรทัดใหม่
        full_title = (
            f"🚗 {row['Car']} (Job: {job_no})\n"
            f"📍 สถานที่: {row['Location']}\n"
            f"👤 ผู้จอง: {row['User']}\n"
            f"🛠️ งานที่ทำ: {purpose_info}\n"
            f"⏱️ เวลา: {start_str} ถึง {finish_str}"
        )
        
        calendar_events.append({
            "title": full_title,  # ส่งข้อความยาวที่มีวัตถุประสงค์เข้าไปที่ title ตรงๆ
            "start": row['Start_Date'].isoformat(),
            "end": row['Finish_Date'].isoformat(),
            "backgroundColor": bg_color,
            "borderColor": border_color,
            "textColor": "#ffffff" if not is_boom else "#033c4e",
            "allDay": False
        })

col_left, col_right = st.columns([1, 2.5])

with col_left:
    tab1, tab2 = st.tabs(["📝 จองรถใหม่", "❌ ยกเลิกการจอง"])
    
    with tab1:
        with st.form(key="booking_form", clear_on_submit=True):
            input_car = st.selectbox("เลือกประเภทรถ", CAR_LIST)
            input_location = st.selectbox("เลือกสถานที่ใช้งาน (Location)", LOCATION_LIST)
            input_user = st.text_input("ชื่อผู้ใช้งาน / ผู้จองรถ", placeholder="พิมพ์ชื่อ-นามสกุล")
            
            # 🔥 เพิ่มฟิลด์: วัตถุประสงค์การนำรถไปใช้งาน
            input_purpose = st.text_area(
                "วัตถุประสงค์การใช้งาน / รายละเอียดงาน", 
                placeholder="ระบุวัตถุประสงค์หรือรายละเอียดงานที่ต้องการนำรถไปใช้ เช่น ซ่อมแซมระบบไฟฟ้าชั้น 2, ทำความสะอาดกระจก, ซ่อมหลังคาคลังสินค้า F1 ฯลฯ",
                max_chars=200
            )
            
            c1, c2 = st.columns(2)
            with c1:
                input_start_date = st.date_input("วันเริ่มต้น", date.today())
                input_finish_date = st.date_input("วันสิ้นสุด", date.today())
            with c2:
                input_start_time = st.time_input("เวลาเริ่ม", time(8, 0))
                input_finish_time = st.time_input("เวลาคืน", time(17, 0))
            
            submit_button = st.form_submit_button(label="💾 บันทึกข้อมูลการจอง")
            
            if submit_button:
                start_datetime = datetime.combine(input_start_date, input_start_time)
                finish_datetime = datetime.combine(input_finish_date, input_finish_time)
                
                if not input_user.strip():
                    st.error("❌ กรุณากรอกชื่อผู้ใช้งานก่อนบันทึกข้อมูลครับ!")
                elif not input_purpose.strip():
                    st.error("❌ กรุณาระบุรายละเอียดวัตถุประสงค์การนำไปใช้งานด้วยครับ!")
                elif start_datetime >= finish_datetime:
                    st.error("❌ วัน/เวลาเริ่มต้น ต้องเกิดขึ้นก่อนวัน/เวลาสิ้นสุด!")
                else:
                    # 🛠️ ตรวจสอบการจองซ้ำ (Conflict Check)
                    is_conflict = False
                    if not df.empty:
                        car_df = df[df['Car'] == input_car]
                        conflict_bookings = car_df[
                            (car_df['Start_Date'] < finish_datetime) & 
                            (car_df['Finish_Date'] > start_datetime)
                        ]
                        
                        if not conflict_bookings.empty:
                            is_conflict = True
                            st.error(f"❌ ไม่สามารถจองได้! รถ {input_car} ถูกจองแล้วในช่วงเวลาดังกล่าว")
                            for _, conf_row in conflict_bookings.iterrows():
                                st.warning(f"⚠️ รายการที่ทับซ้อน: Job {conf_row['No']} โดย {conf_row['User']}")
                    
                    if not is_conflict:
                        try:
                            raw_df = pd.read_csv(DATA_URL)
                            raw_df.columns = raw_df.columns.astype(str).str.strip()
                            next_no = int(raw_df['No'].max() + 1) if not raw_df.empty and 'No' in raw_df.columns else 1
                        except:
                            next_no = int(df['No'].max() + 1) if not df.empty else 1
                        
                        try:
                            # 🛑 อย่าลืมแก้ไขค่า entry.YOUR_PURPOSE_ENTRY_ID ให้ตรงกับไอดีฟิลด์ใน Google Form ของคุณ
                            form_data = {
                                "entry.1395769328": next_no,
                                "entry.779880298": input_car,
                                "entry.572197217": start_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                                "entry.466730705": finish_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                                "entry.26753276": input_location,
                                "entry.665863470": input_user.strip(),
                                "entry.542993285": input_purpose.strip()  # 👈 ฟิลด์ใหม่เก็บวัตถุประสงค์
                            }
                            
                            response = requests.post(FORM_URL, data=form_data)
                            if response.status_code == 200:
                                st.success(f"🎉 ส่งข้อมูลการจองสำเร็จ! (Job: {next_no})")
                                st.rerun()
                            else:
                                st.error("เกิดข้อผิดพลาดในการเชื่อมต่อฟอร์มภายนอก")
                        except Exception as ex:
                            st.error(f"เกิดข้อผิดพลาดในการส่งข้อมูล: {ex}")
                            
    with tab2:
        st.markdown("### ❌ ยกเลิกการจองเดิม")
        if not df.empty:
            job_options = {f"Job {row['No']}: {row['Car']} ({row['User']})": row for _, row in df.iterrows()}
            selected_job_label = st.selectbox("เลือกรายการจองที่ต้องการยกเลิก", list(job_options.keys()))
            
            target_job = job_options[selected_job_label]
            
            st.markdown("⚠️ **ระบบความปลอดภัย:** คุณสามารถยกเลิกได้เฉพาะรายการจองของคุณเองเท่านั้น")
            confirm_user = st.text_input("พิมพ์ชื่อ-นามสกุลของคุณ เพื่อยืนยันความเป็นเจ้าของ", placeholder="พิมพ์ชื่อให้ตรงกับในระบบ")
            
            cancel_button = st.button("🚨 ยืนยันการยกเลิกการจองนี้", type="primary", use_container_width=True)
            
            if cancel_button:
                original_user = str(target_job['User']).strip().lower()
                input_user_confirm = confirm_user.strip().lower()
                
                if not input_user_confirm:
                    st.error("❌ กรุณากรอกชื่อของคุณเพื่อยืนยันตัวตนก่อนทำการยกเลิกครับ")
                elif input_user_confirm != original_user:
                    st.error(f"❌ ไม่สามารถยกเลิกได้! รายการนี้ถูกจองโดยคุณ '{target_job['User']}' กรุณาระบุชื่อผู้จองให้ถูกต้อง")
                else:
                    try:
                        # ดึงวัตถุประสงค์การใช้งานเดิมไปส่งต่อด้วยเพื่อไม่ให้ข้อมูลฟิลด์ใหม่บนคลาวด์หายไป
                        current_purpose = target_job['Purpose'] if 'Purpose' in target_job and pd.notna(target_job['Purpose']) else ""
                        
                        cancel_data = {
                            "entry.1395769328": int(target_job['No']),
                            "entry.779880298": target_job['Car'],
                            "entry.572197217": target_job['Start_Date'].strftime('%Y-%m-%d %H:%M:%S'),
                            "entry.466730705": target_job['Finish_Date'].strftime('%Y-%m-%d %H:%M:%S'),
                            "entry.26753276": target_job['Location'],
                            "entry.665863470": f"[CANCELLED] {target_job['User']}",
                            "entry.YOUR_PURPOSE_ENTRY_ID": current_purpose  # 👈 ส่งค่าวัตถุประสงค์เดิมกลับไปด้วยตอนยกเลิก
                        }
                        
                        response = requests.post(FORM_URL, data=cancel_data)
                        if response.status_code == 200:
                            st.success(f"🎉 ยกเลิก Job หมายเลข {target_job['No']} สำเร็จแล้ว!")
                            st.rerun()
                        else:
                            st.error("ไม่สามารถเชื่อมต่อระบบเพื่อส่งการยกเลิกได้")
                    except Exception as ex:
                        st.error(f"เกิดข้อผิดพลาด: {ex}")
        else:
            st.write("ไม่มีรายการจองที่สามารถยกเลิกได้ในขณะนี้")

with col_right:
    calendar_options = {
        "initialView": "dayGridMonth",
        "headerToolbar": {
            "left": "prev,next today", 
            "center": "title", 
            "right": "dayGridMonth,timeGridWeek,timeGridDay"
        },
        "slotLabelFormat": {"hour": "2-digit", "minute": "2-digit", "hour12": False},
        "editable": False, 
        "selectable": True, 
        "locale": "en",
        "eventDisplay": "block" 
    }
    calendar(
        events=calendar_events, 
        options=calendar_options, 
        custom_css="""
            .fc-event { 
                cursor: pointer; 
                white-space: pre-wrap !important; /* บังคับให้ปฏิทินยอมรับการขึ้นบรรทัดใหม่ \\n */
            }
        """,
        key="car_booking_calendar"
    )
