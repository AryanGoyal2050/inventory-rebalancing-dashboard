import pandas as pd
from pathlib import Path

from utils import *
from optimizer import solve_transportation_problem


def process_product(product_name, df_product, cost_matrix, output_dir, TARGET_INV_DAYS):

    print(f"Processing Product: {product_name}")

    df_product = calculate_inventory_days(df_product)
    # print(f"1\n{df_product.head(1)}")
    df_product = apply_water_filling(df_product, target_days=TARGET_INV_DAYS)
    # print(f"2\n{df_product.head(1)}")
    supply, demand, df_product = generate_supply_demand(df_product)
    # print(f"3\n{df_product.head(1)}")
    shipment_df, total_cost = solve_transportation_problem(supply, demand, cost_matrix)
    # print(f"4\n{df_product.head(1)}")
    df_product = add_post_shipment_inventory(df_product, shipment_df)
    # print(f"5\n{df_product.head(1)}")

    return {
        "product": product_name,
        "cost": total_cost,
        "inventory_df": df_product,
        "shipment_df": shipment_df
    }


def main():

    config = load_config()
    TARGET_INV_DAYS = config["target_days"]

    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)

    inventory_path = r"inputs/vp_sheet_27_05.xlsx"
    cost_matrix_path = r"inputs/cost_matrix.xlsx"
    product_master_path = r"inputs/product_list.xlsx"
    production_plan_path = r"inputs/production_plan.xlsx"

    inventory_df = load_inventory_data(inventory_path)
    cost_matrix = load_cost_matrix(cost_matrix_path)
    cost_matrix = build_adjusted_cost_matrix(cost_matrix)
    production_df = load_production_plan(production_plan_path)

    inventory_df = merge_production_into_inventory(inventory_df, production_df)

    inventory_hubs = set(inventory_df["Hub"].unique())
    matrix_hubs = set(cost_matrix.index)
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

        result = process_product(product_name, df_product, cost_matrix, output_dir, TARGET_INV_DAYS)

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
    # Optimization complete - now generate summaries

    product_category_df = pd.read_excel(
        product_master_path
    )

    inventory_summary_df = generate_inventory_summary(all_inventory, product_category_df)
    inventory_summary_df.to_excel(output_dir / "inventory_summary.xlsx", index=False)

    shipment_summary_df = generate_shipment_summary(all_shipments, product_category_df)
    shipment_summary_df.to_excel(output_dir / "shipment_summary.xlsx", index=False)

    route_analysis_df = generate_route_analysis(shipment_summary_df)
    route_analysis_df.to_excel(output_dir / "route_analysis.xlsx",index=False)

    print("\nALL PRODUCTS COMPLETED")


if __name__ == "__main__":
    main()
