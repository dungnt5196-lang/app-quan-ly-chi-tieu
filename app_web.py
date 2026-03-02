import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import pytz

# --- KẾT NỐI DATABASE SUPABASE ---
SUPABASE_URL = "https://kjzywvulfspgogobdaoe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imtqenl3dnVsZnNwZ29nb2JkYW9lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIyNjcwMTksImV4cCI6MjA4Nzg0MzAxOX0.dtF4tP7em8gJOYO85v5-z8GaYPZFhuUCfmNw8YOVgT4"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Sổ Thu Chi Gia Đình", page_icon="👨‍👩‍👧‍👦", layout="wide")

# ==========================================
# 1. XỬ LÝ DỮ LIỆU & ĐỒNG BỘ TARGET
# ==========================================
DEFAULT_TARGETS = {"Ăn uống": 4000000, "Tiền phòng": 3000000, "Đi lại": 800000, "Mua sắm": 1500000, "Khác": 1000000}

@st.cache_data(ttl=1) 
def load_data():
    response = supabase.table("chi_tieu").select("*").execute()
    return response.data

data = load_data()
df_raw = pd.DataFrame(data) if data else pd.DataFrame()

current_targets = DEFAULT_TARGETS.copy()
df_tam = pd.DataFrame()

if not df_raw.empty:
    # Đồng bộ Target từ mây
    df_targets = df_raw[df_raw['loai_giao_dich'] == 'Cài đặt Target']
    if not df_targets.empty:
        df_targets = df_targets.sort_values('created_at', ascending=False).drop_duplicates(subset=['hang_muc'])
        for _, row in df_targets.iterrows():
            if row['hang_muc'] in current_targets:
                current_targets[row['hang_muc']] = int(row['so_tien'])
    
    # Lấy dữ liệu Thu/Chi thực tế (Bỏ qua các dòng Cài đặt)
    df_tam = df_raw[df_raw['loai_giao_dich'] != 'Cài đặt Target'].copy()
    if 'created_at' in df_tam.columns:
        df_tam['Thời gian thực'] = pd.to_datetime(df_tam['created_at'], utc=True).dt.tz_convert('Asia/Ho_Chi_Minh')
        df_tam['Tháng'] = df_tam['Thời gian thực'].dt.strftime('%m/%Y')

# ==========================================
# 2. THANH SIDEBAR: CÀI ĐẶT & BỘ LỌC
# ==========================================
with st.sidebar:
    st.header("👥 Bộ Lọc Gia Đình")
    view_option = st.radio("Xem dữ liệu của:", ["Cả hai (Tổng)", "Vợ", "Chồng"], index=0)
    
    st.divider()
    st.header("⚙️ Cài đặt Hạn mức")
    with st.form("form_target"):
        new_targets = {}
        for hm, val in current_targets.items():
            new_targets[hm] = st.number_input(f"🎯 {hm}", min_value=0, value=val, step=100000)
        if st.form_submit_button("💾 Lưu Đồng Bộ Target", type="primary"):
            for hm, val in new_targets.items():
                if val != current_targets[hm]:
                    supabase.table("chi_tieu").insert({"loai_giao_dich": "Cài đặt Target", "hang_muc": hm, "so_tien": val, "noi_dung": "System"}).execute()
            st.rerun()

# Lọc dữ liệu hiển thị dựa trên bộ lọc Sidebar
df_display = df_tam.copy()
if not df_display.empty and view_option != "Cả hai (Tổng)":
    if 'noi_dung' in df_display.columns:
        df_display = df_display[df_display['noi_dung'] == view_option]

# ==========================================
# 3. TÍNH TOÁN CÁC CON SỐ (THEO BỘ LỌC)
# ==========================================
t_thu = int(df_display[df_display['loai_giao_dich'] == 'Thu nhập']['so_tien'].sum()) if not df_display.empty else 0
t_chi = int(df_display[df_display['loai_giao_dich'] == 'Chi tiêu']['so_tien'].sum()) if not df_display.empty else 0
c_lai = t_thu - t_chi

c_nay = 0
c_truoc = 0
if not df_display.empty:
    now = datetime.now(pytz.timezone('Asia/Ho_Chi_Minh'))
    m_nay = now.strftime('%m/%Y')
    m_truoc = (now.replace(day=1) - pd.Timedelta(days=1)).strftime('%m/%Y')
    
    df_chi_filter = df_display[df_display['loai_giao_dich'] == 'Chi tiêu']
    c_nay = int(df_chi_filter[df_chi_filter['Tháng'] == m_nay]['so_tien'].sum())
    c_truoc = int(df_chi_filter[df_chi_filter['Tháng'] == m_truoc]['so_tien'].sum())

# ==========================================
# 4. GIAO DIỆN CHÍNH
# ==========================================
st.title(f"📊 Sổ Thu Chi - {view_option}")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Thu Nhập", f"{t_thu:,} đ")
col2.metric("Chi Tháng Trước", f"{c_truoc:,} đ")
diff = c_nay - c_truoc
col3.metric("Chi Tháng Này", f"{c_nay:,} đ", delta=f"{diff:,} đ", delta_color="inverse")
col4.metric("Số Dư Ví", f"{c_lai:,} đ", delta=c_lai)

