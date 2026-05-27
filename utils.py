import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math
import json

CONFIG_PATH = "config.json"

def load_config():
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
    return config

def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(
            config,
            f,
            indent = 4
        )

def auto_detect_column(columns, possible_names):

    lower_map = {c.lower().strip(): c for c in columns}

    for name in possible_names:
        if name.lower() in lower_map:
            return lower_map[name.lower()]

    raise ValueError(f"Could not detect column from: {possible_names}")


def load_inventory_data(file_path):

    df = pd.read_excel(file_path)

    hub_col = auto_detect_column(df.columns, ["Hub"])
    product_col = auto_detect_column(df.columns, ["Product"])
    rf_col = auto_detect_column(df.columns, ["RF", "forecast"])
    rt_col = auto_detect_column(df.columns, ["Ready Transit", "rt"])
    sales_col = auto_detect_column(df.columns, ["Sales", "sales"])
    readystock_col = auto_detect_column(df.columns, ["Ready Stock"])

    df = df.rename(columns={
        hub_col: "Hub",
        product_col: "Product",
        rf_col: "RF",
        sales_col: "Sales",
        readystock_col: "Ready Stock",
        rt_col: "RT"
    })

    df = df[["Hub", "Product", "RF", "Sales", "Ready Stock", "RT"]].copy()

    df["Hub"] = pd.to_numeric(df["Hub"], errors="coerce").astype(int)
    df["Product"] = pd.to_numeric(df["Product"], errors="coerce").astype(int)

    df["RF"] = pd.to_numeric(df["RF"], errors="coerce").fillna(0)
    df["Sales"] = pd.to_numeric(df["Sales"], errors="coerce").fillna(0)
    df["Ready Stock"] = pd.to_numeric(df["Ready Stock"], errors="coerce").fillna(0)
    df["RT"] = pd.to_numeric(df["RT"], errors="coerce").fillna(0)

    df["RF"] = df["RF"].clip(lower=0)
    df["Sales"] = df["Sales"].clip(lower=0)
    df["Ready Stock"] = df["Ready Stock"].clip(lower=0)
    df["RT"] = df["RT"].clip(lower=0)

    return df


def load_cost_matrix(file_path):

    cost_matrix = pd.read_excel(file_path, index_col=0)

    cost_matrix.index = cost_matrix.index.astype(int)
    cost_matrix.columns = cost_matrix.columns.astype(int)

    return cost_matrix

def build_adjusted_cost_matrix(
    base_matrix,
    mother_hubs=[4108, 4301],
    multiplier=1.2
):

    adjusted = base_matrix.astype(float).copy()

    hubs = adjusted.index.tolist()

    for source in hubs:

        for dest in hubs:

            # Skip same hub
            if source == dest:
                adjusted.loc[source, dest] = 0
                continue

            # Mother hub direct movement
            if source in mother_hubs:

                adjusted.loc[source, dest] = (
                    base_matrix.loc[source, dest]
                )

                continue

            # Historical inbound cost
            inbound_cost = min(
                base_matrix.loc[mh, source]
                for mh in mother_hubs
            )

            # Current transfer cost
            transfer_cost = (
                multiplier *
                base_matrix.loc[source, dest]
            )

            adjusted.loc[source, dest] = (
                inbound_cost + transfer_cost
            )

    return adjusted

def load_production_plan(production_plan_path):
    # If file does not exist, create a new file in the same format
    # Check the data types etc for sanity, because is entered manually
    return pd.read_excel(production_plan_path)


def calculate_inventory_days(df):

    df = df.copy()

    df["daily_demand"] = df["RF"] / 30

    df["inv_days"] = np.where(
        df["RF"] > 0,
        (df["RT"] / df["RF"]) * 30,
        999999
    )

    return df


def apply_water_filling(df, target_days=21):

    df = df.copy()

    df["water_fill_inv_days"] = df["inv_days"]

    # Excess inventory pool in UNITS
    total_excess_units = 0

    for idx, row in df.iterrows():

        if row["RF"] <= 0:
            continue

        excess_days = max(row["inv_days"] - target_days, 0)

        excess_units = excess_days * row["daily_demand"]

        total_excess_units += excess_units

    # Deficit hubs only
    deficit_df = df[
        (df["RF"] > 0) &
        (df["inv_days"] < target_days)
    ].copy()

    if deficit_df.empty or total_excess_units <= 0:
        return df

    deficit_df = deficit_df.sort_values(
        by="inv_days"
    ).reset_index()

    levels = deficit_df["inv_days"].tolist()
    demands = deficit_df["daily_demand"].tolist()

    n = len(deficit_df)

    remaining_units = total_excess_units

    i = 0
    while i < n:
        current_level = levels[i]
        
        if i == n - 1:
            next_level = target_days
        else:
            next_level = min(levels[i + 1], target_days)

        if current_level >= target_days:
            break

        active_indices = list(range(i + 1))

        total_daily_demand = sum(
            demands[j] for j in active_indices
        )

        level_gap = next_level - current_level

        required_units = (
            total_daily_demand * level_gap
        )

        if remaining_units >= required_units:

            for j in active_indices:
                levels[j] = next_level

            remaining_units -= required_units

            i += 1

        else:

            possible_increase = (
                remaining_units / total_daily_demand
            )

            for j in active_indices:
                levels[j] += possible_increase

            remaining_units = 0
            break
    
    # Write back final levels
    for idx2, row in deficit_df.iterrows():

        original_index = row["index"]

        df.loc[
            original_index,
            "water_fill_inv_days"
        ] = levels[idx2]

    return df


