import streamlit as st
import pandas as pd
import plotly.express as px
import re
from supabase import create_client, Client

# ==========================================
# 1. ตั้งค่าหน้าเว็บ (ต้องเป็นบรรทัดแรกของ st และไม่มี @)
# ==========================================
st.set_page_config(page_title="Dashboard สรุปยอดขาย", layout="wide")

# ==========================================
# 2. เชื่อมต่อ Supabase
# ==========================================
@st.cache_resource
def init_connection():
    # ดึง Key จาก Secrets ของ Streamlit
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

# ==========================================
# 2. ฟังก์ชันดึงข้อมูล (Load Data)
# ==========================================
@st.cache_data(ttl=300) # จำข้อมูลไว้ 5 นาที
def load_data():
    supabase = init_connection()
    
    # ดึงคอลัมน์ที่จำเป็น (ใช้ "" ครอบชื่อที่มีเว้นวรรค)
    # ถ้าชื่อใน Supabase เป็นตัวเล็กหมด ให้แก้ตรงนี้เป็นตัวเล็กครับ
    try:
        response = supabase.table('orders').select(
            '"Shipped Time", "Warehouse Name", "Seller SKU", "Product Name", "Quantity"'
        ).execute()
        df = pd.DataFrame(response.data)
    except:
        # กรณี Supabase แปลงชื่อเป็นตัวเล็กอัตโนมัติ (Fallback)
        response = supabase.table('orders').select(
            'shipped_time, warehouse_name, seller_sku, product_name, quantity'
        ).execute()
        df = pd.DataFrame(response.data)
        # เปลี่ยนชื่อกลับให้ตรงกับ Logic
        df.rename(columns={
            'shipped_time': 'Shipped Time',
            'warehouse_name': 'Warehouse Name',
            'seller_sku': 'Seller SKU',
            'product_name': 'Product Name',
            'quantity': 'Quantity'
        }, inplace=True)
        
    return df

# ==========================================
# 3. Logic การแปลงข้อมูล (Business Logic)
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
    # เช็คเงื่อนไข Tag ตามลำดับ
    if name.endswith("./"): return "CPL"
    elif name.endswith("."): return "CP"
    elif name.endswith("/"): return "BCDL"
    elif name.endswith("_"): return "BCD"
    else: return "BCD"

def clean_sku_name(sku):
    if not sku: return "Unknown"
    sku = str(sku).lower() # แปลงเป็นตัวพิมพ์เล็ก
    
    # 1. แปลงคำไทย -> อังกฤษ
    sku = sku.replace("สีเงิน", "silver").replace("สีเทา", "gray")
    
    # 2. ลบคำที่ไม่ต้องการ (GB, RAM, ROM)
    sku = re.sub(r'\b(gb|ram|rom)\b', '', sku)
    
    # 3. จัดระเบียบช่องว่าง
    sku = re.sub(r'\s+', ' ', sku).strip()
    
    return sku

# ==========================================
# 4. ส่วนแสดงผลหน้าเว็บ (UI & Visualization)
# ==========================================
st.title("📊 Dashboard สรุปยอดขาย (Supabase Version)")

try:
    with st.spinner('กำลังดึงข้อมูลจาก Database...'):
        df = load_data()

    if not df.empty:
        # --- Data Cleaning ---
        # 1. ลบอักขระแปลกปลอมออกจากวันที่ (\t) และแปลงเป็น Date
        if 'Shipped Time' in df.columns:
            df['Shipped Time'] = df['Shipped Time'].astype(str).str.replace(r'\t', '', regex=True).str.strip()
            df['Date_Obj'] = pd.to_datetime(df['Shipped Time'], dayfirst=True, errors='coerce')
            df['Date'] = df['Date_Obj'].dt.date
        
        # 2. สร้าง Column ใหม่
        df['Shop'] = df['Warehouse Name'].apply(map_warehouse)
        df['Tag'] = df['Product Name'].apply(get_tag)
        df['Clean_SKU'] = df['Seller SKU'].apply(clean_sku_name)

        # --- Filter Sidebar ---
        st.sidebar.header("🔍 ตัวกรองข้อมูล")
        
        # Filter วันที่
        valid_dates = df['Date'].dropna().sort_values()
        if not valid_dates.empty:
            min_date, max_date = valid_dates.iloc[0], valid_dates.iloc[-1]
            start_date, end_date = st.sidebar.date_input("ช่วงวันที่", [min_date, max_date])
        else:
            st.error("ไม่พบข้อมูลวันที่ที่ถูกต้อง")
            st.stop()
            
        # Filter ร้านค้า
        all_shops = sorted(df['Shop'].unique().tolist())
        selected_shops = st.sidebar.multiselect("เลือกร้านค้า", all_shops, default=all_shops)

        # Apply Filters
        mask = (df['Date'] >= start_date) & (df['Date'] <= end_date) & (df['Shop'].isin(selected_shops))
        filtered_df = df.loc[mask]

        # --- Display KPIs ---
        st.markdown("---")
        kpi1, kpi2, kpi3 = st.columns(3)
        total_sales = filtered_df['Quantity'].sum()
        total_orders = len(filtered_df)
        
        kpi1.metric("📦 ยอดขายรวม (ชิ้น)", f"{total_sales:,}")
        kpi2.metric("📝 จำนวนออเดอร์", f"{total_orders:,}")
        kpi3.metric("📅 ข้อมูลวันที่", f"{start_date} - {end_date}")

        # --- Charts ---
        col_chart1, col_chart2 = st.columns([2, 1])
        
        with col_chart1:
            st.subheader("📈 ยอดขายแยกตาม Tag และ ร้านค้า")
            chart_data = filtered_df.groupby(['Shop', 'Tag'])['Quantity'].sum().reset_index()
            fig = px.bar(
                chart_data, 
                x="Shop", 
                y="Quantity", 
                color="Tag", 
                text_auto=True,
                barmode='group',
                height=400,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            st.plotly_chart(fig, use_container_width=True)
            
        with col_chart2:
            st.subheader("🍰 สัดส่วน Tag")
            pie_data = filtered_df.groupby('Tag')['Quantity'].sum().reset_index()
            fig_pie = px.pie(pie_data, values='Quantity', names='Tag', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)

        # --- Top Products Table ---
        st.subheader("🏆 10 อันดับสินค้าขายดี (รวมรุ่น)")
        top_products = (
            filtered_df.groupby(['Clean_SKU', 'Tag', 'Shop'])['Quantity']
            .sum()
            .reset_index()
            .sort_values(by='Quantity', ascending=False)
            .head(10)
        )
        st.dataframe(
            top_products, 
            use_container_width=True,
            column_config={
                "Clean_SKU": "ชื่อสินค้า (จัดกลุ่มแล้ว)",
                "Quantity": st.column_config.NumberColumn("จำนวนที่ขาย", format="%d")
            }
        )

    else:
        st.warning("⚠️ ไม่พบข้อมูลใน Database หรือชื่อคอลัมน์ไม่ถูกต้อง")

except Exception as e:
    st.error(f"❌ เกิดข้อผิดพลาด: {e}")

    st.info("💡 คำแนะนำ: ตรวจสอบชื่อ Table ใน Supabase ต้องชื่อว่า 'orders' (ตัวเล็กหมด)")

