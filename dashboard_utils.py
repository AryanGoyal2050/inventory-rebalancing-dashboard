import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import subprocess
import time

# TAB - 2

def render_dispatch_manifest(
    shipment_df,
    source_hub,
    category,
    hub_df,
    product_df
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

        # If not found, put destination name as "Unknown"
        destinaiton_name = hub_df.loc[
            hub_df["Hub"] == destination,
            "Hub Compress"
        ].iloc[0]

        if pd.isna(destinaiton_name):
            destinaiton_name = "Unknown"

        st.markdown(
            f"""
            ### {destinaiton_name} - {round(destination_total/1000, 2)} MT
            """
        )

        for _, row in destination_df.iterrows():

            product_name = product_df.loc[
                product_df["Product"] == row["Product"],
                "Product Name"
            ].iloc[0]

            st.markdown(
                f"""
                • {product_name} ({row['Product']})
                — {round(row['Quantity'], 2)} KG
                """
            )

        st.divider()

def render_hub_shortages(shortage_df):
    st.subheader("Shortages")
    st.dataframe(
        shortage_df,
        use_container_width=True,
        hide_index=True
    )

def render_hub_excesses(excess_df):
    st.subheader("Excess Inventory")
    st.dataframe(
        excess_df,
        use_container_width=True,
        hide_index=True
    )
    

# TAB - 3

def get_product_inventory_view(
    inventory_df,
    product
):

    df = inventory_df[
        inventory_df["Product"] == product
    ].copy()

    return df

def render_inventory_days_chart(df, hub_df):

    plot_df = df.copy()

    # =========================================
    # CLEAN + PREP (IMPORTANT for mapping)
    # =========================================
    plot_df["Hub"] = plot_df["Hub"].astype(str).str.strip()
    hub_df["Hub"] = hub_df["Hub"].astype(str).str.strip()

    # =========================================
    # SORT
    # =========================================
    plot_df = plot_df.sort_values(
        by="Current Inv Days",
        ascending=False
    )

    # =========================================
    # CAP EXTREME VALUES
    # =========================================
    MAX_DAYS_DISPLAY = 60

    plot_df["Current Display"] = plot_df["Current Inv Days"].clip(upper=MAX_DAYS_DISPLAY)
    plot_df["Post Display"] = plot_df["Post Ship Inv Days"].clip(upper=MAX_DAYS_DISPLAY)

    # =========================================
    # HUB NAME MAPPING
    # =========================================
    hub_map = hub_df.set_index("Hub")["Hub Compress"]
    plot_df["Hub Name"] = plot_df["Hub"].map(hub_map)

    # fallback if mapping fails (very important)
    plot_df["Hub Name"].fillna(plot_df["Hub"], inplace=True)

    # =========================================
    # FIGURE
    # =========================================
    fig = go.Figure()

    # BEFORE
    fig.add_trace(
        go.Bar(
            name="Before Transfer",
            x=plot_df["Hub"],   # ✅ keep real key
            y=plot_df["Current Display"],
            text=plot_df["Current Inv Days"].round(1),
            textposition="outside",
            customdata=plot_df["Current Inv Days"],
            hovertemplate=(
                "<b>Hub:</b> %{customdata}<br>"
                "<b>Inventory Days:</b> %{y:.2f}"
                "<extra></extra>"
            ),
        )
    )

    # AFTER
    fig.add_trace(
        go.Bar(
            name="After Transfer",
            x=plot_df["Hub"],   # ✅ keep real key
            y=plot_df["Post Display"],
            text=plot_df["Post Ship Inv Days"].round(1),
            textposition="outside",
            customdata=plot_df["Post Ship Inv Days"],
            hovertemplate=(
                "<b>Hub:</b> %{customdata}<br>"
                "<b>Inventory Days:</b> %{y:.2f}"
                "<extra></extra>"
            ),
        )
    )

    # TARGET LINE
    fig.add_hline(
        y=21,
        line_dash="dash",
        annotation_text="Target = 21 Days"
    )

    # =========================================
    # LAYOUT (KEY PART FOR DISPLAY)
    # =========================================
    fig.update_layout(
        title="Inventory Days by Hub",
        barmode="group",
        height=600,
        xaxis_title="Hub",
        yaxis_title="Inventory Days",

        yaxis=dict(range=[0, MAX_DAYS_DISPLAY]),

        # ✅ THIS IS THE IMPORTANT PART
        xaxis=dict(
            type="category",
            tickmode="array",
            tickvals=plot_df["Hub"],        # real values
            ticktext=plot_df["Hub Name"],   # display names
            tickangle=-45
        )
    )

    st.plotly_chart(fig, use_container_width=True)

def render_inventory_quantity_chart(df, hub_df):

    plot_df = df.copy()

    # =========================================
    # CLEAN + PREP (IMPORTANT)
    # =========================================
    plot_df["Hub"] = plot_df["Hub"].astype(str).str.strip()
    hub_df["Hub"] = hub_df["Hub"].astype(str).str.strip()

    # =========================================
    # SORT
    # =========================================
    plot_df = plot_df.sort_values(
        by="Current Inv",
        ascending=False
    )

    # =========================================
    # CONVERT TO MT
    # =========================================
    plot_df["Current Inv MT"] = plot_df["Current Inv"] / 1000
    plot_df["Post Ship Inv MT"] = plot_df["Post Ship Inv"] / 1000

    # =========================================
    # HUB NAME MAPPING
    # =========================================
    hub_map = hub_df.set_index("Hub")["Hub Compress"]
    plot_df["Hub Name"] = plot_df["Hub"].map(hub_map)

    # fallback if mapping fails
    plot_df["Hub Name"].fillna(plot_df["Hub"], inplace=True)

    # =========================================
    # FIGURE
    # =========================================
    fig = go.Figure()

    # BEFORE
    fig.add_trace(
        go.Bar(
            name="Before Transfer",
            x=plot_df["Hub"],   # ✅ keep real key
            y=plot_df["Current Inv MT"],
            text=plot_df["Current Inv MT"].round(1),
            textposition="outside",
            customdata=plot_df["Current Inv"],
            hovertemplate=(
                "<b>Hub:</b> %{x}<br>"
                "<b>Inventory:</b> %{customdata:,.0f} kg"
                "<extra></extra>"
            ),
            width=0.4
        )
    )

    # AFTER
    fig.add_trace(
        go.Bar(
            name="After Transfer",
            x=plot_df["Hub"],   # ✅ keep real key
            y=plot_df["Post Ship Inv MT"],
            text=plot_df["Post Ship Inv MT"].round(1),
            textposition="outside",
            customdata=plot_df["Post Ship Inv"],
            hovertemplate=(
                "<b>Hub:</b> %{x}<br>"
                "<b>Inventory:</b> %{customdata:,.0f} kg"
                "<extra></extra>"
            ),
            width=0.4
        )
    )

    # =========================================
    # LAYOUT (DISPLAY HUB NAME)
    # =========================================
    fig.update_layout(
        title="Inventory Quantity by Hub",
        barmode="group",
        height=600,
        xaxis_title="Hub",
        yaxis_title="Inventory Quantity (MT)",

        uniformtext_minsize=8,
        uniformtext_mode='hide',

        xaxis=dict(
            type="category",
            tickmode="array",
            tickvals=plot_df["Hub"],        # real keys
            ticktext=plot_df["Hub Name"],   # display names
            tickangle=-45
        )
    )

    st.plotly_chart(fig, use_container_width=True)

def render_shortage_table(df, hub_df):

    shortage_df = df.copy()

    shortage_df["Shortage Qty"] = (
        shortage_df["RF"] / 30
        *
        (21 - shortage_df["Current Inv Days"])
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
            "RF",
            "Sales",
            "Current Inv Days",
            "Shortage Qty"
        ]
    ]
    shortage_df["Current Inv Days"] = shortage_df["Current Inv Days"].round(1)
    shortage_df["Shortage Qty"] = shortage_df["Shortage Qty"].round(0)

    shortage_df.rename(
        columns={
            "Shortage Qty": "Shortage (kg)"
        },
        inplace=True
    )

    shortage_df["Hub Name"] = shortage_df["Hub"].map(
        hub_df.set_index("Hub")["Hub Compress"]
    )

    st.subheader("Shortages")

    st.dataframe(
        shortage_df["Hub Name, RF, Sales, Current Inv Days, Shortage (kg)".split(", ")],
        use_container_width=True,
        hide_index=True
    )

