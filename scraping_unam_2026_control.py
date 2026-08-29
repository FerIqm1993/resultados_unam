"""
Extraccion completa de resultados UNAM por area.

Flujo:
1. Inicia un Chrome normal con un perfil independiente y se conecta por CDP.
2. Permite completar una sola vez la verificacion de Cloudflare.
3. Recorre automaticamente las paginas de las Areas 1, 2, 3 y 4.
4. Descubre todos los enlaces Carrera-Plantel de cada area.
5. Visita cada pagina de resultados usando la misma sesion de Chrome.
6. Extrae resumen y aspirantes, preservando ceros iniciales.
7. Guarda un CSV por opcion y area para poder reanudar el proceso.
8. Une todo en un DataFrame y genera CSV y Excel consolidados.

Instalacion en Windows:
    py -m pip install playwright pandas xlsxwriter
    py -m playwright install chromium

Ejecucion:
    py scraping_unam_todas_areas.py
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from urllib.request import urlopen

import pandas as pd
from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    Route,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)


# ============================================================
# CONFIGURACION
# ============================================================

# Areas escolarizadas que se procesaran en una sola ejecucion.
AREAS = (1, 2, 3, 4)

if not AREAS or any(area not in {1, 2, 3, 4} for area in AREAS):
    raise ValueError("AREAS solo puede contener los valores 1, 2, 3 y 4.")


def construir_url_area(area: int) -> str:
    """Las paginas escolarizadas de control siguen patron especifico."""
    if area == 1:
        return "https://www.dgae.unam.mx/Licenciatura2026/resultados_control/15.html"
    elif area == 2:
        return "https://www.dgae.unam.mx/Licenciatura2026/resultados_control/25.html"
    elif area == 3:
        return "https://www.dgae.unam.mx/Licenciatura2026/resultados_control/35.html"
    elif area == 4:
        return "https://www.dgae.unam.mx/Licenciatura2026/resultados_control/45.html"
    return ""


PAGINA_INICIAL_URL = construir_url_area(AREAS[0])

BASE_SALIDA = Path.cwd() / "resultados_unam_2026_control"
CARPETA_POR_OPCION = BASE_SALIDA / "por_opcion"
CARPETA_PERFIL = Path.cwd() / "perfil_dgae_playwright"
CARPETA_PERFIL_CDP = Path.cwd() / "perfil_dgae_chrome_normal"

ARCHIVO_CATALOGO = BASE_SALIDA / "catalogo_carreras_planteles.csv"
ARCHIVO_PROGRESO = BASE_SALIDA / "progreso_extraccion.csv"
ARCHIVO_ERRORES = BASE_SALIDA / "errores_extraccion.csv"
ARCHIVO_CSV = BASE_SALIDA / "resultados_todas_las_areas.csv"
ARCHIVO_EXCEL = BASE_SALIDA / "resultados_todas_las_areas.xlsx"

# Si es True, un CSV individual que ya contiene todas sus filas se reutiliza.
REANUDAR = True

# Metodo recomendado: iniciar Chrome como un navegador normal y conectar
# Playwright despues mediante el puerto local de depuracion. Esto evita que
# Cloudflare reciba un Chrome iniciado con los argumentos de automatizacion.
USAR_CHROME_NORMAL_CDP = True
PUERTO_CDP = 9222
URL_CDP = f"http://127.0.0.1:{PUERTO_CDP}"

# Solo se usa cuando USAR_CHROME_NORMAL_CDP es False.
CHROME_VISIBLE = True

# Mantenerlo en False da la mayor compatibilidad con la verificacion. Una vez
# que la sesion funciona puede cambiarse a True para omitir fuentes y medios.
BLOQUEAR_RECURSOS_VISUALES = False

MAX_INTENTOS_POR_PAGINA = 3
TIMEOUT_PAGINA_MS = 120_000
TIMEOUT_TABLA_MS = 120_000
TIMEOUT_VERIFICACION_MS = 300_000

# Pausa pequena para no enviar las 47 solicitudes de forma agresiva.
ESPERA_ENTRE_PAGINAS_SEG = 0.75

GENERAR_CSV = True
GENERAR_EXCEL = True


COLUMNAS_RESULTADOS = [
    "Area",
    "Concurso",
    "Clave_carrera",
    "Codigo_opcion",
    "Carrera",
    "Plantel",
    "Modalidad",
    "URL_resultados",
    "Oferta",
    "Aspirantes",
    "Presentaron_examen",
    "Aciertos_minimos",
    "Seleccionados",
    "Numero_comprobante",
    "Aciertos",
    "Acreditado",
    "Estatus",
    "Detalles",
    "Diagnostico",
]


EQUIVALENCIAS_ESTATUS = {
    "S": "Seleccionada/o",
    "N": "No presentada/o",
    "C": "Cancelada/o",
    "": "No seleccionada/o",
}


# ============================================================
# FUNCIONES GENERALES
# ============================================================

def limpiar_texto(valor: Any) -> str:
    """Normaliza espacios y convierte valores vacios en cadena."""
    return re.sub(r"\s+", " ", "" if valor is None else str(valor)).strip()


def extraer_entero(patron: str, texto: str) -> int | pd._libs.missing.NAType:
    """Extrae un entero mediante una expresion regular."""
    coincidencia = re.search(patron, texto, flags=re.IGNORECASE)
    return int(coincidencia.group(1)) if coincidencia else pd.NA


def nombre_seguro(texto: str, limite: int = 70) -> str:
    """Genera una parte de nombre de archivo valida en Windows."""
    reemplazos = str.maketrans(
        "ÁÀÂÄÃÉÈÊËÍÌÎÏÓÒÔÖÕÚÙÛÜÑÇ",
        "AAAAAEEEEIIIIOOOOOUUUUNC",
    )
    limpio = limpiar_texto(texto).upper().translate(reemplazos)
    limpio = re.sub(r'[\\/*?:"<>|]', "", limpio)
    limpio = re.sub(r"[^A-Z0-9._-]+", "_", limpio)
    limpio = limpio.strip("._-")
    return (limpio or "SIN_NOMBRE")[:limite]


def guardar_tabla_csv(df: pd.DataFrame, ruta: Path) -> None:
    """Escribe un CSV compatible con Excel y conserva ceros iniciales."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta, index=False, encoding="utf-8-sig")


