import unittest

import qore_opt_py as qore


class TestQoreQpSolver(unittest.TestCase):
    """Test cases for the Qore QP solver via pybind11 bindings."""

    def test_is_qp_is_milp_flags(self) -> None:
        """A model is MILP until a quadratic term is added, then it becomes QP."""
        model = qore.QoreModel()
        model.add_variable(qore.VariableType.CONTINUOUS, 0.0, 1.0)
        model.add_variable(qore.VariableType.CONTINUOUS, 0.0, 1.0)

        self.assertTrue(model.is_milp())
        self.assertFalse(model.is_qp())

        model.set_quadratic_objective_coeff(0, 0, 1.0)
        self.assertTrue(model.is_qp())
        self.assertFalse(model.is_milp())

        # Setting a coefficient to 0 removes it.
        model.set_quadratic_objective_coeff(0, 0, 0.0)
        self.assertTrue(model.is_milp())

        self.assertEqual(model.get_quadratic_objective_coeff(0, 0), 0.0)

    def test_set_quadratic_objective_bulk(self) -> None:
        """Bulk setter replaces the whole Hessian and reports coefficients back."""
        model = qore.QoreModel()
        model.add_variable(qore.VariableType.CONTINUOUS, 0.0, 1.0)
        model.add_variable(qore.VariableType.CONTINUOUS, 0.0, 1.0)

        model.set_quadratic_objective([
            qore.MatrixTriplet(0, 0, 2.0),
            qore.MatrixTriplet(1, 1, 3.0),
        ])
        self.assertTrue(model.is_qp())
        self.assertEqual(model.get_quadratic_objective_coeff(0, 0), 2.0)
        self.assertEqual(model.get_quadratic_objective_coeff(1, 1), 3.0)

    def test_solve_minimization_qp(self) -> None:
        """min 0.5*(x0^2 + x1^2) - x0 s.t. x0 + x1 = 1, 0 <= xi <= 1.

        KKT optimum: x0 = 1, x1 = 0, objective = -0.5.
        """
        model = qore.QoreModel()
        model.add_variable(qore.VariableType.CONTINUOUS, 0.0, 1.0)
        model.add_variable(qore.VariableType.CONTINUOUS, 0.0, 1.0)
        model.set_objective_coeff(0, -1.0)
        model.set_quadratic_objective_coeff(0, 0, 1.0)
        model.set_quadratic_objective_coeff(1, 1, 1.0)
        model.add_constraint([0, 1], [1.0, 1.0], qore.ConstraintType.EQ, 1.0)

        self.assertTrue(model.is_qp())

        opt = qore.QoreOpt()
        opt.set_model(model)
        status = opt.optimize()
        solution = opt.get_solution()

        self.assertEqual(status, qore.OptimizationStatus.OPTIMAL)
        self.assertAlmostEqual(solution.objective, -0.5, places=5)
        self.assertAlmostEqual(solution.variables_values[0], 1.0, places=5)
        self.assertAlmostEqual(solution.variables_values[1], 0.0, places=5)
        self.assertFalse(solution.is_lp)

    def test_solve_maximization_qp(self) -> None:
        """max -0.5*x0^2 + x0 s.t. 0 <= x0 <= 1 -> x0 = 1, objective = 0.5.

        Verifies the objective sign is corrected back for ObjSense.MAX.
        """
        model = qore.QoreModel()
        model.add_variable(qore.VariableType.CONTINUOUS, 0.0, 1.0)
        model.set_objective([1.0], qore.ObjSense.MAX)
        model.set_quadratic_objective_coeff(0, 0, -1.0)

        opt = qore.QoreOpt()
        opt.set_model(model)
        status = opt.optimize()
        solution = opt.get_solution()

        self.assertEqual(status, qore.OptimizationStatus.OPTIMAL)
        self.assertAlmostEqual(solution.objective, 0.5, places=5)
        self.assertAlmostEqual(solution.variables_values[0], 1.0, places=5)

    def test_miqp_not_supported(self) -> None:
        """A quadratic objective with discrete variables is rejected as unsupported."""
        model = qore.QoreModel()
        model.add_variable(qore.VariableType.INTEGER, 0.0, 5.0)
        model.add_variable(qore.VariableType.CONTINUOUS, 0.0, 5.0)
        model.set_quadratic_objective_coeff(0, 0, 1.0)

        self.assertTrue(model.is_qp())

        opt = qore.QoreOpt()
        opt.set_model(model)
        status = opt.optimize()

        self.assertEqual(status, qore.OptimizationStatus.NOT_STARTED)


if __name__ == "__main__":
    unittest.main()
