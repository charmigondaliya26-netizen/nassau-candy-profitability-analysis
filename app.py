
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


st.set_page_config(
    page_title="Nassau Candy Profitability Dashboard",
    page_icon="🍫",
    layout="wide"
)

# ---------- Load Dataset ----------
st.title("🍫 Nassau Candy Profitability Dashboard")
st.caption(
    "Product performance, division analysis, cost diagnostics and profit concentration")


@st.cache_data
def load_data():
    data = pd.read_csv("Nassau Candy Distributor.csv")
    data.columns = data.columns.str.strip()

    required = [
        "Order Date", "Product Name", "Division",
        "Sales", "Gross Profit", "Cost", "Units"
    ]

    missing = [col for col in required if col not in data.columns]

    if missing:
        raise ValueError(
            f"Missing required columns: {', '.join(missing)}"
        )

    data["Order Date"] = pd.to_datetime(
        data["Order Date"], errors="coerce"
    )

    for col in ["Sales", "Gross Profit", "Cost", "Units"]:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    data = data.dropna(subset=[
        "Order Date", "Product Name", "Division",
        "Sales", "Gross Profit", "Cost", "Units"
    ])

    data = data[data["Sales"] > 0].copy()

    data["Profit Margin (%)"] = (
        data["Gross Profit"] / data["Sales"] * 100
    )

    return data


try:
    df = load_data()
except Exception as error:
    st.error(f"Could not load the dataset: {error}")
    st.info(
        "Check that the CSV file is named "
        "'Nassau Candy Distributor.csv' and is in the same folder as app.py."
    )
    st.stop()


# ---------- Sidebar Filters ----------
st.sidebar.header("Dashboard Filters")

min_date = df["Order Date"].min().date()
max_date = df["Order Date"].max().date()

date_range = st.sidebar.date_input(
    "Order date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

division_options = sorted(df["Division"].unique())

selected_divisions = st.sidebar.multiselect(
    "Select division",
    options=division_options,
    default=division_options
)

margin_threshold = st.sidebar.slider(
    "Minimum product margin (%)",
    min_value=0,
    max_value=100,
    value=60,
    step=1
)

product_search = st.sidebar.text_input(
    "Search product",
    placeholder="e.g. Milk Chocolate"
)


# ---------- Apply Filters ----------
if len(date_range) != 2:
    st.warning("Please select both a start date and an end date.")
    st.stop()

start_date, end_date = date_range

if start_date > end_date:
    st.error("The start date must not be after the end date.")
    st.stop()

filtered = df[
    (df["Order Date"].dt.date >= start_date) &
    (df["Order Date"].dt.date <= end_date) &
    (df["Division"].isin(selected_divisions))
].copy()

if product_search.strip():
    filtered = filtered[
        filtered["Product Name"].str.contains(
            product_search.strip(),
            case=False,
            na=False
        )
    ]

if filtered.empty:
    st.warning("No records match the selected filters.")
    st.stop()


# ---------- Product-Level Summary ----------
product = filtered.groupby("Product Name", as_index=False).agg(
    Sales=("Sales", "sum"),
    Cost=("Cost", "sum"),
    Gross_Profit=("Gross Profit", "sum"),
    Units=("Units", "sum")
)

product["Profit Margin (%)"] = (
    product["Gross_Profit"] / product["Sales"] * 100
)

product["Profit per Unit"] = (
    product["Gross_Profit"] / product["Units"].replace(0, float("nan"))
)

total_sales = product["Sales"].sum()
total_profit = product["Gross_Profit"].sum()

product["Revenue Contribution (%)"] = (
    product["Sales"] / total_sales * 100
)

product["Profit Contribution (%)"] = (
    product["Gross_Profit"] / total_profit * 100
    if total_profit != 0 else 0
)

# The threshold applies to product-level margins
qualified_products = product[
    product["Profit Margin (%)"] >= margin_threshold
].copy()


# ---------- KPI Cards ----------
st.subheader("Business Overview")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Sales", f"{total_sales:,.2f}")
c2.metric("Gross Profit", f"{total_profit:,.2f}")
c3.metric("Units Sold", f"{product['Units'].sum():,.0f}")

overall_margin = (
    total_profit / total_sales * 100 if total_sales else 0
)
c4.metric("Overall Gross Margin", f"{overall_margin:.2f}%")

st.caption(
    "Metrics reflect the selected dates, divisions and product search. "
    "The margin threshold filters products in the relevant product charts and table."
)


# ---------- Module 1: Product Profitability ----------
st.header("1. Product Profitability Overview")

left, right = st.columns(2)

with left:
    st.subheader("Product Margin Leaderboard")

    leaderboard = qualified_products.sort_values(
        "Profit Margin (%)", ascending=False
    )

    fig = px.bar(
        leaderboard,
        x="Profit Margin (%)",
        y="Product Name",
        orientation="h",
        title="Product Gross Margin (%)",
        hover_data=["Sales", "Gross_Profit", "Units"]
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={}
    )

with right:
    st.subheader("Profit Contribution by Product")

    contribution = qualified_products.sort_values(
        "Gross_Profit", ascending=False
    )

    fig = px.bar(
        contribution,
        x="Product Name",
        y="Gross_Profit",
        title="Gross Profit by Product",
        hover_data=["Profit Contribution (%)", "Profit Margin (%)"]
    )
    fig.update_layout(xaxis_tickangle=-35)
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={}
    )

