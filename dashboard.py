import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# Configuración de la página
st.set_page_config(page_title="Resultados UNAM Dashboard", layout="wide", page_icon="🎓")

@st.cache_data
def load_data():
    # Rutas a los archivos (relativas a la ubicación de este script)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path_2025 = os.path.join(base_dir, "resultados_unam_2025_areas_1_a_4", "resultados_unam_2025_todas_las_areas.csv")
    path_2026 = os.path.join(base_dir, "resultados_unam_2026_areas_1_a_4", "resultados_todas_las_areas.csv")
    path_2026_control = os.path.join(base_dir, "resultados_unam_2026_control", "resultados_todas_las_areas.csv")
    
    # Columnas que nos interesan para el resumen
    cols_to_keep = ['Area', 'Carrera', 'Plantel', 'Modalidad', 'Oferta', 'Aspirantes', 'Presentaron_examen', 'Aciertos_minimos', 'Seleccionados']
    
    df_2025 = pd.DataFrame()
    df_2026 = pd.DataFrame()
    df_2026_control = pd.DataFrame()
    
    if os.path.exists(path_2025):
        df_2025 = pd.read_csv(path_2025, usecols=cols_to_keep + ['Anio'])
        df_2025['Anio'] = df_2025['Anio'].astype(str)
        # Dejar solo un registro por carrera/plantel
        df_2025 = df_2025.drop_duplicates()
        
    if os.path.exists(path_2026):
        df_2026 = pd.read_csv(path_2026, usecols=cols_to_keep)
        df_2026['Anio'] = "2026"
        df_2026 = df_2026.drop_duplicates()
        
    if os.path.exists(path_2026_control):
        df_2026_control = pd.read_csv(path_2026_control, usecols=cols_to_keep)
        df_2026_control['Anio'] = "2026 Control"
        df_2026_control = df_2026_control.drop_duplicates()
        
    # Combinar
    df = pd.concat([df_2025, df_2026, df_2026_control], ignore_index=True)
    
    if 'Area' in df.columns:
        mapa_areas = {
            1: "Área 1: Ciencias Físico-Matemáticas y de las Ingenierías",
            2: "Área 2: Ciencias Biológicas, Químicas y de la Salud",
            3: "Área 3: Ciencias Sociales",
            4: "Área 4: Humanidades y de las Artes"
        }
        df['Nombre_Area'] = df['Area'].map(mapa_areas).fillna(df['Area'].astype(str))
    
    return df

@st.cache_data
def load_detailed_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path_2026 = os.path.join(base_dir, "resultados_unam_2026_areas_1_a_4", "resultados_todas_las_areas.csv")
    path_2026_control = os.path.join(base_dir, "resultados_unam_2026_control", "resultados_todas_las_areas.csv")
    
    if not os.path.exists(path_2026) or not os.path.exists(path_2026_control):
        return pd.DataFrame()
        
    cols = ['Numero_comprobante', 'Aciertos', 'Estatus', 'Area', 'Carrera', 'Plantel']
    df_reg = pd.read_csv(path_2026, usecols=cols)
    df_ctrl = pd.read_csv(path_2026_control, usecols=cols)
    
    # Filtrar solo los que presentaron (tienen aciertos numéricos válidos)
    df_reg = df_reg[df_reg['Aciertos'].notna()].copy()
    df_ctrl = df_ctrl[df_ctrl['Aciertos'].notna()].copy()
    
    # Renombrar para hacer merge
    df_reg = df_reg.rename(columns={'Aciertos': 'Aciertos_Regular', 'Estatus': 'Estatus_Regular'})
    df_ctrl = df_ctrl.rename(columns={'Aciertos': 'Aciertos_Control', 'Estatus': 'Estatus_Control'})
    
    # Merge por folio (comprobante)
    df_merged = pd.merge(
        df_reg[['Numero_comprobante', 'Area', 'Carrera', 'Plantel', 'Aciertos_Regular', 'Estatus_Regular']],
        df_ctrl[['Numero_comprobante', 'Aciertos_Control', 'Estatus_Control']],
        on='Numero_comprobante',
        how='inner' # inner join: solo los que hicieron AMBOS examenes
    )
    
    # Calcular diferencia
    df_merged['Diferencia_Aciertos'] = df_merged['Aciertos_Control'] - df_merged['Aciertos_Regular']
    return df_merged

