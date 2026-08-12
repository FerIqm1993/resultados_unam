# Resultados UNAM

Este proyecto contiene scripts de Python para realizar web scraping y análisis de los resultados del examen de admisión de la Universidad Nacional Autónoma de México (UNAM).

## Descripción

El objetivo de este proyecto es automatizar la extracción de los datos de resultados de admisión para las 4 áreas de estudio de la UNAM, procesarlos y guardarlos estructurados en archivos CSV y Excel para un análisis de datos más sencillo.

### Archivos Principales
- `scraping_unam_2025_todas_areas.py`: Script diseñado para la extracción de resultados correspondientes al proceso de 2025.
- `scraping_unam_2026_todas_areas.py`: Script diseñado para la extracción de resultados del proceso de 2026.
- `scraping_unam_areas.py`: Script base/utilidad para manejar el scraping por áreas.
- `resultados_unam_2026_areas_1_a_4/`: Directorio donde se almacenan los datos estructurados y extraídos.

## Requisitos

El proyecto está desarrollado en Python. Es recomendable usar un entorno virtual. Para que los scripts funcionen correctamente, probablemente necesites instalar algunas librerías comunes de scraping y manejo de datos como:
- `pandas`
- `requests`
- `beautifulsoup4` o `selenium` (dependiendo de la implementación de tu script)

## Ejecución

Para iniciar el proceso de extracción, ejecuta el script correspondiente en tu terminal:

```bash
python scraping_unam_2026_todas_areas.py
```