st.subheader("Product KPI Table")

st.dataframe(
    qualified_products.sort_values(
        "Sales", ascending=False
    ).rename(columns={"Gross_Profit": "Gross Profit"}),
    width="stretch",
    hide_index=True
)


# ---------- Module 2: Division Performance ----------
st.header("2. Division Performance Dashboard")

division = filtered.groupby("Division", as_index=False).agg(
    Sales=("Sales", "sum"),
    Gross_Profit=("Gross Profit", "sum"),
    Cost=("Cost", "sum"),
    Units=("Units", "sum")
)

division["Profit Margin (%)"] = (
    division["Gross_Profit"] / division["Sales"] * 100
)

left, right = st.columns(2)

with left:
    st.subheader("Revenue vs Gross Profit")

    division_long = division.melt(
        id_vars="Division",
        value_vars=["Sales", "Gross_Profit"],
        var_name="Metric",
        value_name="Amount"
    )

    fig = px.bar(
        division_long,
        x="Division",
        y="Amount",
        color="Metric",
        barmode="group",
        title="Division Sales and Gross Profit"
    )
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={}
    )

with right:
    st.subheader("Margin Distribution by Division")

    margin_data = filtered.copy()

    fig = px.box(
        margin_data,
        x="Division",
        y="Profit Margin (%)",
        color="Division",
        title="Transaction-Level Margin Distribution"
    )
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={}
    )

st.dataframe(
    division.rename(columns={"Gross_Profit": "Gross Profit"}),
    width="stretch",
    hide_index=True
)


# ---------- Module 3: Cost vs Margin Diagnostics ----------
st.header("3. Cost vs Margin Diagnostics")

left, right = st.columns(2)

with left:
    st.subheader("Cost vs Sales")

    fig = px.scatter(
        product,
        x="Sales",
        y="Cost",
        color="Profit Margin (%)",
        size="Gross_Profit",
        hover_name="Product Name",
        title="Product Cost vs Sales",
        hover_data=["Units"]
    )
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={}
    )

with right:
    st.subheader("Margin Risk Flags")

    if not product.empty:
        median_margin = product["Profit Margin (%)"].median()

        risk = product[
            product["Profit Margin (%)"] < median_margin
        ].copy()

        risk["Review Flag"] = risk["Profit Margin (%)"].apply(
            lambda x: (
                "High Priority Review"
                if x < margin_threshold
                else "Below Product Median"
            )
        )

        st.caption(
            "Flags are screening indicators, not automatic decisions. "
            "They use the selected data and the product-level margin threshold."
        )

        st.dataframe(
            risk.sort_values("Profit Margin (%)")[
                [
                    "Product Name", "Sales", "Cost",
                    "Gross_Profit", "Profit Margin (%)", "Review Flag"
                ]
            ].rename(columns={"Gross_Profit": "Gross Profit"}),
            width="stretch",
            hide_index=True
        )


# ---------- Module 4: Profit Concentration ----------
st.header("4. Profit Concentration Analysis")


def make_pareto(data, value_column, chart_title):
    pareto = data[["Product Name", value_column]].copy()
    pareto = pareto.sort_values(value_column, ascending=False)

    total = pareto[value_column].sum()

    if total == 0:
        st.info("Cannot calculate contribution because the total is zero.")
        return

    pareto["Contribution (%)"] = (
        pareto[value_column] / total * 100
    )
    pareto["Cumulative (%)"] = pareto["Contribution (%)"].cumsum()

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=pareto["Product Name"],
        y=pareto[value_column],
        name=value_column
    ))

    fig.add_trace(go.Scatter(
        x=pareto["Product Name"],
        y=pareto["Cumulative (%)"],
        name="Cumulative Contribution (%)",
        yaxis="y2",
        mode="lines+markers"
    ))

    fig.update_layout(
        title=chart_title,
        xaxis_title="Product",
        yaxis_title=value_column,
        yaxis2=dict(
            title="Cumulative Contribution (%)",
            overlaying="y",
            side="right",
            range=[0, 105]
        ),
        xaxis_tickangle=-40,
        legend=dict(orientation="h")
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={}
    )


left, right = st.columns(2)

with left:
    make_pareto(product, "Sales", "Sales Pareto Analysis")

with right:
    make_pareto(product, "Gross_Profit", "Gross Profit Pareto Analysis")

if total_sales != 0:
    top_three_sales_share = (
        product.nlargest(3, "Sales")["Sales"].sum()
        / total_sales * 100
    )
else:
    top_three_sales_share = 0

if total_profit != 0:
    top_three_profit_share = (
        product.nlargest(3, "Gross_Profit")["Gross_Profit"].sum()
        / total_profit * 100
    )
else:
    top_three_profit_share = 0

c1, c2 = st.columns(2)

c1.metric(
    "Top 3 Products' Sales Share",
    f"{top_three_sales_share:.2f}%"
)
c2.metric(
    "Top 3 Products' Gross Profit Share",
    f"{top_three_profit_share:.2f}%"
)

st.caption(
    "Higher top-product contribution indicates greater concentration "
    "in a small number of products; it does not by itself prove business risk."
)

st.divider()
st.caption("Nassau Candy Distributor | Profitability Analysis Dashboard")