st.title("🎓 Dashboard de Resultados UNAM")

# Cargar datos generales
try:
    df = load_data()
except Exception as e:
    st.error(f"Error al cargar los datos: {e}")
    st.stop()

if df.empty:
    st.warning("No se encontraron datos.")
    st.stop()

tab1, tab2 = st.tabs(["📊 Datos Generales", "🧑‍🎓 Comparativa de Folios (Control vs 2026)"])

with tab1:
    st.markdown("Visualización de aciertos mínimos y datos estadísticos de ingreso por Año, Área, Sede y Carrera.")
    
    st.sidebar.header("Filtros Generales")
    anios_disponibles = sorted(df['Anio'].dropna().unique().tolist())
    selected_anios = st.sidebar.multiselect("Año", options=anios_disponibles, default=anios_disponibles)
    df_filtered = df[df['Anio'].isin(selected_anios)]
    
    areas_disponibles = sorted(df_filtered['Nombre_Area'].dropna().unique().tolist())
    selected_areas = st.sidebar.multiselect("Área", options=areas_disponibles, default=areas_disponibles)
    df_filtered = df_filtered[df_filtered['Nombre_Area'].isin(selected_areas)]
    
    sedes_disponibles = sorted(df_filtered['Plantel'].dropna().unique().tolist())
    selected_sedes = st.sidebar.multiselect("Sede (Plantel)", options=sedes_disponibles, default=[])
    if selected_sedes:
        df_filtered = df_filtered[df_filtered['Plantel'].isin(selected_sedes)]
        
    carreras_disponibles = sorted(df_filtered['Carrera'].dropna().unique().tolist())
    selected_carreras = st.sidebar.multiselect("Carrera", options=carreras_disponibles, default=[])
    if selected_carreras:
        df_filtered = df_filtered[df_filtered['Carrera'].isin(selected_carreras)]
        
    st.subheader("Datos Generales")
    st.dataframe(
        df_filtered[['Anio', 'Nombre_Area', 'Plantel', 'Carrera', 'Aciertos_minimos', 'Oferta', 'Aspirantes', 'Seleccionados']].sort_values(by=['Anio', 'Aciertos_minimos'], ascending=[False, False]),
        use_container_width=True,
        hide_index=True
    )
    
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📈 Aciertos Mínimos")
        if not df_filtered.empty:
            df_filtered['Carrera_Plantel'] = df_filtered['Carrera'] + " - " + df_filtered['Plantel']
            fig_aciertos = px.bar(
                df_filtered, 
                x='Carrera_Plantel', 
                y='Aciertos_minimos', 
                color='Anio',
                barmode='group',
                labels={'Carrera_Plantel': 'Carrera y Sede', 'Aciertos_minimos': 'Aciertos Mínimos', 'Anio': 'Año'},
                title="Aciertos Mínimos por Carrera y Sede"
            )
            fig_aciertos.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_aciertos, use_container_width=True)
        else:
            st.info("No hay datos para mostrar con los filtros actuales.")
            
    with col2:
        st.subheader("📊 Aspirantes vs Seleccionados")
        if not df_filtered.empty:
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