def ruta_csv_opcion(item: dict[str, str]) -> Path:
    """Crea un nombre unico; Codigo_opcion evita sobreescrituras."""
    area = item["Area"]
    codigo = item["Codigo_opcion"]
    carrera = nombre_seguro(item["Carrera"])
    plantel = nombre_seguro(item["Plantel"])
    return (
        CARPETA_POR_OPCION
        / f"area_{area}"
        / f"{codigo}_{carrera}_{plantel}.csv"
    )


def bloquear_recursos_pesados(route: Route) -> None:
    """Omite recursos visuales; conserva documentos y JavaScript."""
    if route.request.resource_type in {"font", "media"}:
        route.abort()
    else:
        route.continue_()


def buscar_ejecutable_chrome() -> Path:
    """Localiza Google Chrome en Windows, macOS o Linux."""
    candidatos: list[Path] = []

    for variable in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        base = os.environ.get(variable)
        if base:
            candidatos.append(
                Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe"
            )

    candidatos.append(
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    )

    for comando in ("google-chrome", "google-chrome-stable", "chrome", "chromium"):
        ejecutable = shutil.which(comando)
        if ejecutable:
            candidatos.append(Path(ejecutable))

    for candidato in candidatos:
        if candidato.is_file():
            return candidato

    raise FileNotFoundError(
        "No se encontro Google Chrome. Instala Chrome o modifica "
        "buscar_ejecutable_chrome() con la ruta de chrome.exe."
    )


def puerto_cdp_activo() -> bool:
    """Comprueba si existe un Chrome escuchando en el puerto configurado."""
    try:
        with urlopen(f"{URL_CDP}/json/version", timeout=1.5) as respuesta:
            return respuesta.status == 200
    except Exception:
        return False


