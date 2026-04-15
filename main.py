"""
Empleo e Ingresos Argentina — Consulta Integrada
Datasets: empleo_e_ingresos.db · empleo_e_ingresos2.db · empleo_e_ingresos3.db
Backend: FastAPI + SQLite x3
"""

import sqlite3
import io
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB1_PATH = DATA_DIR / "empleo_e_ingresos.db"
DB2_PATH = DATA_DIR / "empleo_e_ingresos2.db"
DB3_PATH = DATA_DIR / "empleo_e_ingresos3.db"

DB_PATHS = {1: DB1_PATH, 2: DB2_PATH, 3: DB3_PATH}

# ── Catálogo de fuentes (hojas) por dataset ────────────────────────────────
# Cada ítem: (fuente_id, nombre_fuente, descripcion, db_num)
FUENTES_CATALOG = [
    # ── Dataset 1: EPH / EIL / EAHU ───────────────────────────────────────
    ("EPH",              "EPH - Tasas generales",                  "Encuesta Permanente de Hogares - Tasas de actividad, empleo y desocupación", 1),
    ("EPH - Asal",       "EPH - Asalariados",                      "Encuesta Permanente de Hogares - Asalariados con y sin descuento jubilatorio", 1),
    ("EPH-Poblaciones",  "EPH - Poblaciones",                      "Encuesta Permanente de Hogares - Poblaciones (trimestral)", 1),
    ("TA 03-",           "Tasa de Actividad (2003-)",               "Tasa de actividad por aglomerado desde 2003", 1),
    ("TD 03-",           "Tasa de Desocupación (2003-)",            "Tasa de desocupación por aglomerado desde 2003", 1),
    ("TE 03-",           "Tasa de Empleo (2003-)",                  "Tasa de empleo por aglomerado desde 2003", 1),
    ("TS 03-",           "Tasa de Subocupación (2003-)",            "Tasa de subocupación por aglomerado desde 2003", 1),
    ("TSD 03-",          "Tasa de Suboc. Demandante (2003-)",       "Tasa de subocupación demandante por aglomerado desde 2003", 1),
    ("TSND 03-",         "Tasa de Suboc. No Demandante (2003-)",    "Tasa de subocupación no demandante por aglomerado desde 2003", 1),
    ("EIL - Aglo",       "EIL - Por Aglomerado",                   "Encuesta de Indicadores Laborales - por aglomerado", 1),
    ("EIL - Sector",     "EIL - Por Sector",                       "Encuesta de Indicadores Laborales - por sector", 1),
    ("EAHU-Tasas",       "EAHU - Tasas",                           "Encuesta Anual de Hogares Urbanos - Tasas", 1),
    ("EAHU-Poblaciones", "EAHU - Poblaciones",                     "Encuesta Anual de Hogares Urbanos - Poblaciones", 1),
    # ── Dataset 2: Ingresos / Salarios / Canastas ─────────────────────────
    ("CGI-2016",         "CGI - Costo Salarial Total",             "Costo del Trabajo - Índice base 2016", 2),
    ("CGI ManodeObra",   "CGI - Mano de Obra",                     "Costo del Trabajo - Componentes mano de obra", 2),
    ("CGI VABpb",        "CGI - VAB pb",                           "Costo del Trabajo - VAB a precios básicos", 2),
    ("IS oct16=100",     "Índice de Salarios",                     "Índice de Salarios (base octubre 2016=100)", 2),
    ("RIPTE",            "RIPTE",                                  "Remuneración Imponible Promedio de los Trabajadores Estables", 2),
    ("SMVM",             "Salario Mínimo (SMVM)",                  "Salario Mínimo Vital y Móvil", 2),
    ("HaberMin",         "Haber Mínimo Jubilatorio",               "Haber Mínimo Jubilatorio mensual", 2),
    ("CBA y CBT 2016",   "CBA y CBT",                              "Canasta Básica Alimentaria y Total (base 2016)", 2),
    ("LP - Pers",        "Línea de Pobreza",                       "Línea de Pobreza por persona - datos semestrales", 2),
    ("DP",               "Distribución del Ingreso",               "Distribución del ingreso - indicadores generales", 2),
    ("DP Deciles",       "Distribución por Deciles",               "Distribución del ingreso por deciles", 2),
    ("AUH",              "Asignación Universal por Hijo (AUH)",    "Evolución del monto de la AUH", 2),
    # ── Dataset 3: OEDE - Empleo Registrado ───────────────────────────────
    ("OEDE Total",       "OEDE - Totales",                         "Observatorio de Empleo y Dinámica Empresarial - Indicadores totales", 3),
    ("OEDE Asal rama",   "OEDE - Asalariados por Rama",            "Asalariados registrados por rama de actividad", 3),
    ("OEDE Asal prov",   "OEDE - Asalariados por Provincia",       "Asalariados registrados por provincia", 3),
    ("OEDE Puestos Rama","OEDE - Puestos por Rama",                "Puestos de trabajo por rama de actividad", 3),
    ("OEDE Puestos Sector","OEDE - Puestos por Sector",            "Puestos de trabajo por sector", 3),
    ("OEDE Remuneraciones","OEDE - Remuneraciones Totales",        "Remuneraciones promedio totales", 3),
    ("OEDE Remuneraciones Rama","OEDE - Remuneraciones por Rama",  "Remuneraciones promedio por rama de actividad", 3),
]

