import streamlit as st
import pandas as pd
import plotly.express as px

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Inventory Rebalancing Dashboard",
    layout="wide"
)

st.title("🚚 Inventory Rebalancing & Logistics Dashboard")


# =========================================================
# LOAD DATA
# =========================================================

@st.cache_data
def load_data():

    shipment_summary_df = pd.read_excel(
        r"outputs\shipment_summary.xlsx"
    )

    inventory_summary_df = pd.read_excel(
        r"outputs\inventory_summary.xlsx"
    )

    return (
        shipment_summary_df,
        inventory_summary_df,
    )


(
    shipment_summary_df,
    inventory_summary_df,
    route_summary_df
) = load_data()


# =========================================================
# CATEGORY TABS
# =========================================================

tabs = st.tabs([
    "Frozen",
    "Ambient",
    "Chilled",
    "Overall"
])


# =========================================================
# HELPER FUNCTION
# =========================================================

def render_dashboard(
    category_name,
    shipment_df,
    inventory_df,
    route_df
):

    st.subheader(f"{category_name} Dashboard")

    # =====================================================
    # FILTER CATEGORY
    # =====================================================

    if category_name != "Overall":

        shipment_df = shipment_df[
            shipment_df["Category"] == category_name
        ]

        inventory_df = inventory_df[
            inventory_df["Category"] == category_name
        ]

        route_df = route_df[
            route_df["Category"] == category_name
        ]

    # =====================================================
    # KPI SECTION
    # =====================================================

    total_qty = shipment_df["Quantity"].sum()

    total_routes = route_df["Route"].nunique()

    total_products = shipment_df["Product"].nunique()

    avg_inv_days = round(
        inventory_df["Current Inv Days"].mean(),
        2
    )

    fulfillment_pct = round(
        inventory_df["Fulfillment %"].mean(),
        2
    )

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "Total Shipment Qty",
        f"{int(total_qty):,} kg"
    )

    col2.metric(
        "Total Routes",
        total_routes
    )

    col3.metric(
        "Products",
        total_products
    )

    col4.metric(
        "Avg Inv Days",
        avg_inv_days
    )

    col5.metric(
        "Fulfillment %",
        f"{fulfillment_pct}%"
    )

    st.divider()

    # =====================================================
    # LARGEST SHORTAGES
    # =====================================================

    st.subheader("⚠ Largest Shortages")

    shortage_df = inventory_df.sort_values(
        by="Remaining Shortage (kg)",
        ascending=False
    ).head(10)

    st.dataframe(
        shortage_df[
            [
                "Product",
                "Hub",
                "Current Inv Days",
                "Remaining Shortage (kg)"
            ]
        ],
        use_container_width=True
    )

    st.divider()

    # =====================================================
    # VEHICLE MOVEMENTS
    # =====================================================

    st.subheader("🚛 Vehicle Movements")

    vehicle_df = route_df.sort_values(
        by="Total Quantity",
        ascending=False
    )

    st.dataframe(
        vehicle_df,
        use_container_width=True
    )

    st.divider()

    # =====================================================
    # RECOMMENDED SALES PUSH
    # =====================================================

    st.subheader("📈 Recommended Sales Push")

    excess_df = inventory_df.sort_values(
        by="Current Inv Days",
        ascending=False
    ).head(10)

    st.dataframe(
        excess_df[
            [
                "Product",
                "Hub",
                "Current Inv Days"
            ]
        ],
        use_container_width=True
    )

    st.divider()

    # =====================================================
    # INVENTORY CHART
    # =====================================================

    st.subheader("📊 Inventory Days Distribution")

    chart_df = inventory_df.sort_values(
        by="Current Inv Days",
        ascending=False
    ).head(20)

    fig = px.bar(
        chart_df,
        x="Hub",
        y="Current Inv Days",
        color="Product",
        title="Inventory Days by Hub"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.divider()

    # =====================================================
    # ROUTE FLOW CHART
    # =====================================================

    st.subheader("🛣 Route Quantities")

    route_chart_df = route_df.sort_values(
        by="Total Quantity",
        ascending=False
    ).head(15)

    fig2 = px.bar(
        route_chart_df,
        x="Route",
        y="Total Quantity",
        color="Category",
        title="Top Route Movements"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )


# =========================================================
# TAB RENDERING
# =========================================================

with tabs[0]:

    render_dashboard(
        "Frozen",
        shipment_summary_df,
        inventory_summary_df,
        route_summary_df
    )

with tabs[1]:

    render_dashboard(
        "Ambient",
        shipment_summary_df,
        inventory_summary_df,
        route_summary_df
    )

with tabs[2]:

    render_dashboard(
        "Chilled",
        shipment_summary_df,
        inventory_summary_df,
        route_summary_df
    )

with tabs[3]:

    render_dashboard(
        "Overall",
        shipment_summary_df,
        inventory_summary_df,
        route_summary_df
    )
