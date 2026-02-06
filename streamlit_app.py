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

        # Date Input (CSS จะทำให้พื้นหลังใส)
        date_range = st.date_input(
            "Select Date", # Label นี้จะถูกซ่อนด้วย CSS
            value=[min_d, max_d],
            min_value=min_d,
            max_value=max_d
        )
        if len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date, end_date = min_d, max_d

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
    # 5. HTML/JS View (Transparent Background)
    # ==========================================
    
    # ... (ส่วนคำนวณข้อมูลเหมือนเดิม) ...
    if not filtered_df.empty:
        top10_df = filtered_df.groupby('Clean_SKU')['Quantity'].sum().reset_index().sort_values('Quantity', ascending=False).head(20)
        top10_rows_html = ""
        for idx, row in top10_df.iterrows():
            icon = ' <span class="icon-gold">🏆</span>' if idx == top10_df.index[0] else ''
            top10_rows_html += f"<tr><td>{icon}{row['Clean_SKU']}</td><td>{row['Quantity']:,}</td></tr>"

        lower_df = filtered_df.groupby('Clean_SKU')['Quantity'].sum().reset_index().sort_values('Quantity', ascending=True).head(7)
        lower_rows_html = ""
        for idx, row in lower_df.iterrows():
            lower_rows_html += f"<tr><td>{row['Clean_SKU']}</td><td>{row['Quantity']:,}</td></tr>"

        chart_products = top10_df['Clean_SKU'].tolist()
        pivot_df = filtered_df[filtered_df['Clean_SKU'].isin(chart_products)].groupby(['Clean_SKU', 'Shop'])['Quantity'].sum().unstack(fill_value=0)
        pivot_df = pivot_df.reindex(chart_products)

        labels_js = json.dumps(chart_products)
        data_namkang = json.dumps(pivot_df['Namkang'].tolist() if 'Namkang' in pivot_df.columns else [0]*len(chart_products))
        data_sim1 = json.dumps(pivot_df['SIM1'].tolist() if 'SIM1' in pivot_df.columns else [0]*len(chart_products))
        data_sim2 = json.dumps(pivot_df['SIM2'].tolist() if 'SIM2' in pivot_df.columns else [0]*len(chart_products))
    else:
        top10_rows_html = "<tr><td>ไม่พบข้อมูล</td><td>-</td></tr>"
        lower_rows_html = "<tr><td>ไม่พบข้อมูล</td><td>-</td></tr>"
        labels_js, data_namkang, data_sim1, data_sim2 = "[]", "[]", "[]", "[]"

    html_code = f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <link href="https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600&display=swap" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            :root {{
                --primary-orange: #ffab91; --primary-orange-text: #ff7043;
                --header-orange: #ffccbc; --header-blue: #81d4fa;
                --bar-purple: #b39ddb; --bar-darkblue: #3f51b5; --bar-orange: #ffab91;
            }}
            /* [สำคัญ] ปรับ body ให้พื้นหลังใส (transparent) 
               เพื่อให้กลืนไปกับพื้นหลังของ Streamlit 
            */
            body {{ 
                font-family: 'Kanit', sans-serif; 
                background-color: transparent; 
                margin: 0; padding: 0; color: #333; overflow-x: hidden; 
            }}
            
            /* ส่วนอื่นคงเดิม แต่เอาพื้นหลังขาวออกจากบางจุด */
            .dashboard-container {{ display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-top: 10px; }}
            .chart-area {{ padding-right: 20px; }}
            .chart-header {{ margin-bottom: 10px; }}
            .chart-title {{ font-size: 14px; color: #999; margin-bottom: 5px; }}
            
            .legend-container {{ display: flex; gap: 15px; font-size: 12px; align-items: center; margin-bottom: 10px; }}
            .legend-item {{ display: flex; align-items: center; gap: 5px; }}
            .dot {{ width: 10px; height: 10px; border-radius: 50%; }}
            .dot.namkang {{ background-color: var(--bar-purple); }}
            .dot.sim1 {{ background-color: var(--bar-darkblue); }}
            .dot.sim2 {{ background-color: var(--bar-orange); }}
            
            /* Ranking Box พื้นหลังขาวเฉพาะตัวกล่อง */
            .ranking-box {{ 
                border: 1px solid #eee; margin-bottom: 20px; 
                background-color: rgba(255, 255, 255, 0.8); /* ขาวโปร่งแสงนิดๆ */
            }}
            .ranking-header {{ padding: 10px; text-align: center; font-weight: 600; font-size: 14px; }}
            .header-top {{ background-color: var(--header-orange); }}
            .header-lower {{ background-color: var(--header-blue); color: #fff; }}
            .ranking-table {{ width: 100%; border-collapse: collapse; }}
            .ranking-table th {{ text-align: left; padding: 8px; border-bottom: 2px solid #333; font-size: 11px; }}
            .ranking-table th:last-child {{ text-align: right; }}
            .ranking-table td {{ padding: 6px 8px; border-bottom: 1px solid #f0f0f0; color: #444; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 200px; }}
            .ranking-table td:last-child {{ text-align: right; }}
            .icon-gold {{ color: #d4af37; }}
        </style>
    </head>
    <body>
        <div class="dashboard-container">
            <div class="chart-area">
                <div class="chart-header">
                    <div class="chart-title">ยอดขายสินค้า ({selected_shop_ui})</div>
                    <div class="legend-container">
                        <strong>SHOP</strong>
                        <div class="legend-item"><span class="dot namkang"></span> Namkang</div>
                        <div class="legend-item"><span class="dot sim1"></span> SIM1</div>
                        <div class="legend-item"><span class="dot sim2"></span> SIM2</div>
                    </div>
                </div>
                <div style="height: 700px; width: 100%;">
                    <canvas id="salesChart"></canvas>
                </div>
            </div>

            <div class="sidebar">
                <div class="ranking-box">
                    <div class="ranking-header header-top">TOP 20 Best Seller</div>
                    <table class="ranking-table">
                        <thead><tr><th>สินค้า</th><th>จำนวน</th></tr></thead>
                        <tbody>{top10_rows_html}</tbody>
                    </table>
                </div>
                <div class="ranking-box">
                    <div class="ranking-header header-lower">
                         <span>⬇</span> Lower Seller <span>⬇</span>
                    </div>
                    <table class="ranking-table">
                        <thead><tr><th>สินค้า</th><th>จำนวน</th></tr></thead>
                        <tbody>{lower_rows_html}</tbody>
                    </table>
                </div>
            </div>
        </div>

        <script>
            const ctx = document.getElementById('salesChart').getContext('2d');
            new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: {labels_js},
                    datasets: [
                        {{ label: 'Namkang', data: {data_namkang}, backgroundColor: '#b39ddb', barThickness: 15, borderRadius: 2 }},
                        {{ label: 'SIM1', data: {data_sim1}, backgroundColor: '#3f51b5', barThickness: 15, borderRadius: 2 }},
                        {{ label: 'SIM2', data: {data_sim2}, backgroundColor: '#ffab91', barThickness: 15, borderRadius: 2 }}
                    ]
                }},
                options: {{
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{ legend: {{ display: false }} }},
                    scales: {{
                        x: {{ 
                            stacked: true, 
                            position: 'bottom', 
                            grid: {{ color: 'rgba(0,0,0,0.05)' }} /* เส้นตารางจางๆ */
                        }},
                        y: {{ 
                            stacked: true, 
                            grid: {{ display: false }}, 
                            ticks: {{ font: {{ family: 'Kanit' }}, autoSkip: false }} 
                        }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """

    components.html(html_code, height=1200, scrolling=True)

else:
    st.warning("No Data found in Supabase")