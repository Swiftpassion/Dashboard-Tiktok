import streamlit as st
import pandas as pd
import json
from supabase import create_client, Client
import streamlit.components.v1 as components
import datetime

# ==========================================
# 1. Config & Styles
# ==========================================
st.set_page_config(page_title="Sales Dashboard", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700&display=swap');
    
    /* Global Font */
    html, body, [class*="css"] {
        font-family: 'Kanit', sans-serif;
    }

    /* Block Container */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 0rem !important;
    }

    /* --- Date Input --- */
    div[data-testid="stDateInput"] label { display: none; }
    div[data-baseweb="input"] {
        background-color: transparent !important;
        border: none !important;
        border-bottom: 3px solid #ff7043 !important;
        border-radius: 0px !important;
    }
    input[class*="st-"] {
        color: #ffffff !important;
        font-size: 30px !important;
        font-weight: 700 !important;
        font-family: 'Kanit', sans-serif !important;
        height: auto !important;
        padding-bottom: 5px !important;
    }
    div[data-baseweb="input"] svg {
        fill: #ff7043 !important;
        width: 24px !important;
        height: 24px !important;
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

    /* --- Multiselect (Search Box) Styles --- */
    .stMultiSelect label {
        color: #ff7043 !important;
        font-size: 20px !important;
        font-weight: 600;
        margin-bottom: 10px;
    }
    div[data-baseweb="select"] > div {
        background-color: #2b2b2b !important;
        border-color: #555 !important;
        color: white !important;
    }
    div[data-baseweb="tag"] {
        background-color: #ff7043 !important;
        border-radius: 5px;
    }
    span[data-baseweb="tag"] span {
        color: #000000 !important;
        font-weight: 600;
    }
    
    /* Header Label */
    .date-header-label {
        font-family: 'Sarabun', sans-serif;
        font-size: 22px;
        color: #a0a0a0;
        margin-bottom: -10px;
        font-weight: 400;
    }
    
    /* Sidebar Styles */
    section[data-testid="stSidebar"] {
        background-color: #111;
        border-right: 1px solid #333;
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
        response = supabase.table('orders').select(
            '"Shipped Time", "Warehouse Name", "Seller SKU", "Product Name", "Quantity"'
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
        import re
        s = re.sub(r'\b(gb|ram|rom)\b', '', s)
        return re.sub(r'\s+', ' ', s).strip().title()

    df['Shop'] = df['Warehouse Name'].apply(map_shop)
    df['Clean_SKU'] = df['Seller SKU'].apply(clean_sku)
    return df

# ==========================================
# 4. Main App Layout
# ==========================================
df_raw = load_data()

if not df_raw.empty:
    df = process_data(df_raw)

    # --- 4.1 Sidebar Menu ---
    with st.sidebar:
        st.title("เมนูหลัก")
        page = st.radio(
            "เลือกหน้าแสดงผล:",
            ["ภาพรวม (Overview)", "ค้นหารายสินค้า (Search)"],
            index=0
        )
        st.markdown("---")
        st.caption("Sales Dashboard v2.0")

    # --- 4.2 Global Filter (Date & Shop) ---
    c_date, c_space, c_shop = st.columns([2, 0.2, 2.5])
    
    with c_date:
        st.markdown('<div class="date-header-label">ช่วงวันที่ขายสินค้า</div>', unsafe_allow_html=True)
        valid_dates = df['Date'].dropna().sort_values()
        if not valid_dates.empty:
            min_d, max_d = valid_dates.iloc[0], valid_dates.iloc[-1]
        else:
            min_d, max_d = datetime.date.today(), datetime.date.today()

        date_range = st.date_input(
            "Select Date", 
            value=[min_d, max_d],
            min_value=min_d,
            max_value=max_d,
            format="DD/MM/YYYY" 
        )
        if len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date, end_date = min_d, max_d

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

    # กรองข้อมูลเบื้องต้น (วันที่ & ร้านค้า)
    mask = (df['Date'] >= start_date) & (df['Date'] <= end_date)
    if selected_shop_ui != 'All Shops':
        mask = mask & (df['Shop'] == selected_shop_ui)
    
    filtered_df = df.loc[mask]

    # --- 4.3 Page Specific Logic ---
    
    # ถ้าเลือกหน้า Search -> ให้แสดง Multiselect และกรองข้อมูลเพิ่ม
    if page == "ค้นหารายสินค้า (Search)":
        st.markdown("---")
        st.markdown("### 🔍 ค้นหาและเลือกสินค้า (Multiselect)")
        
        # ดึงรายการสินค้าทั้งหมดที่มีในช่วงเวลานั้น
        available_skus = sorted(filtered_df['Clean_SKU'].unique().tolist())
        
        selected_skus = st.multiselect(
            "เลือกสินค้าที่ต้องการดูยอดขาย (เลือกได้หลายรายการ):",
            options=available_skus,
            placeholder="พิมพ์ชื่อสินค้า..."
        )
        
        # ถ้ามีการเลือกสินค้า ให้กรอง DataFrame อีกรอบ
        if selected_skus:
            filtered_df = filtered_df[filtered_df['Clean_SKU'].isin(selected_skus)]
            st.info(f"กำลังแสดงผลข้อมูลของสินค้า {len(selected_skus)} รายการที่เลือก")
        else:
            st.warning("💡 กรุณาเลือกสินค้าอย่างน้อย 1 รายการ หรือดูภาพรวมทั้งหมดด้านล่าง")

    # ==========================================
    # 5. Calculation & HTML Generation
    # ==========================================
    
    if not filtered_df.empty:
        # 1. Top Best Seller (20 items)
        # ถ้าเลือก Search แบบเจาะจง อาจจะมีไม่ถึง 20 ก็จะแสดงเท่าที่มี
        top_df = filtered_df.groupby('Clean_SKU')['Quantity'].sum().reset_index().sort_values('Quantity', ascending=False).head(20)
        
        top_rows_html = ""
        for idx, row in top_df.iterrows():
            # ใส่ถ้วยรางวัลแค่อันดับ 1
            icon = ' <span class="trophy-icon">🏆</span>' if idx == top_df.index[0] else ''
            top_rows_html += f"<tr><td>{icon}{row['Clean_SKU']}</td><td>{row['Quantity']:,}</td></tr>"

        # 2. Lower Seller (Bottom 10 items)
        lower_df = filtered_df.groupby('Clean_SKU')['Quantity'].sum().reset_index().sort_values('Quantity', ascending=True).head(10)
        lower_rows_html = ""
        for idx, row in lower_df.iterrows():
            lower_rows_html += f"<tr><td>{row['Clean_SKU']}</td><td>{row['Quantity']:,}</td></tr>"

        # 3. Chart Data (Top 20)
        chart_df = top_df.head(20)
        labels_js = json.dumps(chart_df['Clean_SKU'].tolist())
        data_values_js = json.dumps(chart_df['Quantity'].tolist())
        
        # Color Palette
        color_palette = [
            '#ffab91', '#81d4fa', '#b39ddb', '#ffcc80', '#a5d6a7', 
            '#f48fb1', '#80cbc4', '#ce93d8', '#ffab40', '#90caf9',
            '#ef9a9a', '#b0bec5', '#fff59d', '#bcaaa4', '#e6ee9c',
            '#ff8a65', '#4fc3f7', '#9575cd', '#ffd54f', '#81c784' 
        ]
        bg_colors = []
        for i in range(len(chart_df)):
            bg_colors.append(color_palette[i % len(color_palette)])
        bg_colors_js = json.dumps(bg_colors)

    else:
        top_rows_html = "<tr><td>ไม่พบข้อมูล</td><td>-</td></tr>"
        lower_rows_html = "<tr><td>ไม่พบข้อมูล</td><td>-</td></tr>"
        labels_js, data_values_js, bg_colors_js = "[]", "[]", "[]"

    # HTML Code (Full Template)
    html_code = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>Sales Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <style>
        body {
            font-family: 'Kanit', sans-serif;
            background-color: #0f1115;
            margin: 0;
            padding: 0;
            color: #ffffff;
            box-sizing: border-box;
            overflow: hidden; 
        }

        /* --- Grid Layout --- */
        .dashboard-container {
            display: grid;
            grid-template-columns: 65% 35%; 
            gap: 20px;
            margin-top: 10px;
            height: 98vh;
            width: 100%;
        }

        @media screen and (max-width: 1024px) {
            .dashboard-container {
                grid-template-columns: 1fr;
                height: auto;
                overflow-y: auto;
            }
            .chart-area {
                height: 600px !important;
            }
            .sidebar {
                height: 800px !important;
            }
        }

        /* --- Chart Area --- */
        .chart-area {
            display: flex;
            flex-direction: column;
            padding-right: 10px;
            height: 100%;
        }
        
        .chart-title {
            color: #a0a0a0;
            font-size: 16px;
            margin-bottom: 10px;
        }

        .chart-wrapper {
            flex-grow: 1;
            position: relative;
            min-height: 0;
            width: 100%;
        }

        /* --- Sidebar Area (Tables) --- */
        .sidebar {
            display: flex;
            flex-direction: column;
            gap: 15px;
            height: 100%;
            min-height: 600px;
        }

        .ranking-box {
            background-color: #d9d9d9;
            border-radius: 4px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }

        /* Top Seller (2/3 พื้นที่) */
        .ranking-box.top-seller { 
            flex: 2; 
            min-height: 300px;
        }
        
        /* Lower Seller (1/3 พื้นที่) */
        .ranking-box.lower-seller { 
            flex: 1; 
            min-height: 200px;
        }

        .ranking-header {
            background-color: #ffccbc;
            color: #000000;
            text-align: center;
            padding: 12px;
            font-size: 18px;
            font-weight: 600;
            flex-shrink: 0;
        }
        
        .ranking-header.lower { background-color: #81d4fa; }

        .table-scroll {
            overflow-y: auto;
            flex-grow: 1;
            min-height: 0; 
        }

        .ranking-table {
            width: 100%;
            border-collapse: collapse;
        }

        .ranking-table th {
            text-align: left;
            padding: 8px 12px;
            background-color: #cfd8dc;
            color: #000;
            font-size: 14px;
            font-weight: 600;
            position: sticky; top: 0;
            z-index: 10;
        }
        
        .ranking-table th:last-child { text-align: right; }

        .ranking-table td {
            padding: 8px 12px;
            color: #000;
            border-bottom: 1px solid #ccc;
            font-size: 14px;
            background-color: #e0e0e0;
        }

        .ranking-table td:last-child { text-align: right; }
        .trophy-icon { margin-right: 5px; color: #cca000; }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #2c2c2c; }
        ::-webkit-scrollbar-thumb { background: #555; border-radius: 3px; }
    </style>
</head>
<body>

    <div class="dashboard-container">
        <div class="chart-area">
            <div class="chart-title">ยอดขายสินค้า (__SELECTED_SHOP__)</div>
            <div class="chart-wrapper">
                <canvas id="salesChart"></canvas>
            </div>
        </div>

        <div class="sidebar">
            <div class="ranking-box top-seller">
                <div class="ranking-header">TOP Best Seller</div>
                <div class="table-scroll">
                    <table class="ranking-table">
                        <thead>
                            <tr>
                                <th>สินค้า</th>
                                <th>จำนวน</th>
                            </tr>
                        </thead>
                        <tbody>
                            __TOP_ROWS__
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="ranking-box lower-seller">
                <div class="ranking-header lower">⬇ Lower Seller</div>
                <div class="table-scroll">
                    <table class="ranking-table">
                        <thead>
                            <tr>
                                <th>สินค้า</th>
                                <th>จำนวน</th>
                            </tr>
                        </thead>
                        <tbody>
                            __LOWER_ROWS__
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
        const ctx = document.getElementById('salesChart').getContext('2d');
        
        const labels = __CHART_LABELS__;
        const dataValues = __CHART_DATA__;
        const bgColors = __CHART_COLORS__;

        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Sales',
                    data: dataValues,
                    backgroundColor: bgColors,
                    maxBarThickness: 40,
                    borderRadius: 4
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                layout: {
                    padding: { right: 20 }
                },
                scales: {
                    x: {
                        grid: { color: '#333' },
                        ticks: { color: '#a0a0a0', font: { family: 'Kanit' } }
                    },
                    y: {
                        grid: { display: false },
                        ticks: { 
                            color: '#a0a0a0', 
                            font: { family: 'Kanit', size: 12 },
                            autoSkip: false
                        }
                    }
                }
            }
        });
    </script>
</body>
</html>
"""

    # แทนที่ข้อมูลจริงลงไปใน HTML
    html_code = html_code.replace("__SELECTED_SHOP__", selected_shop_ui)
    html_code = html_code.replace("__TOP_ROWS__", top_rows_html)
    html_code = html_code.replace("__LOWER_ROWS__", lower_rows_html)
    html_code = html_code.replace("__CHART_LABELS__", labels_js)
    html_code = html_code.replace("__CHART_DATA__", data_values_js)
    html_code = html_code.replace("__CHART_COLORS__", bg_colors_js)

    # แสดงผล HTML
    components.html(html_code, height=1400, scrolling=True)

else:
    st.warning("No Data found in Supabase")