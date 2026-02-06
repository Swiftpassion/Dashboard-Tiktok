import streamlit as st
import pandas as pd
import plotly.express as px
import re
from supabase import create_client, Client

# ==========================================
# 1. ตั้งค่าหน้าเว็บ & CSS (TH Sarabun)
# ==========================================
st.set_page_config(page_title="Dashboard สรุปยอดขาย", layout="wide")

# ฝัง CSS เพื่อเปลี่ยนฟอนต์เป็น Sarabun และปรับแต่ง UI
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Sarabun', sans-serif;
    }
    
    /* ปรับขนาด Header ให้สวยงาม */
    h1, h2, h3 {
        color: #2E4053;
        font-weight: 700;
    }
    
    /* ปรับแต่งตาราง */
    div[data-testid="stDataFrame"] {
        width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. เชื่อมต่อ Supabase
# ==========================================
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"⚠️ เชื่อมต่อ Supabase ไม่สำเร็จ: {e}")
        st.stop()

# ==========================================
# 3. ฟังก์ชันดึงข้อมูล (Load Data)
# ==========================================
@st.cache_data(ttl=300) 
def load_data():
    supabase = init_connection()
    try:
        # ดึงข้อมูล (เน้นชื่อ Column แบบตัวใหญ่ตาม CSV)
        response = supabase.table('orders').select(
            '"Shipped Time", "Warehouse Name", "Seller SKU", "Product Name", "Quantity"'
        ).execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"❌ Error Loading Data: {e}")
        return pd.DataFrame()

# ==========================================
# 4. Logic แปลงข้อมูล
# ==========================================
def map_warehouse(name):
    if not name: return "Unknown"
    name = str(name).strip()
    mapping = { "Simmobile": "SIM 1", "Namkangmobile": "SIM 2", "Thailand Pickup Warehouse": "NAMKANG" }
    return mapping.get(name, name)

def get_tag(product_name):
    if not product_name: return "BCD"
    name = str(product_name).strip()
    if name.endswith("./"): return "CPL"
    elif name.endswith("."): return "CP"
    elif name.endswith("/"): return "BCDL"
    elif name.endswith("_"): return "BCD"
    else: return "BCD"

def clean_sku_name(sku):
    if not sku: return "Unknown"
    sku = str(sku).lower()
    sku = sku.replace("สีเงิน", "silver").replace("สีเทา", "gray")
    sku = re.sub(r'\b(gb|ram|rom)\b', '', sku)
    sku = re.sub(r'\s+', ' ', sku).strip()
    return sku

# ==========================================
# 5. ส่วนแสดงผล (Main UI)
# ==========================================

# โหลดข้อมูล
df = load_data()

if not df.empty:
    # --- Processing ---
    if 'Shipped Time' in df.columns:
        df['Shipped Time'] = df['Shipped Time'].astype(str).str.replace(r'\t', '', regex=True).str.strip()
        df['Date_Obj'] = pd.to_datetime(df['Shipped Time'], dayfirst=True, errors='coerce')
        df['Date'] = df['Date_Obj'].dt.date

    df['Shop'] = df['Warehouse Name'].apply(map_warehouse)
    df['Tag'] = df['Product Name'].apply(get_tag)
    df['Clean_SKU'] = df['Seller SKU'].apply(clean_sku_name)

    # ==========================================
    # LAYOUT: ROW 1 (Date | Shop | Table)
    # ==========================================
    
    # แบ่งคอลัมน์: ซ้าย(1) | กลาง(1) | ขวา(2)
    col1, col2, col3 = st.columns([1, 1, 2], gap="medium")

    with col1:
        st.markdown("### 📅 วันที่ต้องการแสดงผล")
        valid_dates = df['Date'].dropna().sort_values()
        if not valid_dates.empty:
            default_start = valid_dates.iloc[0]
            default_end = valid_dates.iloc[-1]
            # ใช้ Date Input แบบ Range
            date_range = st.date_input("เลือกช่วงวันที่", [default_start, default_end])
            if len(date_range) == 2:
                start_date, end_date = date_range
            else:
                start_date, end_date = default_start, default_end
        else:
            st.error("ไม่พบวันที่")
            start_date, end_date = None, None

    with col2:
        st.markdown("### 🏪 เลือกร้านค้า")
        all_shops = sorted(df['Shop'].unique())
        # ใช้ Multiselect ให้ดูเหมือนปุ่ม (หรือใช้ st.pills ในอนาคตถ้าอัปเดต)
        selected_shops = st.multiselect("เลือกร้านค้า", all_shops, default=all_shops)

    # --- Filter Logic ---
    mask = df['Shop'].isin(selected_shops)
    if start_date and end_date:
        mask = mask & (df['Date'] >= start_date) & (df['Date'] <= end_date)
    filtered_df = df.loc[mask]

    with col3:
        st.markdown("### 🏆 สรุปสินค้าขายดี")
        if not filtered_df.empty:
            # รวมยอดขายตาม Clean SKU
            top_products = (
                filtered_df.groupby(['Clean_SKU'])['Quantity']
                .sum().reset_index()
                .sort_values(by='Quantity', ascending=False)
                .head(5) # เอาแค่ Top 5 จะได้ไม่ล้นจอ
            )
            st.dataframe(
                top_products, 
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Clean_SKU": "ชื่อสินค้า",
                    "Quantity": st.column_config.NumberColumn("จำนวน", format="%d ชิ้น")
                }
            )
        else:
            st.info("ไม่มีข้อมูล")

    st.markdown("---") # เส้นขีดคั่น

    # ==========================================
    # LAYOUT: ROW 2 (ชื่อสินค้า | กราฟแนวนอน)
    # ==========================================
    
    row2_col1, row2_col2 = st.columns([1, 3])

    with row2_col1:
        # สรุป KPI ใหญ่ๆ
        total_sales = filtered_df['Quantity'].sum()
        st.markdown(f"""
        <div style="background-color:#F2F3F4; padding: 20px; border-radius: 10px; text-align: center;">
            <h3 style="margin:0; color:#5D6D7E;">ยอดขายรวม</h3>
            <h1 style="font-size: 60px; color:#2E86C1; margin:0;">{total_sales:,}</h1>
            <p style="margin:0;">ชิ้น</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("#### รายการสินค้าที่กรอง:")
        st.caption(f"📅 {start_date} ถึง {end_date}")
        st.caption(f"🏪 {', '.join(selected_shops)}")

    with row2_col2:
        if not filtered_df.empty:
            # เตรียมข้อมูลกราฟ
            chart_data = filtered_df.groupby(['Shop', 'Tag'])['Quantity'].sum().reset_index()
            
            # กราฟแนวนอน (orientation='h')
            fig = px.bar(
                chart_data, 
                x="Quantity",     # แกน X เป็นตัวเลข
                y="Shop",         # แกน Y เป็นชื่อร้าน
                color="Tag", 
                orientation='h',  # <--- ทำให้เป็นแนวนอน
                text_auto=True, 
                title="📊 กราฟสรุปยอดขาย (แนวนอน)",
                color_discrete_sequence=px.colors.qualitative.Pastel,
                height=400
            )
            # ปรับแต่งกราฟให้สวยขึ้น
            fig.update_layout(
                font_family="Sarabun",
                xaxis_title="จำนวนที่ขายได้ (ชิ้น)",
                yaxis_title="ร้านค้า",
                legend_title="หมวดหมู่ (Tag)"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("ไม่มีข้อมูลสำหรับแสดงกราฟ")

else:
    st.warning("กำลังรอข้อมูล... หรือ Database ว่างเปล่า")