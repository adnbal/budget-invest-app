import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import google.generativeai as genai
import uuid  # 👈 for dynamic Botpress session

# 🔐 Secrets
CHAT_API_ID = st.secrets["botpress"]["chat_api_id"]
BOTPRESS_TOKEN = st.secrets["botpress"]["token"]
genai.configure(api_key=st.secrets["gemini"]["api_key"])
OPENROUTER_API_KEY = st.secrets["openrouter"]["api_key"]
API_KEY = st.secrets["alpha_vantage"]["api_key"]

# 📄 App config
st.set_page_config(page_title="💸 Multi-LLM Budget Planner", layout="wide")
st.title("💸 Budgeting + Investment Planner (Multi-LLM AI Suggestions)")

# 📉 Alpha Vantage function
def get_alpha_vantage_monthly_return(symbol):
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_MONTHLY_ADJUSTED&symbol={symbol}&apikey={API_KEY}"
    r = requests.get(url)
    if r.status_code != 200:
        return None
    data = r.json()
    ts = data.get("Monthly Adjusted Time Series", {})
    closes = [float(v["5. adjusted close"]) for v in ts.values()]
    if len(closes) < 2:
        return None
    monthly_return = (closes[0] - closes[1]) / closes[1]
    return monthly_return

# 🧾 Inputs
st.sidebar.header("📊 Monthly Income")
income = st.sidebar.number_input("Monthly income (before tax, $)", min_value=0.0, value=5000.0, step=100.0)
tax_rate = st.sidebar.slider("Tax rate (%)", 0, 50, 20)

st.sidebar.header("📌 Expenses")
housing = st.sidebar.number_input("Housing / Rent ($)", 0.0, 5000.0, 1200.0, 50.0)
food = st.sidebar.number_input("Food / Groceries ($)", 0.0, 5000.0, 500.0, 50.0)
transport = st.sidebar.number_input("Transport ($)", 0.0, 5000.0, 300.0, 50.0)
utilities = st.sidebar.number_input("Utilities ($)", 0.0, 5000.0, 200.0, 50.0)
entertainment = st.sidebar.number_input("Entertainment ($)", 0.0, 5000.0, 200.0, 50.0)
others = st.sidebar.number_input("Other expenses ($)", 0.0, 5000.0, 200.0, 50.0)

st.sidebar.header("📈 Investments")
stocks = st.sidebar.number_input("Stocks investment ($)", 0.0, 5000.0, 500.0, 100.0)
bonds = st.sidebar.number_input("Bonds investment ($)", 0.0, 5000.0, 300.0, 100.0)
real_estate = st.sidebar.number_input("Real estate ($)", 0.0, 5000.0, 0.0, 100.0)
crypto = st.sidebar.number_input("Crypto ($)", 0.0, 5000.0, 0.0, 100.0)
fixed_deposit = st.sidebar.number_input("Fixed deposit ($)", 0.0, 5000.0, 0.0, 100.0)

months = st.sidebar.slider("Projection period (months)", 1, 60, 12)
savings_target = st.sidebar.number_input("Savings target at end of period ($)", 0.0, 1_000_000.0, 10000.0, 500.0)

# 📈 Returns
stock_r = get_alpha_vantage_monthly_return("SPY") or 0.01
bond_r = get_alpha_vantage_monthly_return("AGG") or 0.003
real_r = 0.004
crypto_r = 0.02
fd_r = 0.003

# 💰 Calculations
after_tax_income = income * (1 - tax_rate / 100)
total_exp = housing + food + transport + utilities + entertainment + others
total_inv = stocks + bonds + real_estate + crypto + fixed_deposit
net_flow = after_tax_income - total_exp - total_inv

bal = 0
rows = []
for m in range(1, months + 1):
    bal += net_flow
    stock_val = stocks * ((1 + stock_r)**m - 1) / stock_r
    bond_val = bonds * ((1 + bond_r)**m - 1) / bond_r
    real_val = real_estate * ((1 + real_r)**m - 1) / real_r
    crypto_val = crypto * ((1 + crypto_r)**m - 1) / crypto_r
    fd_val = fixed_deposit * ((1 + fd_r)**m - 1) / fd_r
    net_worth = bal + stock_val + bond_val + real_val + crypto_val + fd_val
    rows.append({
        "Month": m,
        "Balance": bal,
        "Stocks": stock_val,
        "Bonds": bond_val,
        "RealEstate": real_val,
        "Crypto": crypto_val,
        "FixedDeposit": fd_val,
        "NetWorth": net_worth
    })
df = pd.DataFrame(rows)

# 📋 Summary
st.subheader("📋 Summary")
st.metric("Income (gross)", f"${income:,.2f}")
st.metric("After tax income", f"${after_tax_income:,.2f}")
st.metric("Expenses", f"${total_exp:,.2f}")
st.metric("Investments", f"${total_inv:,.2f}")
st.metric("Net Cash Flow", f"${net_flow:,.2f}/mo")

