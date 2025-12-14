import os
import pandas as pd
import streamlit as st
from datetime import datetime

SUBJECTS = [
    "Python",
    "C++",
    "Toán cao cấp",
    "Khoa học dữ liệu",
    "Tin học ứng dụng",
    "Tiếng Anh chuyên ngành"
]

def load_students(file):
    

    try:
        df_temp = pd.read_excel(file, header=None, nrows=5)
    except Exception as e:
        st.error(f"Không thể đọc file. Đảm bảo đây là file Excel (.xlsx) hợp lệ. Lỗi: {e}")
        return None
    
    def find_header_row(temp_df):
        df_str = temp_df.astype(str).apply(lambda x: x.str.strip().str.lower())
        
        for i in range(len(df_str)):
            row = df_str.iloc[i]

            has_name = any(("họ" in c or "tên" in c or "name" in c) for c in row)
            has_masv = any(("mã" in c and ("sv" in c or "số" in c)) or "masv" in c or "id" in c for c in row)
            
            if has_name and has_masv:
                return i
        return None

    header_index = find_header_row(df_temp)
    
    if header_index is None:
        st.error("❌ Không tìm thấy hàng tiêu đề chứa cả Họ tên và Mã SV trong 5 hàng đầu tiên.")
        st.warning("Vui lòng đảm bảo file Excel có tiêu đề chứa từ khóa: 'Họ tên' và 'Mã SV'.")
        return None


    df = pd.read_excel(file, header=header_index)
    

    df.columns = [str(c).strip().lower() for c in df.columns]

    if "ngày tháng" in df.columns:
        df = df.drop(columns=["ngày tháng"])


    col_name = next(
        (c for c in df.columns if ("họ" in c or "tên" in c or "name" in c)), None
    )
    col_masv = next(
        (c for c in df.columns if ("mã" in c and ("sv" in c or "số" in c)) or "masv" in c), None
    )
    if col_masv is None:
         col_masv = next((c for c in df.columns if "mã" in c or "id" in c), None)


    if col_name is None or col_masv is None:
        st.error("❌ Lỗi nội bộ: Không thể khớp tên cột sau khi tải file. Vui lòng kiểm tra lại file.")
        st.dataframe(pd.DataFrame({"Tên cột chuẩn hóa": df.columns}))
        return None
        
    st.success(f"Đã tìm thấy tiêu đề ở hàng {header_index + 1} (Excel). Cột Họ tên = '{col_name}', Mã SV = '{col_masv}'")

    today = datetime.now().strftime("%d/%m")
    if today not in df.columns:
        df[today] = False

    df = df[[col_name, col_masv, today]]
    df.columns = ["__HỌ TÊN__", "__MÃ SV__", today] 
    
    return df

def save_attendance(df, file_name):
    df_to_save = df.copy()
    
    rename_map = {
        df.columns[0]: "HỌ TÊN",
        df.columns[1]: "MÃ SV"
    }
    
    for col in df.columns[2:]:
        df_to_save[col] = df_to_save[col].apply(lambda x: "X" if x else "")
        
    df_to_save = df_to_save.rename(columns=rename_map)
    df_to_save.to_excel(file_name, index=False)
    st.success(f"Đã lưu điểm danh vào file: {file_name}")

def draw_table(df):
    pass 

def attendance_report(df):
    col_name, col_masv = df.columns[:2]
    attendance_cols = df.columns[2:]

    report = pd.DataFrame({
        "Họ tên": df[col_name],
        "Mã SV": df[col_masv],
        "Số buổi học": df[attendance_cols].sum(axis=1)
    })

    report["Số buổi vắng"] = len(attendance_cols) - report["Số buổi học"]
    report["Điểm (%)"] = (report["Số buổi học"] / len(attendance_cols) * 100).round(1)

    st.dataframe(report, use_container_width=True)

def main():
    st.title("🎓 Điểm Danh Sinh Viên")

    st.sidebar.header("📘 Chọn môn học")
    subject = st.sidebar.selectbox("Môn học", SUBJECTS)

    if "view" not in st.session_state:
        st.session_state.view = "attendance"
        

    if "original_file_name" in st.session_state:
        class_name = st.session_state.class_name
        

        safe_subject = subject.replace(" ", "_") 
        attendance_file = os.path.join("attendance", class_name, f"{safe_subject}.xlsx")
        st.session_state.attendance_file = attendance_file
        

        if st.session_state.get("loaded_file_path") != attendance_file and "df" in st.session_state:
            del st.session_state.df 
            st.session_state.view = "attendance" 
            st.rerun()

    if "df" not in st.session_state:
        if "original_file_name" not in st.session_state:
            file = st.file_uploader("📂 Upload file danh sách lớp", type=["xlsx"])
            if file is None:
                st.stop()
            st.session_state.original_file = file
            st.session_state.original_file_name = file.name
        else:
            file = st.session_state.original_file
            
        class_name = os.path.splitext(st.session_state.original_file_name)[0]
        st.session_state.class_name = class_name
        
        class_dir = os.path.join("attendance", class_name)
        os.makedirs(class_dir, exist_ok=True)


        safe_subject = subject.replace(" ", "_") 
        attendance_file = os.path.join(class_dir, f"{safe_subject}.xlsx")
        st.session_state.attendance_file = attendance_file

        if os.path.exists(attendance_file):
            df = pd.read_excel(attendance_file)

            df.columns = ["__HỌ TÊN__", "__MÃ SV__"] + df.columns.tolist()[2:] 
            
            today = datetime.now().strftime("%d/%m")
            if today not in df.columns:
                df[today] = False
                
            for col in df.columns[2:]:
                df[col] = df[col].apply(lambda x: str(x).upper() == "X")
        else:
            df = load_students(file)
            if df is None:
                st.stop()

        st.session_state.df = df
        st.session_state.loaded_file_path = attendance_file
        st.rerun()


    if st.session_state.view == "attendance":
        st.subheader(f"✅ Điểm danh môn: {subject}")


        with st.form(key="attendance_form"):
            st.write("### Bảng điểm danh (Cần nhấn 'Lưu' để cập nhật)")
            

            disabled_cols = st.session_state.df.columns[:-1].tolist()
            edited_df = st.data_editor(
                st.session_state.df,
                column_config={
                    st.session_state.df.columns[-1]: st.column_config.CheckboxColumn(st.session_state.df.columns[-1])
                },
                disabled=disabled_cols,
                key="form_attendance_editor", 
                use_container_width=True
            )
            
            col1, col2 = st.columns([1, 4])
            with col1:

                save_button = st.form_submit_button("💾 Lưu và Cập nhật điểm danh", type="primary")

            if save_button:

                st.session_state.df = edited_df 

                save_attendance(
                    st.session_state.df,
                    st.session_state.attendance_file
                )
        
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