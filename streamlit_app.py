import streamlit as st
import pandas as pd
import plotly.express as px
import re
from supabase import create_client, Client

# ==========================================
# 1. ตั้งค่าหน้าเว็บ (บรรทัดแรกสุด ห้ามมี @)
# ==========================================
st.set_page_config(page_title="Dashboard สรุปยอดขาย", layout="wide")

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
@st.cache_data(ttl=300) # เก็บ Cache 5 นาที
def load_data():
    supabase = init_connection()
    
    # ดึงข้อมูลโดยระบุชื่อคอลัมน์แบบ "ตัวใหญ่มีเว้นวรรค" (ตามที่ Debug เจอ)
    try:
        response = supabase.table('orders').select(
            '"Shipped Time", "Warehouse Name", "Seller SKU", "Product Name", "Quantity"'
        ).execute()
        
        df = pd.DataFrame(response.data)
        return df
        
    except Exception as e:
        st.error(f"❌ ดึงข้อมูลผิดพลาด: {e}")
        return pd.DataFrame()

# ==========================================
# 4. Logic การแปลงข้อมูล (Business Logic)
# ==========================================
def map_warehouse(name):
    if not name: return "Unknown"
    name = str(name).strip()
    mapping = {
        "Simmobile": "SIM 1",
        "Namkangmobile": "SIM 2",
        "Thailand Pickup Warehouse": "NAMKANG"
    }
    return mapping.get(name, name)

def get_tag(product_name):
    if not product_name: return "BCD"
    name = str(product_name).strip()
    # เช็คเงื่อนไข Suffix
    if name.endswith("./"): return "CPL"
    elif name.endswith("."): return "CP"
    elif name.endswith("/"): return "BCDL"
    elif name.endswith("_"): return "BCD"
    else: return "BCD"

def clean_sku_name(sku):
    if not sku: return "Unknown"
    sku = str(sku).lower()
    # 1. แปลงสี ไทย -> อังกฤษ
    sku = sku.replace("สีเงิน", "silver").replace("สีเทา", "gray")
    # 2. ลบคำขยายที่ไม่จำเป็น
    sku = re.sub(r'\b(gb|ram|rom)\b', '', sku)
    # 3. จัดระเบียบช่องว่าง
    sku = re.sub(r'\s+', ' ', sku).strip()
    return sku

# ==========================================
# 5. ส่วนแสดงผลหน้าเว็บ (Main App)
# ==========================================
st.title("📊 Dashboard สรุปยอดขาย (Supabase Real-time)")

# โหลดข้อมูล
with st.spinner('กำลังดึงข้อมูลล่าสุด...'):
    df = load_data()

if not df.empty:
    try:
        # --- Data Cleaning ---
        # 1. จัดการวันที่ (ลบ \t ที่ติดมา และแปลงเป็น Date)
        if 'Shipped Time' in df.columns:
            # ลบ Tab และช่องว่าง
            df['Shipped Time'] = df['Shipped Time'].astype(str).str.replace(r'\t', '', regex=True).str.strip()
            # แปลงเป็น DateTime
            df['Date_Obj'] = pd.to_datetime(df['Shipped Time'], dayfirst=True, errors='coerce')
            df['Date'] = df['Date_Obj'].dt.date
        
        # 2. สร้างคอลัมน์ใหม่ (Shop, Tag, Clean_SKU)
        df['Shop'] = df['Warehouse Name'].apply(map_warehouse)
        df['Tag'] = df['Product Name'].apply(get_tag)
        df['Clean_SKU'] = df['Seller SKU'].apply(clean_sku_name)

        # --- Sidebar Filters ---
        st.sidebar.header("🔍 ตัวกรองข้อมูล")
        
        # กรองวันที่
        valid_dates = df['Date'].dropna().sort_values()
        if not valid_dates.empty:
            min_d, max_d = valid_dates.iloc[0], valid_dates.iloc[-1]
            start_date, end_date = st.sidebar.date_input("เลือกช่วงวันที่", [min_d, max_d])
        else:
            # กรณีไม่มีวันที่ที่ถูกต้องเลย (เช่น ข้อมูลดิบผิดพลาด)
            st.warning("⚠️ ไม่พบข้อมูลวันที่ที่ถูกต้อง แสดงข้อมูลทั้งหมดแทน")
            start_date, end_date = None, None

        # กรองร้านค้า
        all_shops = sorted(df['Shop'].unique())
        selected_shops = st.sidebar.multiselect("เลือกร้านค้า", all_shops, default=all_shops)

        # Apply Filters
        mask = df['Shop'].isin(selected_shops)
        if start_date and end_date:
            mask = mask & (df['Date'] >= start_date) & (df['Date'] <= end_date)
            
        filtered_df = df.loc[mask]

        # --- Display KPIs ---
        st.markdown("---")
        kpi1, kpi2, kpi3 = st.columns(3)
        
        total_sales = filtered_df['Quantity'].sum()
        total_orders = len(filtered_df)
        
        kpi1.metric("📦 ยอดขายรวม (ชิ้น)", f"{total_sales:,}")
        kpi2.metric("📝 จำนวนออเดอร์", f"{total_orders:,}")
        kpi3.metric("📅 ช่วงข้อมูล", f"{start_date} - {end_date}" if start_date else "ทั้งหมด")

        # --- Charts ---
        col_chart1, col_chart2 = st.columns([2, 1])
        
        with col_chart1:
            st.subheader("📈 ยอดขายแยกตาม Tag และ ร้านค้า")
            if not filtered_df.empty:
                chart_data = filtered_df.groupby(['Shop', 'Tag'])['Quantity'].sum().reset_index()
                fig = px.bar(
                    chart_data, 
                    x="Shop", y="Quantity", color="Tag", 
                    text_auto=True, barmode='group', height=400,
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("ไม่มีข้อมูลตามเงื่อนไขที่เลือก")

        with col_chart2:
            st.subheader("🍰 สัดส่วน Tag")
            if not filtered_df.empty:
                pie_data = filtered_df.groupby('Tag')['Quantity'].sum().reset_index()
                fig_pie = px.pie(pie_data, values='Quantity', names='Tag', hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)

        # --- Table ---
        st.subheader("🏆 สินค้าขายดี (Top Products)")
        if not filtered_df.empty:
            top_products = (
                filtered_df.groupby(['Clean_SKU', 'Tag', 'Shop'])['Quantity']
                .sum().reset_index()
                .sort_values(by='Quantity', ascending=False)
                .head(10)
            )
            st.dataframe(
                top_products, 
                use_container_width=True,
                column_config={
                    "Clean_SKU": "ชื่อสินค้า",
                    "Quantity": st.column_config.NumberColumn("ยอดขาย", format="%d")
                }
            )

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการประมวลผลกราฟ: {e}")
else:
    st.warning("📭 ไม่พบข้อมูลใน Database")