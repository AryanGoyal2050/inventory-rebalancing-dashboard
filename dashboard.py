import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Inventory Rebalancing Dashboard",
    layout="wide"
)

# ==========================================
# LOAD DATA
# ==========================================

inventory_df = pd.read_excel(
    "outputs/inventory_summary.xlsx"
)

shipment_df = pd.read_excel(
    "outputs/shipment_summary.xlsx"
)

route_df = pd.read_excel(
    "outputs/route_analysis.xlsx"
)

# ==========================================
# TABS
# ==========================================

tab1, tab2, tab3 = st.tabs(
    [
        "Route Analysis",
        "Tab 2",
        "Tab 3"
    ]
)

# ==========================================
# TAB 1
# ==========================================

with tab1:

    st.title("Route Wise Analysis")

    # --------------------------------------
    # TOP OUTGOING
    # --------------------------------------

    st.subheader("Top Outgoing Routes")

    outgoing_df = (
        route_df
        .sort_values(
            by="Total Qty",
            ascending=False
        )
        .head(20)
    )

    st.dataframe(
        outgoing_df,
        use_container_width=True
    )

    # --------------------------------------
    # TOP INCOMING
    # --------------------------------------

    st.subheader("Top Incoming Routes")

    incoming_df = (
        route_df
        .groupby("Destination")
        .agg(
            {
                "Total Qty": "sum"
            }
        )
        .reset_index()
        .sort_values(
            by="Total Qty",
            ascending=False
        )
    )

    st.dataframe(
        incoming_df,
        use_container_width=True
    )

# ==========================================
# TAB 2
# ==========================================

with tab2:

    st.title("Tab 2")

    st.write(
        "To be added"
    )

# ==========================================
# TAB 3
# ==========================================

with tab3:

    st.title("Tab 3")

    st.write(
        "To be added"
    )