st.divider()

# --- KHU VỰC NHẬP LIỆU ---
st.subheader("📝 Ghi chép mới")
with st.form("form_nhap", clear_on_submit=True):
    c_nhap1, c_nhap2, c_nhap3 = st.columns(3)
    with c_nhap1:
        nguoi_nhap = st.selectbox("Người thực hiện", ["Vợ", "Chồng"])
        loai_gd = st.selectbox("Loại", ["Chi tiêu", "Thu nhập"])
    with c_nhap2:
        h_muc = st.selectbox("Hạng mục", ["Ăn uống", "Đi lại", "Mua sắm", "Lương", "Tiền phòng", "Khác"])
        tien = st.number_input("Số tiền (VNĐ)", min_value=0, step=50000)
    with c_nhap3:
        ghi_chu = st.text_input("Ghi chú thêm")
        st.write("") # Tạo khoảng trống
        if st.form_submit_button("💾 LƯU GIAO DỊCH", type="primary", use_container_width=True):
            if tien > 0:
                # CẬP NHẬT: Thêm cột ghi_chu_them vào lệnh lưu
                supabase.table("chi_tieu").insert({
                    "loai_giao_dich": loai_gd, 
                    "hang_muc": h_muc, 
                    "so_tien": tien, 
                    "noi_dung": nguoi_nhap,
                    "ghi_chu_them": ghi_chu 
                }).execute()
                st.success(f"Đã lưu khoản {loai_gd} của {nguoi_nhap}!")
                st.rerun()

st.divider()

# --- LỊCH SỬ & ĐỐI CHIẾU ---
st.subheader(f"⚖️ Đối Chiếu Chi Tiết - {view_option}")
if not df_display.empty:
    df_hien = df_display.copy()
    df_hien['Thời gian'] = df_hien['Thời gian thực'].dt.strftime('%H:%M - %d/%m/%Y')
    
    # CẬP NHẬT: Xử lý an toàn nếu database chưa có cột ghi_chu_them ở các giao dịch cũ
    if 'ghi_chu_them' not in df_hien.columns:
        df_hien['ghi_chu_them'] = ""
        
    df_hien = df_hien.rename(columns={
        'loai_giao_dich': 'Loại', 
        'hang_muc': 'Hạng mục', 
        'so_tien': 'Tiền (đ)', 
        'noi_dung': 'Người nhập',
        'ghi_chu_them': 'Ghi chú' # Đổi tên hiển thị cho đẹp
    })
    
    # Bảng so sánh hàng cột (Chỉ dành cho Chi tiêu)
    df_chi_view = df_display[df_display['loai_giao_dich'] == 'Chi tiêu']
    if not df_chi_view.empty:
        c_nay_dict = df_chi_view[df_chi_view['Tháng'] == m_nay].groupby('hang_muc')['so_tien'].sum().to_dict()
        c_truoc_dict = df_chi_view[df_chi_view['Tháng'] == m_truoc].groupby('hang_muc')['so_tien'].sum().to_dict()
        
        comp = []
        for hm in set(list(c_nay_dict.keys()) + list(c_truoc_dict.keys())):
            n, t = c_nay_dict.get(hm, 0), c_truoc_dict.get(hm, 0)
            d = n - t
            comp.append({"Hạng mục": hm, "Tháng Trước": f"{t:,} đ", "Tháng Này": f"{n:,} đ", "Chênh lệch": f"+{d:,} đ" if d > 0 else f"{d:,} đ", "Đánh giá": "🔴 Tăng" if d > 0 else "🟢 Giảm"})
        st.dataframe(pd.DataFrame(comp), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.write("**Lịch sử giao dịch gần đây:**")
    # CẬP NHẬT: Thêm 'Ghi chú' vào danh sách hiển thị
    st.dataframe(df_hien[['Thời gian', 'Người nhập', 'Loại', 'Hạng mục', 'Tiền (đ)', 'Ghi chú']].iloc[::-1], use_container_width=True, hide_index=True, height=300)

# --- BIỂU ĐỒ TỔNG QUAN (LUÔN HIỆN TỔNG GIA ĐÌNH) ---
st.divider()
st.subheader("📊 Phân tích Tổng Gia Đình (Cả hai)")
if not df_tam.empty:
    c_bi_1, c_bi_2 = st.columns(2)
    with c_bi_1:
        st.write("Chi tiêu theo người nhập:")
        df_nguoi = df_tam[df_tam['loai_giao_dich'] == 'Chi tiêu'].groupby('noi_dung')['so_tien'].sum().reset_index()
        st.bar_chart(data=df_nguoi.set_index('noi_dung'), y='so_tien')
    with c_bi_2:
        st.write("Xu hướng chi tiêu gia đình:")
        df_trend = df_tam[df_tam['loai_giao_dich'] == 'Chi tiêu'].groupby('Tháng')['so_tien'].sum().reset_index()
        st.line_chart(data=df_trend.set_index('Tháng'), y='so_tien')
