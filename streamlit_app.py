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
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Kanit', sans-serif; }

    div[data-testid="stPills"] button {
        font-size: 20px !important;
        padding: 12px 28px !important;
        font-weight: 600 !important;
        border-radius: 30px !important;
        margin: 5px !important;
    }

    .shop-header-sarabun {
        font-family: 'Sarabun', sans-serif !important;
        font-size: 38px !important;
        font-weight: 700 !important;
        color: #00bcd4;
        margin-bottom: 5px;
        padding-bottom: 5px;
        text-align: center;
    }

    .block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; }

    div[data-testid="stDateInput"] label { display: none; }
    div[data-baseweb="input"] {
        background-color: transparent !important;
        border: none !important;
        border-bottom: 3px solid #ff7043 !important;
        border-radius: 0px !important;
    }
    div[data-testid="stDateInput"] input { text-align: center; }
            
    input[class*="st-"] {
        color: #ffffff !important; font-size: 30px !important;
        font-weight: 700 !important; font-family: 'Kanit', sans-serif !important;
        height: auto !important; padding-bottom: 5px !important;
    }

    div[role="radiogroup"] { display: flex; flex-direction: row; align-items: center; gap: 25px; padding-top: 10px; flex-wrap: wrap; }
    div[data-testid="stRadio"] label { font-size: 26px !important; color: #a0a0a0 !important; cursor: pointer; }
    div[data-testid="stRadio"] label:hover, 
    div[data-testid="stRadio"] label[data-checked="true"] { color: #ffffff !important; font-weight: 600 !important; }
    div[data-testid="stRadio"] label div[role="radio"] { transform: scale(1.3); margin-right: 10px; border-color: #a0a0a0 !important; }
    div[role="radiogroup"] div[data-checked="true"] div:first-child { background-color: #ff7043 !important; border-color: #ff7043 !important; }

    .date-header-label { font-size: 22px; color: #a0a0a0; margin-bottom: -10px; font-weight: 400; }
    section[data-testid="stSidebar"] { background-color: #111; border-right: 1px solid #333; }
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
        [
            "ภาพรวมยอดขาย", 
            "เปรียบเทียบรายการสินค้า", 
            "กราฟเส้นยอดขายรายวัน",        # <- นำเมนูกลับมา
            "ตะกร้าสินค้าร้าน Sim1 กับ Sim2" # <- นำเมนูกลับมา
        ],
        index=0
    )
    st.markdown("---")
    st.caption("Sales Dashboard v2.2")

# =================================================================================
# CASE 1: OVERVIEW 
# =================================================================================
if page == "ภาพรวมยอดขาย": # <- แก้บั๊กเงื่อนไขทับซ้อนแล้ว
    
    c_date, c_space, c_shop = st.columns([2, 0.2, 2.5])
    with c_date:
        st.markdown('<div class="date-header-label">ช่วงวันที่ขายสินค้า</div>', unsafe_allow_html=True)
        valid_dates = df['Date'].dropna().sort_values()
        min_d, max_d = (valid_dates.iloc[0], valid_dates.iloc[-1]) if not valid_dates.empty else (datetime.date.today(), datetime.date.today())
        date_range = st.date_input("Select Date", value=[min_d, max_d], format="DD/MM/YYYY")
        start_date, end_date = date_range if len(date_range) == 2 else (min_d, max_d)

    with c_shop:
        st.write(""); st.write("") 
        shop_options = ['All Shops'] + sorted(df['Shop'].unique().tolist())
        selected_shop_ui = st.radio("Shop", shop_options, horizontal=True, label_visibility="collapsed")

    mask_date = (df['Date'] >= start_date) & (df['Date'] <= end_date)
    filtered_df = df.loc[mask_date]

    if selected_shop_ui != 'All Shops':
        filtered_df = filtered_df[filtered_df['Shop'] == selected_shop_ui]

    if not filtered_df.empty:
        top_df = filtered_df.groupby('Clean_SKU')['Quantity'].sum().reset_index().sort_values('Quantity', ascending=False).head(20)
        top_rows_html = ""
        for idx, row in top_df.iterrows():
            icon = ' <span class="trophy-icon">🏆</span>' if idx == top_df.index[0] else ''
            top_rows_html += f"<tr><td>{icon}{row['Clean_SKU']}</td><td>{row['Quantity']:,}</td></tr>"

        lower_df = filtered_df.groupby('Clean_SKU')['Quantity'].sum().reset_index().sort_values('Quantity', ascending=True).head(10)
        lower_rows_html = ""
        for idx, row in lower_df.iterrows():
            lower_rows_html += f"<tr><td>{row['Clean_SKU']}</td><td>{row['Quantity']:,}</td></tr>"

        chart_df = top_df.head(20)
        labels_js = json.dumps(chart_df['Clean_SKU'].tolist())
        data_values_js = json.dumps(chart_df['Quantity'].tolist())
        color_palette = ['#ffab91', '#81d4fa', '#b39ddb', '#ffcc80', '#a5d6a7', '#f48fb1', '#80cbc4', '#ce93d8', '#ffab40', '#90caf9']
        bg_colors_js = json.dumps([color_palette[i % len(color_palette)] for i in range(len(chart_df))])

        html_code = """
        <!DOCTYPE html><html lang="th"><head><script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>body{font-family:'Kanit';background:#0f1115;color:white;margin:0;overflow:hidden;} .dashboard-container{display:grid;grid-template-columns:65% 35%;gap:20px;height:98vh;} .chart-wrapper{flex-grow:1;position:relative;} .sidebar{display:flex;flex-direction:column;gap:15px;height:100%;} .ranking-box{background:#d9d9d9;border-radius:4px;overflow:hidden;display:flex;flex-direction:column;} .top-seller{flex:2;min-height:300px;} .lower-seller{flex:1;min-height:200px;} .ranking-header{background:#ffccbc;color:black;text-align:center;padding:12px;font-size:18px;font-weight:bold;} .lower{background:#81d4fa;} .table-scroll{overflow-y:auto;} table{width:100%;border-collapse:collapse;} th{text-align:left;padding:8px;background:#cfd8dc;color:black;position:sticky;top:0;} td{padding:8px;color:black;border-bottom:1px solid #ccc;background:#e0e0e0;} td:last-child,th:last-child{text-align:right;} ::-webkit-scrollbar{width:6px;} ::-webkit-scrollbar-thumb{background:#555;border-radius:3px;}</style></head>
        <body><div class="dashboard-container"><div class="chart-area"><div style="color:#a0a0a0;margin-bottom:10px;">ยอดขายสินค้า (__SELECTED_SHOP__)</div><div class="chart-wrapper"><canvas id="salesChart"></canvas></div></div><div class="sidebar"><div class="ranking-box top-seller"><div class="ranking-header">TOP Best Seller</div><div class="table-scroll"><table><thead><tr><th>สินค้า</th><th>จำนวน</th></tr></thead><tbody>__TOP_ROWS__</tbody></table></div></div><div class="ranking-box lower-seller"><div class="ranking-header lower">⬇ Lower Seller</div><div class="table-scroll"><table><thead><tr><th>สินค้า</th><th>จำนวน</th></tr></thead><tbody>__LOWER_ROWS__</tbody></table></div></div></div></div>
        <script>new Chart(document.getElementById('salesChart'),{type:'bar',data:{labels:__CHART_LABELS__,datasets:[{label:'Sales',data:__CHART_DATA__,backgroundColor:__CHART_COLORS__,borderRadius:4}]},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{color:'#333'},ticks:{color:'#a0a0a0'}},y:{grid:{display:false},ticks:{color:'#a0a0a0',autoSkip:false}}}}});</script></body></html>
        """
        html_code = html_code.replace("__SELECTED_SHOP__", selected_shop_ui).replace("__TOP_ROWS__", top_rows_html).replace("__LOWER_ROWS__", lower_rows_html).replace("__CHART_LABELS__", labels_js).replace("__CHART_DATA__", data_values_js).replace("__CHART_COLORS__", bg_colors_js)
        components.html(html_code, height=1400, scrolling=True)
    else:
        st.warning("ไม่พบข้อมูลในช่วงเวลาที่เลือก")

# =================================================================================
# CASE 2: SPECIAL TAGS 
# =================================================================================
elif page == "เปรียบเทียบรายการสินค้า":
    st.markdown("---")
    c_date, c_space, c_search = st.columns([2, 0.5, 3])
    with c_date:
        valid_dates = df['Date'].dropna().sort_values()
        min_d, max_d = (valid_dates.iloc[0], valid_dates.iloc[-1]) if not valid_dates.empty else (datetime.date.today(), datetime.date.today())
        date_range = st.date_input("Date Range", value=[min_d, max_d], format="DD/MM/YYYY", label_visibility="collapsed")
        start_date, end_date = date_range if len(date_range) == 2 else (min_d, max_d)
    
    mask_date = (df['Date'] >= start_date) & (df['Date'] <= end_date)
    df_date_filtered = df.loc[mask_date]

    with c_search:
        available_products = sorted(df_date_filtered['Clean_SKU'].unique().tolist())
        selected_skus = st.multiselect(
            "ค้นหา หรือ เลือกสินค้าหลายตัวเทียบกันได้", # <- เติมลูกน้ำแล้ว!
            options=available_products,
            placeholder="พิมพ์ชื่อรุ่นสินค้าเพื่อค้นหา...",
            label_visibility="collapsed"
        )

    st.write("") 
    tag_options = ["BCD", "BCDL", "CP", "CPL"]
    try:
        selected_tags = st.pills("เลือก Tags", options=tag_options, default=tag_options, selection_mode="multi", label_visibility="collapsed")
    except AttributeError:
        selected_tags = st.multiselect("เลือก Tags", options=tag_options, default=tag_options)

    if not selected_tags: st.error("กรุณาเลือก Tag อย่างน้อย 1 รายการ"); st.stop()

    df_date_filtered['Tag_Group'] = df_date_filtered['product_tag'].fillna('BCD')
    mask = df_date_filtered['Shop'].isin(['SIM1', 'SIM2']) & (df_date_filtered['Tag_Group'].isin(selected_tags))
    if selected_skus: mask = mask & (df_date_filtered['Clean_SKU'].isin(selected_skus))
    
    df_final = df_date_filtered.loc[mask]

    st.markdown("---")
    col1, col2 = st.columns(2, gap="medium")
    color_map = { "BCD": "#b39ddb", "BCDL": "#ef9a9a", "CP": "#3949ab", "CPL": "#c2185b" }

    def plot_shop_chart(shop_name, dataframe):
        shop_df = dataframe[dataframe['Shop'] == shop_name]
        if shop_df.empty:
            st.markdown(f'<div class="shop-header-sarabun">ร้าน {shop_name}</div>', unsafe_allow_html=True)
            st.info("ไม่พบข้อมูล"); return

        total_sales_per_sku = shop_df.groupby('Clean_SKU')['Quantity'].sum().reset_index()
        top_40_skus_df = total_sales_per_sku.sort_values('Quantity', ascending=False).head(40)
        sorted_skus = top_40_skus_df['Clean_SKU'].tolist()

        chart_data = shop_df[shop_df['Clean_SKU'].isin(sorted_skus)].groupby(['Clean_SKU', 'Tag_Group'])['Quantity'].sum().reset_index()

        fig = px.bar(chart_data, y="Clean_SKU", x="Quantity", color="Tag_Group", orientation='h', color_discrete_map=color_map, category_orders={"Clean_SKU": sorted_skus}, text="Quantity")
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white', family='Kanit'), showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=None), margin=dict(l=0, r=0, t=10, b=0), height=max(400, 100 + (len(sorted_skus) * 40)), xaxis=dict(showgrid=True, gridcolor='#333'), yaxis=dict(title="", autorange="reversed"))
        fig.update_traces(textposition='inside', insidetextanchor='middle')

        st.markdown(f'<div class="shop-header-sarabun">ร้าน {shop_name} (Top 40)</div>', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)

    with col1: plot_shop_chart("SIM1", df_final)
    with col2: plot_shop_chart("SIM2", df_final)

# =================================================================================
# CASE 3: DAILY SALES LINE CHART (นำกลับมาแล้ว!)
# =================================================================================
elif page == "กราฟเส้นยอดขายรายวัน":
    st.markdown('<div class="shop-header-sarabun">📈 กราฟเส้นแนวโน้มยอดขายสินค้ารายวัน</div>', unsafe_allow_html=True)
    st.markdown("---")

    c_date, c_space, c_shop = st.columns([2, 0.5, 3])
    with c_date:
        valid_dates = df['Date'].dropna().sort_values()
        min_d, max_d = (valid_dates.iloc[0], valid_dates.iloc[-1]) if not valid_dates.empty else (datetime.date.today(), datetime.date.today())
        date_range = st.date_input("เลือกช่วงวันที่", value=[min_d, max_d], format="DD/MM/YYYY", label_visibility="collapsed")
        start_date, end_date = date_range if len(date_range) == 2 else (min_d, max_d)

    mask_date = (df['Date'] >= start_date) & (df['Date'] <= end_date)
    df_trend = df.loc[mask_date]

    with c_shop:
        shop_options = ['All Shops'] + sorted(df_trend['Shop'].unique().tolist())
        selected_shop_ui = st.radio("Shop", shop_options, horizontal=True, label_visibility="collapsed")

    if selected_shop_ui != 'All Shops':
        df_trend = df_trend[df_trend['Shop'] == selected_shop_ui]

    top_sales_df = df_trend.groupby('Clean_SKU')['Quantity'].sum().reset_index().sort_values('Quantity', ascending=False)
    available_skus = top_sales_df['Clean_SKU'].tolist()

    st.write("") 
    selected_skus = st.multiselect(
        "🔍 ค้นหาและเลือกสินค้า (เรียงตามสินค้าที่ขายดีที่สุดในช่วงเวลานี้):",
        options=available_skus,
        default=available_skus[:10] if len(available_skus) >= 10 else available_skus
    )

    if not selected_skus:
        st.warning("⚠️ กรุณาเลือกสินค้าอย่างน้อย 1 รายการเพื่อแสดงกราฟ")
    else:
        df_chart = df_trend[df_trend['Clean_SKU'].isin(selected_skus)]
        df_chart_grouped = df_chart.groupby(['Date', 'Clean_SKU'])['Quantity'].sum().reset_index().sort_values(['Date'])

        fig = px.line(df_chart_grouped, x="Date", y="Quantity", color="Clean_SKU", markers=True, text="Quantity", category_orders={"Clean_SKU": selected_skus})
        fig.update_traces(textposition="top center", textfont=dict(size=12))
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white', family='Kanit'), xaxis=dict(showgrid=True, gridcolor='#333', title="วันที่"), yaxis=dict(showgrid=True, gridcolor='#333', title="จำนวน (ชิ้น)"), hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1, title=None), height=600, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, use_container_width=True)

# =================================================================================
# CASE 4: SHOP CART COMPARISON (สร้างโครงไว้รอรับฟังก์ชันใหม่!)
# =================================================================================
elif page == "ตะกร้าสินค้าร้าน Sim1 กับ Sim2":
    st.markdown('<div class="shop-header-sarabun">🛒 ตะกร้าสินค้าร้าน SIM1 กับ SIM2</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    st.info("💡 หน้านี้เตรียมพร้อมสำหรับการพัฒนาฟังก์ชันตะกร้าสินค้าเรียบร้อยแล้วครับ!")
    
    # ตัวอย่างการแสดงผลเบื้องต้น
    df_cart = df[df['Shop'].isin(['SIM1', 'SIM2'])]
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="shop-header-sarabun">ร้าน SIM1</div>', unsafe_allow_html=True)
        st.dataframe(df_cart[df_cart['Shop'] == 'SIM1'].head(10), use_container_width=True)
        
    with col2:
        st.markdown(f'<div class="shop-header-sarabun">ร้าน SIM2</div>', unsafe_allow_html=True)
        st.dataframe(df_cart[df_cart['Shop'] == 'SIM2'].head(10), use_container_width=True)