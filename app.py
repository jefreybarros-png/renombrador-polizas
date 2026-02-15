import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import re
import io
import zipfile

# --- MAPEO DE NOMENCLATURA BARRANQUILLA ---
# Convierte sufijos en valores decimales para ordenamiento natural
VALOR_SUFIJOS = {
    'A': 0.1, 'B': 0.2, 'C': 0.3, 'D': 0.4, 'E': 0.5, 
    'F': 0.6, 'G': 0.7, 'H': 0.8, 'BIS': 0.05  # El BIS va justo después del número base
}

# --- JERARQUÍA DE BARRIOS ---
ZONAS_BARRANQUILLA = {
    'ZONA_1_NORTE': ["ALAMEDA DEL RIO", "VILLA SANTOS", "RIOMAR", "ALTOS DE RIOMAR", "EL TABOR"],
    'ZONA_2_CENTRO': ["GRANADILLO", "CIUDAD JARDIN", "OLAYA", "BOSTON", "EL RECREO"],
    'ZONA_3_SUR': ["LA PAZ", "CARIBE VERDE", "VILLAS DE SAN PABLO", "EL BOSQUE", "CIUDADELA"]
}
MAPA_ZONAS = {barrio: i for i, barrios in enumerate(ZONAS_BARRANQUILLA.values()) for barrio in barrios}

st.set_page_config(page_title="Logística Pro V87.0", layout="wide")
st.title("🚛 Sistema Logístico UT ITA RADIAN - Unificación y Reparto")

pdf_file = st.file_uploader("1. Subir PDF con Actas y Recortes", type="pdf")
excel_file = st.file_uploader("2. Subir Base de Datos Logística (Excel)", type=["xlsx"])

def calcular_peso_nomenclatura(dir_text):
    """Calcula un valor numérico para ordenar de mayor a menor considerando letras, BIS y SUR."""
    texto = str(dir_text).upper()
    # 1. Extraer número principal y posible sufijo (ej: 90, 90B, 45BIS)
    match = re.search(r'(\d+)\s*(BIS|[A-I])?', texto)
    
    if match:
        numero = float(match.group(1))
        sufijo = match.group(2)
        peso = numero + VALOR_SUFIJOS.get(sufijo, 0.0)
    else:
        peso = 0.0

    # 2. Manejo de SUR: Se penaliza para enviarlo al final del orden descendente
    if "SUR" in texto:
        peso -= 5000 
    return peso

if pdf_file and excel_file:
    if st.button("🚀 Procesar, Unificar y Organizar"):
        df = pd.read_excel(excel_file)
        df.columns = df.columns.str.upper().str.strip()
        
        pdf_data = pdf_file.read()
        doc_original = fitz.open(stream=pdf_data, filetype="pdf")
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, "w") as zip_final:
            datos_por_gestor = {}

            # --- ESCANEO Y UNIFICACIÓN DE PÁGINAS ---
            i = 0
            while i < len(doc_original):
                texto_pag = doc_original[i].get_text()
                # Buscamos el patrón Póliza No en el documento [cite: 9, 98, 188]
                match_pol = re.search(r"Póliza\s*No:?\s*(\d+)", texto_pag, re.IGNORECASE)
                
                if match_pol:
                    poliza = str(match_pol.group(1))
                    paginas_del_documento = [i]
                    
                    # Unificación: Si la página siguiente NO tiene número de póliza nuevo,
                    # se asume que es el recorte, firmas o sellos del anterior
                    while i + 1 < len(doc_original):
                        texto_sig = doc_original[i+1].get_text()
                        if not re.search(r"Póliza\s*No:?", texto_sig, re.IGNORECASE):
                            paginas_del_documento.append(i+1)
                            i += 1
                        else:
                            break
                    
                    # Cruce con la base de datos de Excel
                    info_excel = df[df['POLIZA'].astype(str).str.contains(poliza)]
                    if not info_excel.empty:
                        gestor = str(info_excel.iloc[0].get('TECNICO', 'SIN_GESTOR')).replace(" ", "_")
                        
                        # Generar el PDF unificado de la póliza
                        pdf_unificado = fitz.open()
                        for p in paginas_del_documento:
                            pdf_unificado.insert_pdf(doc_original, from_page=p, to_page=p)
                        
                        # Guardar en ZIP dentro de la carpeta del gestor
                        zip_final.writestr(f"{gestor}/POLIZAS/Poliza_{poliza}.pdf", pdf_unificado.tobytes())
                        pdf_unificado.close()

                        # Acumular datos para la tabla de reparto
                        if gestor not in datos_por_gestor:
                            datos_por_gestor[gestor] = []
                        datos_por_gestor[gestor].append(info_excel.iloc[0])
                i += 1

            # --- ORDENAMIENTO GEOGRÁFICO Y NOMENCLATURA ---
            for gestor, filas in datos_por_gestor.items():
                df_gestor = pd.DataFrame(filas)
                
                # Clasificar por zona y calcular peso de dirección
                df_gestor['ORDEN_ZONA'] = df_gestor['BARRIO'].map(MAPA_ZONAS).fillna(99)
                df_gestor['ORDEN_NOMENCLATURA'] = df_gestor['DIRECCION'].apply(calcular_peso_nomenclatura)
                
                # Ordenar: Barrio arriba, Nomenclatura de mayor a menor (descendente)
                df_gestor = df_gestor.sort_values(by=['ORDEN_ZONA', 'ORDEN_NOMENCLATURA'], ascending=[True, False])

                # Crear Excel de reparto limpio
                output_xlsx = io.BytesIO()
                with pd.ExcelWriter(output_xlsx, engine='xlsxwriter') as writer:
                    df_gestor.drop(columns=['ORDEN_ZONA', 'ORDEN_NOMENCLATURA']).to_excel(writer, index=False, sheet_name='Mi_Ruta')
                
                zip_final.writestr(f"{gestor}/TABLA_REPARTO_{gestor}.xlsx", output_xlsx.getvalue())

        st.success("✅ ¡Éxito! Las actas han sido unificadas con sus recortes y organizadas geográficamente.")
        st.download_button("⬇️ Descargar Logística Final V87", zip_buffer.getvalue(), "Ruta_Unificada_Barranquilla.zip")
