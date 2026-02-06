import streamlit as st
import pandas as pd
import json
from supabase import create_client, Client
import streamlit.components.v1 as components

# ==========================================
# 1. Config & Connection
# ==========================================
st.set_page_config(page_title="Sales Dashboard", layout="wide")

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
        # ดึงข้อมูลจาก Supabase
        response = supabase.table('orders').select(
            '"Shipped Time", "Warehouse Name", "Seller SKU", "Product Name", "Quantity"'
        ).execute()
        return pd.DataFrame(response.data)
    except:
        return pd.DataFrame() # Return empty if error

# ==========================================
# 2. Data Processing Logic
# ==========================================
def process_data(df):
    # Clean Data Logic เดิม
    if 'Shipped Time' in df.columns:
        df['Shipped Time'] = df['Shipped Time'].astype(str).str.replace(r'\t', '', regex=True).str.strip()
        df['Date_Obj'] = pd.to_datetime(df['Shipped Time'], dayfirst=True, errors='coerce')
        df['Date'] = df['Date_Obj'].dt.date
    
    # Map Shop Name
    def map_shop(name):
        mapping = { "Simmobile": "SIM1", "Namkangmobile": "SIM2", "Thailand Pickup Warehouse": "Namkang" }
        return mapping.get(str(name).strip(), str(name).strip())
    
    # Clean SKU
    def clean_sku(sku):
        if not sku: return "Unknown"
        s = str(sku).lower().replace("สีเงิน", "silver").replace("สีเทา", "gray")
        import re
        s = re.sub(r'\b(gb|ram|rom)\b', '', s)
        return re.sub(r'\s+', ' ', s).strip().title() # Title case ให้สวยแบบในรูป

    df['Shop'] = df['Warehouse Name'].apply(map_shop)
    df['Clean_SKU'] = df['Seller SKU'].apply(clean_sku)
    
    return df

# ==========================================
# 3. Main App
# ==========================================
df_raw = load_data()