def iniciar_chrome_normal() -> None:
    """Inicia Chrome sin las banderas de automatizacion de Playwright."""
    if puerto_cdp_activo():
        return

    chrome = buscar_ejecutable_chrome()
    CARPETA_PERFIL_CDP.mkdir(parents=True, exist_ok=True)

    comando = [
        str(chrome),
        f"--remote-debugging-port={PUERTO_CDP}",
        "--remote-debugging-address=127.0.0.1",
        f"--user-data-dir={CARPETA_PERFIL_CDP.resolve()}",
        "--start-maximized",
        PAGINA_INICIAL_URL,
    ]

    subprocess.Popen(comando)

    limite = time.monotonic() + 30
    while time.monotonic() < limite:
        if puerto_cdp_activo():
            return
        time.sleep(0.5)

    raise RuntimeError(
        "Chrome se abrio, pero no fue posible conectarse al puerto local "
        f"{PUERTO_CDP}. Cierra esa ventana y vuelve a ejecutar el programa."
    )


def abrir_contexto(
    playwright: Playwright,
) -> tuple[Browser | None, BrowserContext]:
    """Conecta un Chrome normal o usa el lanzamiento clasico como respaldo."""
    if USAR_CHROME_NORMAL_CDP:
        iniciar_chrome_normal()
        navegador = playwright.chromium.connect_over_cdp(
            URL_CDP,
            timeout=30_000,
        )
        if not navegador.contexts:
            raise RuntimeError("Chrome no proporciono ningun contexto navegable.")
        contexto = navegador.contexts[0]
        contexto.set_default_timeout(TIMEOUT_TABLA_MS)
        return navegador, contexto

    contexto = playwright.chromium.launch_persistent_context(
        user_data_dir=str(CARPETA_PERFIL),
        channel="chrome",
        headless=not CHROME_VISIBLE,
        no_viewport=True,
        args=["--start-maximized"],
    )
    contexto.set_default_timeout(TIMEOUT_TABLA_MS)
    return None, contexto


def navegar_y_esperar(
    pagina: Page,
    url: str,
    selector: str,
    timeout_selector_ms: int,
) -> None:
    """Navega rapidamente y espera un elemento que confirme la pagina real."""
    pagina.goto(url, wait_until="commit", timeout=TIMEOUT_PAGINA_MS)
    pagina.wait_for_selector(
        selector,
        state="attached",
        timeout=timeout_selector_ms,
    )


# ============================================================
# DESCUBRIMIENTO DE CARRERAS Y PLANTELES
# ============================================================

def descubrir_opciones(
    pagina: Page,
    area_esperada: int,
) -> tuple[list[dict[str, str]], str]:
    """Obtiene dinamicamente todos los botones Carrera-Plantel del area."""
    pagina_area_url = construir_url_area(area_esperada)
    print(f"Abriendo pagina del Area {area_esperada}:\n{pagina_area_url}")
    print(
        "Si Chrome muestra una verificacion de Cloudflare, completala. "
        "El programa continuara cuando aparezca el listado."
    )

    ruta_actual = urlsplit(pagina.url).path
    ruta_objetivo = urlsplit(pagina_area_url).path

    # Chrome se inicia directamente en la pagina del area. No se vuelve a
    # navegar si ya esta verificando esa URL, pues reiniciar la navegacion
    # tambien reiniciaria el desafio de Cloudflare.
    if ruta_actual != ruta_objetivo:
        pagina.goto(
            pagina_area_url,
            wait_until="commit",
            timeout=TIMEOUT_PAGINA_MS,
        )

    pagina.wait_for_selector(
        ".post-preview a[href]",
        state="attached",
        timeout=TIMEOUT_VERIFICACION_MS,
    )

    titulo_area = limpiar_texto(
        pagina.locator("main h2, h2").first.text_content()
    )
    modalidad = "Escolarizado"
    match_modalidad = re.search(r"\(([^()]*)\)\s*$", titulo_area)
    if match_modalidad:
        modalidad = limpiar_texto(match_modalidad.group(1))

    enlaces_brutos = pagina.locator(".post-preview").evaluate_all(
        r"""
        bloques => bloques.flatMap(bloque => {
            const h3 = bloque.querySelector("h3");
            const carrera = (h3?.textContent || "")
                .replace(/\s+/g, " ")
                .trim();

            return Array.from(bloque.querySelectorAll("a[href]")).map(a => ({
                Carrera: carrera,
                Plantel: (a.textContent || "").replace(/\s+/g, " ").trim(),
                URL_resultados: new URL(a.getAttribute("href"), document.baseURI).href
            }));
        })
        """
    )

    opciones: list[dict[str, str]] = []
    urls_vistas: set[str] = set()

    for enlace in enlaces_brutos:
        url = limpiar_texto(enlace.get("URL_resultados"))
        partes = urlsplit(url)
        coincidencia = re.fullmatch(
            r"/Licenciatura2026/resultados_control/(\d+)/(\d+)\.html",
            partes.path,
            flags=re.IGNORECASE,
        )
        if not coincidencia:
            continue

        area, codigo = coincidencia.groups()
        if area != str(area_esperada):
            continue
        url_canonica = f"https://www.dgae.unam.mx{partes.path}"
        if url_canonica in urls_vistas:
            continue
        urls_vistas.add(url_canonica)

        opciones.append(
            {
                "Area": area,
                "Clave_carrera": codigo[:3],
                "Codigo_opcion": codigo,
                "Carrera": limpiar_texto(enlace.get("Carrera")),
                "Plantel": limpiar_texto(enlace.get("Plantel")),
                "Modalidad": modalidad,
                "URL_resultados": url_canonica,
            }
        )

    if not opciones:
        raise RuntimeError(
            "La pagina del area cargo, pero no se encontraron enlaces "
            "con el formato esperado."
        )

    return opciones, titulo_area


