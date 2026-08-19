#!/usr/bin/env python3
"""
Решение MPS-задачи (QP/LP) open-source солверами: PIQP (по умолчанию) или Clarabel.

PIQP - proximal interior-point (C++/Eigen, SIMD), спроектирован под плохо
обусловленные QP. Ключ к скорости на таких данных: preconditioner_scale_cost=True
(масштабирование цели; без него солвер топчется сотни итераций).

Установка:
    pip install piqp clarabel highspy scipy numpy

Запуск:
    python qp_solve.py problem.mps                 # PIQP, tol 1e-8
    python qp_solve.py problem.mps --fast          # PIQP, tol 1e-6 (быстрее)
    python qp_solve.py problem.mps --solver clarabel

highspy используется исключительно как парсер MPS-файла (чтение секций
COLUMNS/RHS/RANGES/BOUNDS/QUADOBJ) — решает задачу только Clarabel.

Установка:
    pip install clarabel highspy scipy numpy

Запуск:
    python clarabel_qp.py problem.mps                  # обычный режим, tol 1e-8
    python clarabel_qp.py problem.mps --robust         # профиль для плохо обусловленных задач
    python clarabel_qp.py problem.mps --robust --tol 1e-6
    python clarabel_qp.py problem.mps --quiet          # без итерационного лога

Профиль --robust включает (под симптомы: огромная цель ~1e9, разброс
коэффициентов на много порядков, застрявшая primal-невязка, шумный IR):
  * усиленное выравнивание данных (Ruiz equilibration: больше итераций,
    шире допустимый диапазон масштабов);
  * усиленное итеративное уточнение решений KKT-систем;
  * увеличенную статическую регуляризацию KKT-матрицы;
  * запасной критерий останова reduced_tol_* (вернёт решение чуть меньшей
    точности вместо бесконечного топтания, статус AlmostSolved).

Конвенция: Clarabel решает  min 1/2 x'Px + q'x,  Ax + s = b, s в конусах.
Hessian из HiGHS (как записан в QUADOBJ) передаётся как P напрямую —
обе стороны используют одинаковую 1/2-конвенцию (проверено на эталоне).
"""
import argparse
import time
import numpy as np
import scipy.sparse as sp

INF = 1e20


# ----------------------------------------------------------------------------
# Чтение MPS (highspy - только парсер, не решатель)
# ----------------------------------------------------------------------------
_QSECTIONS = ("QUADOBJ", "QMATRIX")


def _parse_quad_section_manually(path):
    """Fallback для старых highspy: вырезает QUADOBJ/QMATRIX из файла,
    возвращает (путь_к_temp_без_секции, список_записей (name_i, name_j, val))."""
    import tempfile, os
    with open(path, "r", encoding="latin-1", newline=None) as f:
        lines = f.read().splitlines()

    out, entries, in_q = [], [], False
    for ln in lines:
        head = ln.split("*")[0].rstrip()
        is_section = head and not head[0].isspace()
        if is_section:
            in_q = head.split()[0].upper() in _QSECTIONS
            if in_q:
                continue                    # заголовок Q-секции не переносим
        if in_q:
            tok = ln.split()
            if len(tok) >= 3:
                entries.append((tok[0], tok[1], float(tok[2])))
            continue
        out.append(ln)

    fd, tmp = tempfile.mkstemp(suffix=".mps"); os.close(fd)
    with open(tmp, "w", encoding="latin-1") as f:
        f.write("\n".join(out) + "\n")
    return tmp, entries


def _hessian_from_entries(entries, name_to_idx, n):
    """Собирает верхний треугольник P из записей Q-секции.
    Конвенция MPS (QUADOBJ и QMATRIX одинаково): цель = 0.5 x'Qx, значения
    как в файле; QMATRIX перечисляет обе треугольные части - берём одну."""
    vals = {}
    for ni, nj, v in entries:
        i, j = name_to_idx[ni], name_to_idx[nj]
        key = (i, j) if i <= j else (j, i)
        old = vals.get(key)
        if old is not None and abs(old - v) > 1e-10 * max(1.0, abs(v)):
            print(f">> Внимание: противоречивые значения Q для {ni},{nj}: "
                  f"{old} vs {v}; беру последнее")
        vals[key] = v
    if not vals:
        return sp.csc_matrix((n, n))
    rows = np.fromiter((k[0] for k in vals), dtype=np.int32, count=len(vals))
    cols = np.fromiter((k[1] for k in vals), dtype=np.int32, count=len(vals))
    data = np.fromiter(vals.values(), dtype=float, count=len(vals))
    return sp.csc_matrix((data, (rows, cols)), shape=(n, n))


