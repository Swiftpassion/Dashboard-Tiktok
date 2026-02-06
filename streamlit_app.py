import streamlit as st
import pandas as pd
import plotly.express as px
import re
from supabase import create_client, Client

# ==========================================
# 1. ตั้งค่าหน้าเว็บ & CSS (ฉบับ Custom 100%)
# ==========================================
st.set_page_config(page_title="Dashboard สรุปยอดขาย", layout="wide")

# CSS ชุดนี้จะ "บังคับ" หน้าตาเว็บใหม่ทั้งหมด
st.markdown("""
    <style>
    /* 1. Import Font Sarabun */
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap');
    
    /* 2. Reset Default Streamlit Styles */
    html, body, [class*="css"] {
        font-family: 'Sarabun', sans-serif;
        color: #333333;
    }
    .stApp {
        background-color: #F8F9FA; /* พื้นหลังสีเทาอ่อน สบายตา */
    }
    
    /* 3. Custom Card (กล่องขาว) */
    .custom-card {
        background-color: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        height: 100%;
    }
    
    /* 4. Custom Headers */
    .card-header {
        font-size: 18px;
        font-weight: 700;
        color: #2E86C1;
        margin-bottom: 15px;
        border-bottom: 2px solid #F0F2F5;
        padding-bottom: 8px;
    }
    
    /* 5. Custom Table (HTML Table) */
    .styled-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 16px;
    }
    .styled-table th {
        text-align: left;
        color: #555;
        font-weight: 600;
        padding: 10px 0;
        border-bottom: 1px solid #ddd;
    }
    .styled-table td {
        padding: 8px 0;
        border-bottom: 1px solid #eee;
    }
    .styled-table tr:last-child td {
        border-bottom: none;
    }
    .badge-rank {
        background-color: #EBF5FB;
        color: #2E86C1;
        padding: 2px 8px;
        border-radius: 50%;
        font-size: 12px;
        font-weight: bold;
        margin-right: 8px;
    }
    
    /* 6. ปรับแต่ง Widget ของ Streamlit ให้เข้าธีม */
    .stDateInput > div > div {
        border-radius: 8px;
        border: 1px solid #ddd;
    }
    .stMultiSelect > div > div {
        border-radius: 8px;
        border: 1px solid #ddd;
        background-color: white;
    }
    
    /* ซ่อน Header มาตรฐานของ Streamlit */
    header {visibility: hidden;}
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
# 3. โหลดข้อมูล
# ==========================================
@st.cache_data(ttl=300) 
def load_data():
    supabase = init_connection()
    try:
        response = supabase.table('orders').select(
            '"Shipped Time", "Warehouse Name", "Seller SKU", "Product Name", "Quantity"'
        ).execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return pd.DataFrame()

# ==========================================
# 4. Data Logic
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
# 5. Main UI (Construction)
# ==========================================
df = load_data()

if not df.empty:
    # --- Prepare Data ---
    if 'Shipped Time' in df.columns:
        df['Shipped Time'] = df['Shipped Time'].astype(str).str.replace(r'\t', '', regex=True).str.strip()
        df['Date_Obj'] = pd.to_datetime(df['Shipped Time'], dayfirst=True, errors='coerce')
        df['Date'] = df['Date_Obj'].dt.date

    df['Shop'] = df['Warehouse Name'].apply(map_warehouse)
    df['Tag'] = df['Product Name'].apply(get_tag)
    df['Clean_SKU'] = df['Seller SKU'].apply(clean_sku_name)

    # Header ใหญ่สุด
    st.markdown("<h1 style='text-align: center; margin-bottom: 30px;'>📊 รายงานสรุปยอดขายประจำวัน</h1>", unsafe_allow_html=True)

    # =================================================================================
    # ROW 1: Control Panel & Top Products
    # จัด Layout: [ วันที่ (1) ] [ ร้านค้า (1.5) ] [ ตาราง Top 5 (2.5) ]
    # =================================================================================
    c1, c2, c3 = st.columns([1, 1.5, 2.5], gap="large")

    # --- Column 1: Date Picker ---
    with c1:
        st.markdown("""
        <div class="custom-card">
            <div class="card-header">📅 เลือกช่วงวันที่</div>
        """, unsafe_allow_html=True)
        
        valid_dates = df['Date'].dropna().sort_values()
        if not valid_dates.empty:
            d_start, d_end = valid_dates.iloc[0], valid_dates.iloc[-1]
            date_range = st.date_input("ระบุวันเริ่มต้น - สิ้นสุด", [d_start, d_end], label_visibility="collapsed")
            if len(date_range) == 2:
                start_date, end_date = date_range
            else:
                start_date, end_date = d_start, d_end
        
        st.markdown("</div>", unsafe_allow_html=True) # ปิด div card

    # --- Column 2: Shop Selector ---
    with c2:
        st.markdown("""
        <div class="custom-card">
            <div class="card-header">🏪 เลือกร้านค้า</div>
        """, unsafe_allow_html=True)
        
        all_shops = sorted(df['Shop'].unique())
        selected_shops = st.multiselect("เลือกร้าน", all_shops, default=all_shops, label_visibility="collapsed")
        
        st.markdown("</div>", unsafe_allow_html=True) # ปิด div card

    # --- Filter Data ---
    mask = df['Shop'].isin(selected_shops)
    if start_date and end_date:
        mask = mask & (df['Date'] >= start_date) & (df['Date'] <= end_date)
    filtered_df = df.loc[mask]

    # --- Column 3: Custom HTML Table (Top 5) ---
    with c3:
        # สร้าง HTML Table เอง เพื่อความสวยงามขั้นสุด (ไม่ใช้ st.dataframe)
        top_products = filtered_df.groupby('Clean_SKU')['Quantity'].sum().reset_index().sort_values('Quantity', ascending=False).head(5)
        
        # สร้าง String HTML ของแถวในตาราง
        table_rows = ""
        for i, row in top_products.iterrows():
            rank = i + 1 # ไม่ใช่ index จริง แต่เป็นลำดับการวนลูป (ถ้าอยากได้ 1,2,3 ตามลำดับต้องใช้ enumerate หรือ reset_index drop=True)
        
        # Reset Index เพื่อให้ลำดับเป็น 1,2,3,4,5
        top_products_reset = top_products.reset_index(drop=True)
        
        for idx, row in top_products_reset.iterrows():
            table_rows += f"""
            <tr>
                <td style="width: 70%;"><span class="badge-rank">{idx+1}</span> {row['Clean_SKU']}</td>
                <td style="width: 30%; text-align: right; font-weight: bold;">{row['Quantity']:,} ชิ้น</td>
            </tr>
            """

        st.markdown(f"""
        <div class="custom-card">
            <div class="card-header">🏆 5 อันดับสินค้าขายดี</div>
            <table class="styled-table">
                {table_rows if table_rows else "<tr><td>ไม่มีข้อมูล</td></tr>"}
            </table>
        </div>
        """, unsafe_allow_html=True)

    # =================================================================================
    # ROW 2: Summary Text & Horizontal Bar Chart
    # จัด Layout: [ Text Summary (1) ] [ Chart (3) ]
    # =================================================================================
    r2_c1, r2_c2 = st.columns([1, 3], gap="large")

    with r2_c1:
        # ใช้ HTML ล้วนสร้าง Card สรุปยอด
        total_sales = filtered_df['Quantity'].sum()
        total_orders = len(filtered_df)
        
        st.markdown(f"""
        <div class="custom-card" style="display: flex; flex-direction: column; justify-content: center; text-align: center;">
            <div style="font-size: 16px; color: #7f8c8d;">ยอดขายรวมทั้งหมด</div>
            <div style="font-size: 56px; font-weight: 700; color: #2E86C1; line-height: 1.2;">{total_sales:,}</div>
            <div style="font-size: 18px; color: #2E86C1;">ชิ้น</div>
            <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
            <div style="font-size: 14px; color: #95a5a6;">จำนวนออเดอร์: <b>{total_orders:,}</b> รายการ</div>
            <div style="font-size: 14px; color: #95a5a6; margin-top: 5px;">ข้อมูล: {start_date} - {end_date}</div>
        </div>
        """, unsafe_allow_html=True)

    with r2_c2:
        # เตรียมข้อมูลกราฟ
        if not filtered_df.empty:
            chart_data = filtered_df.groupby(['Shop', 'Tag'])['Quantity'].sum().reset_index()
            
            fig = px.bar(
                chart_data, 
                x="Quantity", 
                y="Shop", 
                color="Tag", 
                orientation='h', # แนวนอน
                text_auto=True,
                title="", # ปิด Title ในกราฟ (เพราะเราจะทำ Header HTML เอง)
                color_discrete_sequence=['#AED6F1', '#5DADE2', '#F5B7B1', '#D2B4DE', '#ABEBC6'] # สีพาสเทล
            )
            
            # ปรับแต่งกราฟให้คลีนที่สุด (โปร่งใส)
            fig.update_layout(
                font_family="Sarabun",
                plot_bgcolor="rgba(0,0,0,0)", # พื้นหลังใส
                paper_bgcolor="rgba(0,0,0,0)", # พื้นหลังใส
                margin=dict(l=20, r=20, t=20, b=20),
                xaxis_title="จำนวนขาย (ชิ้น)",
                yaxis_title=None,
                legend_title="หมวดหมู่",
                height=350,
                barcornerradius=5 # ทำมุมโค้งให้กราฟแท่ง (เฉพาะ Plotly ใหม่ๆ)
            )
            
            # ใส่ Card ครอบกราฟ
            st.markdown("""
            <div class="custom-card">
                <div class="card-header">📈 กราฟสรุปยอดขายแยกตามร้าน</div>
            """, unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("ไม่มีข้อมูลแสดงผลกราฟ")

else:
    st.warning("กำลังโหลดข้อมูล หรือ Database ว่างเปล่า...")