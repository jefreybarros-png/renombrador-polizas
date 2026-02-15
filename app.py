import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import re
import io
import zipfile
import unicodedata

# --- NORMALIZACIÓN RADICAL ---
def limpiar_columna(txt):
    if not txt: return ""
    # Quita tildes, caracteres especiales, espacios y pasa a mayúsculas
    txt = str(txt).upper().strip()
    txt = "".join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^A-Z0-9]', '', txt) # Deja solo letras y números

def limpiar_contenido(txt):
    if not txt: return ""
    txt = str(txt).upper().strip()
    return "".join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')

# --- PESO DE DIRECCIÓN PARA BARRANQUILLA ---
VALOR_SUFIJOS = {'A': 0.1, 'B': 0.2, 'C': 0.3, 'D': 0.4, 'E': 0.5, 'BIS': 0.05}

def calcular_peso_direccion(dir_text):
    texto = limpiar_contenido(dir_text)
    match = re.search(r'(\d+)\s*(BIS|[A-I])?', texto)
    if match:
        peso = float(match.group(1)) + VALOR_SUFIJOS.get(match.group(2), 0.0)
    else:
        peso = 0.0
    if "SUR" in texto: peso -= 5000 
    return peso

st.set_page_config(page_title="Logística Master V91.0", layout="wide")
st.title("🚛 Procesador Inteligente de Rutas - UT ITA RADIAN")

pdf_file = st.file_uploader("1. Subir PDF (Actas/Pólizas)", type="pdf")
excel_file = st.file_uploader("2. Subir Base de Datos (Excel/CSV)", type=["xlsx", "csv"])

if pdf_file and excel_file:
    if st.button("🚀 Ejecutar Proceso Robusto"):
        # --- CARGA CON DETECCIÓN DE FORMATO ---
        try:
            if excel_file.name.endswith('.csv'):
                # Intenta con varios separadores comunes
                df = pd.read_csv(excel_file, sep=None, engine='python', encoding='utf-8-sig')
            else:
                df = pd.read_excel(excel_file)
            
            # Guardamos nombres originales para el reporte, pero creamos un mapa limpio
            columnas_originales = df.columns.tolist()
            mapa_columnas = {limpiar_columna(c): c for c in columnas_originales}
            columnas_limpias = list(mapa_columnas.keys())
            
            # Depuración para el usuario
            with st.expander("Ver columnas detectadas"):
                st.write(columnas_originales)

        except Exception as e:
            st.error(f"Error al leer archivo: {e}")
            st.stop()

        # --- BUSCADOR SEMÁNTICO DE COLUMNAS ---
        def buscar_col(posibles_nombres):
            for p in posibles_nombres:
                for c in columnas_limpias:
                    if p in c: return mapa_columnas[c]
            return None

        col_cuenta = buscar_col(['CUENTA', 'POLIZA', 'NRO', 'CONTRATO'])
        col_tecnico = buscar_col(['TECNICO', 'OPERARIO', 'GESTOR', 'NOMBRE'])
        col_barrio = buscar_col(['BARRIO', 'SECTOR', 'ZONA'])
        col_dir = buscar_col(['DIRECCION', 'DIR', 'UBICACION'])

        if not col_cuenta:
            st.error(f"❌ No se encontró columna similar a 'CUENTA'. Columnas: {columnas_originales}")
            st.stop()

        # --- PROCESAMIENTO ---
        doc_original = fitz.open(stream=pdf_file.read(), filetype="pdf")
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, "w") as zip_final:
            datos_gestores = {}
            i = 0
            while i < len(doc_original):
                texto_pag = doc_original[i].get_text()
                match_pol = re.search(r"Póliza\s*No:?\s*(\d+)", texto_pag, re.IGNORECASE)
                
                if match_pol:
                    poliza_pdf = str(match_pol.group(1))
                    paginas_doc = [i]
                    
                    # Unificación de recortes (pág 19 y 20)
                    while i + 1 < len(doc_original):
                        if "Póliza No" not in doc_original[i+1].get_text():
                            paginas_doc.append(i+1)
                            i += 1
                        else: break
                    
                    # Cruce Account == Policy
                    info = df[df[col_cuenta].astype(str).str.contains(poliza_pdf)]
                    
                    if not info.empty:
                        gestor = limpiar_contenido(info.iloc[0].get(col_tecnico, 'SIN_GESTOR')).replace(" ", "_")
                        barrio = limpiar_contenido(info.iloc[0].get(col_barrio, 'SIN_BARRIO')).replace(" ", "_")
                        
                        pdf_uni = fitz.open()
                        for p in paginas_doc: pdf_uni.insert_pdf(doc_original, from_page=p, to_page=p)
                        
                        ruta_pdf = f"{gestor}/{barrio}/Poliza_{poliza_pdf}.pdf"
                        zip_final.writestr(ruta_pdf, pdf_uni.tobytes())
                        pdf_uni.close()

                        if gestor not in datos_gestores: datos_gestores[gestor] = []
                        datos_gestores[gestor].append(info.iloc[0])
                i += 1

            # --- GENERACIÓN DE TABLAS ORGANIZADAS ---
            for gestor, filas in datos_gestores.items():
                df_gestor = pd.DataFrame(filas)
                df_gestor['PESO_DIR'] = df_gestor[col_dir].apply(calcular_peso_direccion)
                # Ordenar por Barrio y Dirección (Mayor a Menor)
                df_gestor = df_gestor.sort_values(by=[col_barrio, 'PESO_DIR'], ascending=[True, False])

                output_xlsx = io.BytesIO()
                with pd.ExcelWriter(output_xlsx, engine='xlsxwriter') as writer:
                    df_gestor.drop(columns=['PESO_DIR']).to_excel(writer, index=False, sheet_name='Reparto')
                
                zip_final.writestr(f"{gestor}/TABLA_REPARTO_{gestor}.xlsx", output_xlsx.getvalue())

        st.success("✅ ¡Ruta organizada correctamente!")
        st.download_button("⬇️ Descargar ZIP Final", zip_buffer.getvalue(), "Logistica_ItaRadian_V91.zip")