def render_excess_table(df, hub_df):

    excess_df = df.copy()

    excess_df["Excess Qty"] = (
        excess_df["Current Inv Days"]
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
            "RF",
            "Sales",
            "Current Inv Days",
            "Excess Qty"
        ]
    ]
    excess_df["Current Inv Days"] = excess_df["Current Inv Days"].round(1)
    excess_df["Excess Qty"] = excess_df["Excess Qty"].round(0)

    excess_df.rename(
        columns={
            "Excess Qty": "Excess (kg)"
        },
        inplace=True
    )

    excess_df["Hub Name"] = excess_df["Hub"].map(
        hub_df.set_index("Hub")["Hub Compress"]
    )

    st.subheader("Excess")

    st.dataframe(
        excess_df["Hub Name, RF, Sales, Current Inv Days, Excess (kg)".split(", ")],
        use_container_width=True,
        hide_index=True
    )

# TAB - 4

def build_planning_view(inventory_df, product_df):

    planning_df = inventory_df.copy()
    planning_df["Product Name"] = planning_df["Product"].map(
        product_df.set_index("Product")["Product Name"]
    )

    # planning_df["Product Name"] = product_df.loc[
    #     product_df["Product"] == planning_df["Product"],
    #     "Product Name"
    # ].iloc[0]

    # =====================================
    # SHORTAGE
    # =====================================

    planning_df["Shortage Kg"] = (
        planning_df["RF"] / 30
        *
        (21 - planning_df["Post Ship Inv Days"])
    ).clip(lower=0)

    # =====================================
    # EXCESS
    # =====================================

    planning_df["Excess Kg"] = (

        (planning_df["Post Ship Inv Days"] - 21)
        *
        planning_df["RF"] / 30
    ).clip(lower=0)

    # =====================================
    # PRODUCT LEVEL SUMMARY
    # =====================================

    summary_df = (
        planning_df
        .groupby(
            [
                "Product",
                "Category"
            ]
        )
        .agg(
            {
                "Hub": "count",
                "Shortage Kg": "sum",
                "Excess Kg": "sum"
            }
        )
        .reset_index()
    )

    # =====================================
    # NUMBER OF SHORTAGE HUBS
    # =====================================

    shortage_count_df = (
        planning_df[
            planning_df["Shortage Kg"] > 0
        ]
        .groupby("Product")
        .size()
        .reset_index(name="Number of Shortage Hubs")
    )

    summary_df = summary_df.merge(
        shortage_count_df,
        on="Product",
        how="left"
    )

    summary_df[
        "Number of Shortage Hubs"
    ] = summary_df[
        "Number of Shortage Hubs"
    ].fillna(0)

    # =====================================
    # NET SHORTAGE
    # =====================================

    summary_df["Net Shortage Kg"] = (
        summary_df["Shortage Kg"]
        -
        summary_df["Excess Kg"]
    )

    # =====================================
    # SORT
    # =====================================

    summary_df = summary_df.sort_values(
        by="Net Shortage Kg",
        ascending=False
    )

    # =====================================
    # ROUNDING
    # =====================================

    numeric_cols = [
        "Shortage Kg",
        "Excess Kg",
        "Net Shortage Kg"
    ]

    summary_df[numeric_cols] = (
        summary_df[numeric_cols]
        .round(2)
    )

    summary_df["Product Name"] = summary_df["Product"].map(
        product_df.set_index("Product")["Product Name"]
    )

    return summary_df["Product, Product Name, Category, Shortage Kg, Excess Kg, Net Shortage Kg, Number of Shortage Hubs".split(", ")]

