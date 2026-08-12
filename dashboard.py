import streamlit as st
import pandas as pd
import plotly.express as px
import os

# Configuración de la página
st.set_page_config(page_title="Resultados UNAM Dashboard", layout="wide", page_icon="🎓")

@st.cache_data
def load_data():
    # Rutas a los archivos (relativas a la ubicación de este script)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path_2025 = os.path.join(base_dir, "resultados_unam_2025_areas_1_a_4", "resultados_unam_2025_todas_las_areas.csv")
    path_2026 = os.path.join(base_dir, "resultados_unam_2026_areas_1_a_4", "resultados_todas_las_areas.csv")
    
    # Columnas que nos interesan para el resumen
    cols_to_keep = ['Area', 'Carrera', 'Plantel', 'Modalidad', 'Oferta', 'Aspirantes', 'Presentaron_examen', 'Aciertos_minimos', 'Seleccionados']
    
    df_2025 = pd.DataFrame()
    df_2026 = pd.DataFrame()
    
    if os.path.exists(path_2025):
        df_2025 = pd.read_csv(path_2025, usecols=cols_to_keep + ['Anio'])
        # Dejar solo un registro por carrera/plantel (ya que los datos generales se repiten por aspirante)
        df_2025 = df_2025.drop_duplicates()
        
    if os.path.exists(path_2026):
        # El 2026 no tiene columna Anio, la agregamos
        df_2026 = pd.read_csv(path_2026, usecols=cols_to_keep)
        df_2026['Anio'] = 2026
        df_2026 = df_2026.drop_duplicates()
        
    # Combinar ambos años
    df = pd.concat([df_2025, df_2026], ignore_index=True)
    
    # Mapear las áreas a texto para mejor legibilidad si existe la columna Area
    if 'Area' in df.columns:
        mapa_areas = {
            1: "Área 1: Ciencias Físico-Matemáticas y de las Ingenierías",
            2: "Área 2: Ciencias Biológicas, Químicas y de la Salud",
            3: "Área 3: Ciencias Sociales",
            4: "Área 4: Humanidades y de las Artes"
        }
        df['Nombre_Area'] = df['Area'].map(mapa_areas).fillna(df['Area'].astype(str))
    
    return df

st.title("🎓 Dashboard de Resultados UNAM")
st.markdown("Visualización de aciertos mínimos y datos estadísticos de ingreso por Año, Área, Sede y Carrera.")

# Cargar datos
try:
    df = load_data()
except Exception as e:
    st.error(f"Error al cargar los datos: {e}")
    st.stop()

if df.empty:
    st.warning("No se encontraron datos.")
    st.stop()

# --- BARRA LATERAL PARA FILTROS ---
st.sidebar.header("Filtros")

# Filtro por Año
anios_disponibles = sorted(df['Anio'].dropna().unique().tolist())
selected_anios = st.sidebar.multiselect("Año", options=anios_disponibles, default=anios_disponibles)

# Filtrar df por años seleccionados
df_filtered = df[df['Anio'].isin(selected_anios)]

# Filtro por Área
areas_disponibles = sorted(df_filtered['Nombre_Area'].dropna().unique().tolist())
selected_areas = st.sidebar.multiselect("Área", options=areas_disponibles, default=areas_disponibles)

# Filtrar df por áreas seleccionadas
df_filtered = df_filtered[df_filtered['Nombre_Area'].isin(selected_areas)]

# Filtro por Sede (Plantel)
sedes_disponibles = sorted(df_filtered['Plantel'].dropna().unique().tolist())
selected_sedes = st.sidebar.multiselect("Sede (Plantel)", options=sedes_disponibles, default=[])

if selected_sedes:
    df_filtered = df_filtered[df_filtered['Plantel'].isin(selected_sedes)]

# Filtro por Carrera
carreras_disponibles = sorted(df_filtered['Carrera'].dropna().unique().tolist())
selected_carreras = st.sidebar.multiselect("Carrera", options=carreras_disponibles, default=[])

if selected_carreras:
    df_filtered = df_filtered[df_filtered['Carrera'].isin(selected_carreras)]

# --- CONTENIDO PRINCIPAL ---
st.subheader("Datos Generales")
st.dataframe(
    df_filtered[['Anio', 'Nombre_Area', 'Plantel', 'Carrera', 'Aciertos_minimos', 'Oferta', 'Aspirantes', 'Seleccionados']].sort_values(by=['Anio', 'Aciertos_minimos'], ascending=[False, False]),
    use_container_width=True,
    hide_index=True
)

st.divider()

# --- GRÁFICOS ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Aciertos Mínimos")
    if not df_filtered.empty:
        # Gráfico de barras de aciertos mínimos
        # Creamos una columna combinada para el eje x si hay muchos
        df_filtered['Carrera_Plantel'] = df_filtered['Carrera'] + " - " + df_filtered['Plantel']
        # Convertimos Anio a string para que plotly use colores discretos (categóricos)
        df_filtered['Año_str'] = df_filtered['Anio'].astype(str)
        
        fig_aciertos = px.bar(
            df_filtered, 
            x='Carrera_Plantel', 
            y='Aciertos_minimos', 
            color='Año_str',
            barmode='group',
            labels={'Carrera_Plantel': 'Carrera y Sede', 'Aciertos_minimos': 'Aciertos Mínimos', 'Año_str': 'Año'},
            title="Aciertos Mínimos por Carrera y Sede"
        )
        fig_aciertos.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_aciertos, use_container_width=True)
    else:
        st.info("No hay datos para mostrar con los filtros actuales.")

with col2:
    st.subheader("📊 Aspirantes vs Seleccionados")
    if not df_filtered.empty:
        # Scatter plot o bubble chart
        fig_demanda = px.scatter(
            df_filtered,
            x='Aspirantes',
            y='Seleccionados',
            size='Oferta',
            color='Nombre_Area',
            hover_name='Carrera_Plantel',
            labels={'Aspirantes': 'Número de Aspirantes', 'Seleccionados': 'Número de Seleccionados'},
            title="Relación de Demanda y Admisión (Tamaño = Oferta)"
        )
        st.plotly_chart(fig_demanda, use_container_width=True)
    else:
        st.info("No hay datos para mostrar con los filtros actuales.")

# --- MÉTRICAS DESTACADAS ---
if not df_filtered.empty:
    st.subheader("Resumen de la selección actual")
    m1, m2, m3, m4, m5 = st.columns(5)
    
    max_aciertos = df_filtered['Aciertos_minimos'].max()
    carrera_max = df_filtered[df_filtered['Aciertos_minimos'] == max_aciertos]['Carrera'].iloc[0]
    
    min_aciertos = df_filtered['Aciertos_minimos'].min()
    carrera_min = df_filtered[df_filtered['Aciertos_minimos'] == min_aciertos]['Carrera'].iloc[0]
    
    total_aspirantes = df_filtered['Aspirantes'].sum()
    total_seleccionados = df_filtered['Seleccionados'].sum()
    porcentaje_aceptacion = (total_seleccionados / total_aspirantes) * 100 if total_aspirantes > 0 else 0
    
    m1.metric("Mayor puntaje mínimo", f"{int(max_aciertos)}", carrera_max)
    m2.metric("Menor puntaje mínimo", f"{int(min_aciertos)}", carrera_min)
    m3.metric("Total Aspirantes", f"{int(total_aspirantes):,}")
    m4.metric("Total Seleccionados", f"{int(total_seleccionados):,}")
    m5.metric("% de Aceptación Global", f"{porcentaje_aceptacion:.1f}%")