# ============================================================
# EXTRACCION DE UNA PAGINA DE RESULTADOS
# ============================================================

def leer_titulo_programa(pagina: Page, respaldo: dict[str, str]) -> dict[str, str]:
    """Obtiene concurso, clave, carrera, plantel y modalidad del h2."""
    datos = {
        "Concurso": "Licenciatura 2026",
        "Clave_carrera": respaldo["Clave_carrera"],
        "Carrera": respaldo["Carrera"],
        "Plantel": respaldo["Plantel"],
        "Modalidad": respaldo["Modalidad"],
    }

    localizador = pagina.locator("main h2, h2").first
    if localizador.count() == 0:
        return datos

    titulo = limpiar_texto(localizador.text_content())
    coincidencia = re.search(
        r"Concurso\s+(.+?)\s*:\s*"
        r"\((\d+)\)\s*"
        r"(.+?)\s*-\s*"
        r"(.+?)\s*-\s*"
        r"(.+)$",
        titulo,
        flags=re.IGNORECASE,
    )
    if coincidencia:
        datos = {
            "Concurso": limpiar_texto(coincidencia.group(1)),
            "Clave_carrera": limpiar_texto(coincidencia.group(2)),
            "Carrera": limpiar_texto(coincidencia.group(3)),
            "Plantel": limpiar_texto(coincidencia.group(4)),
            "Modalidad": limpiar_texto(coincidencia.group(5)),
        }
    return datos


def leer_resumen_pagina(pagina: Page) -> dict[str, Any]:
    """Extrae Oferta, Aspirantes, Presentados, Minimo y Seleccionados."""
    localizador = pagina.locator(".result-stats").first
    if localizador.count() == 0:
        texto = ""
    else:
        texto = limpiar_texto(localizador.text_content())

    return {
        "Oferta": extraer_entero(r"Oferta[:=]\s*(\d+)", texto),
        "Aspirantes": extraer_entero(r"Aspirantes[:=]\s*(\d+)", texto),
        "Presentaron_examen": extraer_entero(
            r"Presentaron(?: Examen)?[:=]\s*(\d+)", texto
        ),
        "Aciertos_minimos": extraer_entero(
            r"(?:Aciertos )?M[ií]nimos[:=]\s*(\d+)", texto
        ),
        "Seleccionados": extraer_entero(r"Seleccionados[:=]\s*(\d+)", texto),
    }


