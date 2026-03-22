import datetime
import json
import logging
import re

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client, Client

# ==========================================
# 0. Logger Setup
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==========================================
# 1. Config & Styles
# ==========================================
st.set_page_config(page_title="Sales Dashboard", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Noto Sans Thai', sans-serif !important;
    }

    div[data-testid="stPills"] button {
        font-size: 20px !important;   
        padding: 12px 28px !important; 
        font-weight: 600 !important;
        border-radius: 30px !important;
        margin: 5px !important;
    }

    .shop-header-sarabun {
        font-family: 'Noto Sans Thai', sans-serif !important;
        font-size: 38px !important; 
        font-weight: 700 !important;
        color: #00bcd4; 
        margin-bottom: 5px;
        padding-bottom: 5px;
        text-align: center; 
    }

    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
    }

    div[data-testid="stDateInput"] label { display: none; }
    div[data-baseweb="input"] {
        background-color: transparent !important;
        border: none !important;
        border-bottom: 3px solid #ff7043 !important;
        border-radius: 0px !important;
    }
    
    div[data-testid="stDateInput"] input {
        text-align: center;
    }
            
    input[class*="st-"] {
        color: #ffffff !important;
        font-size: 30px !important;
        font-weight: 700 !important;
        font-family: 'Noto Sans Thai', sans-serif !important;
        height: auto !important;
        padding-bottom: 5px !important;
    }

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

    .date-header-label {
        font-size: 22px;
        color: #a0a0a0;
        margin-bottom: -10px;
        font-weight: 400;
    }
    
    section[data-testid="stSidebar"] {
        background-color: #111;
        border-right: 1px solid #333;
    }
    
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
def init_connection() -> Client:
    """
    Initializes and returns the Supabase client.
    
    Returns:
        Client: The initialized Supabase client object.
        
    Raises:
        KeyError: If Supabase secrets are missing.
    """
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except KeyError as ke:
        logger.error("Missing Supabase configuration in secrets: %s", ke)
        st.error("Configuration Error: Please check secrets.toml")
        st.stop()
    except Exception as e:
        logger.error("Failed to connect to Supabase: %s", e)
        st.error("Database connection failed.")
        st.stop()

@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    """
    Loads order data from the Supabase database.
    
    Returns:
        pd.DataFrame: A dataframe containing the order details. 
                      Returns an empty dataframe if the request fails.
    """
    supabase = init_connection()
    try:
        response = supabase.table('orders').select(
            '"Shipped Time", "Warehouse Name", "Seller SKU", "Product Name", "Quantity", "product_tag"'
        ).execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        logger.error("Failed to load data from Supabase: %s", e)
        return pd.DataFrame()

