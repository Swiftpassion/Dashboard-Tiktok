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

# CSS Styling: ปรับแต่ง Widget ของ Streamlit ให้กลายเป็น Header สวยๆ
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Kanit', sans-serif;
        background-color: #0f1115; /* สีพื้นหลังหลัก */
        color: white;
    }

    /* ซ่อน Header มาตรฐานของ Streamlit */
    header {visibility: hidden;}
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 0rem !important;
    }

    /* --- 1. ปรับแต่ง Date Input (วันที่) ให้เป็นตัวหนังสือใหญ่ๆ --- */
    
    /* ซ่อน Label คำว่า "Select Date" เดิม */
    div[data-testid="stDateInput"] label {
        display: none;
    }
    
    /* ปรับแต่งกล่อง Input ให้พื้นหลังใส และตัวหนังสือใหญ่ */
    div[data-baseweb="input"] {
        background-color: transparent !important;
        border: none !important;
        border-bottom: 4px solid #ff7043 !important; /* เส้นขีดล่างสีส้มหนา */
        border-radius: 0px !important;
    }

    div[data-baseweb="input"] > div {
        padding: 0px !important;
    }

    /* ปรับตัวเลขวันที่ภายใน */
    input[class*="st-"] {
        color: #ffffff !important;
        font-size: 36px !important; /* ตัวใหญ่สะใจตามรูป */
        font-weight: 700 !important;
        font-family: 'Kanit', sans-serif !important;
        padding-bottom: 10px !important;
        height: auto !important;
    }
    
    /* ไอคอนปฏิทิน */
    div[data-baseweb="input"] svg {
        fill: #ff7043 !important; /* เปลี่ยนไอคอนเป็นสีส้ม */
        width: 24px !important;
        height: 24px !important;
    }

    /* --- 2. ปรับแต่ง Radio Button (Shop Selector) --- */
    div[role="radiogroup"] {
        display: flex;
        flex-direction: row;
        align-items: center;
        gap: 15px;
        padding-top: 15px; /* ดันลงมาให้ตรงกับบรรทัดวันที่ */
    }

    /* ปรับตัวเลือกแต่ละตัว */
    div[data-testid="stRadio"] label {
        font-size: 20px !important;
        color: #a0a0a0 !important;
        cursor: pointer;
    }

    /* เมื่อเอาเมาส์ชี้ หรือ ถูกเลือก */
    div[data-testid="stRadio"] label:hover, 
    div[data-testid="stRadio"] label[data-checked="true"] {
        color: #ffffff !important;
        font-weight: 600 !important;
    }

    /* สร้างวงกลมสีส้มสำหรับตัวที่เลือก */
    div[role="radiogroup"] div[data-checked="true"] div:first-child {
        background-color: #ff7043 !important;
        border-color: #ff7043 !important;
    }
    
    /* ปรับแต่งส่วนหัว "ช่วงวันที่ขายสินค้า" ที่เราจะสร้างด้วย st.markdown */
    .custom-label {
        font-size: 18px;
        color: #a0a0a0;
        margin-bottom: -15px; /* ดึง Date Input ให้ขยับขึ้นมาใกล้ๆ */
        font-weight: 300;
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

    # --- ส่วน Header (สร้าง Layout 2 คอลัมน์) ---
    # ใช้ st.columns เพื่อจัดให้ Date อยู่ซ้าย และ Shop อยู่ขวา ในบรรทัดเดียวกัน
    c_date, c_space, c_shop = st.columns([2, 0.5, 2])
    
    with c_date:
        # ใส่ Label เองเพราะเราซ่อน Label ของ Widget ไปแล้ว
        st.markdown('<div class="custom-label">ช่วงวันที่ขายสินค้า</div>', unsafe_allow_html=True)
        
        valid_dates = df['Date'].dropna().sort_values()
        if not valid_dates.empty:
            min_d, max_d = valid_dates.iloc[0], valid_dates.iloc[-1]
        else:
            min_d, max_d = datetime.date.today(), datetime.date.today()

        # Date Input (หน้าตาจะถูกเปลี่ยนโดย CSS ด้านบนให้เป็นตัวหนังสือใหญ่)
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

    with c_shop:
        # Shop Selector (CSS จะจัดให้เป็นแนวนอนและวางตำแหน่งขวา)
        # ดันลงมานิดนึงเพื่อให้ตรงกับฐานตัวหนังสือวันที่
        st.write("") 
        st.write("") 
        shop_options = ['All Shops'] + sorted(df['Shop'].unique().tolist())
        selected_shop_ui = st.radio(
            "Shop", # Label นี้จะถูกซ่อนถ้าต้องการ หรือปล่อยไว้เล็กๆ
            shop_options,
            horizontal=True,
            label_visibility="collapsed" # ซ่อน Label คำว่า "Shop"
        )

    # Filter Logic
    mask = (df['Date'] >= start_date) & (df['Date'] <= end_date)
    if selected_shop_ui != 'All Shops':
        mask = mask & (df['Shop'] == selected_shop_ui)
    
    filtered_df = df.loc[mask]

    # ==========================================
    # 5. HTML/JS View (Only Chart & Table)
    # ==========================================
    # ตัดส่วน Header ออกจาก HTML เพราะเราใช้ Widget จริงแสดงผลด้านบนแล้ว
    
    if not filtered_df.empty:
        # เตรียมข้อมูลตาราง Top 20
        top10_df = filtered_df.groupby('Clean_SKU')['Quantity'].sum().reset_index().sort_values('Quantity', ascending=False).head(20)
        top10_rows_html = ""
        for idx, row in top10_df.iterrows():
            icon = ' <span class="trophy-icon">🏆</span>' if idx == top10_df.index[0] else ''
            top10_rows_html += f"<tr><td>{icon}{row['Clean_SKU']}</td><td>{row['Quantity']:,}</td></tr>"

        # เตรียมข้อมูลกราฟ
        chart_df = top10_df.head(10)
        labels_js = json.dumps(chart_df['Clean_SKU'].tolist())
        data_values_js = json.dumps(chart_df['Quantity'].tolist())
        
        # สีหลากสี
        color_palette = [
            '#ffab91', '#81d4fa', '#b39ddb', '#ffcc80', '#a5d6a7', 
            '#f48fb1', '#80cbc4', '#ce93d8', '#ffab40', '#90caf9',
            '#ef9a9a', '#b0bec5', '#fff59d', '#bcaaa4', '#e6ee9c'
        ]
        bg_colors = []
        for i in range(len(chart_df)):
            bg_colors.append(color_palette[i % len(color_palette)])
        bg_colors_js = json.dumps(bg_colors)

    else:
        top10_rows_html = "<tr><td>ไม่พบข้อมูล</td><td>-</td></tr>"
        labels_js, data_values_js, bg_colors_js = "[]", "[]", "[]"

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
            padding: 0; /* ตัด Padding ออก เพราะ Header อยู่ที่ Streamlit แล้ว */
            color: #ffffff;
            box-sizing: border-box;
            overflow-x: hidden;
        }

        /* Dashboard Layout */
        .dashboard-container {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 30px;
            margin-top: 10px;
        }

        /* Chart Area */
        .chart-title {
            color: #a0a0a0;
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
            height: 800px;
        }

        .ranking-header {
            background-color: #ffccbc;
            color: #000000;
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

    <div class="dashboard-container">
        <div class="chart-area">
            <div class="chart-title">ยอดขายสินค้า (__SELECTED_SHOP__)</div>
            <div style="height: 700px; width: 100%;">
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

    html_code = html_code.replace("__SELECTED_SHOP__", selected_shop_ui)
    html_code = html_code.replace("__TABLE_ROWS__", top10_rows_html)
    html_code = html_code.replace("__CHART_LABELS__", labels_js)
    html_code = html_code.replace("__CHART_DATA__", data_values_js)
    html_code = html_code.replace("__CHART_COLORS__", bg_colors_js)

    components.html(html_code, height=1600, scrolling=False) # scrolling=False เพื่อไม่ให้มี scrollbar ซ้อน

else:
    st.warning("No Data found in Supabase")