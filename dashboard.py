import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import subprocess
import time

from dashboard_utils import *

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

product_df = pd.read_excel(
    "inputs/product_list.xlsx"
)

hub_df = pd.read_excel(
    "inputs/hub_list.xlsx"
)

st.title("Inventory Rebalancing Dashboard")

# ==========================================
# TABS
# ==========================================

tab0, tab1, tab2, tab3, tab4 = st.tabs(
    [
        "Control Centre",
        "Overall Summary",
        "Hub View",
        "Product View",
        "Planning View"
    ]
)

# ==========================================
# TAB 0
# ==========================================

with tab0:

    st.title("Control Center")

    st.markdown("---")

    st.subheader("Optimization Engine")

    st.write(
        """
        Click the button below to:
        - Reload latest inventory input
        - Run optimization
        - Generate fresh outputs
        - Refresh dashboard analytics
        """
    )

    # ======================================
    # RUN BUTTON
    # ======================================

    if st.button(
        "Run Optimization",
        type="primary",
        use_container_width=True
    ):

        with st.spinner(
            "Running optimization engine..."
        ):

            try:
                result = subprocess.run(
                    ["python", "main.py"],
                    capture_output=True,
                    text=True
                )

                st.success(
                    "Optimization completed successfully."
                )

                st.code(result.stdout)

                # Small delay
                time.sleep(2)

                st.rerun()

            except Exception as e:
                st.error(
                    f"Optimization failed: {e}"
                )

# ==========================================
# TAB 1
# ==========================================

with tab1:

    st.title("Overall Summary")

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
# TAB 2 - Hub View
# ==========================================

with tab2:

    hub_list = sorted(
        shipment_df["From"].unique()
    )

    st.title("Select Hub")
    
    selected_hub = st.selectbox(
        "Select Hub",
        hub_list,
        label_visibility="collapsed"
    )

    hub_inventory_df = inventory_df[
        inventory_df["Hub"] == selected_hub
    ].copy()
    hub_inventory_df = hub_inventory_df[
        hub_inventory_df["RF"] > 0
    ]

    # =========================================================
    # INVENTORY TARGETS
    # =========================================================

    TARGET_INV_DAYS = 21

    # =========================================================
    # DAILY DEMAND
    # RF = monthly demand
    # =========================================================

    hub_inventory_df["daily_demand"] = (
        hub_inventory_df["RF"] / 30
    )

    # =========================================================
    # SHORTAGE / EXCESS CALCULATION
    # =========================================================

    hub_inventory_df["target_stock"] = (
        TARGET_INV_DAYS *
        hub_inventory_df["daily_demand"]
    )

    hub_inventory_df["inventory_gap"] = (
        hub_inventory_df["Current Inv"] -
        hub_inventory_df["target_stock"]
    )

    # =========================================================
    # SHORTAGES
    # current inv days < target
    # =========================================================

    shortage_df = hub_inventory_df[
        hub_inventory_df["Current Inv Days"] < TARGET_INV_DAYS
    ].copy()

    shortage_df["Shortage (KG)"] = abs(
        shortage_df["inventory_gap"]
    ).round(0)

    shortage_df["RF"] = shortage_df["RF"].round(0)
    shortage_df["Current Inv Days"] = shortage_df["Current Inv Days"].round(2)

    shortage_df["Product Name"] = shortage_df["Product"].map(
        product_df.set_index("Product")["Product Name"]
    )

    shortage_df = shortage_df[[
        "Product",
        "Product Name",
        "RF",
        "Current Inv",
        "Current Inv Days",
        "Shortage (KG)"
    ]]

    shortage_df = shortage_df.sort_values(
        by="Shortage (KG)",
        ascending=False
    )

    # =========================================================
    # EXCESSES
    # current inv days > target
    # =========================================================

    excess_df = hub_inventory_df[
        hub_inventory_df["Current Inv Days"] > TARGET_INV_DAYS
    ].copy()

    excess_df["Excess (KG)"] = (
        excess_df["inventory_gap"]
    ).round(0)

    excess_df["RF"] = excess_df["RF"].round(0)
    excess_df["Current Inv Days"] = excess_df["Current Inv Days"].round(2)

    excess_df["Product Name"] = excess_df["Product"].map(
        product_df.set_index("Product")["Product Name"]
    )

    excess_df = excess_df[[
        "Product",
        "Product Name",
        "RF",
        "Current Inv",
        "Current Inv Days",
        "Excess (KG)"
    ]]

    excess_df = excess_df.sort_values(
        by="Excess (KG)",
        ascending=False
    )

    shortage_col, excess_col = st.columns(2)

    with shortage_col:
        render_hub_shortages(shortage_df)

    with excess_col:
        render_hub_excesses(excess_df)

    st.title("Hub Dispatch Analysis")

    frozen_col, ambient_col, chill_col = st.columns(3)

    with frozen_col:

        render_dispatch_manifest(
            shipment_df,
            selected_hub,
            "Frozen",
            hub_df,
            product_df
        )

    with ambient_col:

        render_dispatch_manifest(
            shipment_df,
            selected_hub,
            "Ambient",
            hub_df,
            product_df
        )

    with chill_col:

        render_dispatch_manifest(
            shipment_df,
            selected_hub,
            "Chill",
            hub_df,
            product_df
        )

# ==========================================
# TAB 3
# ==========================================

with tab3:

    st.title("Product Analysis")

    product_list = sorted(
        inventory_df["Product"].unique()
    )

    selected_product = st.selectbox(
        "Select Product",
        product_list
    )

    product_inventory_df = get_product_inventory_view(
        inventory_df,
        selected_product
    )

    shortage_col, excess_col = st.columns(2)

    with shortage_col:
        render_shortage_table(
            product_inventory_df
        )

    with excess_col:
        render_excess_table(
            product_inventory_df
        )

    render_inventory_days_chart(
        product_inventory_df[(product_inventory_df["RF"] > 0) | (product_inventory_df["Current Inv"] > 0)],
        hub_df
    )


    render_inventory_quantity_chart(
        product_inventory_df[(product_inventory_df["RF"] > 0) | (product_inventory_df["Current Inv"] > 0)],
        hub_df
    )

# ==========================================
# TAB 4 - Planning View
# ==========================================

with tab4:

    st.title("Production Planning View")

    planning_df = build_planning_view(
        inventory_df,
        product_df
    )

    # ======================================
    # MAIN TABLE
    # ======================================

    st.subheader("Product Planning Summary")

    st.dataframe(
        planning_df,
        use_container_width=True,
        hide_index=True
    )

    # ======================================
    # HUB TABLE
    # ======================================

    hub_stats_df = build_hub_stats_view(
        inventory_df,
        shipment_df,
        hub_df
    )

    st.subheader("Hub Statistics")

    st.dataframe(
        hub_stats_df,
        use_container_width=True,
        hide_index=True
    )

    # ======================================
    # CHARTS
    # ======================================

    # render_net_shortage_chart(
    #     planning_df
    # )

    # render_shortage_excess_chart(
    #     planning_df
    # )

