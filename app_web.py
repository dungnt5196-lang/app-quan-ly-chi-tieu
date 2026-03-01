import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import pytz

# --- KẾT NỐI DATABASE SUPABASE ---
SUPABASE_URL = "https://kjzywvulfspgogobdaoe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imtqenl3dnVsZnNwZ29nb2JkYW9lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIyNjcwMTksImV4cCI6MjA4Nzg0MzAxOX0.dtF4tP7em8gJOYO85v5-z8GaYPZFhuUCfmNw8YOVgT4"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Sổ Thu Chi", page_icon="💰", layout="wide")

# ==========================================
# CÀI ĐẶT MỤC TIÊU CHI TIÊU (TARGET)
# ==========================================
TARGET_THANG = {
    "Ăn uống": 4000000,
    "Tiền phòng": 3000000,
    "Đi lại": 800000,
    "Mua sắm": 1500000,
    "Khác": 1000000
}

# --- LẤY DỮ LIỆU TỪ MÂY ---
@st.cache_data(ttl=1) 
def load_data():
    response = supabase.table("chi_tieu").select("*").execute()
    return response.data

data = load_data()

# --- TÍNH TOÁN CÁC CON SỐ ---
tong_thu = sum(item['so_tien'] for item in data if item.get('loai_giao_dich') == 'Thu nhập')
tong_chi = sum(item['so_tien'] for item in data if item.get('loai_giao_dich') == 'Chi tiêu')
con_lai = tong_thu - tong_chi

# Thuật toán tính "Tháng này" và "Tháng trước"
chi_thang_nay = 0
chi_thang_truoc = 0

if data:
    df_tam = pd.DataFrame(data)
    if 'created_at' in df_tam.columns:
        # Xác định mốc thời gian
        now = datetime.now(pytz.timezone('Asia/Ho_Chi_Minh'))
        thang_hien_tai = now.strftime('%m/%Y')
        
        # Xử lý lùi tháng (nếu là tháng 1 thì lùi về tháng 12 năm ngoái)
        if now.month == 1:
            thang_truoc = f"12/{now.year - 1}"
        else:
            thang_truoc = f"{now.month - 1:02d}/{now.year}"
            
        df_tam['Tháng'] = pd.to_datetime(df_tam['created_at'], utc=True).dt.tz_convert('Asia/Ho_Chi_Minh').dt.strftime('%m/%Y')
        
        df_chi = df_tam[df_tam['loai_giao_dich'] == 'Chi tiêu']
        
        # Cắt dữ liệu ra 2 tháng
        chi_thang_nay = int(df_chi[df_chi['Tháng'] == thang_hien_tai]['so_tien'].sum())
        chi_thang_truoc = int(df_chi[df_chi['Tháng'] == thang_truoc]['so_tien'].sum())

# ==========================================
# GIAO DIỆN CHÍNH
# ==========================================
st.title("📊 Quản Lý Tài Chính Cá Nhân")

# 1. Hiển thị 4 Thẻ Thống Kê (Bản nâng cấp So sánh)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Tổng Thu Nhập", f"{tong_thu:,} đ")
col2.metric("Chi Tháng Trước", f"{chi_thang_truoc:,} đ") 

# Tính mức độ chênh lệch để vẽ mũi tên cảnh báo
chenh_lech = chi_thang_nay - chi_thang_truoc
col3.metric(
    "Chi Tháng Này", 
    f"{chi_thang_nay:,} đ", 
    delta=f"{chenh_lech:,} đ" if chi_thang_truoc > 0 else None, 
    delta_color="inverse" # Đảo màu: Số dương (tăng chi tiêu) = Đỏ báo động
) 

col4.metric("Còn Lại", f"{con_lai:,} đ", delta=con_lai)

st.divider()

# TẠO 2 TAB CHUYỂN ĐỔI GIAO DIỆN
tab1, tab2 = st.tabs(["📝 Ghi chép & Lịch sử", "📈 Phân tích & Cảnh báo"])

