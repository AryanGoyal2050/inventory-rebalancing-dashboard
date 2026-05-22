import pandas as pd

from ortools.graph.python import min_cost_flow


def solve_transportation_problem(
    supply,
    demand,
    cost_matrix
):
    
    SCALE_FACTOR = 100

    supply = {
        k: int(round(v * SCALE_FACTOR))
        for k, v in supply.items()
    }

    demand = {
        k: int(round(v * SCALE_FACTOR))
        for k, v in demand.items()
    }


    total_supply = sum(supply.values())
    total_demand = sum(demand.values())

    excess_demand = total_demand - total_supply
    if excess_demand > 0:
        last_demand_key = list(demand.keys())[-1]
        demand[last_demand_key] -= excess_demand

    if not supply or not demand:

        return (
            pd.DataFrame(
                columns=[
                    "From",
                    "To",
                    "Quantity",
                    "Unit Cost",
                    "Total Cost"
                ]
            ),
            0
        )

    solver = min_cost_flow.SimpleMinCostFlow()

    all_hubs = set(supply.keys()) | set(demand.keys())

    hub_to_node = {
        hub: idx
        for idx, hub in enumerate(all_hubs)
    }

    dummy_node = len(hub_to_node)

    # ==========================================
    # TRANSPORT ARCS
    # ==========================================

    for source_hub, supply_qty in supply.items():

        for dest_hub in demand.keys():

            cost = int(round(
                cost_matrix.loc[
                    source_hub,
                    dest_hub
                ]
            ))

            solver.add_arc_with_capacity_and_unit_cost(
                hub_to_node[source_hub],
                hub_to_node[dest_hub],
                int(supply_qty),
                cost
            )

    # ==========================================
    # DUMMY NODE
    # ==========================================

    total_supply = sum(supply.values())

    total_demand = sum(demand.values())

    excess_inventory = max(
        total_supply - total_demand,
        0
    )

    if excess_inventory > 0:

        for source_hub, supply_qty in supply.items():

            solver.add_arc_with_capacity_and_unit_cost(
                hub_to_node[source_hub],
                dummy_node,
                int(supply_qty),
                0
            )

    # ==========================================
    # NODE SUPPLIES
    # ==========================================

    for hub, qty in supply.items():

        solver.set_node_supply(
            hub_to_node[hub],
            int(qty)
        )

    for hub, qty in demand.items():

        solver.set_node_supply(
            hub_to_node[hub],
            -int(qty)
        )

    if excess_inventory > 0:

        solver.set_node_supply(
            dummy_node,
            -int(excess_inventory)
        )

    # ==========================================
    # SOLVE
    # ==========================================

    status = solver.solve()

    if status != solver.OPTIMAL:

        raise Exception(
            "Optimization failed."
        )

    # ==========================================
    # RESULTS
    # ==========================================

    results = []

    node_to_hub = {
        node: hub
        for hub, node in hub_to_node.items()
    }

    for i in range(solver.num_arcs()):

        flow = solver.flow(i)

        if flow <= 0:
            continue

        tail = solver.tail(i)
        head = solver.head(i)

        if head == dummy_node:
            continue

        from_hub = node_to_hub[tail]

        to_hub = node_to_hub[head]

        unit_cost = solver.unit_cost(i)

        results.append({
            "From": from_hub,
            "To": to_hub,
            "Quantity": flow,
            "Unit Cost": unit_cost,
            "Total Cost": flow * unit_cost
        })

    shipment_df = pd.DataFrame(results)

    total_cost = shipment_df[
        "Total Cost"
    ].sum() if not shipment_df.empty else 0

    shipment_df["Quantity"] = shipment_df["Quantity"] / SCALE_FACTOR

    # print(f"printing shipment_df in optimizer.py: \n{shipment_df}")

    return shipment_df, total_cost
