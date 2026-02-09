import streamlit as st
import pandas as pd
import json
import plotly.express as px
from supabase import create_client
import streamlit.components.v1 as components
import datetime
import re

# ==========================================
# 1. Config & Styles
# ==========================================
st.set_page_config(page_title="Sales Dashboard", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600;700&display=swap');
    /* นำเข้าฟอนต์ Sarabun สำหรับหัวข้อร้าน */
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700&display=swap');
    
    /* Global Font */
    html, body, [class*="css"] {
        font-family: 'Kanit', sans-serif;
    }

    /* --- ขยายขนาดปุ่ม Pills (Tag) --- */
    div[data-testid="stPills"] button {
        font-size: 20px !important;   /* เพิ่มขนาดตัวหนังสือ */
        padding: 12px 28px !important; /* เพิ่มขนาดปุ่ม */
        font-weight: 600 !important;
        border-radius: 30px !important;
        margin: 5px !important;
    }

    /* --- Shop Header (Sarabun Font) --- */
    .shop-header-sarabun {
        font-family: 'Sarabun', sans-serif !important;
        font-size: 38px !important; /* ขนาดตัวหนังสือใหญ่สะใจ */
        font-weight: 700 !important;
        color: #00bcd4; /* สีฟ้า */
        margin-bottom: 5px;
        padding-bottom: 5px;
        text-align: center; /* จัดกึ่งกลางให้สวยงาม */
    }

    /* Block Container */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
    }

    /* --- Date Input --- */
    div[data-testid="stDateInput"] label { display: none; }
    div[data-baseweb="input"] {
        background-color: transparent !important;
        border: none !important;
        border-bottom: 3px solid #ff7043 !important;
        border-radius: 0px !important;
    }
    
    /* Date Input Formatting Fix */
    div[data-testid="stDateInput"] input {
        text-align: center;
    }
            
    input[class*="st-"] {
        color: #ffffff !important;
        font-size: 30px !important;
        font-weight: 700 !important;
        font-family: 'Kanit', sans-serif !important;
        height: auto !important;
        padding-bottom: 5px !important;
    }

    /* --- Radio Button --- */
    div[role="radiogroup"] {
        display: flex;
        flex-direction: row;
        align-items: center;
        gap: 25px;
        padding-top: 10px;
        flex-wrap: wrap;
    }
    div[data-testid="stRadio"] label {
        font-size: 26px !important;
        color: #a0a0a0 !important;
        cursor: pointer;
    }
    div[data-testid="stRadio"] label:hover, 
    div[data-testid="stRadio"] label[data-checked="true"] {
        color: #ffffff !important;
        font-weight: 600 !important;
    }
    div[data-testid="stRadio"] label div[role="radio"] {
        transform: scale(1.3);
        margin-right: 10px;
        border-color: #a0a0a0 !important;
    }
    div[role="radiogroup"] div[data-checked="true"] div:first-child {
        background-color: #ff7043 !important;
        border-color: #ff7043 !important;
    }

    /* --- Header Label --- */
    .date-header-label {
        font-size: 22px;
        color: #a0a0a0;
        margin-bottom: -10px;
        font-weight: 400;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #111;
        border-right: 1px solid #333;
    }
    
    /* Shop Header (Special Page) */
    .shop-header {
        font-size: 24px;
        font-weight: 700;
        color: #00bcd4;
        margin-bottom: 10px;
        border-bottom: 2px solid #333;
        padding-bottom: 5px;
    }

</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. Connection & Load Data
# ==========================================
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Connect Error: {e}")
        st.stop()

@st.cache_data(ttl=300)
def load_data():
    supabase = init_connection()
    try:
        # ดึง product_tag มาด้วยตามที่สร้างไว้ใน DB
        response = supabase.table('orders').select(
            '"Shipped Time", "Warehouse Name", "Seller SKU", "Product Name", "Quantity", "product_tag"'
        ).execute()
        return pd.DataFrame(response.data)
    except:
        return pd.DataFrame()

# ==========================================
# 3. Process Data
# ==========================================
def process_data(df):
    if 'Shipped Time' in df.columns:
        df['Shipped Time'] = df['Shipped Time'].astype(str).str.replace(r'\t', '', regex=True).str.strip()
        df['Date_Obj'] = pd.to_datetime(df['Shipped Time'], dayfirst=True, errors='coerce')
        df['Date'] = df['Date_Obj'].dt.date
    
    def map_shop(name):
        mapping = { "Simmobile": "SIM1", "Namkangmobile": "SIM2", "Thailand Pickup Warehouse": "Namkang" }
        return mapping.get(str(name).strip(), str(name).strip())
    
    def clean_sku(sku):
        if not sku: return "Unknown"
        s = str(sku).lower().replace("สีเงิน", "silver").replace("สีเทา", "gray")
        s = re.sub(r'\b(gb|ram|rom)\b', '', s)
        return re.sub(r'\s+', ' ', s).strip().title()

    df['Shop'] = df['Warehouse Name'].apply(map_shop)
    df['Clean_SKU'] = df['Seller SKU'].apply(clean_sku)
    return df