# ==========================================
# 3. Process Data
# ==========================================
def process_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans and processes the raw dataframe for dashboard usage.
    Handles date formatting and standardizes shop names and SKUs.
    
    Args:
        df (pd.DataFrame): The raw dataframe loaded from the database.
        
    Returns:
        pd.DataFrame: The processed dataframe.
    """
    if 'Shipped Time' in df.columns:
        df['Shipped Time'] = df['Shipped Time'].astype(str).str.replace(r'\t', '', regex=True)
        df['Date_Obj'] = pd.to_datetime(df['Shipped Time'], dayfirst=True, errors='coerce')
        df['Date'] = df['Date_Obj'].dt.date
    
    def map_shop(name: str) -> str:
        """Cleans typos and maps raw warehouse names to standard shop names."""
        if pd.isna(name):
            return "Unknown"
        
        # Clean whitespaces and fix double vowel typos
        clean_name = str(name).strip()
        clean_name = re.sub(r'\s+', '', clean_name)
        clean_name = clean_name.replace("มืือ", "มือ")
        
        mapping = {
            "Simmobile": "SIM1", 
            "Namkangmobile": "SIM2", 
            "ThailandPickupWarehouse": "Namkang",
            "มือ2": "มือ 2",
            "มือสอง": "มือ 2"
        }
        return mapping.get(clean_name, clean_name)
    
    def clean_sku(sku: str) -> str:
        """Standardizes SKU names by removing colors and memory capacities."""
        if not sku or pd.isna(sku): 
            return "Unknown"
        s = str(sku).lower().replace("สีเงิน", "silver").replace("สีเทา", "gray")
        s = re.sub(r'\b(gb|ram|rom)\b', '', s)
        return re.sub(r'\s+', ' ', s).strip().title()

    df['Shop'] = df['Warehouse Name'].apply(map_shop)
    df['Clean_SKU'] = df['Seller SKU'].apply(clean_sku)
    return df

def fetch_secondhand_data(
    df_all: pd.DataFrame,
    supabase_client: Client, 
    start_dt: datetime.date, 
    end_dt: datetime.date
) -> pd.DataFrame:
    """
    Fetches and merges second-hand stock data with filtered sales data.
    
    Args:
        df_all (pd.DataFrame): The complete processed dataframe containing all orders.
        supabase_client (Client): The initialized Supabase client.
        start_dt (datetime.date): The start date for filtering sales.
        end_dt (datetime.date): The end date for filtering sales.
        
    Returns:
        pd.DataFrame: A melted dataframe containing both stock and sold quantities.
    """
    try:
        # 1. Fetch Sales: Data is already cleaned in process_data()
        mask_shop = df_all["Shop"] == "มือ 2"
        mask_date = (df_all["Date"] >= start_dt) & (df_all["Date"] <= end_dt)
        df_sales = df_all[mask_shop & mask_date].copy()
        
        if not df_sales.empty:
            df_sales["Quantity"] = pd.to_numeric(df_sales["Quantity"], errors="coerce").fillna(0)
            # Use 'Clean_SKU' for proper grouping and merging
            df_sold = df_sales.groupby("Clean_SKU")["Quantity"].sum().reset_index()
            df_sold.rename(
                columns={"Clean_SKU": "product_name", "Quantity": "sold_qty"}, 
                inplace=True
            )
            df_sold["merge_key"] = df_sold["product_name"].astype(str).str.strip().str.lower()
        else:
            logger.info("No sales found for second-hand items between %s and %s", start_dt, end_dt)
            df_sold = pd.DataFrame(columns=["product_name", "sold_qty", "merge_key"])

        # 2. Fetch Remaining Stock
        res_stock = supabase_client.table("secondhand_stock").select("product_name, stock_qty").execute()
        df_stock = pd.DataFrame(res_stock.data)
        
        if not df_stock.empty:
            df_stock["merge_key"] = df_stock["product_name"].astype(str).str.strip().str.lower()
        else:
            logger.warning("No data returned from secondhand_stock table.")
            df_stock = pd.DataFrame(columns=["product_name", "stock_qty", "merge_key"])

        # 3. Merge Data
        df_merged = pd.merge(df_stock, df_sold, on="merge_key", how="outer", suffixes=("_stock", "_sold"))
        
        if not df_merged.empty:
            df_merged["product_name"] = df_merged["product_name_stock"].combine_first(
                df_merged["product_name_sold"]
            )
        
        df_merged.fillna(0, inplace=True) 

        # 4. Melt DataFrame for Plotly
        df_melted = df_merged.melt(
            id_vars="product_name", 
            value_vars=["stock_qty", "sold_qty"],
            var_name="data_type", 
            value_name="quantity"
        )
        
        label_map = {"stock_qty": "Stock คงเหลือ", "sold_qty": "ยอดขาย (Sold)"}
        df_melted["data_type"] = df_melted["data_type"].map(label_map)
        
        return df_melted

    except KeyError as ke:
        logger.error("Missing expected column during processing: %s", ke)
        return pd.DataFrame()
    except Exception as e:
        logger.error("Unexpected error fetching second-hand data: %s", e)
        return pd.DataFrame()

# ==========================================
# 4. Main App Layout
# ==========================================
df_raw = load_data()

if df_raw.empty:
    logger.warning("No data retrieved from Supabase. Halting application.")
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
            "กราฟเส้นยอดขายรายวัน",
            "ตะกร้าสินค้าร้าน Sim1 กับ Sim2",
            "กราฟเทียบยอดขายเฉพาะสินค้ามือ 2"
        ],
        index=0
    )
    st.markdown("---")
    st.caption("Sales Dashboard v2.2")

# =================================================================================
# CASE 1: OVERVIEW & SEARCH
# =================================================================================
if page in ["ภาพรวมยอดขาย", "เปรียบเทียบรายการสินค้า"]:
    
    # -- Header Filter --
    c_date, c_space, c_shop = st.columns([2, 0.2, 2.5])
    with c_date:
        st.markdown(
            '<div class="date-header-label">ช่วงวันที่ขายสินค้า</div>', 
            unsafe_allow_html=True
        )
        valid_dates = df['Date'].dropna().sort_values()
        if not valid_dates.empty:
            min_d, max_d = valid_dates.iloc[0], valid_dates.iloc[-1]
        else:
            min_d, max_d = datetime.date.today(), datetime.date.today()
            
        date_range = st.date_input("Select Date", value=[min_d, max_d], format="DD/MM/YYYY")
        start_date, end_date = date_range if len(date_range) == 2 else (min_d, max_d)

    with c_shop:
        st.write("") 
        st.write("") 
        shop_options = ['All Shops'] + sorted(df['Shop'].unique().tolist())
        selected_shop_ui = st.radio(
            "Shop", 
            shop_options, 
            horizontal=True, 
            label_visibility="collapsed"
        )

    # -- Filter Data --
    mask_date = (df['Date'] >= start_date) & (df['Date'] <= end_date)
    filtered_df = df.loc[mask_date]

    if selected_shop_ui != 'All Shops':
        filtered_df = filtered_df[filtered_df['Shop'] == selected_shop_ui]

    # -- Search Logic --
    if page == "เปรียบเทียบรายการสินค้า":
        st.markdown("---")
        st.markdown("### 🔍 ค้นหาและเลือกสินค้าเพื่อเปรียบเทียบจำนวนยอดขาย")
        available_skus = sorted(filtered_df['Clean_SKU'].unique().tolist())
        selected_skus = st.multiselect("เลือกสินค้าสินค้าหลายรายการ:", options=available_skus)
        if selected_skus:
            filtered_df = filtered_df[filtered_df['Clean_SKU'].isin(selected_skus)]

    # -- Calculation & HTML Generation --
    if not filtered_df.empty:
        # 1. Top Best Seller
        top_df = filtered_df.groupby('Clean_SKU')['Quantity'].sum().reset_index()
        top_df = top_df.sort_values('Quantity', ascending=False).head(20)
        top_rows_html = ""
        for idx, row in top_df.iterrows():
            icon = ' <span class="trophy-icon">🏆</span>' if idx == top_df.index[0] else ''
            top_rows_html += f"<tr><td>{icon}{row['Clean_SKU']}</td><td>{row['Quantity']:,}</td></tr>"

        # 2. Lower Seller
        lower_df = filtered_df.groupby('Clean_SKU')['Quantity'].sum().reset_index()
        lower_df = lower_df.sort_values('Quantity', ascending=True).head(10)
        lower_rows_html = ""
        for idx, row in lower_df.iterrows():
            lower_rows_html += f"<tr><td>{row['Clean_SKU']}</td><td>{row['Quantity']:,}</td></tr>"

        # 3. Chart Data
        chart_df = top_df.head(20)
        labels_js = json.dumps(chart_df['Clean_SKU'].tolist())
        data_values_js = json.dumps(chart_df['Quantity'].tolist())
        
        color_palette = [
            '#ffab91', '#81d4fa', '#b39ddb', '#ffcc80', '#a5d6a7', 
            '#f48fb1', '#80cbc4', '#ce93d8', '#ffab40', '#90caf9'
        ]
        bg_colors_js = json.dumps(
            [color_palette[i % len(color_palette)] for i in range(len(chart_df))]
        )

        display_shop_name = selected_shop_ui

        html_code = """
        <!DOCTYPE html>
        <html lang="th">
        <head>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@300;400;500;600;700&display=swap');
                * { box-sizing: border-box; }
                body { 
                    font-family: 'Noto Sans Thai', sans-serif; 
                    background-color: #0f1115; 
                    color: white; 
                    margin: 0; 
                    overflow: hidden; 
                    padding: 0 10px; 
                }
                .dashboard-container { 
                    display: grid; 
                    grid-template-columns: 1.8fr 1.2fr; 
                    gap: 15px; 
                    height: 98vh; 
                    width: 100%; 
                }
                .chart-area { display: flex; flex-direction: column; height: 100%; padding-right: 10px; }
                .chart-wrapper { flex-grow: 1; position: relative; width: 100%; }
                .sidebar { display: flex; flex-direction: column; gap: 15px; height: 100%; }
                .ranking-box { background-color: #d9d9d9; border-radius: 4px; overflow: hidden; display: flex; flex-direction: column; }
                .top-seller { flex: 2; min-height: 300px; }
                .lower-seller { flex: 1; min-height: 200px; }
                .ranking-header { background-color: #ffccbc; color: black; text-align: center; padding: 12px; font-size: 18px; font-weight: bold; }
                .lower { background-color: #81d4fa; }
                .table-scroll { overflow-y: auto; flex-grow: 1; width: 100%; }
                table { width: 100%; border-collapse: collapse; table-layout: fixed; }
                th { text-align: left; padding: 8px 12px; background-color: #cfd8dc; color: black; position: sticky; top: 0; }
                th:first-child { width: 75%; }
                th:last-child { width: 25%; text-align: right; }
                td { padding: 8px 12px; color: black; border-bottom: 1px solid #ccc; background-color: #e0e0e0; font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
                td:last-child { text-align: right; }
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
                    options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { color: '#333' }, ticks: { color: '#a0a0a0', font: {family: "'Noto Sans Thai', sans-serif"} } }, y: { grid: { display: false }, ticks: { color: '#a0a0a0', autoSkip: false, font: {family: "'Noto Sans Thai', sans-serif"} } } } }
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
# CASE 2: SPECIAL TAGS (ตะกร้าสินค้าร้าน Sim1 กับ Sim2)
# =================================================================================
elif page == "ตะกร้าสินค้าร้าน Sim1 กับ Sim2":
    
    st.markdown("---")
    
    c_date, c_space, c_search = st.columns([2, 0.5, 3])
    with c_date:
        valid_dates = df['Date'].dropna().sort_values()
        if not valid_dates.empty:
            min_d, max_d = valid_dates.iloc[0], valid_dates.iloc[-1]
        else:
            min_d = max_d = datetime.date.today()
            
        date_range = st.date_input(
            "Date Range", 
            value=[min_d, max_d], 
            format="DD/MM/YYYY",
            label_visibility="collapsed"
        )
        if len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date, end_date = min_d, max_d
    
    mask_date = (df['Date'] >= start_date) & (df['Date'] <= end_date)
    df_date_filtered = df.loc[mask_date]

    with c_search:
        available_products = sorted(df_date_filtered['Clean_SKU'].unique().tolist())
        selected_skus = st.multiselect(
            "ค้นหา หรือ เลือกสินค้าหลายตัวเทียบกันได้",
            options=available_products,
            placeholder="พิมพ์ชื่อรุ่นสินค้าเพื่อค้นหา...",
            label_visibility="collapsed"
        )

    st.write("") 
    
    tag_options = ["BCD", "BCDL", "CP", "CPL"]
    try:
        selected_tags = st.pills(
            "เลือก Tags", 
            options=tag_options, 
            default=tag_options, 
            selection_mode="multi", 
            label_visibility="collapsed"
        )
    except AttributeError as attr_err:
        logger.warning("st.pills fallback used: %s", attr_err)
        selected_tags = st.multiselect("เลือก Tags", options=tag_options, default=tag_options)

    if not selected_tags:
        st.error("กรุณาเลือก Tag อย่างน้อย 1 รายการ")
        st.stop()

    df_date_filtered['Tag_Group'] = df_date_filtered['product_tag'].fillna('BCD')

    mask = df_date_filtered['Shop'].isin(['SIM1', 'SIM2'])
    mask &= df_date_filtered['Tag_Group'].isin(selected_tags)
    
    if selected_skus:
        mask &= df_date_filtered['Clean_SKU'].isin(selected_skus)
    
    df_final = df_date_filtered.loc[mask]

    st.markdown("---")
    col1, col2 = st.columns(2, gap="medium")
    
    COLOR_MAP = {"BCD": "#b39ddb", "BCDL": "#ef9a9a", "CP": "#3949ab", "CPL": "#c2185b"}

    def plot_shop_chart(shop_name: str, dataframe: pd.DataFrame) -> None:
        """Plot top 40 best-selling SKUs for a specific shop."""
        shop_df = dataframe[dataframe['Shop'] == shop_name]
        
        if shop_df.empty:
            st.markdown(
                f'<div class="shop-header-sarabun">ร้าน {shop_name}</div>', 
                unsafe_allow_html=True
            )
            st.info("ไม่พบข้อมูล")
            return

        total_sales_per_sku = shop_df.groupby('Clean_SKU')['Quantity'].sum().reset_index()
        top_40_skus_df = total_sales_per_sku.sort_values('Quantity', ascending=False).head(40)
        sorted_skus = top_40_skus_df['Clean_SKU'].tolist()

        chart_data = shop_df[shop_df['Clean_SKU'].isin(sorted_skus)].groupby(
            ['Clean_SKU', 'Tag_Group']
        )['Quantity'].sum().reset_index()

        fig = px.bar(
            chart_data, 
            y="Clean_SKU", 
            x="Quantity", 
            color="Tag_Group", 
            orientation='h', 
            color_discrete_map=COLOR_MAP, 
            category_orders={"Clean_SKU": sorted_skus},
            text="Quantity"
        )
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white', family='Noto Sans Thai'),
            showlegend=True, 
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=None
            ),
            margin=dict(l=0, r=0, t=10, b=0),
            height=max(400, 100 + (len(sorted_skus) * 40)),
            xaxis=dict(showgrid=True, gridcolor='#333'), 
            yaxis=dict(title="", autorange="reversed") 
        )
        fig.update_traces(textposition='inside', insidetextanchor='middle')

        st.markdown(
            f'<div class="shop-header-sarabun">ร้าน {shop_name} (Top 40)</div>', 
            unsafe_allow_html=True
        )
        st.plotly_chart(fig, use_container_width=True)

    with col1: 
        plot_shop_chart("SIM1", df_final)
    with col2: 
        plot_shop_chart("SIM2", df_final)

