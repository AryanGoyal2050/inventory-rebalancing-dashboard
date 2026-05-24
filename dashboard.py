import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Inventory Rebalancing Dashboard",
    layout="wide"
)

import pandas as pd
import streamlit as st

# ==========================================
# HELPER FUNCTIONS
# ==========================================

# TAB - 2

def render_dispatch_manifest(
    shipment_df,
    source_hub,
    category
):

    filtered_df = shipment_df[
        (shipment_df["From"] == source_hub)
        &
        (shipment_df["Category"] == category)
    ]

    st.subheader(category)

    if filtered_df.empty:
        st.info("No dispatches")
        return

    destination_order = (
        filtered_df
        .groupby("To")["Quantity"]
        .sum()
        .sort_values(ascending=False)
        .index
    )

    # print(destination_df)

    for destination in destination_order:

        destination_df = filtered_df[
            filtered_df["To"] == destination
        ]

        destination_df = destination_df.sort_values(
            by="Quantity",
            ascending=False
        )

        destination_total = (
            destination_df["Quantity"].sum()
        )

        st.markdown(
            f"""
            ### {destination} - ({round(destination_total/1000, 2)} MT)
            """
        )

        for _, row in destination_df.iterrows():

            st.markdown(
                f"""
                • Product {int(row['Product'])}
                — {round(row['Quantity']/1000, 2)} MT
                """
            )

        st.divider()

# TAB - 3

def get_product_inventory_view(
    inventory_df,
    product
):

    df = inventory_df[
        inventory_df["Product"] == product
    ].copy()

    return df

def render_inventory_days_chart(df):

    plot_df = df.copy()

    # =========================================
    # SORT
    # =========================================

    plot_df = plot_df.sort_values(
        by="Current Inv Days",
        ascending=False
    )

    # =========================================
    # CONVERT HUBS TO STRING
    # =========================================

    plot_df["Hub"] = plot_df["Hub"].astype(str)

    # =========================================
    # CAP EXTREME VALUES
    # =========================================

    MAX_DAYS_DISPLAY = 100

    plot_df["Current Display"] = plot_df[
        "Current Inv Days"
    ].clip(upper=MAX_DAYS_DISPLAY)

    plot_df["Post Display"] = plot_df[
        "Post Ship Inv Days"
    ].clip(upper=MAX_DAYS_DISPLAY)

    # =========================================
    # FIGURE
    # =========================================

    fig = go.Figure()

    # BEFORE
    fig.add_trace(
        go.Bar(
            name="Before Transfer",
            x=plot_df["Hub"],
            y=plot_df["Current Display"],
            text=plot_df["Current Inv Days"].round(1),
            textposition="outside",
            customdata=plot_df[
                "Current Inv Days"
            ],
            hovertemplate=
            (
                "<b>Hub:</b> %{x}<br>"
                "<b>Inventory Days:</b> %{customdata:.2f}"
                "<extra></extra>"
            )
        )
    )

    # AFTER
    fig.add_trace(
        go.Bar(
            name="After Transfer",
            x=plot_df["Hub"],
            y=plot_df["Post Display"],
            customdata=plot_df[
                "Post Ship Inv Days"
            ],
            text=plot_df["Post Ship Inv Days"].round(1),
            textposition="outside",
            hovertemplate=
            (
                "<b>Hub:</b> %{x}<br>"
                "<b>Inventory Days:</b> %{customdata:.2f}"
                "<extra></extra>"
            )
        )
    )

    # TARGET LINE
    fig.add_hline(
        y=21,
        line_dash="dash",
        annotation_text="Target = 21 Days"
    )

    # =========================================
    # LAYOUT
    # =========================================

    fig.update_layout(

        title="Inventory Days by Hub",

        barmode="group",

        height=600,

        xaxis_title="Hub",

        yaxis_title="Inventory Days",

        yaxis=dict(
            range=[0, MAX_DAYS_DISPLAY]
        ),

        # IMPORTANT FIX
        xaxis=dict(
            type="category",
            tickmode="array",
            tickvals=plot_df["Hub"],
            ticktext=plot_df["Hub"]
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

def render_inventory_quantity_chart(df):

    plot_df = df.sort_values(
        by="Current Inv",
        ascending=False
    )

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name="Before Transfer",
            x=plot_df["Hub"].astype(str),
            y=plot_df["Current Inv"]
        )
    )

    fig.add_trace(
        go.Bar(
            name="After Transfer",
            x=plot_df["Hub"].astype(str),
            y=plot_df["Post Ship Inv"]
        )
    )

    fig.update_layout(
        title="Inventory Quantity by Hub",
        barmode="group",
        xaxis_title="Hub",
        yaxis_title="Quantity (kg)",
        height=500
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

def render_shortage_table(df):

    shortage_df = df.copy()

    shortage_df["Shortage Qty"] = (

        shortage_df["RF"]
        *
        (21 - shortage_df["Post Ship Inv Days"])
        / 30

    ).clip(lower=0)

    shortage_df = shortage_df[
        shortage_df["Shortage Qty"] > 0
    ]

    shortage_df = shortage_df.sort_values(
        by="Shortage Qty",
        ascending=False
    )

    shortage_df = shortage_df[
        [
            "Hub",
            "Post Ship Inv Days",
            "Shortage Qty"
        ]
    ]

    shortage_df.rename(
        columns={
            "Post Ship Inv Days": "Inv Days",
            "Shortage Qty": "Shortage (kg)"
        },
        inplace=True
    )

    st.subheader("Shortages")

    st.dataframe(
        shortage_df,
        use_container_width=True,
        hide_index=True
    )

def render_excess_table(df):

    excess_df = df.copy()

    excess_df["Excess Qty"] = (

        excess_df["Post Ship Inv Days"]
        - 21

    ) * excess_df["RF"] / 30

    excess_df["Excess Qty"] = excess_df[
        "Excess Qty"
    ].clip(lower=0)

    excess_df = excess_df[
        excess_df["Excess Qty"] > 0
    ]

    excess_df = excess_df.sort_values(
        by="Excess Qty",
        ascending=False
    )

    excess_df = excess_df[
        [
            "Hub",
            "Post Ship Inv Days",
            "Excess Qty"
        ]
    ]

    excess_df.rename(
        columns={
            "Post Ship Inv Days": "Inv Days",
            "Excess Qty": "Excess (kg)"
        },
        inplace=True
    )

    st.subheader("Excess")

    st.dataframe(
        excess_df,
        use_container_width=True,
        hide_index=True
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

    st.title("Hub Dispatch Analysis")

    hub_list = sorted(
        shipment_df["From"].unique()
    )

    selected_hub = st.selectbox(
        "Select Source Hub",
        hub_list
    )

    frozen_col, ambient_col, chill_col = st.columns(3)

    with frozen_col:

        render_dispatch_manifest(
            shipment_df,
            selected_hub,
            "Frozen"
        )

    with ambient_col:

        render_dispatch_manifest(
            shipment_df,
            selected_hub,
            "Ambient"
        )

    with chill_col:

        render_dispatch_manifest(
            shipment_df,
            selected_hub,
            "Chill"
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

    product_df = get_product_inventory_view(
        inventory_df,
        selected_product
    )


    render_inventory_days_chart(
        product_df
    )


    render_inventory_quantity_chart(
        product_df
    )

    shortage_col, excess_col = st.columns(2)

    with shortage_col:

        render_shortage_table(
            product_df
        )

    with excess_col:

        render_excess_table(
            product_df
        )