# ==========================================
# 4. Main App Layout
# ==========================================
df_raw = load_data()

if df_raw.empty:
    st.warning("No Data found in Supabase")
    st.stop()

df = process_data(df_raw)

# --- 4.1 Sidebar Menu ---
with st.sidebar:
    st.title("เมนูหลัก")
    page = st.radio(
        "เลือกหน้าแสดงผล:",
        ["ภาพรวม (Overview)", "ค้นหารายสินค้า (Search)", "รายงานกลุ่มสินค้า (Special Tags)"],
        index=0
    )
    st.markdown("---")
    st.caption("Sales Dashboard v2.2")

# =================================================================================
# CASE 1: OVERVIEW & SEARCH (ใช้ HTML/Chart.js แบบเดิม)
# =================================================================================
if page in ["ภาพรวม (Overview)", "ค้นหารายสินค้า (Search)"]:
    
    # -- Header Filter --
    c_date, c_space, c_shop = st.columns([2, 0.2, 2.5])
    with c_date:
        st.markdown('<div class="date-header-label">ช่วงวันที่ขายสินค้า</div>', unsafe_allow_html=True)
        valid_dates = df['Date'].dropna().sort_values()
        min_d, max_d = (valid_dates.iloc[0], valid_dates.iloc[-1]) if not valid_dates.empty else (datetime.date.today(), datetime.date.today())
        date_range = st.date_input("Select Date", value=[min_d, max_d], format="DD/MM/YYYY")
        start_date, end_date = date_range if len(date_range) == 2 else (min_d, max_d)

    with c_shop:
        st.write("") 
        st.write("") 
        shop_options = ['All Shops'] + sorted(df['Shop'].unique().tolist())
        selected_shop_ui = st.radio("Shop", shop_options, horizontal=True, label_visibility="collapsed")

    # -- Filter Data --
    mask_date = (df['Date'] >= start_date) & (df['Date'] <= end_date)
    filtered_df = df.loc[mask_date]

    if selected_shop_ui != 'All Shops':
        filtered_df = filtered_df[filtered_df['Shop'] == selected_shop_ui]

    # -- Search Logic --
    if page == "ค้นหารายสินค้า (Search)":
        st.markdown("---")
        st.markdown("### 🔍 ค้นหาและเลือกสินค้า")
        available_skus = sorted(filtered_df['Clean_SKU'].unique().tolist())
        selected_skus = st.multiselect("เลือกสินค้า:", options=available_skus)
        if selected_skus:
            filtered_df = filtered_df[filtered_df['Clean_SKU'].isin(selected_skus)]

    # -- Calculation & HTML Generation (เฉพาะหน้า Overview/Search) --
    if not filtered_df.empty:
        # 1. Top Best Seller (20 items)
        top_df = filtered_df.groupby('Clean_SKU')['Quantity'].sum().reset_index().sort_values('Quantity', ascending=False).head(20)
        top_rows_html = ""
        for idx, row in top_df.iterrows():
            icon = ' <span class="trophy-icon">🏆</span>' if idx == top_df.index[0] else ''
            top_rows_html += f"<tr><td>{icon}{row['Clean_SKU']}</td><td>{row['Quantity']:,}</td></tr>"

        # 2. Lower Seller (Bottom 10 items)
        lower_df = filtered_df.groupby('Clean_SKU')['Quantity'].sum().reset_index().sort_values('Quantity', ascending=True).head(10)
        lower_rows_html = ""
        for idx, row in lower_df.iterrows():
            lower_rows_html += f"<tr><td>{row['Clean_SKU']}</td><td>{row['Quantity']:,}</td></tr>"

        # 3. Chart Data
        chart_df = top_df.head(20)
        labels_js = json.dumps(chart_df['Clean_SKU'].tolist())
        data_values_js = json.dumps(chart_df['Quantity'].tolist())
        
        # Colors
        color_palette = ['#ffab91', '#81d4fa', '#b39ddb', '#ffcc80', '#a5d6a7', '#f48fb1', '#80cbc4', '#ce93d8', '#ffab40', '#90caf9']
        bg_colors_js = json.dumps([color_palette[i % len(color_palette)] for i in range(len(chart_df))])

        display_shop_name = selected_shop_ui

        # HTML Template
        html_code = """
        <!DOCTYPE html>
        <html lang="th">
        <head>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body { font-family: 'Kanit', sans-serif; background-color: #0f1115; color: white; margin:0; overflow: hidden; }
                .dashboard-container { display: grid; grid-template-columns: 65% 35%; gap: 20px; height: 98vh; width: 100%; }
                .chart-area { display: flex; flex-direction: column; height: 100%; padding-right: 10px; }
                .chart-wrapper { flex-grow: 1; position: relative; width: 100%; }
                .sidebar { display: flex; flex-direction: column; gap: 15px; height: 100%; }
                .ranking-box { background-color: #d9d9d9; border-radius: 4px; overflow: hidden; display: flex; flex-direction: column; }
                .top-seller { flex: 2; min-height: 300px; }
                .lower-seller { flex: 1; min-height: 200px; }
                .ranking-header { background-color: #ffccbc; color: black; text-align: center; padding: 12px; font-size: 18px; font-weight: bold; }
                .lower { background-color: #81d4fa; }
                .table-scroll { overflow-y: auto; flex-grow: 1; }
                table { width: 100%; border-collapse: collapse; }
                th { text-align: left; padding: 8px 12px; background-color: #cfd8dc; color: black; position: sticky; top: 0; }
                td { padding: 8px 12px; color: black; border-bottom: 1px solid #ccc; background-color: #e0e0e0; font-size: 14px; }
                td:last-child, th:last-child { text-align: right; }
                ::-webkit-scrollbar { width: 6px; }
                ::-webkit-scrollbar-thumb { background: #555; border-radius: 3px; }
            </style>
        </head>
        <body>
            <div class="dashboard-container">
                <div class="chart-area">
                    <div style="color:#a0a0a0; margin-bottom:10px;">ยอดขายสินค้า (__SELECTED_SHOP__)</div>
                    <div class="chart-wrapper"><canvas id="salesChart"></canvas></div>
                </div>
                <div class="sidebar">
                    <div class="ranking-box top-seller">
                        <div class="ranking-header">TOP Best Seller</div>
                        <div class="table-scroll"><table><thead><tr><th>สินค้า</th><th>จำนวน</th></tr></thead><tbody>__TOP_ROWS__</tbody></table></div>
                    </div>
                    <div class="ranking-box lower-seller">
                        <div class="ranking-header lower">⬇ Lower Seller</div>
                        <div class="table-scroll"><table><thead><tr><th>สินค้า</th><th>จำนวน</th></tr></thead><tbody>__LOWER_ROWS__</tbody></table></div>
                    </div>
                </div>
            </div>
            <script>
                new Chart(document.getElementById('salesChart'), {
                    type: 'bar',
                    data: { labels: __CHART_LABELS__, datasets: [{ label: 'Sales', data: __CHART_DATA__, backgroundColor: __CHART_COLORS__, borderRadius: 4 }] },
                    options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { color: '#333' }, ticks: { color: '#a0a0a0' } }, y: { grid: { display: false }, ticks: { color: '#a0a0a0', autoSkip: false } } } }
                });
            </script>
        </body>
        </html>
        """
        html_code = html_code.replace("__SELECTED_SHOP__", display_shop_name)\
                             .replace("__TOP_ROWS__", top_rows_html)\
                             .replace("__LOWER_ROWS__", lower_rows_html)\
                             .replace("__CHART_LABELS__", labels_js)\
                             .replace("__CHART_DATA__", data_values_js)\
                             .replace("__CHART_COLORS__", bg_colors_js)

        components.html(html_code, height=1400, scrolling=True)
    else:
        st.warning("ไม่พบข้อมูลในช่วงเวลาที่เลือก")