def _extract(h):
    """Вытаскивает данные модели из объекта Highs."""
    model = h.getModel()
    lp = model.lp_
    hess = model.hessian_
    n, m = lp.num_col_, lp.num_row_

    if hess.dim_ and len(hess.value_) > 0:
        P = sp.csc_matrix(
            (np.array(hess.value_, dtype=float),
             np.array(hess.index_),
             np.array(hess.start_)),
            shape=(n, n))
    else:
        P = sp.csc_matrix((n, n))

    A_lp = sp.csc_matrix(
        (np.array(lp.a_matrix_.value_, dtype=float),
         np.array(lp.a_matrix_.index_),
         np.array(lp.a_matrix_.start_)),
        shape=(m, n))

    return dict(
        n=n, m=m, P=P, q=np.array(lp.col_cost_, dtype=float),
        A_lp=A_lp.tocsr(),
        row_lower=np.array(lp.row_lower_, dtype=float),
        row_upper=np.array(lp.row_upper_, dtype=float),
        col_lower=np.array(lp.col_lower_, dtype=float),
        col_upper=np.array(lp.col_upper_, dtype=float),
        offset=float(getattr(lp, "offset_", 0.0)),
        sense=int(getattr(lp, "sense_", 1)),  # 1=min, -1=max
        col_names=list(getattr(lp, "col_names_", []) or []),
    )


def _symmetrize_full(P):
    """Приводит хессиан к ПОЛНОЙ симметричной матрице независимо от того,
    как он хранился: нижний треугольник (так отдаёт HiGHS), верхний
    (наш fallback-парсер) или уже полный."""
    lo = sp.tril(P, -1)
    up = sp.triu(P, 1)
    if up.nnz == 0 and lo.nnz > 0:        # хранился нижний треугольник
        return (P + lo.T).tocsc()
    if lo.nnz == 0 and up.nnz > 0:        # хранился верхний треугольник
        return (P + up.T).tocsc()
    if lo.nnz == 0 and up.nnz == 0:       # диагональная
        return P.tocsc()
    asym = abs(lo - up.T)
    if asym.nnz and asym.max() > 1e-8 * max(1.0, abs(P).max()):
        print(">> Внимание: хессиан несимметричен, симметризую (P+P')/2")
        return ((P + P.T) * 0.5).tocsc()
    return P.tocsc()                      # уже полная симметричная


def _normalize_source(path):
    """Определяет и чинит типичные проблемы файла после Windows-переноса:
    UTF-16 (нулевые байты), UTF-8 BOM, gzip. Возвращает (путь_для_чтения,
    временный_файл_или_None)."""
    import gzip as _gz, tempfile, os
    with open(path, "rb") as f:
        head = f.read(4096)

    def _tmp(data_bytes):
        fd, t = tempfile.mkstemp(suffix=".mps"); os.close(fd)
        with open(t, "wb") as g:
            g.write(data_bytes)
        return t

    if head[:2] == b"\x1f\x8b":                       # gzip
        print(">> Файл сжат gzip - распаковываю")
        with _gz.open(path, "rb") as g:
            return (t := _tmp(g.read())), t
    if head[:2] in (b"\xff\xfe", b"\xfe\xff") or head.count(b"\x00") > len(head) // 5:
        print(">> Файл в кодировке UTF-16 (типично после сохранения в Windows-"
              "редакторе) - перекодирую в обычный текст")
        enc = "utf-16" if head[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-16-le"
        with open(path, "r", encoding=enc) as g:
            text = g.read()
        return (t := _tmp(text.encode("latin-1", errors="replace"))), t
    if head[:3] == b"\xef\xbb\xbf":                   # UTF-8 BOM
        with open(path, "rb") as g:
            return (t := _tmp(g.read()[3:])), t
    return path, None


def load_mps(path):
    import highspy, os
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"Файл не найден: {os.path.abspath(path)} - проверьте путь и имя "
            "(в Windows расширение может быть скрыто: файл.mps.txt)")
    ok_statuses = (highspy.HighsStatus.kOk, highspy.HighsStatus.kWarning)

    use_path, tmp_norm = _normalize_source(path)
    try:
        d = _load_mps_inner(use_path, ok_statuses)
        if d["n"] == 0:
            with open(use_path, "rb") as f:
                head = f.read(32)
            raise RuntimeError(
                f"Модель пуста (0 переменных) - файл повреждён или это не MPS.\n"
                f"Размер: {os.path.getsize(path)} байт, первые байты: {head!r}\n"
                "Сравните размер с оригиналом (оригинал DV2_2H ~4.5 МБ; "
                "UTF-16-копия ~9 МБ; усечённая - меньше).")
        return d
    finally:
        if tmp_norm:
            os.unlink(tmp_norm)


def _load_mps_inner(path, ok_statuses):
    import highspy, os

    h = highspy.Highs()
    h.setOptionValue("output_flag", False)
    st = h.readModel(path)

    d = _extract(h) if st in ok_statuses else None
    if d is not None and d["P"].nnz > 0:
        d["P"] = _symmetrize_full(d["P"])
        return d                                # обычный путь: всё прочиталось

    # highspy не отдал квадратичную часть (старая версия без QMATRIX
    # или ошибка чтения) - пробуем встроенный парсер Q-секции
    with open(path, "r", encoding="latin-1") as f:
        text = f.read()
    has_q = any(s in text for s in _QSECTIONS)

    if not has_q:
        if d is None:
            with open(path, "rb") as f:
                head = f.read(32)
            raise RuntimeError(
                f"highspy не смог прочитать файл (status={st}).\n"
                f"Первые байты: {head!r}\n"
                "Вероятные причины: файл повреждён/скопирован не полностью, "
                "это не MPS-файл, или экзотическая кодировка. "
                "Сравните размер с оригиналом.")
        return d                                # честный LP без Q-секции

    print(">> highspy не вернул квадратичную часть - включаю встроенный "
          "парсер QMATRIX/QUADOBJ (рекомендую обновить: pip install -U highspy)")
    tmp, entries = _parse_quad_section_manually(path)
    try:
        h2 = highspy.Highs()
        h2.setOptionValue("output_flag", False)
        st2 = h2.readModel(tmp)
        if st2 not in ok_statuses:
            raise RuntimeError(
                f"highspy не прочитал даже LP-часть файла (status={st2}). "
                "Обновите highspy: pip install -U highspy")
        d = _extract(h2)
    finally:
        os.unlink(tmp)

    if not d["col_names"]:
        raise RuntimeError("highspy не вернул имена переменных - "
                           "невозможно сопоставить Q-секцию. "
                           "Обновите highspy: pip install -U highspy")
    name_to_idx = {nm: i for i, nm in enumerate(d["col_names"])}
    d["P"] = _symmetrize_full(_hessian_from_entries(entries, name_to_idx, d["n"]))
    return d


def data_report(d):
    """Диагностика масштаба данных - сразу видно, ill-conditioned ли задача."""
    def rng(M):
        v = np.abs(M.data if sp.issparse(M) else M)
        v = v[v > 0]
        return (v.min(), v.max()) if v.size else (0.0, 0.0)
    aP, bP = rng(d["P"]); aA, bA = rng(d["A_lp"]); aq, bq = rng(d["q"])
    lines = [
        f"|A| ненулевые: [{aA:.2e}, {bA:.2e}]  (разброс {bA/max(aA,1e-300):.1e})",
        f"|Q| ненулевые: [{aP:.2e}, {bP:.2e}]" + (f"  (разброс {bP/max(aP,1e-300):.1e})" if bP else ""),
        f"|c| ненулевые: [{aq:.2e}, {bq:.2e}]" if bq else "|c| = 0",
    ]
    warn = (bA / max(aA, 1e-300) > 1e8) or (bP and bP / max(aP, 1e-300) > 1e8)
    return "\n".join(lines), warn


# ----------------------------------------------------------------------------
# Конвертация в форму Clarabel: [равенства -> ZeroCone] + [неравенства -> NN]
# ----------------------------------------------------------------------------
def build_cones(d):
    import clarabel
    n, m = d["n"], d["m"]
    A = d["A_lp"]
    rl, ru, cl, cu = d["row_lower"], d["row_upper"], d["col_lower"], d["col_upper"]

    eq = rl == ru
    le = (~eq) & (ru < INF)      # A x <= ru
    ge = (~eq) & (rl > -INF)     # A x >= rl  ->  -A x <= -rl
    ub = cu < INF                # x <= cu
    lb = cl > -INF               # x >= cl  -> -x <= -cl

    blocks_A, blocks_b = [], []
    n_zero = int(eq.sum())
    if n_zero:
        blocks_A.append(A[eq]);  blocks_b.append(ru[eq])
    if le.any():
        blocks_A.append(A[le]);  blocks_b.append(ru[le])
    if ge.any():
        blocks_A.append(-A[ge]); blocks_b.append(-rl[ge])
    I = sp.eye(n, format="csr")
    if ub.any():
        blocks_A.append(I[ub]);  blocks_b.append(cu[ub])
    if lb.any():
        blocks_A.append(-I[lb]); blocks_b.append(-cl[lb])

    Ab = sp.vstack(blocks_A).tocsc() if blocks_A else sp.csc_matrix((0, n))
    bb = np.concatenate(blocks_b) if blocks_b else np.zeros(0)

    n_nn = Ab.shape[0] - n_zero
    cones = []
    if n_zero:
        cones.append(clarabel.ZeroConeT(n_zero))
    if n_nn:
        cones.append(clarabel.NonnegativeConeT(n_nn))
    return Ab, bb, cones



def solve_piqp(d, tol=1e-6, verbose=True, max_iter=6000):
    import piqp
    P = d["P"].tocsc(); c = d["q"].copy()
    if d["sense"] == -1:
        P = -P; c = -c
    A = d["A_lp"]; rl, ru = d["row_lower"], d["row_upper"]
    eq = rl == ru
    A_eq = A[eq].tocsc(); b_eq = np.ascontiguousarray(ru[eq])
    G = A[~eq].tocsc()
    h_l = np.where(rl[~eq] > -INF, rl[~eq], -np.inf)
    h_u = np.where(ru[~eq] <  INF, ru[~eq],  np.inf)
    x_l = np.where(d["col_lower"] > -INF, d["col_lower"], -np.inf)
    x_u = np.where(d["col_upper"] <  INF, d["col_upper"],  np.inf)

    s = piqp.SparseSolver()
    s.settings.verbose = verbose
    s.settings.eps_abs = tol
    s.settings.eps_rel = tol
    s.settings.max_iter = max_iter
    # КЛЮЧЕВАЯ настройка для данных с огромным масштабом цели (|c|~1e8):
    s.settings.preconditioner_scale_cost = True

    t0 = time.time()
    s.setup(P, c, A_eq, b_eq, G, h_l, h_u, x_l, x_u)
    st = s.solve()
    dt = time.time() - t0

    x = np.array(s.result.x)
    sgn = -1.0 if d["sense"] == -1 else 1.0
    obj = sgn * (0.5 * x @ (P @ x) + c @ x) + d["offset"]
    status = str(st).replace("Status.PIQP_", "").capitalize()
    return dict(status=status, x=x, obj=obj, time=dt,
                iters=s.result.info.iter)