# Lookup rápido
FUENTE_DB: dict[str, int] = {f[0]: f[3] for f in FUENTES_CATALOG}


# ── App ────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Empleo e Ingresos Argentina",
    description="Consulta integrada de series de empleo e ingresos — INDEC / OEDE",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


# ── DB connection ──────────────────────────────────────────────────────────
def get_conn(db_num: int) -> sqlite3.Connection:
    path = DB_PATHS.get(db_num)
    if not path:
        raise HTTPException(400, detail=f"db_num={db_num} inválido.")
    if not path.exists():
        raise HTTPException(
            503,
            detail=(
                f"Base de datos '{path.name}' no disponible. "
                f"El archivo debe estar en la carpeta data/ del repositorio."
            ),
        )
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


# ── API: Diagnóstico ───────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    db_status = {f"db{i}_ok": DB_PATHS[i].exists() for i in (1, 2, 3)}
    all_ok = all(db_status.values())
    return {"status": "ok" if all_ok else "degraded", **db_status}


@app.get("/api/debug")
def debug():
    archivos = [f.name for f in DATA_DIR.iterdir()] if DATA_DIR.exists() else []
    counts = {}
    for i in (1, 2, 3):
        if DB_PATHS[i].exists():
            try:
                conn = sqlite3.connect(str(DB_PATHS[i]))
                counts[f"db{i}_series"] = conn.execute(
                    "SELECT COUNT(DISTINCT serie_nombre) FROM empleo_datos"
                ).fetchone()[0]
                counts[f"db{i}_rows"] = conn.execute(
                    "SELECT COUNT(*) FROM empleo_datos"
                ).fetchone()[0]
                conn.close()
            except Exception as e:
                counts[f"db{i}_error"] = str(e)
    return {
        "version": "1.0.0",
        "base_dir": str(BASE_DIR),
        "data_dir": str(DATA_DIR),
        "archivos_data": archivos,
        "fuentes_catalogo": len(FUENTES_CATALOG),
        **{f"db{i}_exists": DB_PATHS[i].exists() for i in (1, 2, 3)},
        **counts,
    }


# ── API: Catálogos ─────────────────────────────────────────────────────────
@app.get("/api/fuentes")
def get_fuentes():
    """Lista completa de fuentes/hojas disponibles con su DB de origen."""
    return [
        {
            "fuente":      f[0],
            "fuente_nombre": f[1],
            "descripcion": f[2],
            "db_num":      f[3],
        }
        for f in FUENTES_CATALOG
        if DB_PATHS[f[3]].exists()
    ]


@app.get("/api/frecuencias")
def get_frecuencias(fuente: str = Query(...)):
    db_num = FUENTE_DB.get(fuente)
    if db_num is None:
        raise HTTPException(404, detail=f"Fuente '{fuente}' no encontrada.")
    order = {"Anual": 0, "Semestral": 1, "Trimestral": 2, "Mensual": 3}
    conn = get_conn(db_num)
    try:
        rows = conn.execute(
            "SELECT DISTINCT frecuencia FROM empleo_datos WHERE ho_origen=? ORDER BY frecuencia",
            [fuente],
        ).fetchall()
    finally:
        conn.close()
    freqs = sorted([r["frecuencia"] for r in rows], key=lambda f: order.get(f, 99))
    if not freqs:
        raise HTTPException(404, detail=f"No hay frecuencias para la fuente '{fuente}'.")
    return freqs


