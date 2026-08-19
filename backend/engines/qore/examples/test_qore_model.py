import sys
from typing import Tuple


def main() -> int:
    try:
        from qore_opt_py import QoreModel, VariableType, ConstraintType, ObjSense
    except ImportError as e:
        print(f"❌ Failed to import qore_opt_py: {e}")
        print("💡 Hint: ensure the module is built and in PYTHONPATH")
        return 1

    print("🔹 Creating model...")
    model = QoreModel()
    model.reserve_for_variables(10)
    model.reserve_for_constraints(10)

    x1 = model.add_variable(VariableType.CONTINUOUS, 0.0, 10.0, name="x1")
    x2 = model.add_variable(VariableType.INTEGER, 0.0, 5.0, name="x2")
    x3 = model.add_variable(VariableType.BOOLEAN, name="x3")

    x4 = model.add_variable(VariableType.SEMICONTINUOUS, 4.41, float('inf'))
    lb, ub = model.get_variable_bounds(x4)
    assert lb == 4.41 and ub == float('inf'), "Variable bound mismatch"

    assert model.get_variables_count() == 4, "Variable count mismatch"
    print(f"✓ Added {model.get_variables_count()} variables")

    model.set_objective_coeff(x1, 1.0)
    model.set_objective_coeff(x2, 2.0)
    model.set_objective_coeff(x3, 3.0)
    model.set_objective_offset(0.0)

    assert model.get_objective_coeff(x2) == 2.0, "Objective coeff mismatch"
    print("✓ Objective coefficients set")

    c1 = model.add_constraint(ConstraintType.LESS_EQ, rhs=20.0, name="c1")
    model.set_constraint_coeff(c1, x1, 2.0)
    model.set_constraint_coeff(c1, x2, 3.0)
    model.set_constraint_coeff(c1, x3, 1.0)

    assert model.get_constraints_count() == 1, "Constraint count mismatch"
    assert model.get_constraint_rhs(c1) == 20.0, "Constraint RHS mismatch"
    print(f"✓ Added constraint with 3 coefficients, RHS={model.get_constraint_rhs(c1)}")

    y1 = model.add_variable(VariableType.CONTINUOUS, 0.0, 100.0, name="y1")
    y2 = model.add_variable(VariableType.CONTINUOUS, 0.0, 100.0, name="y2")
    y3 = model.add_variable(VariableType.CONTINUOUS, 0.0, 100.0, name="y3")

    c2 = model.add_constraint(
        var_indices=[y1, y2, y3],
        coeffs=[1.5, -2.0, 0.5],
        type=ConstraintType.GREATER_EQ,
        rhs=10.0,
        name="c2"
    )

    assert model.get_constraints_count() == 2, "Constraint count after overload #2 mismatch"
    assert model.get_constraint_rhs(c2) == 10.0, "Constraint RHS mismatch for overload #2"
    assert model.get_constraint_coeff(c2, y1) == 1.5, "Coeff y1 mismatch"
    assert model.get_constraint_coeff(c2, y2) == -2.0, "Coeff y2 mismatch"
    assert model.get_constraint_coeff(c2, y3) == 0.5, "Coeff y3 mismatch"
    print(f"✓ Constraint added with inline coefficients, RHS={model.get_constraint_rhs(c2)}")

    indicator_var = model.add_variable(VariableType.BOOLEAN, 0.0, 1.0, name="ind")
    constrained_var = model.add_variable(VariableType.CONTINUOUS, 0.0, 8.0, name="cons")
    ind_idx = model.add_indicator_constraint(indicator_var, constrained_var, name="ind_c")

    assert isinstance(ind_idx, int), "Indicator constraint should return integer index"
    print(f"✓ Indicator constraint added with index {ind_idx}")

    assert model.get_constraint_coeff(c2, x1) == 0.0, "Unexpected coeff for variable not in constraint"
    print("✓ Coefficients for variables not in constraint are correctly zero")

    bounds: Tuple[float, float] = model.get_variable_bounds(x1)
    assert bounds == (0.0, 10.0), f"Expected (0.0, 10.0), got {bounds}"
    print(f"✓ Variable x1 bounds: {bounds}")

    model.fix_variable(x3, 1.0)
    fixed = model.get_variable_bounds(x3)
    assert fixed[0] == fixed[1] == 1.0, f"Variable not fixed: got {fixed}"
    print("✓ Variable x3 fixed to 1.0")

    model.write_model_to_file("mps_model", ".mps")
    model.write_model_to_file("lp_model", ".lp")

    model.clear()
    assert model.get_variables_count() == 0, "Clear should reset variables"
    assert model.get_constraints_count() == 0, "Clear should reset constraints"
    print("✓ Model cleared successfully")

    model.add_variable(VariableType.CONTINUOUS, 0.0, 10.0)
    model.add_variable(VariableType.CONTINUOUS, 0.0, 10.0)
    model.set_objective([1.0, -2.0], sense=ObjSense.MAX)
    assert model.get_objective_coeff(0) == 1.0
    assert model.get_objective_coeff(1) == -2.0
    print("✓ SetObjective with ObjSense works")

    v_named = model.add_variable(name="only_name")
    assert model.get_variable_bounds(v_named) == (0.0, float('inf')), "Default bounds mismatch"

    c_named = model.add_constraint(ConstraintType.EQ, name="empty_constr")
    assert model.get_constraint_rhs(c_named) == 0.0, "Default RHS mismatch"
    print("✓ Optional name parameter works correctly")

    print("\n✅ All checks passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())