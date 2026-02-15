import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import re
import io
import zipfile
import unicodedata

# --- FUNCIONES DE NORMALIZACIÓN Y LIMPIEZA ---
def normalizar(texto):
    """Elimina tildes, espacios extra y convierte a mayúsculas."""
    if not texto: return ""
    texto = str(texto).upper().strip()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

# --- LÓGICA DE ORDENAMIENTO DE NOMENCLATURA (BARRANQUILLA) ---
VALOR_SUFIJOS = {
    'A': 0.1, 'B': 0.2, 'C': 0.3, 'D': 0.4, 'E': 0.5, 
    'F': 0.6, 'G': 0.7, 'H': 0.8, 'BIS': 0.05
}

def calcular_peso_direccion(dir_text):
    """Convierte direcciones en números comparables para orden descendente."""
    texto = normalizar(dir_text)
    # Extrae el número principal y sufijo (ej: 90B, 45BIS)
    match = re.search(r'(\d+)\s*(BIS|[A-I])?', texto)
    if match:
        numero = float(match.group(1))
        sufijo = match.group(2)
        peso = numero + VALOR_SUFIJOS.get(sufijo, 0.0)
    else:
        peso = 0.0
    
    # El 'SUR' se penaliza para que en orden descendente quede al final del recorrido
    if "SUR" in texto:
        peso -= 5000 
    return peso

# --- CONFIGURACIÓN DE LA APP ---
st.set_page_config(page_title="Logística Pro V89.0 - ITA RADIAN", layout="wide")
st.title("🚛 Sistema Logístico: Unificación, Cruce y Reparto Inteligente")
st.markdown("Organiza actas por **Gestor > Barrio > Dirección (Mayor a Menor)**.")

# --- CARGA DE ARCHIVOS ---
pdf_file = st.file_uploader("1. Subir PDF con Actas y Recortes", type="pdf")
excel_file = st.file_uploader("2. Subir Base de Datos (Excel/CSV)", type=["xlsx", "csv"])

if pdf_file and excel_file:
    if st.button("🚀 Procesar y Generar Ruta Maestra"):
        # 1. Carga y Normalización del Excel
        try:
            df = pd.read_excel(excel_file) if ".xlsx" in excel_file.name else pd.read_csv(excel_file)
            df.columns = [normalizar(c) for c in df.columns]
        except Exception as e:
            st.error(f"Error al leer el Excel: {e}")
            st.stop()

        # 2. Identificación dinámica de columnas
        col_cuenta = next((c for c in df.columns if 'CUENTA' in c), None)
        col_tecnico = next((c for c in df.columns if 'TECNICO' in c or 'OPERARIO' in c), 'TECNICO')
        col_barrio = next((c for c in df.columns if 'BARRIO' in c), 'BARRIO')
        col_dir = next((c for c in df.columns if 'DIRECCION' in c or 'DIR' in c), 'DIRECCION')

        if not col_cuenta:
            st.error(f"❌ No se encontró la columna 'CUENTA'. Columnas detectadas: {list(df.columns)}")
            st.stop()

        # 3. Procesamiento del PDF
        doc_original = fitz.open(stream=pdf_file.read(), filetype="pdf")
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, "w") as zip_final:
            datos_por_gestor = {}
            i = 0
            while i < len(doc_original):
                texto_pag = doc_original[i].get_text()
                # Buscamos 'Póliza No' en el PDF
                match_pol = re.search(r"Póliza\s*No:?\s*(\d+)", texto_pag, re.IGNORECASE)
                
                if match_pol:
                    poliza_pdf = str(match_pol.group(1))
                    paginas_del_doc = [i]
                    
                    # Unificación de recortes/firmas (hojas sin póliza nueva)
                    while i + 1 < len(doc_original):
                        if not re.search(r"Póliza\s*No:?", doc_original[i+1].get_text(), re.IGNORECASE):
                            paginas_del_doc.append(i+1)
                            i += 1
                        else: break
                    
                    # Cruce: Cuenta (Excel) == Póliza (PDF)
                    info_excel = df[df[col_cuenta].astype(str).str.contains(poliza_pdf)]
                    
                    if not info_excel.empty:
                        gestor = normalizar(info_excel.iloc[0].get(col_tecnico, 'SIN_GESTOR')).replace(" ", "_")
                        barrio = normalizar(info_excel.iloc[0].get(col_barrio, 'SIN_BARRIO')).replace(" ", "_")
                        
                        # Crear el PDF unificado (une pág 19 y 20 si es necesario)
                        pdf_unificado = fitz.open()
                        for p in paginas_del_doc:
                            pdf_unificado.insert_pdf(doc_original, from_page=p, to_page=p)
                        
                        # Guardar en ZIP: Carpeta Gestor -> Carpeta Barrio -> Archivo.pdf
                        ruta_archivo_pdf = f"{gestor}/{barrio}/Poliza_{poliza_pdf}.pdf"
                        zip_final.writestr(ruta_archivo_pdf, pdf_unificado.tobytes())
                        pdf_unificado.close()

                        # Guardar para el reporte del gestor
                        if gestor not in datos_por_gestor:
                            datos_por_gestor[gestor] = []
                        datos_por_gestor[gestor].append(info_excel.iloc[0])
                i += 1

            # --- GENERACIÓN DE TABLAS DE REPARTO ORGANIZADAS ---
            for gestor, filas in datos_por_gestor.items():
                df_gestor = pd.DataFrame(filas)
                # Ordenamiento de mayor a menor nomenclatura por barrio
                df_gestor['PESO_ORDEN'] = df_gestor[col_dir].apply(calcular_peso_direccion)
                # Orden: Barrio (A-Z), Dirección (Mayor a Menor)
                df_gestor = df_gestor.sort_values(by=[col_barrio, 'PESO_ORDEN'], ascending=[True, False])

                output_xlsx = io.BytesIO()
                with pd.ExcelWriter(output_xlsx, engine='xlsxwriter') as writer:
                    df_gestor.drop(columns=['PESO_ORDEN']).to_excel(writer, index=False, sheet_name='Hoja_de_Ruta')
                
                # Guardar Excel de reparto en la carpeta principal del gestor
                zip_final.writestr(f"{gestor}/TABLA_REPARTO_{gestor}.xlsx", output_xlsx.getvalue())

        st.success("✅ ¡Ruta Maestra generada con éxito!")
        st.download_button(
            label="⬇️ Descargar ZIP de Logística Final",
            data=zip_buffer.getvalue(),
            file_name="Logistica_ItaRadian_V89.zip",
            mime="application/zip"
        )
        doc_original.close()