def leer_filas_tabla(pagina: Page) -> list[list[str]]:
    """Transfiere las filas desde el DOM sin serializar todo el HTML."""
    return pagina.locator("#buttons-container .btn-number").evaluate_all(
        r"""
        botones => botones.map(btn => {
            const numero = btn.querySelector('.numero')?.textContent.trim() || '';
            
            const aciertosText = btn.querySelector('.badge-aciertos')?.textContent.trim() || '';
            let aciertos = '';
            const aciertosMatch = aciertosText.match(/\d+/);
            if (aciertosMatch) aciertos = aciertosMatch[0];
            
            let estatus = '';
            const elements = btn.querySelectorAll('*');
            for (let el of elements) {
                if (el.childNodes.length === 1 && el.childNodes[0].nodeType === 3) {
                    const txt = el.textContent.trim();
                    if (txt === 'S' || txt === 'N' || txt === 'C') {
                        estatus = txt;
                        break;
                    }
                }
            }
            
            const detalle = btn.querySelector('.detalle')?.textContent.trim() || '';
            
            return [numero, aciertos, estatus, detalle, ""];
        })
        """
    )


def convertir_filas_dataframe(
    filas: list[list[str]],
    item: dict[str, str],
    datos_programa: dict[str, str],
    resumen: dict[str, Any],
) -> pd.DataFrame:
    """Convierte las celdas crudas en el esquema consolidado."""
    registros: list[dict[str, Any]] = []

    for fila_original in filas:
        fila = [limpiar_texto(valor) for valor in list(fila_original)]
        fila.extend([""] * max(0, 5 - len(fila)))
        fila = fila[:5]

        numero = fila[0]
        if not re.fullmatch(r"\d+", numero):
            continue

        aciertos = pd.to_numeric(fila[1], errors="coerce")
        codigo_estatus = fila[2].upper()

        registros.append(
            {
                "Area": item["Area"],
                **datos_programa,
                "Codigo_opcion": item["Codigo_opcion"],
                "URL_resultados": item["URL_resultados"],
                **resumen,
                "Numero_comprobante": numero,
                "Aciertos": pd.NA if pd.isna(aciertos) else int(aciertos),
                "Acreditado": codigo_estatus,
                "Estatus": EQUIVALENCIAS_ESTATUS.get(
                    codigo_estatus, "Codigo no identificado"
                ),
                "Detalles": fila[3],
                "Diagnostico": fila[4],
            }
        )

    df = pd.DataFrame(registros, columns=COLUMNAS_RESULTADOS)
    if not df.empty:
        df["Numero_comprobante"] = df["Numero_comprobante"].astype("string")
        df["Aciertos"] = df["Aciertos"].astype("Int64")
    return df


def extraer_opcion(pagina: Page, item: dict[str, str]) -> pd.DataFrame:
    """Carga y extrae una combinacion Carrera-Plantel con reintentos."""
    ultimo_error: Exception | None = None

    for intento in range(1, MAX_INTENTOS_POR_PAGINA + 1):
        try:
            navegar_y_esperar(
                pagina,
                item["URL_resultados"],
                "#buttons-container",
                TIMEOUT_TABLA_MS,
            )
            datos_programa = leer_titulo_programa(pagina, item)
            resumen = leer_resumen_pagina(pagina)
            filas = leer_filas_tabla(pagina)
            return convertir_filas_dataframe(
                filas, item, datos_programa, resumen
            )
        except Exception as exc:
            ultimo_error = exc
            print(
                f"  Intento {intento}/{MAX_INTENTOS_POR_PAGINA} fallido: "
                f"{type(exc).__name__}: {exc}"
            )
            if intento < MAX_INTENTOS_POR_PAGINA:
                pagina.wait_for_timeout(2_000 * intento)

    raise RuntimeError(str(ultimo_error) if ultimo_error else "Error desconocido")


# ============================================================
# REANUDACION Y RESUMEN
# ============================================================

def cargar_csv_terminado(ruta: Path) -> pd.DataFrame | None:
    """Reutiliza un archivo solo si el numero de filas coincide con Aspirantes."""
    if not REANUDAR or not ruta.exists():
        return None
    try:
        df = pd.read_csv(
            ruta,
            dtype={
                "Numero_comprobante": "string",
                "Acreditado": "string",
                "Codigo_opcion": "string",
            },
            keep_default_na=False,
        )
        if df.empty or not set(COLUMNAS_RESULTADOS).issubset(df.columns):
            return None

        aspirantes = pd.to_numeric(df["Aspirantes"].iloc[0], errors="coerce")
        if pd.isna(aspirantes) or len(df) != int(aspirantes):
            return None

        df = df[COLUMNAS_RESULTADOS]
        df["Numero_comprobante"] = df["Numero_comprobante"].astype("string")
        df["Aciertos"] = pd.to_numeric(
            df["Aciertos"].replace("", pd.NA), errors="coerce"
        ).astype("Int64")
        return df
    except Exception:
        return None


