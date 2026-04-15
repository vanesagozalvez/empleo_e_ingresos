# Empleo e Ingresos · Argentina

Aplicación web de consulta de series estadísticas de **empleo e ingresos de Argentina**, construida con **FastAPI** (backend) y HTML/JS vanilla (frontend). Lista para hacer deploy en [Render](https://render.com).

---

## Fuentes de datos

| Dataset | Archivo | Contenido |
|---------|---------|-----------|
| DB1 | `empleo_e_ingresos.db` | EPH, EIL, EAHU — tasas de actividad, empleo, desocupación, subocupación por aglomerado |
| DB2 | `empleo_e_ingresos2.db` | Salarios (IS, RIPTE, SMVM), canastas (CBA/CBT), línea de pobreza, distribución del ingreso, AUH |
| DB3 | `empleo_e_ingresos3.db` | OEDE — empleo registrado, puestos y remuneraciones por rama, sector y provincia |

---

## Estructura del proyecto

```
empleo_e_ingresos/
├── main.py                  # Backend FastAPI
├── requirements.txt         # Dependencias Python
├── render.yaml              # Configuración de deploy en Render
├── .gitignore
├── README.md
├── static/
│   └── index.html           # Frontend (HTML + CSS + JS vanilla)
└── data/                    # Bases de datos SQLite (se cargan manualmente)
    ├── empleo_e_ingresos.db
    ├── empleo_e_ingresos2.db
    └── empleo_e_ingresos3.db
```

---

## Cómo hacer deploy en Render

### 1. Preparar el repositorio en GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/TU_USUARIO/empleo_e_ingresos.git
git push -u origin main
```

### 2. Crear el servicio en Render

1. Entrá a [render.com](https://render.com) y logueate
2. Hacé clic en **New → Web Service**
3. Conectá tu repositorio de GitHub `empleo_e_ingresos`
4. Render detectará el `render.yaml` automáticamente, o usá estos valores manualmente:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Python Version:** `3.11.0`

### 3. Agregar el Disk (almacenamiento persistente)

Esto es **fundamental**: las bases de datos SQLite necesitan un disco persistente para no perderse en cada deploy.

1. En la configuración del servicio → **Disks** → **Add Disk**
2. Configurar:
   - **Name:** `data-disk`
   - **Mount Path:** `/opt/render/project/src/data`
   - **Size:** 2 GB (o más si es necesario)
3. Guardar

### 4. Subir las bases de datos al Disk

Las bases de datos **no se versionan en Git** (son archivos binarios grandes que cambian frecuentemente). Se suben directamente al Disk de Render:

**Opción A — Render Shell (recomendado):**
1. En tu servicio en Render → **Shell**
2. El directorio `/opt/render/project/src/data/` ya existe (montado por el Disk)
3. Usá `curl` o un script para copiar los archivos, o subí via SFTP si tenés acceso

**Opción B — Script de carga inicial:**
Podés subir los archivos `.db` via SSH o usando la Render CLI:
```bash
render ssh <service-id>
# Dentro del shell de Render:
ls /opt/render/project/src/data/
```

**Opción C — Incluir las DBs en el repositorio:**
Si las bases de datos son pequeñas (<100 MB total) y no se actualizan muy seguido, podés simplemente incluirlas en el repo dentro de la carpeta `data/` y Git las versionará. En ese caso, editá el `.gitignore` para NO excluirlas.

### 5. Actualizar las bases de datos

Cuando tengas nuevas versiones de las bases de datos:

1. **Si están en el repo:** actualizá los archivos `.db` en `data/`, hacé commit y push → Render redeploya automáticamente
2. **Si están en el Disk:** conectate al shell de Render y reemplazá los archivos en `/opt/render/project/src/data/`

---

## Desarrollo local

```bash
# Clonar
git clone https://github.com/TU_USUARIO/empleo_e_ingresos.git
cd empleo_e_ingresos

# Crear entorno virtual
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# Instalar dependencias
pip install -r requirements.txt

# Colocar los archivos .db en data/
mkdir -p data
# cp /ruta/a/tus/bases/*.db data/

# Correr el servidor
uvicorn main:app --reload
```

Abrí `http://localhost:8000` en el navegador.

---

## Endpoints de la API

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Frontend (index.html) |
| GET | `/api/health` | Estado de las bases de datos |
| GET | `/api/debug` | Info detallada del sistema |
| GET | `/api/fuentes` | Lista de fuentes/encuestas disponibles |
| GET | `/api/frecuencias?fuente=EPH` | Frecuencias disponibles para una fuente |
| GET | `/api/series?fuente=EPH&frecuencia=Trimestral` | Series de una fuente y frecuencia |
| GET | `/api/periodos?fuente=EPH&frecuencia=Trimestral&serie=...` | Rango de períodos disponibles |
| GET | `/api/datos?fuente=...&frecuencia=...&serie=...&desde=...&hasta=...` | Datos de una serie |
| GET | `/api/export/csv?...` | Descarga CSV de una serie |

---

## Stack tecnológico

- **Backend:** Python 3.11, FastAPI, SQLite, Uvicorn
- **Frontend:** HTML5, CSS3, JavaScript (vanilla), Chart.js 4
- **Deploy:** Render (Web Service + Persistent Disk)
- **Datos:** INDEC (EPH, EIL, EAHU) · Ministerio de Trabajo (OEDE)