# ----------------------------------------------------------------------------
# Решение (Clarabel)
# ----------------------------------------------------------------------------
def solve(d, tol=1e-8, robust=False, verbose=True, max_iter=400, time_limit=None,
          threads=1):
    import clarabel
    A, b, cones = build_cones(d)
    P = sp.triu(d["P"]).tocsc()          # Clarabel хочет верхний треугольник P
    q = d["q"].copy()
    if d["sense"] == -1:                  # max -> min
        P = -P; q = -q

    s = clarabel.DefaultSettings()
    s.verbose = verbose
    s.max_iter = max_iter
    # ВАЖНО: на KKT такого размера многопоточный faer в РАЗЫ медленнее
    # однопоточного (оверхед синхронизации >> полезной работы): 12 потоков
    # давали 30с там, где 1 поток решает за 3с при тех же итерациях.
    s.max_threads = threads
    s.tol_gap_abs = tol
    s.tol_gap_rel = tol
    s.tol_feas = tol
    if time_limit:
        s.time_limit = float(time_limit)

    if robust:
        # -- выравнивание данных: агрессивнее, шире диапазон масштабов --
        s.equilibrate_enable = True
        s.equilibrate_max_iter = 25           # дефолт 10
        s.equilibrate_max_scaling = 1e8       # дефолт 1e4 - мало при разбросе 1e10
        s.equilibrate_min_scaling = 1e-8
        # -- итеративное уточнение KKT-решений: настойчивее --
        s.iterative_refinement_enable = True
        s.iterative_refinement_max_iter = 15  # дефолт 10
        s.iterative_refinement_reltol = 1e-14
        s.iterative_refinement_abstol = 1e-14
        # -- регуляризация KKT против вырожденности --
        s.static_regularization_enable = True
        s.static_regularization_constant = 1e-7   # дефолт 1e-8
        s.dynamic_regularization_enable = True
        # -- запасной критерий: вернуть чуть менее точное решение,
        #    а не топтаться (статус будет AlmostSolved) --
        s.reduced_tol_gap_abs = max(1e-5, tol * 1e3)
        s.reduced_tol_gap_rel = max(1e-5, tol * 1e3)
        s.reduced_tol_feas = max(1e-5, tol * 1e3)

    t0 = time.time()
    solver = clarabel.DefaultSolver(P, q, A, b, cones, s)
    sol = solver.solve()
    dt = time.time() - t0

    x = np.array(sol.x)
    obj = 0.5 * x @ (d["P"] @ x) + d["q"] @ x + d["offset"]
    if d["sense"] == -1:
        obj = -(0.5 * x @ (d["P"] @ x)) + d["q"] @ x + d["offset"]
    return dict(status=str(sol.status), x=x, obj=obj, time=dt,
                iters=getattr(sol, "iterations", None),
                r_prim=getattr(sol, "r_prim", None),
                r_dual=getattr(sol, "r_dual", None))


def main():
    ap = argparse.ArgumentParser(description="MPS (QP/LP) -> PIQP/Clarabel")
    ap.add_argument("mps")
    ap.add_argument("--solver", choices=["piqp", "clarabel"], default="piqp")
    ap.add_argument("--tol", type=float, default=1e-8)
    ap.add_argument("--fast", action="store_true",
                    help="быстрый режим: tol=1e-6 (обычно достаточно)")
    ap.add_argument("--robust", action="store_true",
                    help="профиль для плохо обусловленных задач")
    ap.add_argument("--no-robust", action="store_true",
                    help="запретить авто-включение robust-профиля")
    ap.add_argument("--out", default=None,
                    help="куда сохранить решение x (по умолч. <имя>.sol в текущей папке)")
    ap.add_argument("--max-iter", type=int, default=400)
    ap.add_argument("--time-limit", type=float, default=None, help="секунды")
    ap.add_argument("--threads", type=int, default=1,
                    help="потоков линейной алгебры (по умолч. 1 - на этих "
                         "размерах многопоточность только вредит; 0 = авто)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    print(f"Читаю MPS: {args.mps}")
    d = load_mps(args.mps)
    kind = "QP" if d["P"].nnz else "LP"
    print(f"Тип: {kind} | переменных: {d['n']} | ограничений: {d['m']} "
          f"| nnz(A): {d['A_lp'].nnz} | nnz(Q): {d['P'].nnz}")
    rep, warn = data_report(d)
    print(rep)
    robust = args.robust or (warn and not args.no_robust)
    if warn and robust and not args.robust:
        print(">> Большой разброс коэффициентов - авто-включаю robust-профиль "
              "(отключить: --no-robust)")
    print("-" * 64)

    # tol = 1e-6 if args.fast and args.tol == 1e-8 else args.tol
    if args.solver == "piqp":
        r = solve_piqp(d, verbose=not args.quiet,
                       max_iter=max(args.max_iter, 6000))
    else:
        r = solve(d, robust=robust,
                  verbose=not args.quiet, max_iter=args.max_iter,
                  time_limit=args.time_limit, threads=args.threads)
    print("-" * 64)
    print(f"{args.solver}: status={r['status']}  time={r['time']:.3f}s  "
          f"iters={r['iters']}")
    print(f"objective = {r['obj']:.8e}")

    import os
    base = os.path.basename(args.mps).rsplit(".", 1)[0] + "_solution.sol"
    out = args.out or base
    np.savetxt(out, r["x"])
    print(f"x сохранён: {out}")


if __name__ == "__main__":
    main()