def cargar_resultado_reutilizable(
    item: dict[str, str],
    ruta_destino: Path,
) -> tuple[pd.DataFrame | None, str]:
    """Busca primero en la salida nueva y luego en salidas de una sola area."""
    ruta_anterior = (
        Path.cwd()
        / f"resultados_unam_area{item['Area']}"
        / "por_opcion"
        / ruta_destino.name
    )

    for ruta in (ruta_destino, ruta_anterior):
        df = cargar_csv_terminado(ruta)
        if df is None:
            continue
        if ruta != ruta_destino:
            guardar_tabla_csv(df, ruta_destino)
            return df, "Importado de ejecucion anterior"
        return df, "Reutilizado"

    return None, ""


def resumen_desde_df(
    df: pd.DataFrame,
    item: dict[str, str],
    estado: str,
    duracion: float,
    error: str = "",
) -> dict[str, Any]:
    """Genera una fila del control de avance."""
    fila: dict[str, Any] = {
        "Area": item["Area"],
        "Clave_carrera": item["Clave_carrera"],
        "Codigo_opcion": item["Codigo_opcion"],
        "Carrera": item["Carrera"],
        "Plantel": item["Plantel"],
        "Modalidad": item["Modalidad"],
        "URL_resultados": item["URL_resultados"],
        "Estado_extraccion": estado,
        "Filas_extraidas": len(df),
        "Seleccionados_extraidos": (
            int(df["Estatus"].eq("Seleccionado").sum()) if not df.empty else 0
        ),
        "Duracion_segundos": round(duracion, 2),
        "Error": error,
    }
    if not df.empty:
        primera = df.iloc[0]
        for columna in [
            "Concurso",
            "Oferta",
            "Aspirantes",
            "Presentaron_examen",
            "Aciertos_minimos",
            "Seleccionados",
        ]:
            fila[columna] = primera.get(columna, pd.NA)
    return fila


