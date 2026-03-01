import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import pytz

# --- KẾT NỐI DATABASE SUPABASE ---
SUPABASE_URL = "https://kjzywvulfspgogobdaoe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imtqenl3dnVsZnNwZ29nb2JkYW9lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIyNjcwMTksImV4cCI6MjA4Nzg0MzAxOX0.dtF4tP7em8gJOYO85v5-z8GaYPZFhuUCfmNw8YOVgT4"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Sổ Thu Chi", page_icon="💰", layout="wide")

# ==========================================
# 1. XỬ LÝ DỮ LIỆU & ĐỒNG BỘ TARGET TỪ MÂY
# ==========================================
DEFAULT_TARGETS = {
    "Ăn uống": 4000000,
    "Tiền phòng": 3000000,
    "Đi lại": 800000,
    "Mua sắm": 1500000,
    "Khác": 1000000
}

@st.cache_data(ttl=1) 
def load_data():
    response = supabase.table("chi_tieu").select("*").execute()
    return response.data

data = load_data()
df_all = pd.DataFrame(data) if data else pd.DataFrame()

current_targets = DEFAULT_TARGETS.copy()
df_tam = pd.DataFrame()

if not df_all.empty and 'loai_giao_dich' in df_all.columns:
    # Lấy lịch sử Target ẩn trên mây để đồng bộ mọi thiết bị
    df_targets = df_all[df_all['loai_giao_dich'] == 'Cài đặt Target']
    if not df_targets.empty:
        if 'created_at' in df_targets.columns:
            df_targets = df_targets.sort_values('created_at', ascending=False)
        df_targets = df_targets.drop_duplicates(subset=['hang_muc'])
        for _, row in df_targets.iterrows():
            if row['hang_muc'] in current_targets:
                current_targets[row['hang_muc']] = int(row['so_tien'])
    
    # Lọc bỏ data Target ẩn để bảng Thống kê thu chi không bị sai số
    df_tam = df_all[df_all['loai_giao_dich'] != 'Cài đặt Target'].copy()

# ==========================================
# 2. MENU BÊN TRÁI (ĐÃ THÊM NÚT LƯU ĐỒNG BỘ)
# ==========================================
with st.sidebar:
    st.header("⚙️ Cài đặt Hạn mức")
    st.markdown("Chỉnh số tiền và bấm **Lưu Đồng Bộ** để lưu cho mọi thiết bị:")
    
    with st.form("form_target"):
        new_targets = {}
        for hm, val in current_targets.items():
            new_targets[hm] = st.number_input(f"🎯 {hm} (VNĐ)", min_value=0, value=val, step=100000)
        
        # Nút này sẽ bắn dữ liệu lên Supabase
        if st.form_submit_button("💾 Lưu Đồng Bộ Lên Mây", type="primary"):
            for hm, val in new_targets.items():
                if val != current_targets[hm]:
                    supabase.table("chi_tieu").insert({
                        "loai_giao_dich": "Cài đặt Target", 
                        "hang_muc": hm, 
                        "so_tien": val, 
                        "noi_dung": "System"
                    }).execute()
            st.success("Đã đồng bộ thành công! Hãy tải lại trang.")
            st.rerun()

# ==========================================
# 3. TÍNH TOÁN CÁC CON SỐ THỐNG KÊ
# ==========================================
tong_thu = int(df_tam[df_tam['loai_giao_dich'] == 'Thu nhập']['so_tien'].sum()) if not df_tam.empty else 0
tong_chi = int(df_tam[df_tam['loai_giao_dich'] == 'Chi tiêu']['so_tien'].sum()) if not df_tam.empty else 0
con_lai = tong_thu - tong_chi

chi_thang_nay = 0
chi_thang_truoc = 0
thang_hien_tai = ""
thang_truoc = ""
df_chi = pd.DataFrame()

if not df_tam.empty and 'created_at' in df_tam.columns:
    now = datetime.now(pytz.timezone('Asia/Ho_Chi_Minh'))
    thang_hien_tai = now.strftime('%m/%Y')
    
    if now.month == 1:
        thang_truoc = f"12/{now.year - 1}"
    else:
        thang_truoc = f"{now.month - 1:02d}/{now.year}"
        
    df_tam['Tháng'] = pd.to_datetime(df_tam['created_at'], utc=True).dt.tz_convert('Asia/Ho_Chi_Minh').dt.strftime('%m/%Y')
    df_chi = df_tam[df_tam['loai_giao_dich'] == 'Chi tiêu']
    
    chi_thang_nay = int(df_chi[df_chi['Tháng'] == thang_hien_tai]['so_tien'].sum()) if not df_chi.empty else 0
    chi_thang_truoc = int(df_chi[df_chi['Tháng'] == thang_truoc]['so_tien'].sum()) if not df_chi.empty else 0

# ==========================================
# 4. GIAO DIỆN CHÍNH TRÊN MÀN HÌNH
# ==========================================
st.title("📊 Quản Lý Tài Chính Cá Nhân")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Tổng Thu Nhập", f"{tong_thu:,} đ")
col2.metric("Chi Tháng Trước", f"{chi_thang_truoc:,} đ") 

# Công thức: Tháng Này - Tháng Trước (Dương = Tiêu lố, Âm = Tiết kiệm)
chenh_lech_tong = chi_thang_nay - chi_thang_truoc 
col3.metric("Chi Tháng Này", f"{chi_thang_nay:,} đ", delta=f"{chenh_lech_tong:,} đ", delta_color="inverse") 
col4.metric("Còn Lại", f"{con_lai:,} đ", delta=con_lai)

st.markdown("---")

