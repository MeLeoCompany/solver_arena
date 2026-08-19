import unittest
import qore_opt_py as qore
from pathlib import Path


class TestQoreMilpSolver(unittest.TestCase):
    """Test cases for the Qore MILP solver via pybind11 bindings."""

    @classmethod
    def setUpClass(cls) -> None:
        """Create test MPS file with known binary MILP problem."""
        test_data_dir = Path("test_data")
        test_data_dir.mkdir(exist_ok=True)

        mps_path = test_data_dir / "binary_milp_test_1.mps"

        # MPS content: same problem as test_small_binary_milp
        # Minimize: -86*x0 - 4*x1 - 40*x2
        # s.t.: 774*x0 + 76*x1 + 42*x2 <= 875
        #       67*x0 + 27*x1 + 53*x2 <= 875
        #       x0, x1, x2 ∈ {0, 1}
        mps_content = """NAME  TEST_BINARY_MILP_1
ROWS
 N  COST
 L  LIM1
 L  LIM2
COLUMNS
 X1 	COST   	-86
 X1     LIM1    774
 X1     LIM2    67
 X2     COST    -4
 X2     LIM1    76
 X2     LIM2    27
 X3     COST    -40
 X3     LIM1    42
 X3     LIM2    53
RHS
 RHS1   LIM1    875
 RHS1   LIM2    875
RANGES
BOUNDS
 BV  BND1  X1  1
 BV  BND1  X2  1
 BV  BND1  X3  1
ENDATA
"""
        with open(mps_path, "w", encoding="ascii") as f:
            f.write(mps_content)

        cls.MPS_TEST_FILE = str(mps_path)

    @classmethod
    def tearDownClass(cls) -> None:
        """Optional: clean up test files after all tests."""
        pass

    # -------------------------------------------------------------------------
    # Тест 1: Программное построение модели (ручная сборка)
    # -------------------------------------------------------------------------
    def test_solve_manual_assembly_model(self) -> None:
        """
        Test a small binary MILP problem built programmatically:

        Minimize:   -86*x0 - 4*x1 - 40*x2
        Subject to: 774*x0 + 76*x1 + 42*x2 <= 875
                    67*x0 + 27*x1 + 53*x2 <= 875
                    x0, x1, x2 ∈ {0, 1}

        Expected optimal solution: x = [1, 0, 1], objective = -126
        """
        try:
            opt = qore.QoreOpt()
        except RuntimeError as e:
            self.fail(f"Failed to create QoreOpt (license error?): {e}")

        config_json = """{
            "logs_config": {
                "log_file_level": "info",
                "log_console_level": "info",
                "simplex_log": false,
                "ph_log_level": "off",
                "max_time_between_log": 0
            }
        }"""
        opt.set_configuration(config_json)
        opt.set_up_logger("")

        model = qore.QoreModel()

        n_vars = 3
        n_ineq = 2
        f = [-86.0, -4.0, -40.0]
        lb = [0.0, 0.0, 0.0]
        ub = [1.0, 1.0, 1.0]

        var_indices = []
        for i in range(n_vars):
            idx = model.add_variable(
                type=qore.VariableType.BOOLEAN,
                lower_bound=lb[i],
                upper_bound=ub[i]
            )
            var_indices.append(idx)
            model.set_objective_coeff(idx, f[i])

        Aineq = [
            [774.0, 76.0, 42.0],
            [67.0, 27.0, 53.0],
        ]
        bineq = [875.0, 875.0]

        for j in range(n_ineq):
            constr_idx = model.add_constraint(
                type=qore.ConstraintType.LESS_EQ,
                rhs=bineq[j]
            )
            for i in range(n_vars):
                if Aineq[j][i] != 0.0:
                    model.set_constraint_coeff(constr_idx, var_indices[i], Aineq[j][i])

        opt.set_model(model)
        status = opt.optimize()

        self.assertEqual(status, qore.OptimizationStatus.OPTIMAL, f"Expected OPTIMAL status, got {status}")

        solution = opt.get_solution()
        x = solution.variables_values

        self.assertEqual(len(x), n_vars, f"Expected {n_vars} variables, got {len(x)}")
        self.assertAlmostEqual(x[0], 1.0, places=6, msg=f"x[0] = {x[0]}, expected 1.0")
        self.assertAlmostEqual(x[1], 0.0, places=6, msg=f"x[1] = {x[1]}, expected 0.0")
        self.assertAlmostEqual(x[2], 1.0, places=6, msg=f"x[2] = {x[2]}, expected 1.0")

        expected_objective = -126.0
        self.assertAlmostEqual(
            solution.objective,
            expected_objective,
            places=6,
            msg=f"objective = {solution.objective}, expected {expected_objective}"
        )

        self.assertGreaterEqual(solution.gap, 0.0, "MIP gap should be non-negative")
        self.assertGreaterEqual(solution.time, 0.0, "Solve time should be non-negative")

        print(f"\n=== Test solve manual assembly model results  ===")
        print(f"Status: {status}")
        print(f"Solution x: {x}")
        print(f"Objective: {solution.objective:.6f} (expected: {expected_objective})")
        print(f"MIP Gap: {solution.gap:.6f}%")
        print(f"Solve Time: {solution.time:.4f} seconds")
        print(f"Processed Nodes: {solution.processed_nodes}")
        print(f"Simplex Iterations: {solution.total_simplex_iterations}")
        print(f"Is LP: {solution.is_lp}")

    # -------------------------------------------------------------------------
    # Тест 2: Чтение модели из MPS-файла
    # -------------------------------------------------------------------------
    def test_solve_model_from_mps_file(self) -> None:
        """
        Test reading and solving MILP from MPS file.

        File: test_data/binary_milp_test_1.mps
        Problem: Minimize -86*x0 -4*x1 -40*x2
                 s.t. 774*x0 + 76*x1 + 42*x2 <= 875
                      67*x0 + 27*x1 + 53*x2 <= 875
                      x0, x1, x2 ∈ {0, 1}

        Expected: x = [1, 0, 1], objective = -126 (same as test_small_binary_milp)
        """
        import os

        mps_path = self.MPS_TEST_FILE

        self.assertTrue(
            os.path.exists(mps_path),
            f"MPS file not found: {os.path.abspath(mps_path)}"
        )

        try:
            opt = qore.QoreOpt()
        except RuntimeError as e:
            self.fail(f"Failed to create QoreOpt (license error?): {e}")

        config_json = """{
              "logs_config": {
                  "log_file_level": "info",
                  "log_console_level": "info",
                  "simplex_log": false,
                  "ph_log_level": "off",
                  "max_time_between_log": 0
              }
          }"""
        opt.set_configuration(config_json)
        opt.set_up_logger("")

        model = qore.QoreModel()
        load_success = model.read_model_from_file(mps_path)

        self.assertTrue(load_success, f"Failed to read model from MPS file: {mps_path}")

        # Валидация структуры модели
        self.assertEqual(model.variables_count, 3, "Expected 3 variables in MPS model")
        self.assertEqual(model.constraints_count, 2, "Expected 2 constraints in MPS model")

        opt.set_model(model)
        status = opt.optimize()

        self.assertEqual(status, qore.OptimizationStatus.OPTIMAL, f"Expected OPTIMAL status, got {status}")

        solution = opt.get_solution()
        x = solution.variables_values

        self.assertEqual(len(x), 3, f"Expected 3 variable values, got {len(x)}")

        # Ожидаемое решение: X1=1, X2=0, X3=1 → индексы [0, 1, 2]
        self.assertAlmostEqual(
            x[0], 1.0, places=6,
            msg=f"x[0] (X1) = {x[0]}, expected 1.0"
        )
        self.assertAlmostEqual(
            x[1], 0.0, places=6,
            msg=f"x[1] (X2) = {x[1]}, expected 0.0"
        )
        self.assertAlmostEqual(
            x[2], 1.0, places=6,
            msg=f"x[2] (X3) = {x[2]}, expected 1.0"
        )

        expected_objective = -126.0
        self.assertAlmostEqual(
            solution.objective,
            expected_objective,
            places=6,
            msg=f"objective = {solution.objective}, expected {expected_objective}"
        )

        self.assertGreaterEqual(solution.gap, 0.0, "MIP gap should be non-negative")
        self.assertGreaterEqual(solution.time, 0.0, "Solve time should be non-negative")
        self.assertFalse(solution.is_lp, "This is a MILP, not a pure LP")

        print(f"\n=== Test solve model from mps results ===")
        print(f"File: {mps_path}")
        print(f"Status: {status}")
        print(f"Solution [X1, X2, X3]: {x}")
        print(f"Objective: {solution.objective:.6f} (expected: {expected_objective})")
        print(f"MIP Gap: {solution.gap:.6f}%")
        print(f"Solve Time: {solution.time:.4f}s")
        print(f"Processed Nodes: {solution.processed_nodes}")

    # -------------------------------------------------------------------------
    # Тест 3: Установка полной модели через set_full_model() (COO-формат)
    # -------------------------------------------------------------------------
    def test_solve_model_via_set_full_model(self) -> None:
        """
        Test solving the same binary MILP using set_full_model().

        Problem: Minimize -86*x0 - 4*x1 - 40*x2
                 s.t. 774*x0 + 76*x1 + 42*x2 <= 875
                      67*x0 + 27*x1 + 53*x2 <= 875
                      x0, x1, x2 ∈ {0, 1}

        Expected: x = [1, 0, 1], objective = -126
        """
        try:
            opt = qore.QoreOpt()
        except RuntimeError as e:
            self.fail(f"Failed to create QoreOpt (license error?): {e}")

        opt.set_configuration('{"logs_config": {"log_console_level": "info", "log_file_level": "off"}}')
        opt.set_up_logger("")

        model = qore.QoreModel()

        n = 3  # variables
        m = 2  # total constraints (2 inequalities)

        # Objective coefficients
        f = [-86.0, -4.0, -40.0]

        # Indices of integer/binary variables (0-based)
        intcon = [0, 1, 2]

        # Inequality matrix in COO format: (row, col, value)
        Aineq = [
            qore.MatrixTriplet(0, 0, 774.0), qore.MatrixTriplet(0, 1, 76.0), qore.MatrixTriplet(0, 2, 42.0),
            qore.MatrixTriplet(1, 0, 67.0), qore.MatrixTriplet(1, 1, 27.0), qore.MatrixTriplet(1, 2, 53.0)
        ]
        bineq = [875.0, 875.0]

        # Equality constraints (empty for this problem)
        Aeq = []
        beq = []

        # Variable bounds
        lb = [0.0, 0.0, 0.0]
        ub = [1.0, 1.0, 1.0]

        # 📦 Fill model in one call
        model.set_full_model(
            m=m, n=n,
            f=f, intcon=intcon,
            Aeq=Aeq, beq=beq,
            Aineq=Aineq, bineq=bineq,
            lb=lb, ub=ub
        )

        # Validate structure
        self.assertEqual(model.variables_count, n, f"Expected {n} variables")
        self.assertEqual(model.constraints_count, m, f"Expected {m} constraints")

        # Run optimization
        opt.set_model(model)
        status = opt.optimize()

        self.assertEqual(status, qore.OptimizationStatus.OPTIMAL, f"Expected OPTIMAL status, got {status}")

        solution = opt.get_solution()
        x = solution.variables_values

        self.assertEqual(len(x), n, f"Expected {n} variable values, got {len(x)}")
        self.assertAlmostEqual(x[0], 1.0, places=6, msg=f"x[0] = {x[0]}, expected 1.0")
        self.assertAlmostEqual(x[1], 0.0, places=6, msg=f"x[1] = {x[1]}, expected 0.0")
        self.assertAlmostEqual(x[2], 1.0, places=6, msg=f"x[2] = {x[2]}, expected 1.0")

        expected_objective = -126.0
        self.assertAlmostEqual(
            solution.objective,
            expected_objective,
            places=6,
            msg=f"objective = {solution.objective}, expected {expected_objective}"
        )

        self.assertGreaterEqual(solution.gap, 0.0, "MIP gap should be non-negative")
        self.assertGreaterEqual(solution.time, 0.0, "Solve time should be non-negative")
        self.assertFalse(solution.is_lp, "This is a MILP, not a pure LP")

        print(f"\n=== Test solve via set_full_model results ===")
        print(f"Status: {status}")
        print(f"Solution x: {x}")
        print(f"Objective: {solution.objective:.6f} (expected: {expected_objective})")
        print(f"MIP Gap: {solution.gap:.6f}%")
        print(f"Solve Time: {solution.time:.4f}s")


# -------------------------------------------------------------------------
# Вспомогательные функции запуска
# -------------------------------------------------------------------------
def run_tests() -> bool:
    """Run all tests and return True if all passed."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestQoreMilpSolver)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


def main() -> int:
    """Main entry point for script execution."""
    print("Starting Qore MILP solver tests (pybind11 API: qore_opt_py)...")
    module_path = qore.__file__ if hasattr(qore, "__file__") else "built-in"
    print(f"Module location: {module_path}")

    success = run_tests()

    if success:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    exit(main())