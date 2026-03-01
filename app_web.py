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
# KHỞI TẠO BỘ NHỚ LƯU TARGET CÓ THỂ ĐIỀU CHỈNH
# ==========================================
if 'targets' not in st.session_state:
    st.session_state.targets = {
        "Ăn uống": 4000000,
        "Tiền phòng": 3000000,
        "Đi lại": 800000,
        "Mua sắm": 1500000,
        "Khác": 1000000
    }

# ==========================================
# MENU BÊN TRÁI (SIDEBAR) ĐỂ CHỈNH TARGET
# ==========================================
with st.sidebar:
    st.header("⚙️ Cài đặt Hạn mức")
    st.markdown("Kéo hoặc nhập số tiền tối đa bạn muốn chi tiêu cho tháng này:")
    for hm in st.session_state.targets.keys():
        st.session_state.targets[hm] = st.number_input(
            f"🎯 {hm} (VNĐ)", min_value=0, value=st.session_state.targets[hm], step=100000
        )
    st.divider()
    st.info("💡 Thay đổi ở đây sẽ tự động cập nhật ngay vào bảng Cảnh báo bên ngoài.")

# --- LẤY DỮ LIỆU TỪ MÂY ---
@st.cache_data(ttl=1) 
def load_data():
    response = supabase.table("chi_tieu").select("*").execute()
    return response.data

data = load_data()

# --- TÍNH TOÁN CÁC CON SỐ CHÍNH ---
tong_thu = sum(item['so_tien'] for item in data if item.get('loai_giao_dich') == 'Thu nhập')
tong_chi = sum(item['so_tien'] for item in data if item.get('loai_giao_dich') == 'Chi tiêu')
con_lai = tong_thu - tong_chi

chi_thang_nay = 0
chi_thang_truoc = 0
thang_hien_tai = ""
thang_truoc = ""
df_chi = pd.DataFrame()

if data:
    df_tam = pd.DataFrame(data)
    if 'created_at' in df_tam.columns:
        now = datetime.now(pytz.timezone('Asia/Ho_Chi_Minh'))
        thang_hien_tai = now.strftime('%m/%Y')
        
        if now.month == 1:
            thang_truoc = f"12/{now.year - 1}"
        else:
            thang_truoc = f"{now.month - 1:02d}/{now.year}"
            
        df_tam['Tháng'] = pd.to_datetime(df_tam['created_at'], utc=True).dt.tz_convert('Asia/Ho_Chi_Minh').dt.strftime('%m/%Y')
        df_chi = df_tam[df_tam['loai_giao_dich'] == 'Chi tiêu']
        
        chi_thang_nay = int(df_chi[df_chi['Tháng'] == thang_hien_tai]['so_tien'].sum())
        chi_thang_truoc = int(df_chi[df_chi['Tháng'] == thang_truoc]['so_tien'].sum())

# ==========================================
# GIAO DIỆN CHÍNH (FULL TRANG - KHÔNG DÙNG TAB)
# ==========================================
st.title("📊 Quản Lý Tài Chính Cá Nhân")

# --- 1. HIỂN THỊ THẺ THỐNG KÊ ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Tổng Thu Nhập", f"{tong_thu:,} đ")
col2.metric("Chi Tháng Trước", f"{chi_thang_truoc:,} đ") 

chenh_lech_tong = chi_thang_nay - chi_thang_truoc
col3.metric("Chi Tháng Này", f"{chi_thang_nay:,} đ", delta=f"{chenh_lech_tong:,} đ", delta_color="inverse") 
col4.metric("Còn Lại", f"{con_lai:,} đ", delta=con_lai)

st.markdown("---")

# --- 2. KẾT LUẬN SO SÁNH NHANH ---
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

st.container(height=20, border=False) # Tạo khoảng trống cho thoáng

# --- 3. KHU VỰC NHẬP LIỆU & LỊCH SỬ ---
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
        st.dataframe(df_hien_thi, use_container_width=True, hide_index=True, height=350)

st.markdown("---")

# --- 4. BẢNG SO SÁNH ĐỐI CHIẾU CHI TIẾT ---
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
        chenh = nay - truoc
        
        if chenh < 0:
            danh_gia = "🟢 Tiết kiệm"
        elif chenh > 0:
            danh_gia = "🔴 Tiêu lố"
        else:
            danh_gia = "⚪ Bằng nhau"
            
        bang_so_sanh.append({
            "Hạng mục": hm,
            "Tháng Trước": f"{truoc:,} đ",
            "Tháng Này": f"{nay:,} đ",
            "Chênh Lệch": f"{chenh:,} đ" if chenh <= 0 else f"+{chenh:,} đ",
            "Đánh Giá": danh_gia,
            "_sort_val": chenh # Cột ẩn dùng để sắp xếp
        })
    
    if bang_so_sanh:
        df_bang = pd.DataFrame(bang_so_sanh)
        # Sắp xếp để những mục tiêu lố nhiều nhất nổi lên trên cùng
        df_bang = df_bang.sort_values(by="_sort_val", ascending=False).drop(columns=["_sort_val"])
        
        st.dataframe(df_bang, use_container_width=True, hide_index=True)

st.markdown("---")

# --- 5. CẢNH BÁO TARGET & BIỂU ĐỒ ---
st.subheader("🎯 Theo dõi Hạn mức & Xu hướng")
if not df_chi.empty:
    c_trai, c_phai = st.columns([1, 1])
    
    # Bên trái: Danh sách cảnh báo Target
    with c_trai:
        for hang_muc, target in st.session_state.targets.items():
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
                    
    # Bên phải: Biểu đồ cột tổng quan các tháng
    with c_phai:
        st.markdown("**Biểu đồ Tổng chi tiêu các tháng**")
        chi_theo_thang = df_chi.groupby('Tháng')['so_tien'].sum().reset_index()
        st.bar_chart(data=chi_theo_thang.set_index('Tháng'), y='so_tien', color="#38A896")
