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

# --- ĐOẠN CODE LÀM TÀNG HÌNH GIAO DIỆN STREAMLIT ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .stAppDeployButton {display:none;}
            [class^="viewerBadge_"] {display: none !important;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)
# ----------------------------------------------------

# ==========================================
# 1. XỬ LÝ DỮ LIỆU
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
    df_targets = df_raw[df_raw['loai_giao_dich'] == 'Cài đặt Target']
    if not df_targets.empty:
        df_targets = df_targets.sort_values('created_at', ascending=False).drop_duplicates(subset=['hang_muc'])
        for _, row in df_targets.iterrows():
            if row['hang_muc'] in current_targets:
                current_targets[row['hang_muc']] = int(row['so_tien'])
    
    df_tam = df_raw[df_raw['loai_giao_dich'] != 'Cài đặt Target'].copy()
    if 'created_at' in df_tam.columns:
        df_tam['Thời gian thực'] = pd.to_datetime(df_tam['created_at'], utc=True).dt.tz_convert('Asia/Ho_Chi_Minh')
        df_tam['Tháng'] = df_tam['Thời gian thực'].dt.strftime('%m/%Y')

# ==========================================
# 2. GIAO DIỆN VÀ TÍNH TOÁN
# ==========================================
with st.sidebar:
    st.header("👥 Bộ Lọc")
    view_option = st.radio("Xem dữ liệu của:", ["Cả hai (Tổng)", "Vợ", "Chồng"], index=0)
    st.divider()
    st.header("⚙️ Cài đặt Hạn mức")
    with st.form("form_target"):
        new_targets = {}
        for hm, val in current_targets.items():
            new_targets[hm] = st.number_input(f"🎯 {hm}", min_value=0, value=val, step=100000)
        if st.form_submit_button("💾 Lưu Target", type="primary"):
            for hm, val in new_targets.items():
                if val != current_targets[hm]:
                    supabase.table("chi_tieu").insert({"loai_giao_dich": "Cài đặt Target", "hang_muc": hm, "so_tien": val, "noi_dung": "System"}).execute()
            st.rerun()

df_display = df_tam.copy()
if not df_display.empty and view_option != "Cả hai (Tổng)":
    if 'noi_dung' in df_display.columns:
        df_display = df_display[df_display['noi_dung'] == view_option]

t_thu = int(df_display[df_display['loai_giao_dich'] == 'Thu nhập']['so_tien'].sum()) if not df_display.empty else 0
t_chi = int(df_display[df_display['loai_giao_dich'] == 'Chi tiêu']['so_tien'].sum()) if not df_display.empty else 0
c_lai = t_thu - t_chi

# --- MAIN UI ---
st.title(f"📊 Sổ Thu Chi - {view_option}")
c1, c2, c3 = st.columns(3)
c1.metric("Thu Nhập", f"{t_thu:,} đ")
c2.metric("Chi Tiêu", f"{t_chi:,} đ")
c3.metric("Số Dư", f"{c_lai:,} đ")

st.divider()
st.subheader("📝 Ghi chép mới")
with st.form("form_nhap", clear_on_submit=True):
    col_a, col_b, col_c = st.columns(3)
    nguoi = col_a.selectbox("Người thực hiện", ["Vợ", "Chồng"])
    loai = col_a.selectbox("Loại", ["Chi tiêu", "Thu nhập"])
    hmuc = col_b.selectbox("Hạng mục", ["Ăn uống", "Đi lại", "Mua sắm", "Lương", "Tiền phòng", "Khác"])
    stien = col_b.number_input("Số tiền", min_value=0, step=10000)
    gchu = col_c.text_input("Ghi chú thêm")
    if st.form_submit_button("💾 LƯU", type="primary", use_container_width=True):
        if stien > 0:
            supabase.table("chi_tieu").insert({
                "loai_giao_dich": loai, "hang_muc": hmuc, "so_tien": stien, 
                "noi_dung": nguoi, "ghi_chu_them": gchu 
            }).execute()
            st.rerun()

st.divider()
st.subheader("⚖️ Lịch sử")
if not df_display.empty:
    df_hien = df_display.copy()
    df_hien['Thời gian'] = df_hien['Thời gian thực'].dt.strftime('%H:%M - %d/%m/%Y')
    if 'ghi_chu_them' not in df_hien.columns: df_hien['ghi_chu_them'] = ""
    df_hien = df_hien.rename(columns={'loai_giao_dich': 'Loại', 'hang_muc': 'Hạng mục', 'so_tien': 'Tiền (đ)', 'noi_dung': 'Người nhập', 'ghi_chu_them': 'Ghi chú'})
    st.dataframe(df_hien[['Thời gian', 'Người nhập', 'Loại', 'Hạng mục', 'Tiền (đ)', 'Ghi chú']].iloc[::-1], use_container_width=True, hide_index=True)
