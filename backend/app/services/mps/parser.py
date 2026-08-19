"""Minimal free-format MPS reader.

ALGLIB's minlp module (unlike cuOpt/CPLEX) has no native MPS reader — it
only takes a cost vector, box constraints, and a linear constraint matrix.
This fills that gap: enough of the MPS spec to build those from a standard
file (ROWS/COLUMNS/RHS/RANGES/BOUNDS, OBJSENSE, integer MARKER blocks,
QMATRIX for QP). Not a full MPS implementation — free rows beyond the
first N row and exotic bound types are not handled.

QMATRIX (CPLEX's convention, also what cuOpt and QORE expect when fed
directly): each line is `col1 col2 value`, the FULL symmetric matrix (both
(i, j) and (j, i) given explicitly, verified empirically against a real
vendored QP file), and the quadratic term contributes 0.5 * x^T Q x to the
objective.
"""

from dataclasses import dataclass, field

import numpy as np

INF = float("inf")

_KNOWN_SECTIONS = ("NAME", "ROWS", "COLUMNS", "RHS", "RANGES", "BOUNDS", "QMATRIX", "ENDATA", "OBJSENSE")


@dataclass
class MpsProblem:
    """Numeric fields are numpy arrays, built once here rather than as plain
    Python lists — problems in this app can have hundreds of thousands of
    variables/nonzeros (e.g. ~338k vars in one real run), so every consumer
    doing vector math on this (ALGLIB's execute.py, the comparison services)
    would otherwise have to pay for its own list-to-array conversion.

    Both the constraint matrix and the quadratic objective (Hessian) are COO
    triplets, not dense arrays — a dense (rows x vars) or (vars x vars)
    array would be far too large to allocate at this scale.
    """

    minimize: bool
    var_names: list[str]
    var_lb: np.ndarray
    var_ub: np.ndarray
    integer_vars: list[int]
    obj: np.ndarray
    row_names: list[str]
    row_lo: np.ndarray
    row_hi: np.ndarray
    constraint_rows: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=int))
    constraint_cols: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=int))
    constraint_values: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=float))
    quad_rows: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=int))
    quad_cols: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=int))
    quad_values: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=float))

    @property
    def var_count(self) -> int:
        return len(self.var_names)

    @property
    def row_count(self) -> int:
        return len(self.row_names)

    @property
    def is_qp(self) -> bool:
        return len(self.quad_rows) > 0

    def compute_lhs(self, x: np.ndarray) -> np.ndarray:
        """Ax for the given variable vector x, one entry per constraint row."""
        lhs = np.zeros(self.row_count)
        if self.row_count and len(self.constraint_rows):
            np.add.at(lhs, self.constraint_rows, self.constraint_values * x[self.constraint_cols])
        return lhs

    def compute_quadratic_term(self, x: np.ndarray) -> float:
        """0.5 * x^T Q x, from the full-symmetric QMATRIX triplets."""
        if not len(self.quad_rows):
            return 0.0
        return 0.5 * float(np.sum(self.quad_values * x[self.quad_rows] * x[self.quad_cols]))