# =================================================================================
# CASE 2: SPECIAL TAGS (แก้ไขใหม่: ค้นหาแบบกลุ่ม / ปุ่มใหญ่ / ฟอนต์ Sarabun)
# =================================================================================
elif page == "รายงานกลุ่มสินค้า (Special Tags)":
    
    st.markdown("---")
    
    # 1. Filter UI (Date & Search)
    c_date, c_space, c_search = st.columns([2, 0.5, 3])
    with c_date:
        # กำหนด Format วันที่บังคับเป็น DD/MM/YYYY
        valid_dates = df['Date'].dropna().sort_values()
        min_d, max_d = (valid_dates.iloc[0], valid_dates.iloc[-1]) if not valid_dates.empty else (datetime.date.today(), datetime.date.today())
        
        date_range = st.date_input(
            "Date Range", 
            value=[min_d, max_d], 
            format="DD/MM/YYYY",  # <--- บังคับ Format ตรงนี้
            label_visibility="collapsed"
        )
        if len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date, end_date = min_d, max_d
    
    # กรองวันที่ก่อน เพื่อให้ List สินค้าในช่องค้นหาไม่เยอะเกินไป
    mask_date = (df['Date'] >= start_date) & (df['Date'] <= end_date)
    df_date_filtered = df.loc[mask_date]

    with c_search:
        # เปลี่ยนเป็น Multiselect (ค้นหาและเลือกได้หลายอัน)
        # ดึงรายชื่อสินค้าที่มีขายในช่วงเวลานั้นมาแสดง
        available_products = sorted(df_date_filtered['Clean_SKU'].unique().tolist())
        selected_skus = st.multiselect(
            "ค้นหา (เลือกสินค้าได้หลายรายการ)", 
            options=available_products,
            placeholder="พิมพ์ชื่อรุ่นสินค้าเพื่อค้นหา...",
            label_visibility="collapsed"
        )

    st.write("") # เว้นบรรทัดนิดนึง
    
    # 2. Tag Selection (ปุ่ม Pills ใหญ่ขึ้นด้วย CSS ด้านบน)
    tag_options = ["BCD", "BCDL", "CP", "CPL"]
    try:
        # ใช้ st.pills (Streamlit version ใหม่)
        selected_tags = st.pills(
            "เลือก Tags", 
            options=tag_options, 
            default=tag_options, 
            selection_mode="multi", 
            label_visibility="collapsed"
        )
    except AttributeError:
        # Fallback กรณีเวอร์ชันเก่า
        selected_tags = st.multiselect("เลือก Tags", options=tag_options, default=tag_options)

    if not selected_tags:
        st.error("กรุณาเลือก Tag อย่างน้อย 1 รายการ")
        st.stop()

    # 3. Prepare Data (ใช้ product_tag จาก DB)
    df_date_filtered['Tag_Group'] = df_date_filtered['product_tag'].fillna('BCD')

    # 4. Apply Filters (Shop + Tags + Selected SKUs)
    mask = df_date_filtered['Shop'].isin(['SIM1', 'SIM2'])
    mask = mask & (df_date_filtered['Tag_Group'].isin(selected_tags))
    
    # ถ้ามีการเลือกสินค้าในช่องค้นหา ให้กรองด้วย
    if selected_skus:
        mask = mask & (df_date_filtered['Clean_SKU'].isin(selected_skus))
    
    df_final = df_date_filtered.loc[mask]

    # 5. Render Charts (Split View)
    st.markdown("---")
    col1, col2 = st.columns(2, gap="medium")
    
    color_map = { "BCD": "#b39ddb", "BCDL": "#ef9a9a", "CP": "#3949ab", "CPL": "#c2185b" }

    def plot_shop_chart(shop_name, dataframe):
        # กรองเฉพาะร้านที่ต้องการ
        shop_df = dataframe[dataframe['Shop'] == shop_name]
        
        if shop_df.empty:
            st.markdown(f'<div class="shop-header-sarabun">ร้าน {shop_name}</div>', unsafe_allow_html=True)
            st.info(f"ไม่พบข้อมูล")
            return

        # 1. เตรียมข้อมูลสำหรับกราฟ (แยกตาม Tag เพื่อให้เห็นสี)
        chart_data = shop_df.groupby(['Clean_SKU', 'Tag_Group'])['Quantity'].sum().reset_index()
        
        # 2. คำนวณยอดรวมของแต่ละสินค้าเพื่อใช้จัดลำดับ
        total_sales_per_sku = shop_df.groupby('Clean_SKU')['Quantity'].sum().reset_index()
        
        # 3. สร้างลำดับการเรียง (แก้ไขเป็น False: มาก -> น้อย)
        # เพื่อให้ค่ามากที่สุด (Top 1) อยู่ที่ตำแหน่งแรก และ Plotly จะวาดไว้ด้านบนสุด
        sorted_skus = total_sales_per_sku.sort_values('Quantity', ascending=False)['Clean_SKU'].tolist()

        # 4. สร้างกราฟ
        fig = px.bar(
            chart_data, 
            y="Clean_SKU", 
            x="Quantity", 
            color="Tag_Group", 
            orientation='h', 
            color_discrete_map=color_map, 
            category_orders={"Clean_SKU": sorted_skus}, # บังคับลำดับ
            text="Quantity"
        )
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white', family='Kanit'),
            showlegend=True, 
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=None),
            margin=dict(l=0, r=0, t=10, b=0),
            height=max(400, 100 + (len(sorted_skus) * 40)),
            xaxis=dict(showgrid=True, gridcolor='#333'), 
            yaxis=dict(title="", autorange="reversed") # เพิ่ม autorange="reversed" เพื่อความชัวร์ว่าบนคืออันดับ 1
        )
        fig.update_traces(textposition='inside', insidetextanchor='middle')

        # แสดงผล
        st.markdown(f'<div class="shop-header-sarabun">ร้าน {shop_name}</div>', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)

    with col1: plot_shop_chart("SIM1", df_final)
    with col2: plot_shop_chart("SIM2", df_final)