with tab2:
    st.markdown("Análisis comparativo de aspirantes evaluados en ambas modalidades (En Línea vs. Control).")
    df_detalles = load_detailed_data()
    
    if df_detalles.empty:
        st.info("No se encontraron coincidencias de folios (comprobantes) que hayan presentado ambos exámenes o falta generar los datos de control.")
    else:
        # Filtros locales para la pestaña de folios
        carreras_folios = sorted(df_detalles['Carrera'].unique().tolist())
        sel_carreras = st.multiselect("Filtrar por Carrera (Folios)", options=carreras_folios, default=[])
        if sel_carreras:
            df_detalles = df_detalles[df_detalles['Carrera'].isin(sel_carreras)]
            
        st.subheader(f"Total de folios coincidentes: {len(df_detalles)}")
        
        # --- ANÁLISIS POR ESTATUS DE SELECCIÓN ---
        st.markdown("### Resumen por Estatus de Selección")
        
        sel_ctrl = df_detalles['Estatus_Control'] == 'Seleccionada/o'
        nosel_ctrl = df_detalles['Estatus_Control'] == 'No seleccionada/o'
        sel_reg = df_detalles['Estatus_Regular'] == 'Seleccionado'
        nosel_reg = df_detalles['Estatus_Regular'] == 'No seleccionado'
        
        total = len(df_detalles)
        mantuvieron_lugar = len(df_detalles[sel_reg & sel_ctrl])
        perdieron = len(df_detalles[sel_reg & nosel_ctrl])
        ganaron = len(df_detalles[nosel_reg & sel_ctrl])
        siguen_fuera = len(df_detalles[nosel_reg & nosel_ctrl])
        
        c_est1, c_est2, c_est3, c_est4 = st.columns(4)
        c_est1.metric("Siguen Seleccionados", f"{mantuvieron_lugar}", f"{(mantuvieron_lugar/total)*100 if total else 0:.1f}%")
        c_est2.metric("Perdieron Selección", f"{perdieron}", f"{(perdieron/total)*100 if total else 0:.1f}%")
        c_est3.metric("Ganaron Selección", f"{ganaron}", f"{(ganaron/total)*100 if total else 0:.1f}%")
        c_est4.metric("Siguen No Seleccionados", f"{siguen_fuera}", f"{(siguen_fuera/total)*100 if total else 0:.1f}%")
        
        def pct_cambio(df_sub):
            if df_sub.empty: return 0,0,0
            t = len(df_sub)
            return (len(df_sub[df_sub['Diferencia_Aciertos'] > 0])/t)*100, (len(df_sub[df_sub['Diferencia_Aciertos'] < 0])/t)*100, (len(df_sub[df_sub['Diferencia_Aciertos'] == 0])/t)*100
        
        grupo_ambos = df_detalles[sel_reg & sel_ctrl]
        grupo_perdieron = df_detalles[sel_reg & nosel_ctrl]
        
        inc_s, ret_s, man_s = pct_cambio(grupo_ambos)
        inc_n, ret_n, man_n = pct_cambio(grupo_perdieron)
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.info(f"**Seleccionados En Línea y Seleccionados en Control ({len(grupo_ambos)})**\n"
                    f"- 📈 Mejora de puntaje: {inc_s:.1f}%\n"
                    f"- 📉 Disminución de puntaje: {ret_s:.1f}%\n"
                    f"- ➖ Mantuvieron puntaje: {man_s:.1f}%")
        with col_s2:
            st.warning(f"**Seleccionados En Línea y No Seleccionados en Control ({len(grupo_perdieron)})**\n"
                       f"- 📈 Mejora de puntaje: {inc_n:.1f}%\n"
                       f"- 📉 Disminución de puntaje: {ret_n:.1f}%\n"
                       f"- ➖ Mantuvieron puntaje: {man_n:.1f}%")
        
        st.divider()
        
        # Medidas de tendencia central
        mean_reg = df_detalles['Aciertos_Regular'].mean()
        mean_ctrl = df_detalles['Aciertos_Control'].mean()
        median_reg = df_detalles['Aciertos_Regular'].median()
        median_ctrl = df_detalles['Aciertos_Control'].median()
        
        st.markdown("### Medidas de Tendencia Central")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Promedio En Línea 2026", f"{mean_reg:.2f}")
        c2.metric("Promedio Control", f"{mean_ctrl:.2f}", delta=f"{mean_ctrl - mean_reg:.2f}")
        c3.metric("Mediana En Línea 2026", f"{median_reg:.1f}")
        c4.metric("Mediana Control", f"{median_ctrl:.1f}", delta=f"{median_ctrl - median_reg:.1f}")
        
        # Histograma superpuesto
        st.markdown("### Distribución de Puntajes (En Línea vs Control)")
        fig_super = px.histogram(
            df_detalles, 
            x=['Aciertos_Regular', 'Aciertos_Control'], 
            barmode='overlay',
            nbins=40,
            title="Comparativa de Aciertos",
            labels={'value': 'Aciertos', 'variable': 'Examen'},
            color_discrete_map={'Aciertos_Regular': '#1f77b4', 'Aciertos_Control': '#ff7f0e'}
        )
        # Cambiar el nombre de las variables en la leyenda
        newnames = {'Aciertos_Regular': 'En Línea 2026', 'Aciertos_Control': 'Control'}
        fig_super.for_each_trace(lambda t: t.update(name = newnames.get(t.name, t.name)))
        
        fig_super.update_traces(opacity=0.75)
        # Líneas representativas (promedios)
        fig_super.add_vline(x=mean_reg, line_dash="dash", line_color="#1f77b4", annotation_text="Prom. En Línea")
        fig_super.add_vline(x=mean_ctrl, line_dash="dash", line_color="#ff7f0e", annotation_text="Prom. Ctrl")
        st.plotly_chart(fig_super, use_container_width=True)

        st.divider()
        
        # Métricas generales de la comparativa (Mejoras y Diferencias)
        mejoraron = len(df_detalles[df_detalles['Diferencia_Aciertos'] > 0])
        empeoraron = len(df_detalles[df_detalles['Diferencia_Aciertos'] < 0])
        igual = len(df_detalles[df_detalles['Diferencia_Aciertos'] == 0])
        promedio_dif = df_detalles['Diferencia_Aciertos'].mean()
        
        st.markdown("### Evolución de Aspirantes")
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Mejoraron su puntaje", f"{mejoraron} aspirantes")
        col_m2.metric("Empeoraron su puntaje", f"{empeoraron} aspirantes")
        col_m3.metric("Mantuvieron puntaje", f"{igual} aspirantes")
        col_m4.metric("Diferencia Promedio", f"{promedio_dif:.2f} aciertos", delta=f"{promedio_dif:.2f}")
        
        # Gráfica de distribución de diferencias
        st.markdown("### Distribución de la Diferencia de Aciertos")
        fig_hist = px.histogram(
            df_detalles, 
            x="Diferencia_Aciertos", 
            nbins=40,
            title="Histograma de Diferencia (Control - En Línea)",
            labels={'Diferencia_Aciertos': 'Diferencia (Aciertos Control - Aciertos En Línea)'}
        )
        # Añadir línea vertical en 0
        fig_hist.add_vline(x=0, line_dash="dash", line_color="red")
        st.plotly_chart(fig_hist, use_container_width=True)
        
        # 1. Gráfico de Violín
        st.markdown("### Distribución Detallada (Violín y Cajas)")
        df_long = pd.melt(df_detalles, id_vars=['Numero_comprobante', 'Carrera'], 
                          value_vars=['Aciertos_Regular', 'Aciertos_Control'],
                          var_name='Examen', value_name='Aciertos')
        df_long['Examen'] = df_long['Examen'].replace({'Aciertos_Regular': 'En Línea 2026', 'Aciertos_Control': 'Control'})
        fig_violin = px.violin(df_long, x="Examen", y="Aciertos", color="Examen", box=True, points="all",
                               title="Densidad y Distribución de Aciertos",
                               color_discrete_map={'En Línea 2026': '#1f77b4', 'Control': '#ff7f0e'})
        st.plotly_chart(fig_violin, use_container_width=True)

        st.divider()

        # 2. Gráfico de Dispersión
        st.markdown("### Aciertos: En Línea vs Control")
        fig_scatter = px.scatter(
            df_detalles,
            x="Aciertos_Regular",
            y="Aciertos_Control",
            color="Carrera",
            hover_data=["Numero_comprobante", "Plantel"],
            title="Comparativa Puntual de Aciertos",
            labels={'Aciertos_Regular': 'En Línea 2026', 'Aciertos_Control': 'Control'}
        )
        # Línea y=x perfecta correlación
        max_val = max(df_detalles['Aciertos_Regular'].max(), df_detalles['Aciertos_Control'].max()) + 5
        fig_scatter.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val, line=dict(color="red", dash="dash"))
        st.plotly_chart(fig_scatter, use_container_width=True)

        st.divider()

        # 3. Mapa de Calor (Heatmap)
        st.markdown("### Matriz de Transición de Rangos (Heatmap)")
        bins = range(0, 140, 20)
        labels_bins = [f"{i}-{i+19}" for i in bins[:-1]]
        # Categorizar copiando de forma segura
        df_heatmap = df_detalles.copy()
        df_heatmap['Rango_En_Linea'] = pd.cut(df_heatmap['Aciertos_Regular'], bins=bins, labels=labels_bins, right=False)
        df_heatmap['Rango_Control'] = pd.cut(df_heatmap['Aciertos_Control'], bins=bins, labels=labels_bins, right=False)
        heatmap_data = df_heatmap.groupby(['Rango_En_Linea', 'Rango_Control'], observed=False).size().reset_index(name='count')
        heatmap_pivot = heatmap_data.pivot(index='Rango_Control', columns='Rango_En_Linea', values='count').fillna(0)
        
        fig_heatmap = px.imshow(heatmap_pivot, text_auto=True, origin='lower',
                                labels=dict(x="Rango En Línea", y="Rango Control", color="Aspirantes"),
                                title="Transición de Rangos de Aciertos",
                                color_continuous_scale="Blues")
        st.plotly_chart(fig_heatmap, use_container_width=True)

        st.divider()

        # 4. Gráfico de Barras Apiladas (Mejoras/Empeoramiento por Carrera)
        st.markdown("### Proporción de Mejora por Carrera (%)")
        def categorize_diff(diff):
            if diff > 0: return "Mejoraron"
            elif diff < 0: return "Empeoraron"
            else: return "Se mantuvieron"
        
        df_barras = df_detalles.copy()
        df_barras['Evolucion'] = df_barras['Diferencia_Aciertos'].apply(categorize_diff)
        evolucion_carrera = df_barras.groupby(['Carrera', 'Evolucion']).size().reset_index(name='Cantidad')
        
        # Calcular porcentaje
        totales = evolucion_carrera.groupby('Carrera')['Cantidad'].transform('sum')
        evolucion_carrera['Porcentaje'] = ((evolucion_carrera['Cantidad'] / totales) * 100).round(1)
        
        fig_bar = px.bar(evolucion_carrera, x="Carrera", y="Porcentaje", color="Evolucion",
                         title="Evolución de Puntajes por Carrera (%)",
                         color_discrete_map={"Mejoraron": "#2ca02c", "Empeoraron": "#d62728", "Se mantuvieron": "gray"},
                         text=evolucion_carrera['Porcentaje'].apply(lambda x: f"{x:.1f}%"),
                         hover_data={"Cantidad": True, "Porcentaje": False, "Carrera": False, "Evolucion": False})
        fig_bar.update_traces(hovertemplate="<b>%{x}</b><br>Porcentaje: %{text}<br>Aspirantes: %{customdata[0]}<extra></extra>")
        fig_bar.update_layout(barmode='stack', yaxis_title="Porcentaje (%)", xaxis_title="Carrera", bargap=0.3)
        st.plotly_chart(fig_bar, use_container_width=True)
        
        # Tabla detallada
        st.subheader("Tabla Detallada de Aspirantes")
        st.dataframe(
            df_detalles.sort_values(by='Diferencia_Aciertos', ascending=False),
            use_container_width=True,
            hide_index=True
        )
