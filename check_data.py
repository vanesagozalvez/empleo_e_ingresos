"""
check_data.py — Verificación rápida de las bases de datos

Uso:
    python check_data.py

Reporta el estado de cada DB: tablas, columnas, cantidad de registros y series.
Útil para verificar antes de hacer deploy o luego de actualizar las bases.
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

DBS = {
    1: "empleo_e_ingresos.db",
    2: "empleo_e_ingresos2.db",
    3: "empleo_e_ingresos3.db",
}

SEP = "─" * 65

def check_db(db_num: int, filename: str):
    path = DATA_DIR / filename
    print(f"\n{SEP}")
    print(f"  DB{db_num}: {filename}")
    print(SEP)
    if not path.exists():
        print(f"  ✗ ARCHIVO NO ENCONTRADO en {path}")
        return

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        print(f"  ✓ Archivo encontrado ({path.stat().st_size / 1024 / 1024:.1f} MB)")
        for t in tables:
            tname = t["name"]
            cols = [c[1] for c in conn.execute(f"PRAGMA table_info('{tname}')")]
            rows = conn.execute(f"SELECT COUNT(*) FROM '{tname}'").fetchone()[0]
            series = conn.execute(
                f"SELECT COUNT(DISTINCT serie_nombre) FROM '{tname}'"
            ).fetchone()[0]
            freqs = conn.execute(
                f"SELECT DISTINCT frecuencia FROM '{tname}' ORDER BY frecuencia"
            ).fetchall()
            fuentes = conn.execute(
                f"SELECT DISTINCT ho_origen FROM '{tname}' ORDER BY ho_origen"
            ).fetchall()
            print(f"\n  Tabla: {tname}")
            print(f"    Columnas:   {cols}")
            print(f"    Registros:  {rows:,}")
            print(f"    Series:     {series:,}")
            print(f"    Frecuencias:{[f['frecuencia'] for f in freqs]}")
            print(f"    Fuentes ({len(fuentes)}):")
            for f in fuentes:
                cnt = conn.execute(
                    f"SELECT COUNT(DISTINCT serie_nombre) FROM '{tname}' WHERE ho_origen=?",
                    [f["ho_origen"]]
                ).fetchone()[0]
                print(f"      · {f['ho_origen']:<40s} {cnt} series")
    finally:
        conn.close()


if __name__ == "__main__":
    print("\n" + "═" * 65)
    print("  Verificación de bases de datos — Empleo e Ingresos Argentina")
    print("═" * 65)
    print(f"  Directorio data/: {DATA_DIR}")

    for num, fname in DBS.items():
        check_db(num, fname)

    print(f"\n{SEP}")
    print("  Verificación completada.")
    print(SEP + "\n")