if not df_raw.empty:
    df = process_data(df_raw)

    # --- INPUT CONTROLS (ซ่อนไว้ใน Sidebar เพื่อความเนียน) ---
    st.sidebar.header("⚙️ ตั้งค่าข้อมูล")
    
    # Date Filter
    valid_dates = df['Date'].dropna().sort_values()
    if not valid_dates.empty:
        start_date, end_date = st.sidebar.date_input(
            "เลือกช่วงวันที่", 
            [valid_dates.iloc[0], valid_dates.iloc[-1]]
        )
    else:
        start_date, end_date = None, None

    # Filter Data
    mask = (df['Date'] >= start_date) & (df['Date'] <= end_date)
    filtered_df = df.loc[mask]

    # --- PREPARE DATA FOR HTML/JS ---
    
    # 1. ตาราง Top 10 Best Seller
    top10_df = filtered_df.groupby('Clean_SKU')['Quantity'].sum().reset_index().sort_values('Quantity', ascending=False).head(20)
    
    # สร้าง HTML Rows สำหรับ Top 10
    top10_rows_html = ""
    for idx, row in top10_df.iterrows():
        icon = ' <span class="icon-gold">🏆</span>' if idx == top10_df.index[0] else ''
        top10_rows_html += f"<tr><td>{icon}{row['Clean_SKU']}</td><td>{row['Quantity']:,}</td></tr>"

    # 2. ตาราง Lower Seller (สินค้าขายน้อยสุด 5 อันดับ)
    lower_df = filtered_df.groupby('Clean_SKU')['Quantity'].sum().reset_index().sort_values('Quantity', ascending=True).head(7)
    
    lower_rows_html = ""
    for idx, row in lower_df.iterrows():
        lower_rows_html += f"<tr><td>{row['Clean_SKU']}</td><td>{row['Quantity']:,}</td></tr>"

    # 3. เตรียมข้อมูลกราฟ (Chart.js)
    # เราจะใช้สินค้า Top 20 มาพล็อต เพื่อไม่ให้กราฟแน่นเกินไป
    chart_products = top10_df['Clean_SKU'].tolist()
    
    # Pivot ข้อมูลแยกตามร้าน (Shop)
    pivot_df = filtered_df[filtered_df['Clean_SKU'].isin(chart_products)].groupby(['Clean_SKU', 'Shop'])['Quantity'].sum().unstack(fill_value=0)
    
    # Reindex ให้ลำดับตรงกับ Labels
    pivot_df = pivot_df.reindex(chart_products)
    
    # แปลงเป็น List เพื่อส่งเข้า JS
    labels_js = json.dumps(chart_products)
    
    # ดึงข้อมูลแต่ละร้าน (ถ้าไม่มีร้านนั้นให้ใส่ 0)
    data_namkang = json.dumps(pivot_df['Namkang'].tolist() if 'Namkang' in pivot_df.columns else [0]*len(chart_products))
    data_sim1 = json.dumps(pivot_df['SIM1'].tolist() if 'SIM1' in pivot_df.columns else [0]*len(chart_products))
    data_sim2 = json.dumps(pivot_df['SIM2'].tolist() if 'SIM2' in pivot_df.columns else [0]*len(chart_products))

    # วันที่สำหรับแสดงผล
    date_start_str = start_date.strftime("%d/%m/%Y")
    date_end_str = end_date.strftime("%d/%m/%Y")

    # ==========================================
    # 4. HTML INJECTION (Code ของคุณ + Python Variables)
    # ==========================================
    
    html_code = f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <link href="https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600&display=swap" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            /* CSS เดิมของคุณ Copy มาแปะตรงนี้ 100% */
            :root {{
                --primary-orange: #ffab91;
                --primary-orange-text: #ff7043;
                --header-orange: #ffccbc;
                --header-blue: #81d4fa;
                --bar-purple: #b39ddb;
                --bar-darkblue: #3f51b5;
                --bar-orange: #ffab91;
                --text-gray: #555;
                --bg-gray: #eeeeee;
            }}
            body {{
                font-family: 'Kanit', sans-serif;
                background-color: #fff;
                margin: 0; padding: 20px; color: #333;
                /* ปรับให้เข้ากับ Iframe ของ Streamlit */
                overflow-x: hidden; 
            }}
            .top-controls {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }}
            .date-section {{ display: flex; flex-direction: column; gap: 10px; }}
            .date-inputs {{ display: flex; gap: 15px; }}
            .date-box {{ border: 1px solid var(--primary-orange-text); color: var(--primary-orange-text); padding: 5px 15px; font-weight: 600; background: #fff; font-size: 16px; border-radius: 4px; }}
            .timeline-slider {{ position: relative; height: 30px; width: 300px; display: flex; align-items: center; }}
            .timeline-line {{ height: 4px; background-color: var(--primary-orange); width: 100%; position: absolute; top: 50%; transform: translateY(-50%); z-index: 1; }}
            .timeline-point {{ width: 16px; height: 16px; background-color: #fff; border: 3px solid var(--primary-orange); border-radius: 50%; position: absolute; top: 50%; transform: translateY(-50%); z-index: 2; }}
            .point-start {{ left: 0%; }} 
            .point-end {{ right: 0; }}
            .shop-selector {{ display: flex; gap: 5px; }}
            .shop-tab {{ background-color: #f5f5f5; padding: 15px 30px; font-size: 16px; color: var(--text-gray); font-weight: 500; cursor: default; }}
            .shop-tab.active {{ background-color: #e0e0e0; color: #333; font-weight: bold; border: 1px solid #ccc; }}
            .dashboard-container {{ display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }}
            .chart-area {{ padding-right: 20px; }}
            .chart-header {{ margin-bottom: 10px; }}
            .chart-title {{ font-size: 14px; color: #999; margin-bottom: 5px; }}
            .legend-container {{ display: flex; gap: 15px; font-size: 12px; align-items: center; margin-bottom: 10px; }}
            .legend-item {{ display: flex; align-items: center; gap: 5px; }}
            .dot {{ width: 10px; height: 10px; border-radius: 50%; }}
            .dot.namkang {{ background-color: var(--bar-purple); }}
            .dot.sim1 {{ background-color: var(--bar-darkblue); }}
            .dot.sim2 {{ background-color: var(--bar-orange); }}
            .sidebar {{ font-size: 12px; }}
            .ranking-box {{ border: 1px solid #eee; margin-bottom: 20px; }}
            .ranking-header {{ padding: 10px; text-align: center; font-weight: 600; font-size: 14px; }}
            .header-top {{ background-color: var(--header-orange); }}
            .header-lower {{ background-color: var(--header-blue); color: #fff; }}
            .ranking-table {{ width: 100%; border-collapse: collapse; }}
            .ranking-table th {{ text-align: left; padding: 8px; border-bottom: 2px solid #333; font-size: 11px; }}
            .ranking-table th:last-child {{ text-align: right; }}
            .ranking-table td {{ padding: 6px 8px; border-bottom: 1px solid #f0f0f0; color: #444; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 200px; }}
            .ranking-table td:last-child {{ text-align: right; }}
            .ranking-table tr:hover {{ background-color: #f9f9f9; }}
            .icon-gold {{ color: #d4af37; margin-right: 3px; }}
        </style>
    </head>
    <body>
        <div class="top-controls">
            <div class="date-section">
                <div class="date-inputs">
                    <div class="date-box">{date_start_str}</div>
                    <div class="date-box">{date_end_str}</div>
                </div>
                <div class="timeline-slider">
                    <div class="timeline-line"></div>
                    <div class="timeline-point point-start"></div>
                    <div class="timeline-point point-end"></div>
                </div>
            </div>

            <div class="shop-selector">
                <div class="shop-tab active">All Shops</div>
                </div>
        </div>

        <div class="dashboard-container">
            <div class="chart-area">
                <div class="chart-header">
                    <div class="chart-title">ยอดขายสินค้า (Top 20 Models)</div>
                    <div class="legend-container">
                        <strong>SHOP</strong>
                        <div class="legend-item"><span class="dot namkang"></span> Namkang</div>
                        <div class="legend-item"><span class="dot sim1"></span> SIM1</div>
                        <div class="legend-item"><span class="dot sim2"></span> SIM2</div>
                    </div>
                </div>
                <div style="height: 600px; width: 100%;">
                    <canvas id="salesChart"></canvas>
                </div>
            </div>

            <div class="sidebar">
                <div class="ranking-box">
                    <div class="ranking-header header-top">TOP 20 Best Seller</div>
                    <table class="ranking-table">
                        <thead>
                            <tr>
                                <th>สินค้า</th>
                                <th>จำนวน</th>
                            </tr>
                        </thead>
                        <tbody>
                            {top10_rows_html}
                        </tbody>
                    </table>
                </div>

                <div class="ranking-box">
                    <div class="ranking-header header-lower">
                         <span>⬇</span> Lower Seller (Bottom 7) <span>⬇</span>
                    </div>
                    <table class="ranking-table">
                        <thead>
                            <tr>
                                <th>สินค้า</th>
                                <th>จำนวน</th>
                            </tr>
                        </thead>
                        <tbody>
                             {lower_rows_html}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <script>
            // รับค่าจาก Python (JSON format)
            const labels = {labels_js};
            const dataNamkang = {data_namkang};
            const dataSim1 = {data_sim1};
            const dataSim2 = {data_sim2};

            const ctx = document.getElementById('salesChart').getContext('2d');
            const salesChart = new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: labels,
                    datasets: [
                        {{
                            label: 'Namkang',
                            data: dataNamkang,
                            backgroundColor: '#b39ddb',
                            hoverBackgroundColor: '#9575cd',
                            barThickness: 15,
                            borderRadius: 2
                        }},
                        {{
                            label: 'SIM1',
                            data: dataSim1,
                            backgroundColor: '#3f51b5',
                            hoverBackgroundColor: '#303f9f',
                            barThickness: 15,
                            borderRadius: 2
                        }},
                        {{
                            label: 'SIM2',
                            data: dataSim2,
                            backgroundColor: '#ffab91',
                            hoverBackgroundColor: '#ff8a65',
                            barThickness: 15,
                            borderRadius: 2
                        }}
                    ]
                }},
                options: {{
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ display: false }}, // Hide default legend
                        tooltip: {{ enabled: true }}
                    }},
                    scales: {{
                        x: {{
                            stacked: true,
                            position: 'bottom',
                            grid: {{ color: '#f0f0f0' }},
                            ticks: {{
                                font: {{ family: 'Kanit', size: 12 }}
                            }}
                        }},
                        y: {{
                            stacked: true,
                            grid: {{ display: false }},
                            ticks: {{
                                font: {{ family: 'Kanit', size: 12 }},
                                autoSkip: false
                            }}
                        }}
                    }},
                    layout: {{
                        padding: {{ right: 20 }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """

    # Render HTML ลงหน้าเว็บ
    # height=1200 เพื่อให้ Scroll ได้ยาวๆ ไม่ต้องมี Scrollbar ซ้อน
    components.html(html_code, height=1200, scrolling=True)

else:
    st.warning("No Data found in Supabase")