# 📊 Charts
st.subheader("📈 Net Worth Growth")
fig = px.line(df, x="Month", y=["Balance", "Stocks", "Bonds", "RealEstate", "Crypto", "FixedDeposit", "NetWorth"],
              markers=True, title="Net Worth & Investments Over Time")
fig.add_hline(y=savings_target, line_dash="dash", line_color="red", annotation_text="Target")
st.plotly_chart(fig, use_container_width=True)

st.subheader("🧾 Expense Breakdown")
exp_s = pd.Series({
    "Housing": housing,
    "Food": food,
    "Transport": transport,
    "Utilities": utilities,
    "Entertainment": entertainment,
    "Others": others
})
st.plotly_chart(px.pie(names=exp_s.index, values=exp_s.values, title="Expense Breakdown"), use_container_width=True)

st.subheader("💼 Investment Breakdown")
inv_s = pd.Series({
    "Stocks": stocks,
    "Bonds": bonds,
    "RealEstate": real_estate,
    "Crypto": crypto,
    "FixedDeposit": fixed_deposit
})
st.plotly_chart(px.pie(names=inv_s.index, values=inv_s.values, title="Investment Breakdown"), use_container_width=True)

# ⚠️ Warnings and Emojis
st.subheader("⚠️ Warnings and Financial Tips")
warnings = []

if total_exp > after_tax_income * 0.8:
    warning = "⚠️ Your expenses exceed 80% of your after-tax income. Consider reducing discretionary spending."
    warnings.append(warning)
    st.warning(warning)

if total_inv < after_tax_income * 0.1:
    warning = "📉 You're investing less than 10% of your income. Try to increase your long-term savings."
    warnings.append(warning)
    st.info(warning)

if net_flow < 0:
    warning = "❌ Your monthly cash flow is negative. You're spending more than you earn!"
    warnings.append(warning)
    st.error(warning)

if total_exp + total_inv > after_tax_income:
    warning = "⚠️ Total expenses and investments exceed income. Review your budgeting strategy."
    warnings.append(warning)
    st.warning(warning)

if savings_target > df['NetWorth'].iloc[-1]:
    warning = "🎯 Your projected net worth is below your savings goal. Consider adjusting your targets or boosting investments."
    warnings.append(warning)
    st.info(warning)

warning_text = "\n".join(warnings) if warnings else "✅ No critical warnings."

# 💬 AI Prompt
prompt = f"""
Financial summary:
Gross income: ${income}
Tax rate: {tax_rate}%
After-tax income: ${after_tax_income}
Expenses: ${total_exp}
Investments: ${total_inv}
Net cash flow: ${net_flow}/mo
Savings target: ${savings_target}
Projected net worth: ${df['NetWorth'].iloc[-1]}

Warnings:
{warning_text}

Please provide personalized financial advice on managing expenses, investments, and achieving savings goals.
"""

# 🤖 AI Suggestions
st.subheader("🤖 AI Suggestions")
col1, col2 = st.columns(2)

if "gemini_output" not in st.session_state:
    st.session_state.gemini_output = ""
if "deepseek_output" not in st.session_state:
    st.session_state.deepseek_output = ""

if col1.button("Generate Gemini Suggestion"):
    with col1:
        with st.spinner("Gemini generating..."):
            try:
                gemini_resp = genai.GenerativeModel("gemini-1.5-flash").generate_content(prompt)
                st.session_state.gemini_output = gemini_resp.text
            except Exception as e:
                st.session_state.gemini_output = f"Gemini error: {e}"

if col2.button("Generate DeepSeek Suggestion"):
    with col2:
        with st.spinner("DeepSeek generating..."):
            try:
                headers = {
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "deepseek/deepseek-r1:free",
                    "messages": [{"role": "user", "content": prompt}]
                }
                resp = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                st.session_state.deepseek_output = data["choices"][0]["message"]["content"]
            except Exception as e:
                st.session_state.deepseek_output = f"OpenRouter error: {e}"

# Display AI outputs
with col1:
    if st.session_state.gemini_output:
        st.subheader("🤖 Gemini Suggestion")
        st.write(st.session_state.gemini_output)

with col2:
    if st.session_state.deepseek_output:
        st.subheader("🤖 DeepSeek Suggestion")
        st.write(st.session_state.deepseek_output)

# ✅ Embedded Botpress WebChat with new chat every reload
st.subheader("🤖 Ask Your Financial Assistant (Botpress)")
user_id = str(uuid.uuid4())  # 👈 New chat every time
config_url = "https://files.bpcontent.cloud/2025/07/02/02/20250702020605-VDMFG1YB.json"  # your actual config URL
iframe_url = f"https://cdn.botpress.cloud/webchat/v3.0/shareable.html?configUrl={config_url}&userId={user_id}"

st.markdown(
    f"""
    <iframe
        src="{iframe_url}"
        width="100%"
        height="600"
        style="border: none; margin-top: 20px;"
        allow="microphone">
    </iframe>
    """,
    unsafe_allow_html=True
)
