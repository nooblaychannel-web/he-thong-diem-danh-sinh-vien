import pandas as pd
import streamlit as st
from datetime import datetime
import gspread 
import json
import os

GOOGLE_SHEET_NAME = "Data Diem Danh" 

SUBJECTS = [
    "Python",
    "C++",
    "Toán cao cấp",
    "Khoa học dữ liệu",
    "Tin học ứng dụng",
    "Tiếng Anh chuyên ngành"
]

WORKSHEET_NAME = "Sheet1" 


conn = None 
gc = None

conn = None 
gc = None

try:
    # 1. ĐỌC CHUỖI KEY NÉN TỪ BIẾN MÔI TRƯỜNG
    # Tên biến môi trường đã đặt trong Streamlit Secrets
    KEY_ENV_NAME = "GCP_SERVICE_ACCOUNT_KEY"
    
    if KEY_ENV_NAME not in os.environ:
        st.error(f"❌ Lỗi cấu hình: Không tìm thấy biến môi trường {KEY_ENV_NAME}. Vui lòng kiểm tra Secrets.")
        st.stop()

    # 2. TẢI CHUỖI JSON NÉN THÀNH DICT PYTHON
    # Key được nén 1 dòng nên không cần xử lý ký tự đặc biệt
    service_account_info_dict = json.loads(os.environ[KEY_ENV_NAME])

    # 3. KẾT NỐI GSPREAD
    gc = gspread.service_account_from_dict(service_account_info_dict)
    
    # 4. MỞ SHEET VÀ WORKSHEET
    spreadsheet = gc.open(GOOGLE_SHEET_NAME) 
    worksheet = spreadsheet.worksheet(WORKSHEET_NAME) 
    
    st.session_state.worksheet = worksheet 
    conn = True 

except json.JSONDecodeError:
    st.error("❌ Lỗi kết nối Google Sheet: Key JSON trong biến môi trường bị hỏng hoặc chưa được nén đúng.")
    st.stop()
except gspread.exceptions.SpreadsheetNotFound:
    st.error(f"❌ Lỗi: Không tìm thấy Google Sheet có tên '{GOOGLE_SHEET_NAME}'.")
    st.stop()
except Exception as e:
    # Bắt các lỗi kết nối/quyền truy cập khác
    st.error(f"❌ Lỗi kết nối Google Sheet (Gspread Error): {e}. Vui lòng kiểm tra Quyền truy cập cho Service Account.")
    st.stop()

def load_data(subject_name):
    """Đọc dữ liệu điểm danh hiện tại từ Google Sheet và thêm cột ngày hôm nay."""
    
    if conn is None or 'worksheet' not in st.session_state:
        return None 

    st.info(f"Đang tải dữ liệu điểm danh môn: {subject_name}...")
    try:
        records = st.session_state.worksheet.get_all_records()
        df_all = pd.DataFrame(records)
        
        df_all = df_all.dropna(how="all") 
        
        if df_all.empty or '__MÃ SV__' not in df_all.columns:
            st.warning("Google Sheet trống hoặc không tìm thấy cột '__MÃ SV__'. Ứng dụng sẽ dừng.")
            return None 

        df = df_all[['__HỌ TÊN__', '__MÃ SV__']].copy()
        
        for col in df_all.columns:
            if col not in df.columns: 
                df[col] = df_all[col].apply(lambda x: str(x).upper() == "X") 
        
        today = datetime.now().strftime("%d/%m")
        if today not in df.columns:
            df[today] = False
        
        st.success("Tải dữ liệu thành công!")
        return df

    except Exception as e:
        st.error(f"❌ Lỗi khi đọc dữ liệu từ Google Sheet: {e}. Vui lòng kiểm tra lại cấu trúc Sheet.")
        return None

def save_attendance(df_updated):
    """Ghi toàn bộ DataFrame điểm danh đã cập nhật vào Google Sheet."""
    
    if conn is None or 'worksheet' not in st.session_state:
        st.error("Lưu thất bại: Worksheet không khả dụng.")
        return

    try:
        df_to_save = df_updated.copy()
        for col in df_to_save.columns[2:]: 
            df_to_save[col] = df_to_save[col].apply(lambda x: "X" if x else "")
            
        data_to_write = [df_to_save.columns.values.tolist()] + df_to_save.values.tolist()

        st.session_state.worksheet.update('A1', data_to_write)
        
        st.session_state.df = df_updated 
        st.success("✅ Lưu điểm danh thành công vào Google Sheet (qua gspread)!")
    except Exception as e:
        st.error(f"❌ Lỗi khi ghi vào Google Sheet: {e}. Lỗi có thể do giới hạn quyền hoặc lỗi cấu hình.")
        st.exception(e)


def attendance_report(df):
    col_name, col_masv = df.columns[:2]
    attendance_cols = df.columns[2:]

    report = pd.DataFrame({
        "Họ tên": df[col_name],
        "Mã SV": df[col_masv],
        "Số buổi học": df[attendance_cols].sum(axis=1)
    })

    if len(attendance_cols) > 0:
        report["Số buổi vắng"] = len(attendance_cols) - report["Số buổi học"]
        report["Điểm (%)"] = (report["Số buổi học"] / len(attendance_cols) * 100).round(1)
    else:
        report["Số buổi vắng"] = 0
        report["Điểm (%)"] = 0

    st.dataframe(report, use_container_width=True)


def main():
    st.title("🎓 Điểm Danh Sinh Viên (Google Sheets)")
    
    st.sidebar.header("📘 Chọn môn học")
    subject = st.sidebar.selectbox("Môn học", SUBJECTS)
    st.session_state.subject = subject

    if "view" not in st.session_state:
        st.session_state.view = "attendance"
    
    load_key = f"data_loaded_{subject}"

    if load_key not in st.session_state:
        df = load_data(subject)
        
        if df is None:
            st.error("Không thể tiếp tục vì không tải được dữ liệu gốc từ Google Sheet.")
            st.stop()

        st.session_state.df = df
        st.session_state[load_key] = True 
        st.rerun() 

    if st.session_state.view == "attendance":
        st.subheader(f"✅ Điểm danh môn: {subject}")

        with st.form(key="attendance_form"):
            st.write("### Bảng điểm danh (Cần nhấn 'Lưu' để cập nhật lên Google Sheets)")
            
            
            if 'df' not in st.session_state or st.session_state.df.empty:
                 st.warning("Chưa có dữ liệu sinh viên để hiển thị.")
                 st.stop()
                 
            today_col = st.session_state.df.columns[-1]
            disabled_cols = st.session_state.df.columns[:-1].tolist()
            
            edited_df = st.data_editor(
                st.session_state.df,
                column_config={
                    today_col: st.column_config.CheckboxColumn(today_col)
                },
                disabled=disabled_cols,
                key="form_attendance_editor", 
                use_container_width=True
            )
            
            col1, col2 = st.columns([1, 4])
            with col1:
                save_button = st.form_submit_button("💾 Lưu và Cập nhật điểm danh", type="primary")

            if save_button:
                save_attendance(edited_df)
        
        if st.button("📊 Báo cáo chuyên cần"):
            st.session_state.view = "report"
            st.rerun()

    else: 
        st.subheader(f"📊 Báo cáo chuyên cần – {subject}")

        if st.button("⬅️ Quay lại điểm danh"):
            st.session_state.view = "attendance"
            st.rerun()

        attendance_report(st.session_state.df)

if __name__ == "__main__":
    main()