import pandas as pd
from pathlib import Path

from utils import *
from optimizer import solve_transportation_problem

TARGET_DAYS = 21


def process_product(product_name, df_product, cost_matrix, output_dir):

    print(f"Processing Product: {product_name}")

    df_product = calculate_inventory_days(df_product)
    df_product = apply_water_filling(df_product, target_days=TARGET_DAYS)
    supply, demand, df_product = generate_supply_demand(df_product)
    shipment_df, total_cost = solve_transportation_problem(supply, demand, cost_matrix)
    df_product = add_post_shipment_inventory(df_product, shipment_df)

    # TODO: Shift output saving to a separate function to keep this cleaner
    # This function is only for product-level processing

    # save_product_results(
    #     product_name,
    #     df_product,
    #     shipment_df,
    #     total_cost,
    #     output_dir
    # )

    # plot_inventory_comparison(
    #     product_name,
    #     df_product,
    #     output_dir / "plots"
    # )

    return {
        "product": product_name,
        "cost": total_cost,
        "inventory_df": df_product,
        "shipment_df": shipment_df
    }


def main():

    output_dir = Path("outputs")

    output_dir.mkdir(exist_ok=True)
    # (output_dir / "plots").mkdir(exist_ok=True)
    # (output_dir / "shipments").mkdir(exist_ok=True)

    inventory_path = r"vp_sheet_21_05.xlsx"
    cost_matrix_path = r"cost_matrix.xlsx"
    product_master_path = r"product_list.xlsx"

    inventory_df = load_inventory_data(inventory_path)

    cost_matrix = load_cost_matrix(cost_matrix_path)

    cost_matrix = build_adjusted_cost_matrix(
        cost_matrix
    )

    inventory_hubs = set(
        inventory_df["Hub"].unique()
    )

    matrix_hubs = set(
        cost_matrix.index
    )

    missing_hubs = inventory_hubs - matrix_hubs
    if missing_hubs:
        raise ValueError(
            f"Missing hubs in cost matrix: {missing_hubs}"
        )

    product_data = {
        product: df.reset_index(drop=True)
        for product, df in inventory_df.groupby("Product")
    }

    all_shipments = []
    all_inventory = []

    for product_name, df_product in product_data.items():

        # if not product_name == 6151:
        #     continue

        result = process_product(product_name, df_product, cost_matrix, output_dir)

        # result = {
        #     "product": product_name,
        #     "cost": total_cost,
        #     "inventory_df": df_product,
        #     "shipment_df": shipment_df
        # }

        # print(f"product_name: \n{product_name}")
        # print(f"total_cost: \n{result['cost']}")
        # print(f"shipment_df: \n{result['shipment_df'].head()}")
        # print(f"inventory_df: \n{result['inventory_df'].head()}")
        # print(f"inventory_df columns: \n{result['inventory_df'].columns}")

        inventory_df_product = result["inventory_df"].copy()
        inventory_df_product["Product"] = product_name
        all_inventory.append(
            inventory_df_product
        )
        
        shipment_df = result["shipment_df"].copy()

        if not shipment_df.empty:
            shipment_df["Product"] = product_name
            shipment_df = shipment_df.drop(
                columns=["Unit Cost", "Total Cost"],
                errors="ignore"
            )

            all_shipments.append(
                shipment_df
            )


    product_category_df = pd.read_excel(
        product_master_path
    )

    # =====================================================
    # MASTER INVENTORY
    # =====================================================

    inventory_summary_df = pd.concat(
        all_inventory,
        ignore_index=True
    )

    inventory_summary_df = inventory_summary_df.merge(
        product_category_df[
            ["Product", "Category"]
        ],
        on="Product",
        how="left"
    )

    inventory_summary_df = (
        inventory_summary_df[
            [
                "Hub",
                "Product",
                "Category",
                "RF",
                "RT",
                "inv_days",
                "post_ship_RT",
                "post_ship_inv_days"
            ]
        ]
        .copy()
    )

    inventory_summary_df.rename(
        columns={
            "RT": "Current Inv",
            "post_ship_RT": "Post Ship Inv",
            "inv_days": "Current Inv Days",
            "post_ship_inv_days": "Post Ship Inv Days"
        },
        inplace=True
    )

    # print(f"Final inventory_summary_df: \n{inventory_summary_df.head()}")

    inventory_summary_df.to_excel(
        output_dir / "inventory_summary.xlsx",
        index=False
    )

    # =====================================================
    # MASTER SHIPMENTS
    # =====================================================

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

    shipment_summary_df = shipment_summary_df.merge(
        product_category_df[
            ["Product", "Category"]
        ],
        on="Product",
        how="left"
    )

    shipment_summary_df.to_excel(
        output_dir / "shipment_summary.xlsx",
        index=False
    )

    # print(f"Final shipment_summary_df: \n{shipment_summary_df.head()}")

    # =====================================================
    # CATEGORY SHEETS
    # =====================================================

    # frozen_df = master_shipment_df[
    #     master_shipment_df["Category"] == "Frozen"
    # ]

    # ambient_df = master_shipment_df[
    #     master_shipment_df["Category"] == "Ambient"
    # ]

    # chill_df = master_shipment_df[
    #     master_shipment_df["Category"] == "Chill"
    # ]

    # =====================================================
    # ROUTE SUMMARY
    # =====================================================

    # frozen_routes = create_route_summary_df(
    #     frozen_df
    # )

    # ambient_routes = create_route_summary_df(
    #     ambient_df
    # )

    # chill_routes = create_route_summary_df(
    #     chill_df
    # )

    # route_summary_df = pd.concat(
    #     [
    #         frozen_routes,
    #         ambient_routes,
    #         chill_routes
    #     ],
    #     ignore_index=True
    # )

    # route_summary_df.to_excel(
    #     output_dir / "route_summary.xlsx",
    #     index=False
    # )

    print("\nALL PRODUCTS COMPLETED")


if __name__ == "__main__":
    main()