import pandas as pd

import pandas as pd

def build_hub_stats_view(inventory_df, shipment_df, hub_df):

    # --- FIX TYPES ---
    inventory_df["Hub"] = pd.to_numeric(inventory_df["Hub"], errors="coerce")
    shipment_df["From"] = pd.to_numeric(shipment_df["From"], errors="coerce")
    shipment_df["To"] = pd.to_numeric(shipment_df["To"], errors="coerce")
    hub_df["Hub"] = pd.to_numeric(hub_df["Hub"], errors="coerce")

    # --- STOCK & RF ---
    inv_agg = (
        inventory_df
        .groupby("Hub", as_index=False)
        .agg(
            Stock=("Current Inv", "sum"),   # ✅ better column from your table
            RF=("RF", "sum")
        )
    )

    # --- OUTGOING ---
    outgoing = (
        shipment_df
        .groupby("From", as_index=False)["Quantity"]
        .sum()
        .rename(columns={"From": "Hub", "Quantity": "Outgoing"})
    )

    # --- INCOMING ---
    incoming = (
        shipment_df
        .groupby("To", as_index=False)["Quantity"]
        .sum()
        .rename(columns={"To": "Hub", "Quantity": "Incoming"})
    )

    # --- BASE HUB TABLE ---
    df = hub_df[["Hub", "Hub Name"]].copy()

    # --- MERGES ---
    df = df.merge(inv_agg, on="Hub", how="left")
    df = df.merge(incoming, on="Hub", how="left")
    df = df.merge(outgoing, on="Hub", how="left")

    # --- CLEAN NULLS ---
    df[["Stock", "RF", "Incoming", "Outgoing"]] = df[
        ["Stock", "RF", "Incoming", "Outgoing"]
    ].fillna(0)

    # --- INVENTORY POSITION ---
    df["Inventory Position"] = df["Stock"] + df["Incoming"] - df["Outgoing"]

    # --- SORT ---
    df = df.sort_values("RF", ascending=False)

    return df

def render_net_shortage_chart(planning_df):

    plot_df = planning_df.head(20).copy()
    plot_df["Product"] = (
        plot_df["Product"].astype(str)
    )
    fig = px.bar(
        plot_df,
        x="Product",
        y="Net Shortage Kg",
        color="Category",
        title="Top Products by Net Shortage",
        text="Net Shortage Kg"
    )

    fig.update_layout(
        height=600,
        xaxis_title="Product",
        yaxis_title="Net Shortage (kg)",
        xaxis_tickangle=-45
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

def render_shortage_excess_chart(planning_df):

    plot_df = planning_df.head(20).copy()

    plot_df["Product"] = (
        plot_df["Product"].astype(str)
    )

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name="Shortage",
            x=plot_df["Product"],
            y=plot_df["Shortage Kg"]
        )
    )

    fig.add_trace(
        go.Bar(
            name="Excess",
            x=plot_df["Product"],
            y=plot_df["Excess Kg"]
        )
    )

    fig.update_layout(

        title="Shortage vs Excess",
        barmode="group",
        height=600,
        xaxis_title="Product",
        yaxis_title="Quantity (kg)",
        xaxis_tickangle=-45
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )
