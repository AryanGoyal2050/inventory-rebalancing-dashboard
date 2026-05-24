import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Inventory Rebalancing Dashboard",
    layout="wide"
)

import pandas as pd
import streamlit as st


def get_dispatch_summary_for_hub(
    shipment_df,
    source_hub,
    category
):

    filtered_df = shipment_df[

        (shipment_df["From"] == source_hub)

        &

        (shipment_df["Category"] == category)

    ]

    if filtered_df.empty:

        return pd.DataFrame(
            columns=[
                "To",
                "Total Qty",
                "Products"
            ]
        )

    summary_df = (
        filtered_df
        .groupby("To")
        .agg(
            {
                "Quantity": "sum",

                "Product": lambda x:
                    ", ".join(
                        map(
                            str,
                            sorted(x.unique())
                        )
                    )
            }
        )
        .reset_index()
    )

    summary_df.rename(
        columns={
            "Quantity": "Total Qty",
            "Product": "Products"
        },
        inplace=True
    )

    summary_df = summary_df.sort_values(
        by="Total Qty",
        ascending=False
    )

    return summary_df


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

    st.title("Tab 3")

    st.write(
        "To be added"
    )