def escribir_excel(
    df_maestro: pd.DataFrame,
    df_resumen: pd.DataFrame,
    df_catalogo: pd.DataFrame,
    df_errores: pd.DataFrame,
) -> None:
    """Escribe el consolidado y divide hojas si se supera el limite de Excel."""
    resumen_numerico = df_resumen.copy()
    for columna in [
        "Oferta",
        "Aspirantes",
        "Presentaron_examen",
        "Seleccionados",
        "Filas_extraidas",
        "Seleccionados_extraidos",
    ]:
        if columna in resumen_numerico.columns:
            resumen_numerico[columna] = pd.to_numeric(
                resumen_numerico[columna], errors="coerce"
            )

    resumen_por_area = (
        resumen_numerico.groupby("Area", as_index=False)
        .agg(
            Carreras=("Carrera", "nunique"),
            Opciones_Carrera_Plantel=("Codigo_opcion", "nunique"),
            Oferta_total=("Oferta", "sum"),
            Aspirantes_declarados=("Aspirantes", "sum"),
            Presentaron_examen=("Presentaron_examen", "sum"),
            Seleccionados_declarados=("Seleccionados", "sum"),
            Filas_extraidas=("Filas_extraidas", "sum"),
            Seleccionados_extraidos=("Seleccionados_extraidos", "sum"),
        )
        .sort_values("Area")
        .reset_index(drop=True)
    )

    filas_por_hoja = 1_048_575  # Se reserva una fila para encabezados.
    with pd.ExcelWriter(ARCHIVO_EXCEL, engine="xlsxwriter") as writer:
        for numero, inicio in enumerate(
            range(0, len(df_maestro), filas_por_hoja), start=1
        ):
            fin = inicio + filas_por_hoja
            nombre = "Resultados" if numero == 1 else f"Resultados_{numero}"
            df_maestro.iloc[inicio:fin].to_excel(
                writer, sheet_name=nombre, index=False
            )

        resumen_por_area.to_excel(writer, sheet_name="Resumen por area", index=False)
        df_resumen.to_excel(writer, sheet_name="Resumen por opcion", index=False)
        df_catalogo.to_excel(writer, sheet_name="Catalogo", index=False)
        df_errores.to_excel(writer, sheet_name="Errores", index=False)

        conteo = (
            df_maestro["Estatus"]
            .value_counts(dropna=False)
            .rename_axis("Estatus")
            .reset_index(name="Cantidad")
        )
        conteo.to_excel(writer, sheet_name="Conteo estatus", index=False)


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main() -> None:
    inicio_total = time.perf_counter()
    BASE_SALIDA.mkdir(parents=True, exist_ok=True)
    CARPETA_POR_OPCION.mkdir(parents=True, exist_ok=True)

    dataframes: list[pd.DataFrame] = []
    progreso: list[dict[str, Any]] = []
    errores: list[dict[str, Any]] = []

    with sync_playwright() as playwright:
        navegador_cdp, contexto = abrir_contexto(playwright)
        ruta_area = urlsplit(PAGINA_INICIAL_URL).path
        pagina = next(
            (
                candidata
                for candidata in contexto.pages
                if urlsplit(candidata.url).path == ruta_area
            ),
            None,
        )
        if pagina is None:
            pagina = contexto.new_page()

        try:
            opciones: list[dict[str, str]] = []
            resumen_indices: list[dict[str, Any]] = []

            print("\n" + "=" * 66)
            print("DESCUBRIMIENTO DE CARRERAS Y PLANTELES")
            print("=" * 66)

            for area in AREAS:
                opciones_area, titulo_area = descubrir_opciones(pagina, area)
                opciones.extend(opciones_area)
                resumen_indices.append(
                    {
                        "Area": area,
                        "Titulo": titulo_area,
                        "Carreras": len(
                            {opcion["Carrera"] for opcion in opciones_area}
                        ),
                        "Opciones_Carrera_Plantel": len(opciones_area),
                    }
                )
                print(
                    f"  Area {area}: "
                    f"{resumen_indices[-1]['Carreras']} carreras, "
                    f"{len(opciones_area)} opciones"
                )

            # Proteccion frente a enlaces duplicados en las paginas indice.
            opciones_unicas: list[dict[str, str]] = []
            urls_vistas: set[str] = set()
            for opcion in opciones:
                if opcion["URL_resultados"] in urls_vistas:
                    continue
                urls_vistas.add(opcion["URL_resultados"])
                opciones_unicas.append(opcion)
            opciones = opciones_unicas

            if BLOQUEAR_RECURSOS_VISUALES:
                contexto.route("**/*", bloquear_recursos_pesados)

            df_catalogo = pd.DataFrame(opciones)
            guardar_tabla_csv(df_catalogo, ARCHIVO_CATALOGO)

            carreras_unicas = df_catalogo["Carrera"].nunique()
            print("\n" + "=" * 66)
            print("CATALOGO GENERAL DE LAS AREAS 1 A 4")
            print(f"Carreras distintas encontradas: {carreras_unicas}")
            print(f"Opciones Carrera-Plantel: {len(opciones)}")
            print("=" * 66)

            for indice, item in enumerate(opciones, start=1):
                ruta_individual = ruta_csv_opcion(item)
                etiqueta = (
                    f"[{indice:02d}/{len(opciones):02d}] "
                    f"{item['Carrera']} - {item['Plantel']}"
                )
                print(f"\n{etiqueta}")

                df_existente, estado_reutilizado = cargar_resultado_reutilizable(
                    item, ruta_individual
                )
                if df_existente is not None:
                    print(
                        f"  {estado_reutilizado}: "
                        f"{len(df_existente):,} filas"
                    )
                    dataframes.append(df_existente)
                    progreso.append(
                        resumen_desde_df(
                            df_existente, item, estado_reutilizado, 0.0
                        )
                    )
                    guardar_tabla_csv(pd.DataFrame(progreso), ARCHIVO_PROGRESO)
                    continue

                inicio_opcion = time.perf_counter()
                try:
                    df_opcion = extraer_opcion(pagina, item)
                    duracion = time.perf_counter() - inicio_opcion

                    if df_opcion.empty:
                        raise RuntimeError(
                            "La tabla se encontro, pero no contenia filas validas."
                        )

                    guardar_tabla_csv(df_opcion, ruta_individual)
                    dataframes.append(df_opcion)
                    progreso.append(
                        resumen_desde_df(
                            df_opcion, item, "Completado", duracion
                        )
                    )
                    print(
                        f"  Completado: {len(df_opcion):,} filas "
                        f"en {duracion:.1f} s"
                    )
                except Exception as exc:
                    duracion = time.perf_counter() - inicio_opcion
                    mensaje = f"{type(exc).__name__}: {exc}"
                    print(f"  ERROR: {mensaje}")
                    registro_error = resumen_desde_df(
                        pd.DataFrame(columns=COLUMNAS_RESULTADOS),
                        item,
                        "Error",
                        duracion,
                        mensaje,
                    )
                    progreso.append(registro_error)
                    errores.append(registro_error)

                # El progreso se conserva incluso si el proceso se interrumpe.
                guardar_tabla_csv(pd.DataFrame(progreso), ARCHIVO_PROGRESO)
                guardar_tabla_csv(pd.DataFrame(errores), ARCHIVO_ERRORES)
                pagina.wait_for_timeout(int(ESPERA_ENTRE_PAGINAS_SEG * 1_000))

        finally:
            # Un Chrome conectado por CDP pertenece al usuario y se deja
            # abierto. Al finalizar Playwright solo se desconecta de el.
            if navegador_cdp is None:
                contexto.close()

    if not dataframes:
        raise RuntimeError("No se obtuvo ningun resultado para consolidar.")

    print("\nConsolidando resultados...")
    df_maestro = pd.concat(dataframes, ignore_index=True)
    df_maestro = df_maestro[COLUMNAS_RESULTADOS]
    df_maestro["Numero_comprobante"] = df_maestro[
        "Numero_comprobante"
    ].astype("string")
    df_maestro["Aciertos"] = pd.to_numeric(
        df_maestro["Aciertos"], errors="coerce"
    ).astype("Int64")

    df_resumen = pd.DataFrame(progreso)
    df_errores = pd.DataFrame(errores)

    # Orden estable: carrera, plantel y numero de comprobante.
    df_maestro = df_maestro.sort_values(
        ["Area", "Clave_carrera", "Codigo_opcion", "Numero_comprobante"],
        kind="stable",
    ).reset_index(drop=True)

    if GENERAR_CSV:
        guardar_tabla_csv(df_maestro, ARCHIVO_CSV)
        print(f"CSV consolidado: {ARCHIVO_CSV}")

    if GENERAR_EXCEL:
        escribir_excel(df_maestro, df_resumen, df_catalogo, df_errores)
        print(f"Excel consolidado: {ARCHIVO_EXCEL}")

    duracion_total = time.perf_counter() - inicio_total
    completadas = int(
        df_resumen["Estado_extraccion"]
        .isin(
            [
                "Completado",
                "Reutilizado",
                "Importado de ejecucion anterior",
            ]
        )
        .sum()
    )

    print("\n" + "=" * 66)
    print("EXTRACCION FINALIZADA")
    print(f"Areas procesadas: {', '.join(map(str, AREAS))}")
    print(f"Opciones completas: {completadas}/{len(df_resumen)}")
    print(f"Registros consolidados: {len(df_maestro):,}")
    print("Registros por area:")
    for area, cantidad in df_maestro.groupby("Area").size().sort_index().items():
        print(f"  Area {area}: {cantidad:,}")
    print(f"Errores: {len(df_errores)}")
    print(f"Tiempo total: {duracion_total / 60:.2f} minutos")
    print(f"Carpeta de salida: {BASE_SALIDA.resolve()}")
    print("=" * 66)


if __name__ == "__main__":
    try:
        main()
    except PlaywrightTimeoutError as exc:
        raise SystemExit(
            "Tiempo agotado. Revisa la ventana de Chrome y completa "
            f"cualquier verificacion pendiente. Detalle: {exc}"
        ) from exc