# -------------------------------------------------------------------
# TAB 1: GHI CHÉP & LỊCH SỬ
# -------------------------------------------------------------------
with tab1:
    cot_trai, cot_phai = st.columns([1, 2])
    
    with cot_trai:
        st.subheader("Thêm Giao Dịch")
        with st.form("form_nhap_lieu", clear_on_submit=True):
            loai = st.selectbox("Loại", ["Thu nhập", "Chi tiêu"])
            hang_muc = st.selectbox("Hạng mục", ["Lương", "Ăn uống", "Đi lại", "Mua sắm", "Tiền phòng", "Khác"])
            so_tien = st.number_input("Số tiền (VNĐ)", min_value=0, step=50000)
            noi_dung = st.text_input("Ghi chú")
            submitted = st.form_submit_button("💾 Lưu Giao Dịch", type="primary")
            
            if submitted:
                if so_tien <= 0:
                    st.error("Vui lòng nhập số tiền lớn hơn 0!")
                else:
                    new_data = {"loai_giao_dich": loai, "hang_muc": hang_muc, "so_tien": so_tien, "noi_dung": noi_dung}
                    supabase.table("chi_tieu").insert(new_data).execute()
                    st.success("Đã lưu thành công!")
                    st.rerun()

    with cot_phai:
        st.subheader("Lịch sử chi tiết")
        if data:
            df = pd.DataFrame(data)
            if 'created_at' in df.columns:
                df['Thời gian thực'] = pd.to_datetime(df['created_at'], utc=True).dt.tz_convert('Asia/Ho_Chi_Minh')
                df['Thời gian'] = df['Thời gian thực'].dt.strftime('%H:%M - %d/%m/%Y')
            else:
                df['Thời gian'] = "Không rõ"
                
            df_hien_thi = df.rename(columns={'loai_giao_dich': 'Loại', 'hang_muc': 'Hạng mục', 'so_tien': 'Số tiền (đ)', 'noi_dung': 'Ghi chú'})
            df_hien_thi = df_hien_thi[['Thời gian', 'Loại', 'Hạng mục', 'Số tiền (đ)', 'Ghi chú']]
            df_hien_thi = df_hien_thi.iloc[::-1]
            st.dataframe(df_hien_thi, use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có dữ liệu giao dịch.")

# -------------------------------------------------------------------
# TAB 2: PHÂN TÍCH & CẢNH BÁO
# -------------------------------------------------------------------
with tab2:
    if not data:
        st.warning("Chưa có đủ dữ liệu để phân tích. Hãy nhập thêm chi tiêu nhé!")
    else:
        df = pd.DataFrame(data)
        df['Thời gian thực'] = pd.to_datetime(df['created_at'], utc=True).dt.tz_convert('Asia/Ho_Chi_Minh')
        df['Tháng'] = df['Thời gian thực'].dt.strftime('%m/%Y') 
        
        df_chi = df[df['loai_giao_dich'] == 'Chi tiêu'].copy()
        
        if df_chi.empty:
            st.info("Chưa có khoản chi tiêu nào để tính toán cảnh báo.")
        else:
            st.subheader("📊 So sánh Tổng chi tiêu các tháng")
            chi_theo_thang = df_chi.groupby('Tháng')['so_tien'].sum().reset_index()
            st.bar_chart(data=chi_theo_thang.set_index('Tháng'), y='so_tien', color="#F44336")
            
            st.divider()
            
            st.subheader("🚨 Hệ thống Cảnh báo Tháng này")
            thang_hien_tai = datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime('%m/%Y')
            
            df_thang_nay = df_chi[df_chi['Tháng'] == thang_hien_tai]
            chi_thang_nay_dict = df_thang_nay.groupby('hang_muc')['so_tien'].sum().to_dict()
            
            df_thang_truoc = df_chi[df_chi['Tháng'] != thang_hien_tai]
            so_thang_truoc = df_thang_truoc['Tháng'].nunique()
            
            trung_binh_thang_truoc = {}
            if so_thang_truoc > 0:
                trung_binh_thang_truoc = (df_thang_truoc.groupby('hang_muc')['so_tien'].sum() / so_thang_truoc).to_dict()

            c1, c2 = st.columns(2)
            
            for hang_muc, target in TARGET_THANG.items():
                da_tieu = chi_thang_nay_dict.get(hang_muc, 0)
                tb_truoc_day = trung_binh_thang_truoc.get(hang_muc, 0)
                
                with (c1 if list(TARGET_THANG.keys()).index(hang_muc) % 2 == 0 else c2):
                    with st.container(border=True):
                        st.markdown(f"**🏷️ Hạng mục: {hang_muc}**")
                        st.write(f"Đã tiêu: **{da_tieu:,} đ** / Target: {target:,} đ")
                        
                        phan_tram = (da_tieu / target) * 100 if target > 0 else 0
                        if da_tieu > target:
                            st.error(f"❌ VƯỢT TARGET! Bạn đã tiêu lố {da_tieu - target:,} đ.")
                        elif phan_tram >= 80:
                            st.warning(f"⚠️ Sắp hết hạn mức! Đã dùng {phan_tram:.1f}%.")
                        else:
                            st.success(f"✅ An toàn. Còn lại {target - da_tieu:,} đ.")
                            
                        if tb_truoc_day > 0 and da_tieu > tb_truoc_day:
                            st.info(f"📈 Chú ý: Mục này đang tiêu nhiều hơn mức trung bình tháng trước ({tb_truoc_day:,.0f} đ). Cần hãm lại!")