def parse_mps(text: str) -> MpsProblem:
    var_index: dict[str, int] = {}
    var_names: list[str] = []
    var_lb: list[float] = []
    var_ub: list[float] = []
    integer_vars: list[int] = []

    row_index: dict[str, int] = {}
    row_names: list[str] = []
    row_senses: list[str] = []
    row_rhs: list[float] = []
    row_range: list[float | None] = []
    obj_row: str | None = None
    obj: dict[int, float] = {}
    coeffs: list[tuple[int, int, float]] = []
    quad_coeffs: list[tuple[int, int, float]] = []

    minimize = True
    section = None
    in_integer_block = False

    def get_var(name: str) -> int:
        if name not in var_index:
            var_index[name] = len(var_names)
            var_names.append(name)
            var_lb.append(0.0)
            var_ub.append(INF)
        return var_index[name]

    for raw_line in text.splitlines():
        line = raw_line.rstrip("\n")
        if not line.strip() or line.startswith("*"):
            continue
        if not line[0].isspace():
            keyword = line.split()[0].upper()
            # Any other all-caps section header (e.g. a vendor extension we
            # don't parse) is skipped rather than left to fall through to
            # whatever section was active before — that used to misread the
            # next section's data lines as belonging to the previous one,
            # crashing with an IndexError on real QMATRIX-bearing files.
            section = keyword if keyword in _KNOWN_SECTIONS else None
            if section == "OBJSENSE":
                rest = line.split(None, 1)
                if len(rest) > 1 and "MAX" in rest[1].upper():
                    minimize = False
            continue

        tokens = line.split()
        if not tokens:
            continue

        if section == "OBJSENSE":
            if tokens[0].upper() in ("MAX", "MAXIMIZE"):
                minimize = False
            elif tokens[0].upper() in ("MIN", "MINIMIZE"):
                minimize = True
            continue

        if section == "ROWS":
            sense, name = tokens[0].upper(), tokens[1]
            if sense == "N":
                if obj_row is None:
                    obj_row = name
                continue  # extra free rows are dropped
            row_index[name] = len(row_names)
            row_names.append(name)
            row_senses.append(sense)
            row_rhs.append(0.0)
            row_range.append(None)
            continue

        if section == "COLUMNS":
            if len(tokens) >= 3 and tokens[1] == "'MARKER'":
                in_integer_block = "INTORG" in tokens[2].upper()
                continue
            col = get_var(tokens[0])
            if in_integer_block and col not in integer_vars:
                integer_vars.append(col)
                if var_ub[col] == INF:  # MPS convention: integer default bound is [0,1] unless overridden later
                    var_ub[col] = 1.0
            pairs = tokens[1:]
            for i in range(0, len(pairs) - 1, 2):
                row_name, value = pairs[i], float(pairs[i + 1])
                if row_name == obj_row:
                    obj[col] = obj.get(col, 0.0) + value
                elif row_name in row_index:
                    coeffs.append((row_index[row_name], col, value))
            continue

        if section == "RHS":
            pairs = tokens[1:]
            for i in range(0, len(pairs) - 1, 2):
                row_name, value = pairs[i], float(pairs[i + 1])
                if row_name in row_index:
                    row_rhs[row_index[row_name]] = value
            continue

        if section == "RANGES":
            pairs = tokens[1:]
            for i in range(0, len(pairs) - 1, 2):
                row_name, value = pairs[i], float(pairs[i + 1])
                if row_name in row_index:
                    row_range[row_index[row_name]] = value
            continue

        if section == "BOUNDS":
            bnd_type = tokens[0].upper()
            col = get_var(tokens[2])
            value = float(tokens[3]) if len(tokens) > 3 else None
            if bnd_type == "UP":
                var_ub[col] = value
            elif bnd_type == "LO":
                var_lb[col] = value
            elif bnd_type == "FX":
                var_lb[col] = value
                var_ub[col] = value
            elif bnd_type == "FR":
                var_lb[col] = -INF
                var_ub[col] = INF
            elif bnd_type == "MI":
                var_lb[col] = -INF
            elif bnd_type == "PL":
                var_ub[col] = INF
            elif bnd_type == "BV":
                var_lb[col] = 0.0
                var_ub[col] = 1.0
                if col not in integer_vars:
                    integer_vars.append(col)
            elif bnd_type == "LI":
                var_lb[col] = value
                if col not in integer_vars:
                    integer_vars.append(col)
            elif bnd_type == "UI":
                var_ub[col] = value
                if col not in integer_vars:
                    integer_vars.append(col)
            continue

        if section == "QMATRIX":
            col1 = get_var(tokens[0])
            col2 = get_var(tokens[1])
            quad_coeffs.append((col1, col2, float(tokens[2])))
            continue

    row_lo: list[float] = []
    row_hi: list[float] = []
    for sense, rhs, rng in zip(row_senses, row_rhs, row_range):
        if sense == "E":
            if rng is None:
                lo, hi = rhs, rhs
            elif rng >= 0:
                lo, hi = rhs, rhs + rng
            else:
                lo, hi = rhs + rng, rhs
        elif sense == "L":
            lo, hi = (rhs - abs(rng), rhs) if rng is not None else (-INF, rhs)
        elif sense == "G":
            lo, hi = (rhs, rhs + abs(rng)) if rng is not None else (rhs, INF)
        else:
            raise ValueError(f"unknown row sense {sense!r}")
        row_lo.append(lo)
        row_hi.append(hi)

    obj_vec = [obj.get(i, 0.0) for i in range(len(var_names))]
    constraint_rows, constraint_cols, constraint_values = (
        zip(*coeffs) if coeffs else ((), (), ())
    )
    quad_rows, quad_cols, quad_values = zip(*quad_coeffs) if quad_coeffs else ((), (), ())

    return MpsProblem(
        minimize=minimize,
        var_names=var_names,
        var_lb=np.array(var_lb, dtype=float),
        var_ub=np.array(var_ub, dtype=float),
        integer_vars=integer_vars,
        obj=np.array(obj_vec, dtype=float),
        row_names=row_names,
        row_lo=np.array(row_lo, dtype=float),
        row_hi=np.array(row_hi, dtype=float),
        constraint_rows=np.array(constraint_rows, dtype=int),
        constraint_cols=np.array(constraint_cols, dtype=int),
        constraint_values=np.array(constraint_values, dtype=float),
        quad_rows=np.array(quad_rows, dtype=int),
        quad_cols=np.array(quad_cols, dtype=int),
        quad_values=np.array(quad_values, dtype=float),
    )