# =================================================================================
# CASE 3: DAILY SALES LINE CHART
# =================================================================================
elif page == "กราฟเส้นยอดขายรายวัน":
    
    st.markdown(
        '<div class="shop-header-sarabun">📈 กราฟเส้นแนวโน้มยอดขายสินค้ารายวัน</div>', 
        unsafe_allow_html=True
    )
    st.markdown("---")

    c_date, c_space, c_shop = st.columns([2, 0.5, 3])
    
    with c_date:
        valid_dates = df['Date'].dropna().sort_values()
        if not valid_dates.empty:
            min_d, max_d = valid_dates.iloc[0], valid_dates.iloc[-1]
        else:
            min_d, max_d = datetime.date.today(), datetime.date.today()
        
        date_range = st.date_input(
            "เลือกช่วงวันที่", 
            value=[min_d, max_d], 
            format="DD/MM/YYYY",
            label_visibility="collapsed"
        )
        if len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date, end_date = min_d, max_d

    mask_date = (df['Date'] >= start_date) & (df['Date'] <= end_date)
    df_trend = df.loc[mask_date]

    with c_shop:
        shop_options = ['All Shops'] + sorted(df_trend['Shop'].unique().tolist())
        selected_shop_ui = st.radio(
            "Shop", 
            shop_options, 
            horizontal=True, 
            label_visibility="collapsed"
        )

    if selected_shop_ui != 'All Shops':
        df_trend = df_trend[df_trend['Shop'] == selected_shop_ui]

    top_sales_df = df_trend.groupby('Clean_SKU')['Quantity'].sum().reset_index()
    top_sales_df = top_sales_df.sort_values('Quantity', ascending=False)
    available_skus = top_sales_df['Clean_SKU'].tolist()

    st.write("") 
    selected_skus = st.multiselect(
        "🔍 ค้นหาและเลือกสินค้า (เพื่อเปรียบเทียบจำนวนยอดขาย):",
        options=available_skus,
        default=available_skus[:6] if len(available_skus) >= 6 else available_skus
    )

    if not selected_skus:
        st.warning("⚠️ กรุณาเลือกสินค้าอย่างน้อย 1 รายการเพื่อแสดงกราฟ")
    else:
        df_chart = df_trend[df_trend['Clean_SKU'].isin(selected_skus)]
        df_chart_grouped = df_chart.groupby(['Date', 'Clean_SKU'])['Quantity'].sum().reset_index()
        df_chart_grouped = df_chart_grouped.sort_values(['Date'])

        fig = px.line(
            df_chart_grouped,
            x="Date",
            y="Quantity",
            color="Clean_SKU",
            markers=True,
            text="Quantity", 
            category_orders={"Clean_SKU": selected_skus} 
        )

        fig.update_traces(textposition="top center", textfont=dict(size=12))
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white', family='Noto Sans Thai'),
            xaxis=dict(showgrid=True, gridcolor='#333', title="วันที่"),
            yaxis=dict(showgrid=True, gridcolor='#333', title="จำนวน (ชิ้น)"),
            hovermode="x unified", 
            legend=dict(
                orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1, title=None
            ),
            height=600,
            margin=dict(l=20, r=20, t=50, b=20)
        )

        st.plotly_chart(fig, use_container_width=True)