def generate_supply_demand(df):

    df = df.copy()

    # ==========================================
    # REQUIRED QTY FOR DEFICIT HUBS
    # ==========================================

    df["required_qty"] = np.where(
        df["water_fill_inv_days"] > df["inv_days"],
        (df["water_fill_inv_days"] - df["inv_days"])*df["daily_demand"],
        0
    )

    # ==========================================
    # SUPPLY
    # ==========================================

    df["target_inventory"] = np.where(
        df["RF"] > 0,
        21*df["RF"]/30,
        0
    )

    df["excess_qty"] = np.where(
        df["RF"] == 0,
        df["RT"],
        np.maximum(df["RT"]-df["target_inventory"],0)
    )

    supply = (
        df[df["excess_qty"] > 0]
        .groupby("Hub")["excess_qty"]
        .sum()
        .round(2)
        .to_dict()
    )

    df.drop(columns=["target_inventory", "excess_qty"], inplace=True)

    # ==========================================
    # DEMAND
    # ==========================================

    demand = (
        df[df["required_qty"] > 0]
        .groupby("Hub")["required_qty"]
        .sum()
        .round(2)
        .to_dict()
    )

    df.drop(columns=["water_fill_inv_days", "required_qty"], inplace=True)

    return supply, demand, df


def add_post_shipment_inventory(
    df_product,
    shipment_df
):

    df = df_product.copy()

    if shipment_df.empty:
        df["post_ship_RT"] = df["RT"]
        df["post_ship_inv_days"] = df["inv_days"]
        return df

    outward = (
        shipment_df.groupby("From")["Quantity"]
        .sum()
        .to_dict()
    )

    inward = (
        shipment_df.groupby("To")["Quantity"]
        .sum()
        .to_dict()
    )

    df["outward"] = df["Hub"].map(outward).fillna(0)
    df["inward"] = df["Hub"].map(inward).fillna(0)

    df["post_ship_RT"] = (
        df["RT"]
        +
        df["inward"]
        -
        df["outward"]
    )

    df["post_ship_inv_days"] = np.where(
        df["RF"] > 0,
        df["post_ship_RT"]/df["RF"] * 30,
        np.nan
    )

    df.drop(columns=["outward", "inward", "daily_demand"], inplace=True)

    return df


def plot_inventory_comparison(product_name, df, plot_dir):

    plot_dir.mkdir(exist_ok=True)

    # ✅ Filter valid hubs (avoid RF=0 issues)
    df = df[df["daily_demand"] > 0].copy()
    
    # ✅ HANDLE EMPTY DATA (critical fix)
    if df.empty:
        print(f"Skipping plot for {product_name}: no valid data")
        return


    # ✅ Sort by original inventory (descending)
    df = df.sort_values("inv_days", ascending=False).reset_index(drop=True)

    # ✅ Prepare values (no temp columns in df)
    cap = 100  # optional cap for extreme values
    original_vals = df["inv_days"]
    post_vals = df["post_ship_inv_days"]

    x = np.arange(len(df))
    width = 0.35

    fig, ax = plt.subplots(figsize=(14, 6))

    # ✅ Bars
    ax.bar(x - width/2, original_vals, width, label="Before")
    ax.bar(x + width/2, post_vals, width, label="After")

    # ✅ Target line
    ax.axhline(y=21, linestyle="--", color="black", label=f"Target (21 days)")

    # ✅ ✅ Dynamic Y-axis scaling
    max_y = max(original_vals.max(), post_vals.max())

    # Decide step dynamically
    if max_y <= 30:
        step = 5
    elif max_y <= 100:
        step = 10
    elif max_y <= 300:
        step = 25
    else:
        step = round(max_y / 10, -1)

    # Round max nicely
    max_y_rounded = math.ceil(max_y / step) * step

    ax.set_ylim(0, max_y_rounded)
    ax.set_yticks(np.arange(0, max_y_rounded + step, step))

    # ✅ Grid (clean)
    ax.grid(axis='y', linestyle='--', alpha=0.3)

    # ✅ X-axis
    ax.set_xticks(x)
    ax.set_xticklabels(df["Hub"], rotation=45)

    # ✅ Labels & title
    ax.set_ylabel("Inventory Days")
    ax.set_title(f"{product_name} Inventory Rebalancing")

    ax.legend()

    plt.tight_layout()
    plt.savefig(plot_dir / f"{product_name}.png")
    plt.close()