@app.get("/api/series")
def get_series(fuente: str = Query(...), frecuencia: str = Query(...)):
    db_num = FUENTE_DB.get(fuente)
    if db_num is None:
        raise HTTPException(404, detail=f"Fuente '{fuente}' no encontrada.")
    conn = get_conn(db_num)
    try:
        rows = conn.execute(
            """SELECT DISTINCT serie_nombre, unidad
               FROM empleo_datos
               WHERE ho_origen=? AND frecuencia=? AND serie_nombre != ''
               ORDER BY serie_nombre""",
            [fuente, frecuencia],
        ).fetchall()
    finally:
        conn.close()
    return [{"serie_nombre": r["serie_nombre"], "unidad": r["unidad"]} for r in rows]


@app.get("/api/periodos")
def get_periodos(
    fuente:     str = Query(...),
    frecuencia: str = Query(...),
    serie:      str = Query(...),
):
    db_num = FUENTE_DB.get(fuente)
    if db_num is None:
        raise HTTPException(404, detail=f"Fuente '{fuente}' no encontrada.")
    conn = get_conn(db_num)
    try:
        rows = conn.execute(
            """SELECT periodo FROM empleo_datos
               WHERE ho_origen=? AND frecuencia=? AND serie_nombre=?
               ORDER BY periodo""",
            [fuente, frecuencia, serie],
        ).fetchall()
    finally:
        conn.close()
    if not rows:
        return {"desde": None, "hasta": None}
    periodos = [r["periodo"][:10] for r in rows if r["periodo"]]
    return {"desde": min(periodos), "hasta": max(periodos)}


@app.get("/api/datos/")
@app.get("/api/datos")

def get_datos(
    fuente:     str = Query(...),
    frecuencia: str = Query(...),
    serie:      str = Query(...),
    desde:      str = Query(...),
    hasta:      str = Query(...),
):
    if desde > hasta:
        raise HTTPException(400, detail="'desde' debe ser ≤ 'hasta'.")
    db_num = FUENTE_DB.get(fuente)
    if db_num is None:
        raise HTTPException(404, detail=f"Fuente '{fuente}' no encontrada.")
    conn = get_conn(db_num)
    try:
        rows = conn.execute(
            """SELECT periodo_raw, periodo, valor, unidad, serie_nombre, frecuencia, ho_origen
               FROM empleo_datos
               WHERE ho_origen=? AND frecuencia=? AND serie_nombre=?
                 AND periodo >= ? AND periodo <= ?
               ORDER BY periodo""",
            [fuente, frecuencia, serie, desde, hasta],
        ).fetchall()
    finally:
        conn.close()
    if not rows:
        return {"datos": [], "meta": {}}

    first = dict(rows[0])
    meta = {
        "serie_nombre":    first["serie_nombre"],
        "fuente":          first["ho_origen"],
        "frecuencia":      first["frecuencia"],
        "unidad":          first["unidad"],
        "db_num":          db_num,
        "total_registros": len(rows),
    }
    datos = [
        {
            "periodo_raw": r["periodo_raw"],
            "periodo":     r["periodo"][:10] if r["periodo"] else None,
            "valor":       r["valor"],
        }
        for r in rows
    ]
    return {"datos": datos, "meta": meta}


@app.get("/api/export/csv")
def export_csv(
    fuente:     str = Query(...),
    frecuencia: str = Query(...),
    serie:      str = Query(...),
    desde:      str = Query(...),
    hasta:      str = Query(...),
):
    result = get_datos(
        fuente=fuente, frecuencia=frecuencia,
        serie=serie, desde=desde, hasta=hasta,
    )
    datos, meta = result["datos"], result["meta"]

    buf = io.StringIO()
    buf.write(f"# Serie: {meta.get('serie_nombre','')}\n")
    buf.write(f"# Fuente: {meta.get('fuente','')}\n")
    buf.write(f"# Unidad: {meta.get('unidad','')}\n")
    buf.write(f"# Frecuencia: {meta.get('frecuencia','')}\n")
    buf.write("periodo,periodo_raw,valor\n")
    for row in datos:
        buf.write(f"{row['periodo']},{row['periodo_raw']},{row['valor']}\n")
    buf.seek(0)

    fname = (
        f"empleo_{meta.get('fuente','')[:20]}_{serie[:30]}"
        f"_{desde}_{hasta}.csv"
    ).replace(" ", "_").replace("/", "-")

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


# ── Frontend ───────────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
def root():
    return HTMLResponse((BASE_DIR / "static" / "index.html").read_text(encoding="utf-8"))