if not df_chi.empty:
    if chenh_lech_tong < 0:
        st.success(f"🎉 **TUYỆT VỜI!** Tháng này bạn đang **TIẾT KIỆM ĐƯỢC {abs(chenh_lech_tong):,} đ** so với tháng trước.")
    elif chenh_lech_tong > 0:
        st.error(f"💸 **BÁO ĐỘNG!** Tháng này bạn đã **TIÊU NHIỀU HƠN {chenh_lech_tong:,} đ** so với tháng trước.")
    else:
        if chi_thang_nay > 0:
            st.info("⚖️ Tháng này bạn chi tiêu vừa bằng tháng trước.")
else:
    st.info("👋 Chào mừng bạn! Hãy nhập khoản chi tiêu đầu tiên nhé.")

st.container(height=20, border=False)

# --- KHU VỰC NHẬP LIỆU ---
st.subheader("📝 Ghi chép & Lịch sử")
cot_trai, cot_phai = st.columns([1, 2])

with cot_trai:
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
    if not df_tam.empty:
        df_hien_thi = df_tam.rename(columns={'loai_giao_dich': 'Loại', 'hang_muc': 'Hạng mục', 'so_tien': 'Số tiền (đ)', 'noi_dung': 'Ghi chú'})
        if 'Thời gian thực' not in df_hien_thi.columns and 'created_at' in df_hien_thi.columns:
            df_hien_thi['Thời gian thực'] = pd.to_datetime(df_hien_thi['created_at'], utc=True).dt.tz_convert('Asia/Ho_Chi_Minh')
            df_hien_thi['Thời gian'] = df_hien_thi['Thời gian thực'].dt.strftime('%H:%M - %d/%m/%Y')
        else:
            df_hien_thi['Thời gian'] = "Không rõ"
            
        df_hien_thi = df_hien_thi[['Thời gian', 'Loại', 'Hạng mục', 'Số tiền (đ)', 'Ghi chú']]
        df_hien_thi = df_hien_thi.iloc[::-1]
        st.dataframe(df_hien_thi, use_container_width=True, hide_index=True, height=350)

st.markdown("---")

# --- BẢNG SO SÁNH ĐỐI CHIẾU ---
st.subheader("⚖️ Bảng Đối Chiếu Từng Hạng Mục")
if not df_chi.empty:
    df_thang_nay = df_chi[df_chi['Tháng'] == thang_hien_tai]
    df_thang_truoc = df_chi[df_chi['Tháng'] == thang_truoc]
    
    chi_nay_dict = df_thang_nay.groupby('hang_muc')['so_tien'].sum().to_dict()
    chi_truoc_dict = df_thang_truoc.groupby('hang_muc')['so_tien'].sum().to_dict()
    
    danh_sach_hang_muc = set(list(chi_nay_dict.keys()) + list(chi_truoc_dict.keys()))
    bang_so_sanh = []
    
    for hm in danh_sach_hang_muc:
        nay = chi_nay_dict.get(hm, 0)
        truoc = chi_truoc_dict.get(hm, 0)
        
        # Công thức: Tháng Này - Tháng Trước
        chenh = nay - truoc 
        
        if chenh > 0:
            danh_gia = "🔴 Tiêu lố"
            hien_thi_chenh = f"+{chenh:,} đ"
        elif chenh < 0:
            danh_gia = "🟢 Tiết kiệm"
            hien_thi_chenh = f"{chenh:,} đ" # Số âm tự có dấu trừ
        else:
            danh_gia = "⚪ Bằng nhau"
            hien_thi_chenh = "0 đ"
            
        bang_so_sanh.append({
            "Hạng mục": hm,
            "Tháng Trước": f"{truoc:,} đ",
            "Tháng Này": f"{nay:,} đ",
            "Chênh Lệch": hien_thi_chenh,
            "Đánh Giá": danh_gia,
            "_sort_val": chenh 
        })
    
    if bang_so_sanh:
        df_bang = pd.DataFrame(bang_so_sanh)
        # Sắp xếp để những mục tiêu lố nhiều nhất (số dương lớn nhất) nổi lên trên
        df_bang = df_bang.sort_values(by="_sort_val", ascending=False).drop(columns=["_sort_val"])
        st.dataframe(df_bang, use_container_width=True, hide_index=True)

st.markdown("---")

# --- CẢNH BÁO TARGET & BIỂU ĐỒ ---
st.subheader("🎯 Theo dõi Hạn mức & Xu hướng")
if not df_chi.empty:
    c_trai, c_phai = st.columns([1, 1])
    
    with c_trai:
        for hang_muc, target in current_targets.items():
            da_tieu = chi_nay_dict.get(hang_muc, 0) if 'chi_nay_dict' in locals() else 0
            
            with st.container(border=True):
                st.markdown(f"**🏷️ {hang_muc}**")
                st.write(f"Đã tiêu: **{da_tieu:,} đ** / Target: {target:,} đ")
                
                phan_tram = (da_tieu / target) * 100 if target > 0 else 0
                if da_tieu > target:
                    st.error(f"❌ Bạn đã tiêu lố {da_tieu - target:,} đ.")
                elif phan_tram >= 80:
                    st.warning(f"⚠️ Cẩn thận! Đã dùng {phan_tram:.1f}% hạn mức.")
                else:
                    st.success(f"✅ An toàn. Còn dư {target - da_tieu:,} đ.")
                    
    with c_phai:
        st.markdown("**Biểu đồ Tổng chi tiêu các tháng**")
        chi_theo_thang = df_chi.groupby('Tháng')['so_tien'].sum().reset_index()
        st.bar_chart(data=chi_theo_thang.set_index('Tháng'), y='so_tien', color="#38A896")