def save_product_results(
    product_name,
    inventory_df,
    shipment_df,
    total_cost,
    output_dir
):

    shipment_path = (
        output_dir /
        "shipments" /
        f"{product_name}_shipments.xlsx"
    )

    with pd.ExcelWriter(shipment_path) as writer:

        inventory_df.to_excel(
            writer,
            sheet_name="Inventory",
            index=False
        )

        shipment_df.to_excel(
            writer,
            sheet_name="Shipments",
            index=False
        )

        pd.DataFrame([{
            "Total Cost": total_cost
        }]).to_excel(
            writer,
            sheet_name="Summary",
            index=False
        )


def create_route_summary_df(
    shipment_df
):

    if shipment_df.empty:

        return pd.DataFrame(
            columns=[
                "Route",
                "From",
                "To",
                "Category",
                "Total Quantity"
            ]
        )

    df = shipment_df.copy()

    df["Route"] = (
        df["From"].astype(str)
        +
        "_"
        +
        df["To"].astype(str)
    )

    route_summary_df = (
        df.groupby(
            [
                "Route",
                "From",
                "To",
                "Category"
            ],
            as_index=False
        )["Quantity"]
        .sum()
    )

    route_summary_df.rename(
        columns={
            "Quantity":
                "Total Quantity"
        },
        inplace=True
    )

    return route_summary_df

import pandas as pd

def generate_inventory_summary(all_inventory, product_category_df):

    # combine all product-level dfs
    inventory_summary_df = pd.concat(
        all_inventory,
        ignore_index=True
    )

    # add category
    inventory_summary_df = inventory_summary_df.merge(
        product_category_df[["Product", "Category"]],
        on="Product",
        how="left"
    )

    # select required columns
    inventory_summary_df = inventory_summary_df[
        [
            "Hub",
            "Product",
            "Category",
            "RF",
            "Sales",
            "RT",
            "inv_days",
            "post_ship_RT",
            "post_ship_inv_days"
        ]
    ].copy()

    # rename columns
    inventory_summary_df.rename(
        columns={
            "RT": "Current Inv",
            "post_ship_RT": "Post Ship Inv",
            "inv_days": "Current Inv Days",
            "post_ship_inv_days": "Post Ship Inv Days"
        },
        inplace=True
    )

    return inventory_summary_df

def generate_shipment_summary(all_shipments, product_category_df):

    # combine shipments
    if all_shipments:
        shipment_summary_df = pd.concat(
            all_shipments,
            ignore_index=True
        )
    else:
        shipment_summary_df = pd.DataFrame(
            columns=[
                "From",
                "To",
                "Quantity",
                "Product"
            ]
        )

    # add category
    shipment_summary_df = shipment_summary_df.merge(
        product_category_df[["Product", "Category"]],
        on="Product",
        how="left"
    )

    return shipment_summary_df

def generate_route_analysis(shipment_summary_df):

    if shipment_summary_df.empty:

        return pd.DataFrame(
            columns=[
                "Source",
                "Destination",
                "Total Qty",
                "Products"
            ]
        )

    route_df = (
        shipment_summary_df
        .groupby(
            ["From", "To"]
        )
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

    route_df.rename(
        columns={
            "From": "Source",
            "To": "Destination",
            "Quantity": "Total Qty",
            "Product": "Products"
        },
        inplace=True
    )

    route_df = route_df.sort_values(
        by="Total Qty",
        ascending=False
    )

    return route_df

def merge_production_into_inventory(inventory_df, production_df):
    
    # =====================================
    # CLEAN TYPES
    # =====================================

    inventory_df["Hub"] = inventory_df["Hub"].astype(int)
    inventory_df["Product"] = inventory_df["Product"].astype(int)

    production_df["Hub"] = production_df["Hub"].astype(int)
    production_df["Product"] = production_df["Product"].astype(int)

    production_df["Production Qty"] = pd.to_numeric(
        production_df["Production Qty"],
        errors="coerce"
    ).fillna(0)

    # =====================================
    # AGGREGATE PRODUCTION
    # =====================================

    production_summary = (
        production_df
        .groupby(
            ["Hub", "Product"],
            as_index=False
        )["Production Qty"]
        .sum()
    )

    # =====================================
    # MERGE
    # =====================================

    merged_df = inventory_df.merge(
        production_summary,
        on=["Hub", "Product"],
        how="left"
    )

    merged_df["Production Qty"] = (
        merged_df["Production Qty"]
        .fillna(0)
    )

    # =====================================
    # ADD INTO RT
    # =====================================

    merged_df["RT"] = (
        merged_df["RT"]
        +
        merged_df["Production Qty"]
    )

    merged_df.drop(columns = ["Production Qty"], inplace = True)

    return merged_df
