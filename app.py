import streamlit as st
import pandas as pd
import json

# Set Page Configuration
st.set_page_config(page_title="Retail Financial Automator", layout="wide")

st.title("🇮🇳 Retail Financial Insights (Rupee & Dollar)")
st.markdown("""
### Data-to-Dashboard Automator
*Upload your sales file to generate a multi-currency interactive report.*
""")

# --- Helper Functions ---
def clean_currency(value):
    """Removes symbols and converts to float."""
    if isinstance(value, str):
        return float(value.replace('$', '').replace('₹', '').replace(',', '').strip())
    return value

def get_ibr_rate(date):
    """
    Simulates historical IBR USD/INR rates. 
    In a live production environment, you would use an API (e.g., ExchangeRate-API).
    """
    year = date.year
    # Sample Historical Averages (2021-2024)
    rates = {2021: 74.1, 2022: 78.6, 2023: 82.5, 2024: 83.4, 2025: 84.5}
    return rates.get(year, 83.0)

# 1. File Uploader
uploaded_file = st.file_uploader("Upload your Retail Data (CSV or XLSX)", type=['csv', 'xlsx'])

if uploaded_file:
    try:
        # Load Data
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        
        # --- CLEANING PIPELINE ---
        # A. Clean Column Names (removing leading/trailing spaces)
        df.columns = df.columns.str.strip()
        
        # B. Handle Missing Values
        df['Category'] = df['Category'].fillna('Uncategorized')
        df['Sales Per'] = df['Sales Per'].fillna(0)
        
        # C. Currency Formatting (Clean symbols if they exist)
        df['Sales Per'] = df['Sales Per'].apply(clean_currency)
        df['Profit'] = df['Profit'].apply(clean_currency)
        
        # D. Date Processing & IBR Mapping
        df['Order Date'] = pd.to_datetime(df['Order Date'], errors='coerce')
        df = df.dropna(subset=['Order Date'])
        
        # Calculate IBR Rate for each row and convert to Rupees
        df['IBR_Rate'] = df['Order Date'].apply(get_ibr_rate)
        
        # Assuming original "Sales Per" is in USD
        df['Sales_USD'] = df['Sales Per']
        df['Profit_USD'] = df['Profit']
        
        df['Sales_INR'] = df['Sales_USD'] * df['IBR_Rate']
        df['Profit_INR'] = df['Profit_USD'] * df['IBR_Rate']
        
        df['YearMonth'] = df['Order Date'].dt.to_period('M').astype(str)

        st.success(f"Successfully processed {len(df)} records with IBR Date-Matching!")
        st.write("### Data Preview (Last 5 Rows)", df.tail())

        # Prepare JSON for HTML Dashboard
        records = df[['YearMonth', 'Category', 'Segment', 'State', 'Sales_INR', 'Sales_USD', 
                      'Profit_INR', 'Profit_USD', 'Quantity', 'Order ID', 'Customer ID', 'IBR_Rate']].to_dict(orient='records')

        # --- GENERATE HTML DASHBOARD ---
        # The JavaScript inside this HTML handles the dynamic switching
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Interactive Financial Dashboard</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {{ background: #f0f2f6; font-family: 'Segoe UI', sans-serif; }}
                .card {{ border:none; border-radius:15px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }}
                .kpi-val {{ font-size: 2rem; font-weight: bold; color: #004a99; }}
                .header {{ background: #004a99; color: white; padding: 20px; border-radius: 0 0 20px 20px; margin-bottom: 30px; }}
            </style>
        </head>
        <body>
            <div class="header text-center">
                <h2>Retail Performance Analytics</h2>
                <div class="mt-3">
                    <label class="me-2">Select Currency: </label>
                    <div class="btn-group" role="group">
                        <input type="radio" class="btn-check" name="curr" id="btnINR" checked onclick="render('INR')">
                        <label class="btn btn-outline-light" for="btnINR">Rupees (₹)</label>
                        <input type="radio" class="btn-check" name="curr" id="btnUSD" onclick="render('USD')">
                        <label class="btn btn-outline-light" for="btnUSD">Dollars ($)</label>
                    </div>
                </div>
            </div>

            <div class="container-fluid">
                <div class="row g-3 text-center mb-4">
                    <div class="col-md-3"><div class="card p-3"><h5>Total Sales</h5><div id="kpi-sales" class="kpi-val"></div></div></div>
                    <div class="col-md-3"><div class="card p-3"><h5>Total Profit</h5><div id="kpi-profit" class="kpi-val"></div></div></div>
                    <div class="col-md-3"><div class="card p-3"><h5>Avg Order Val</h5><div id="kpi-aov" class="kpi-val"></div></div></div>
                    <div class="col-md-3"><div class="card p-3"><h5>Items Sold</h5><div class="kpi-val">{df['Quantity'].sum():,}</div></div></div>
                </div>
                <div class="row">
                    <div class="col-md-8"><div class="card p-3"><div id="chart-trend" style="height:400px;"></div></div></div>
                    <div class="col-md-4"><div class="card p-3"><div id="chart-cat" style="height:400px;"></div></div></div>
                </div>
            </div>

            <script>
                const data = {json.dumps(records)};
                
                function render(currency) {{
                    const sKey = 'Sales_' + currency;
                    const pKey = 'Profit_' + currency;
                    const symbol = currency === 'INR' ? '₹' : '$';

                    // 1. Calculate KPIs
                    const totalSales = data.reduce((a, b) => a + b[sKey], 0);
                    const totalProfit = data.reduce((a, b) => a + b[pKey], 0);
                    const orders = new Set(data.map(d => d['Order ID'])).size;

                    document.getElementById('kpi-sales').innerText = symbol + totalSales.toLocaleString(undefined, {{maximumFractionDigits:0}});
                    document.getElementById('kpi-profit').innerText = symbol + totalProfit.toLocaleString(undefined, {{maximumFractionDigits:0}});
                    document.getElementById('kpi-aov').innerText = symbol + (totalSales/orders).toLocaleString(undefined, {{maximumFractionDigits:0}});

                    // 2. Charts
                    const trend = {{}};
                    data.forEach(d => trend[d.YearMonth] = (trend[d.YearMonth] || 0) + d[sKey]);
                    const months = Object.keys(trend).sort();

                    Plotly.newPlot('chart-trend', [{{
                        x: months, y: months.map(m => trend[m]), type: 'scatter', mode: 'lines+markers', line: {{color: '#004a99'}}
                    }}], {{title: 'Sales Trend ('+symbol+')'}});

                    const catData = {{}};
                    data.forEach(d => catData[d.Category] = (catData[d.Category] || 0) + d[sKey]);
                    Plotly.newPlot('chart-cat', [{{
                        labels: Object.keys(catData), values: Object.values(catData), type: 'pie'
                    }}], {{title: 'Sales by Category'}});
                }}
                
                // Initial Load
                render('INR');
            </script>
        </body>
        </html>
        """

        # Download Button
        st.download_button("📥 Download Final Dashboard", html_content, "Interactive_Retail_Dashboard.html", "text/html")

    except Exception as e:
        st.error(f"Error: {e}")