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

# CSS: ปรับแต่งให้ "โปร่งใส" (Transparent) และดู Clean ที่สุด
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Kanit', sans-serif;
    }

    /* ซ่อน Header ปกติของ Streamlit */
    header {visibility: hidden;}
    
    /* 1. ปรับ Date Input ให้พื้นหลังใส และเหลือแค่เส้นขอบล่างบางๆ (Minimal) */
    div[data-baseweb="input"] {
        background-color: transparent !important; /* พื้นหลังใส */
        border: none !important;
        border-bottom: 2px solid #ff7043 !important; /* เหลือแค่ขอบล่างสีส้ม */
        border-radius: 0px !important;
        color: #333 !important;
    }
    
    /* ปรับตัว Text ภายใน Input */
    div[data-testid="stDateInput"] label {
        display: none; /* ซ่อน Label คำว่า "ช่วงวันที่" ออกไปเลยเพื่อความคลีน */
    }

    /* 2. ปรับ Radio Button (Shop Selector) ให้พื้นหลังใส */
    div.row-widget.stRadio > div {
        background-color: transparent;
        gap: 10px;
    }
    
    div.row-widget.stRadio > div > label {
        background-color: transparent;
        border: 1px solid #ddd;
        border-radius: 20px !important; /* ปรับเป็นวงรีมนๆ */
        padding: 5px 20px;
        transition: all 0.3s;
    }
    
    div.row-widget.stRadio > div > label:hover {
        border-color: #ff7043;
        color: #ff7043;
    }

    /* Active State ของปุ่มเลือก Shop */
    div.row-widget.stRadio > div > label[data-checked="true"] {
        background-color: #ff7043 !important;
        color: white !important;
        border-color: #ff7043 !important;
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

    # จัด Layout ส่วนควบคุม (Controls)
    c_date, c_space, c_shop = st.columns([1.5, 0.5, 2])
    
    with c_date:
        valid_dates = df['Date'].dropna().sort_values()
        if not valid_dates.empty:
            min_d, max_d = valid_dates.iloc[0], valid_dates.iloc[-1]
        else:
            min_d, max_d = datetime.date.today(), datetime.date.today()

        # Date Input
        date_range = st.date_input(
            "Select Date",
            value=[min_d, max_d],
            min_value=min_d,
            max_value=max_d
        )
        if len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date, end_date = min_d, max_d
            
        # สร้าง string วันที่เพื่อไปแสดงใน HTML
        date_display_str = f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}"

    with c_shop:
        # Shop Selector
        shop_options = ['All Shops'] + sorted(df['Shop'].unique().tolist())
        selected_shop_ui = st.radio(
            "Shop",
            shop_options,
            horizontal=True,
            label_visibility="collapsed"
        )

    # Filter Logic
    mask = (df['Date'] >= start_date) & (df['Date'] <= end_date)
    if selected_shop_ui != 'All Shops':
        mask = mask & (df['Shop'] == selected_shop_ui)
    
    filtered_df = df.loc[mask]

    # ==========================================
    # 5. HTML/JS View (Dynamic Data Injection)
    # ==========================================
    
    if not filtered_df.empty:
        # 1. เตรียมข้อมูลตาราง Top 20
        top10_df = filtered_df.groupby('Clean_SKU')['Quantity'].sum().reset_index().sort_values('Quantity', ascending=False).head(20)
        top10_rows_html = ""
        for idx, row in top10_df.iterrows():
            # ใส่ไอคอนถ้วยรางวัลแค่แถวแรก
            icon = ' <span class="trophy-icon">🏆</span>' if idx == top10_df.index[0] else ''
            top10_rows_html += f"<tr><td>{icon}{row['Clean_SKU']}</td><td>{row['Quantity']:,}</td></tr>"

        # 2. เตรียมข้อมูลกราฟ (Chart.js)
        # เอา Top 10 ตัวแรกมาแสดงในกราฟ
        chart_df = top10_df.head(10) 
        labels_js = json.dumps(chart_df['Clean_SKU'].tolist())
        data_values_js = json.dumps(chart_df['Quantity'].tolist())
        
    else:
        top10_rows_html = "<tr><td>ไม่พบข้อมูล</td><td>-</td></tr>"
        labels_js = "[]"
        data_values_js = "[]"
        date_display_str += " (ไม่พบข้อมูล)"

    # HTML Template (ใช้ตัวแปรแทนที่ค่า Hardcoded)
    html_code = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sales Dashboard Dark Mode</title>
    <link href="https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <style>
        :root {
            --bg-dark: #0f1115;
            --text-white: #ffffff;
            --text-gray: #a0a0a0;
            --accent-orange: #ff7043;
            --bar-salmon: #ffab91;
            --table-header-bg: #ffccbc;
            --table-text-black: #000000;
        }

        body {
            font-family: 'Kanit', sans-serif;
            background-color: var(--bg-dark);
            margin: 0;
            padding: 20px;
            color: var(--text-white);
            box-sizing: border-box;
            overflow-x: hidden; /* ป้องกัน scroll แนวนอนเกินจำเป็น */
        }

        /* --- Header Section --- */
        .top-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            margin-bottom: 30px;
            padding-bottom: 10px;
            border-bottom: 1px solid #333;
        }

        .date-section {
            display: flex;
            flex-direction: column;
            gap: 5px;
            padding-bottom: 5px;
        }

        .date-label {
            font-size: 18px;
            color: var(--text-gray);
            font-weight: 300;
        }

        .date-display {
            font-size: 28px;
            font-weight: 500;
            color: var(--text-white);
            position: relative;
            padding-bottom: 10px;
        }

        .date-display::after {
            content: '';
            position: absolute;
            left: 0;
            bottom: 0;
            width: 100%;
            height: 3px;
            background-color: var(--accent-orange);
        }

        /* Dashboard Grid */
        .dashboard-container {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 30px;
        }

        /* Chart Area */
        .chart-title {
            color: var(--text-gray);
            font-size: 16px;
            margin-bottom: 15px;
        }

        /* Table Area */
        .ranking-box {
            background-color: #d9d9d9;
            border-radius: 4px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            height: 600px;
        }

        .ranking-header {
            background-color: var(--table-header-bg);
            color: var(--table-text-black);
            text-align: center;
            padding: 15px;
            font-size: 18px;
            font-weight: 600;
        }

        .table-scroll {
            overflow-y: auto;
            flex-grow: 1;
        }

        .ranking-table {
            width: 100%;
            border-collapse: collapse;
        }

        .ranking-table th {
            text-align: left;
            padding: 10px 15px;
            background-color: #cfd8dc;
            color: #000;
            font-size: 14px;
            font-weight: 600;
            position: sticky; top: 0;
        }
        
        .ranking-table th:last-child { text-align: right; }

        .ranking-table td {
            padding: 10px 15px;
            color: #000;
            border-bottom: 1px solid #ccc;
            font-size: 14px;
            background-color: #e0e0e0;
        }

        .ranking-table td:last-child { text-align: right; }
        .trophy-icon { margin-right: 5px; color: #cca000; }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #2c2c2c; }
        ::-webkit-scrollbar-thumb { background: #555; border-radius: 4px; }
    </style>
</head>
<body>

    <div class="top-header">
        <div class="date-section">
            <div class="date-label">ช่วงวันที่ขายสินค้า</div>
            <div class="date-display">__DATE_DISPLAY__</div>
        </div>
        <div style="font-size: 18px; color: #a0a0a0;">
            SHOP: <span style="color: #fff; font-weight: bold;">__SELECTED_SHOP__</span>
        </div>
    </div>

    <div class="dashboard-container">
        
        <div class="chart-area">
            <div class="chart-title">ยอดขายสินค้า (__SELECTED_SHOP__)</div>
            <div style="height: 550px; width: 100%;">
                <canvas id="salesChart"></canvas>
            </div>
        </div>

        <div class="sidebar">
            <div class="ranking-box">
                <div class="ranking-header">TOP 20 Best Seller</div>
                <div class="table-scroll">
                    <table class="ranking-table">
                        <thead>
                            <tr>
                                <th>สินค้า</th>
                                <th>จำนวน</th>
                            </tr>
                        </thead>
                        <tbody>
                            __TABLE_ROWS__
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
        const ctx = document.getElementById('salesChart').getContext('2d');
        
        // จุดที่ 3: แทรกข้อมูลกราฟ
        const labels = __CHART_LABELS__;
        const dataValues = __CHART_DATA__;

        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Sales',
                    data: dataValues,
                    backgroundColor: '#ffab91',
                    barThickness: 25,
                    borderRadius: 4
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: {
                        grid: { color: '#333' },
                        ticks: { color: '#a0a0a0', font: { family: 'Kanit' } }
                    },
                    y: {
                        grid: { display: false },
                        ticks: { color: '#a0a0a0', font: { family: 'Kanit', size: 14 } }
                    }
                }
            }
        });
    </script>
</body>
</html>
"""

    # --- ส่วนสำคัญ: นำข้อมูลจาก Python ไปแทนที่ Placeholder ใน HTML ---
    html_code = html_code.replace("__DATE_DISPLAY__", date_display_str)
    html_code = html_code.replace("__SELECTED_SHOP__", selected_shop_ui)
    html_code = html_code.replace("__TABLE_ROWS__", top10_rows_html)
    html_code = html_code.replace("__CHART_LABELS__", labels_js)
    html_code = html_code.replace("__CHART_DATA__", data_values_js)

    # แสดงผล
    components.html(html_code, height=900, scrolling=True)

else:
    st.warning("No Data found in Supabase")