# =================================================================================
# CASE 5: SECOND-HAND SALES VS STOCK
# =================================================================================
elif page == "กราฟเทียบยอดขายเฉพาะสินค้ามือ 2":
    st.markdown(
        '<div class="shop-header-sarabun">📊 เทียบยอดขาย และ Stock คงเหลือ (ร้านมือ 2)</div>', 
        unsafe_allow_html=True
    )
    st.markdown("---")

    col_date, col_space = st.columns([4, 6])
    with col_date:
        st.markdown(
            '<div class="date-header-label">📅 เลือกช่วงวันที่ต้องการดูยอดขาย</div>', 
            unsafe_allow_html=True
        )
        date_range = st.date_input(
            "ช่วงวันที่ขายสินค้า:",
            value=(datetime.date.today() - datetime.timedelta(days=7), datetime.date.today()),
            key="secondhand_date_filter",
            label_visibility="collapsed" 
        )

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        st.info("กรุณาเลือกวันที่เริ่มต้นและสิ้นสุดให้ครบถ้วนเพื่อดูข้อมูลยอดขาย")
        st.stop()

    with st.spinner("กำลังโหลดข้อมูล Stock และยอดขาย..."):
        supabase_client = init_connection()  
        df_chart = fetch_secondhand_data(df, supabase_client, start_date, end_date)

    if df_chart.empty:
        st.warning("⚠️ ไม่พบข้อมูลยอดขายหรือ Stock สินค้ามือ 2 ในระบบ หรือข้อมูลไม่ตรงกัน")
    else:
        st.write("")
        available_products = sorted(df_chart["product_name"].unique().tolist())
        selected_products = st.multiselect(
            "🔍 ค้นหาและเลือกสินค้าเพื่อเปรียบเทียบ (เว้นว่างไว้เพื่อแสดงทั้งหมด):",
            options=available_products,
            placeholder="พิมพ์ชื่อรุ่นสินค้าเพื่อค้นหา...",
        )

        df_plot = df_chart.copy()
        if selected_products:
            df_plot = df_plot[df_plot["product_name"].isin(selected_products)]

        if df_plot.empty:
            st.info("กรุณาเลือกสินค้าเพื่อแสดงกราฟ")
            st.stop()

        chart_title = (
            f"เปรียบเทียบยอดขาย ({start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}) "
            f"และ Stock สินค้ามือ 2 ปัจจุบัน"
        )
        
        fig = px.bar(
            df_plot,
            x="product_name",
            y="quantity",
            color="data_type",
            barmode="group",
            text_auto=True,
            color_discrete_map={"Stock คงเหลือ": "#00bcd4", "ยอดขาย (Sold)": "#ff5722"},
            title=chart_title
        )
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white', family='Noto Sans Thai'),
            xaxis=dict(showgrid=False, title="ชื่อสินค้า (Product)"),
            yaxis=dict(showgrid=True, gridcolor='#333', title="จำนวน (ชิ้น)"),
            hovermode="x unified",
            legend_title_text="ประเภทข้อมูล",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        fig.update_traces(textposition="outside", textfont=dict(size=12))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown(
            "<br><h4 style='text-align: center;'>🏆 อันดับสินค้า Top 10 (เรียงตาม Stock และ ยอดขาย)</h4><hr>", 
            unsafe_allow_html=True
        )
        
        col_left, col_right = st.columns(2)

        df_wide = df_plot.pivot(
            index="product_name", columns="data_type", values="quantity"
        ).reset_index()
        col_stock = "Stock คงเหลือ"
        col_sold = "ยอดขาย (Sold)"
        
        if col_stock in df_wide.columns and col_sold in df_wide.columns:
            
            excluded_keywords = [
                "สายชาร์จ usb-c to usb-c",
                "สายชาร์จ usb-c to lightning สภาพดี 90%",
                "หัวชาร์จ มือสอง",
                "adapter สภาพดี 90%",
                "สาย lightning มือสอง"
            ]
            
            def is_excluded(product_name: str) -> bool:
                """Checks if the product name contains any excluded keywords."""
                name_lower = str(product_name).strip().lower()
                return any(keyword in name_lower for keyword in excluded_keywords)

            mask_keep = ~df_wide["product_name"].apply(is_excluded)
            df_wide = df_wide[mask_keep]
            
            with col_left:
                df_top_stock = df_wide.nlargest(10, col_stock)
                
                df_top_stock_melted = df_top_stock.melt(
                    id_vars="product_name", 
                    value_vars=[col_stock, col_sold],
                    var_name="data_type", 
                    value_name="quantity"
                )
                
                fig_stock = px.bar(
                    df_top_stock_melted,
                    x="product_name",
                    y="quantity",
                    color="data_type",
                    barmode="group",
                    text_auto=True,
                    color_discrete_map={col_stock: "#00bcd4", col_sold: "#ff5722"},
                    title="📦 Top 10 สินค้าที่มี Stock คงเหลือมากที่สุด"
                )
                fig_stock.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white', family='Noto Sans Thai'),
                    xaxis=dict(showgrid=False, title="ชื่อสินค้า (Product)"),
                    yaxis=dict(showgrid=True, gridcolor='#333', title="จำนวน (ชิ้น)"),
                    legend_title_text="",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                fig_stock.update_traces(textposition="outside", textfont=dict(size=12))
                st.plotly_chart(fig_stock, use_container_width=True)

            with col_right:
                df_top_sales = df_wide[df_wide[col_sold] > 0].nlargest(10, col_sold)
                
                if df_top_sales.empty:
                    st.info("ยังไม่มียอดขายในช่วงวันที่เลือกครับ")
                else:
                    df_top_sales_melted = df_top_sales.melt(
                        id_vars="product_name", 
                        value_vars=[col_stock, col_sold],
                        var_name="data_type", 
                        value_name="quantity"
                    )
                    
                    fig_sales = px.bar(
                        df_top_sales_melted,
                        x="product_name",
                        y="quantity",
                        color="data_type",
                        barmode="group",
                        text_auto=True,
                        color_discrete_map={col_stock: "#00bcd4", col_sold: "#ff5722"},
                        title="🔥 Top 10 สินค้าที่ขายดีที่สุด (ช่วงวันที่เลือก)"
                    )
                    fig_sales.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='white', family='Noto Sans Thai'),
                        xaxis=dict(showgrid=False, title="ชื่อสินค้า (Product)"),
                        yaxis=dict(showgrid=True, gridcolor='#333', title="จำนวน (ชิ้น)"),
                        legend_title_text="",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    fig_sales.update_traces(textposition="outside", textfont=dict(size=12))
                    st.plotly_chart(fig_sales, use_container_width=True)

            st.markdown(
                "<br><br><h4 style='text-align: center;'>⚠️ แจ้งเตือนสินค้าค้างสต๊อก (ยอดขายน้อย แต่ Stock เหลือเยอะ) Top 10</h4><hr>", 
                unsafe_allow_html=True
            )

            df_worst_sales = df_wide.sort_values(
                by=[col_sold, col_stock], 
                ascending=[True, False]
            ).head(10)
            
            if df_worst_sales.empty:
                st.info("ไม่มีข้อมูลสินค้าค้างสต๊อกครับ")
            else:
                col_chart, col_table = st.columns([6, 4])
                
                with col_chart:
                    df_worst_melted = df_worst_sales.melt(
                        id_vars="product_name", 
                        value_vars=[col_stock, col_sold],
                        var_name="data_type", 
                        value_name="quantity"
                    )
                    
                    fig_worst = px.bar(
                        df_worst_melted,
                        x="product_name",
                        y="quantity",
                        color="data_type",
                        barmode="group",
                        text_auto=True,
                        color_discrete_map={col_stock: "#00bcd4", col_sold: "#ff5722"},
                        title="📊 กราฟ Top 10 สินค้าจมค้างสต๊อก"
                    )
                    
                    fig_worst.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='white', family='Noto Sans Thai'),
                        xaxis=dict(showgrid=False, title="ชื่อสินค้า (Product)"),
                        yaxis=dict(showgrid=True, gridcolor='#333', title="จำนวน (ชิ้น)"),
                        legend_title_text="",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    
                    fig_worst.update_traces(textposition="outside", textfont=dict(size=12))
                    st.plotly_chart(fig_worst, use_container_width=True)

                with col_table:
                    st.markdown(
                        "<br><h5>📑 ตารางสินค้าที่มียอดขายแย่ และ Stock คงเหลือเยอะ</h5>", 
                        unsafe_allow_html=True
                    )
                    
                    df_display = df_worst_sales[["product_name", col_stock, col_sold]].copy()
                    
                    df_display.rename(columns={
                        "product_name": "ชื่อสินค้า",
                        col_stock: "ยอดคงเหลือใน Stock",
                        col_sold: "ยอดขาย"
                    }, inplace=True)
                    
                    df_display["ยอดคงเหลือใน Stock"] = df_display["ยอดคงเหลือใน Stock"].astype(int)
                    df_display["ยอดขาย"] = df_display["ยอดขาย"].astype(int)
                    
                    df_display.reset_index(drop=True, inplace=True)
                    df_display.index += 1
                    
                    st.dataframe(df_display, use_container_width=True)

            st.markdown(
                "<br><br><h4 style='text-align: center;'>📋 ตารางสรุปข้อมูลยอดขายและ Stock ทั้งหมด (ตามช่วงเวลาที่เลือก)</h4><hr>", 
                unsafe_allow_html=True
            )

            df_full_wide = df_chart.pivot(
                index="product_name", columns="data_type", values="quantity"
            ).reset_index()
            
            if "Stock คงเหลือ" in df_full_wide.columns and "ยอดขาย (Sold)" in df_full_wide.columns:
                df_full_display = df_full_wide[["product_name", "Stock คงเหลือ", "ยอดขาย (Sold)"]].copy()
                
                df_full_display.rename(columns={
                    "product_name": "ชื่อสินค้า",
                    "Stock คงเหลือ": "ยอดคงเหลือใน Stock",
                    "ยอดขาย (Sold)": "ยอดขาย"
                }, inplace=True)
                
                df_full_display = df_full_display.sort_values(by="ยอดขาย", ascending=False)
                
                df_full_display["ยอดคงเหลือใน Stock"] = df_full_display["ยอดคงเหลือใน Stock"].fillna(0).astype(int)
                df_full_display["ยอดขาย"] = df_full_display["ยอดขาย"].fillna(0).astype(int)
                
                df_full_display.reset_index(drop=True, inplace=True)
                df_full_display.index += 1
                
                st.dataframe(df_full_display, use_container_width=True, height=500)
            else:
                st.info("ไม่สามารถสร้างตารางสรุปได้ เนื่องจากข้อมูลไม่ครบถ้วน")
