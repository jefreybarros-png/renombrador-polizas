import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import re
import io
import zipfile
import unicodedata
from fpdf import FPDF
from datetime import datetime

# --- CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="Logística Master V101", layout="wide")
st.title("🚛 Logística ITA RADIAN: Generador de Paquetes Blindado")

# --- NORMALIZACIÓN ---
def limpiar_texto(txt):
    if not txt: return ""
    txt = str(txt).upper().strip()
    return "".join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')

# --- ORDENAMIENTO DE DIRECCIONES (BARRANQUILLA) ---
VALOR_SUFIJOS = {'A': 0.1, 'B': 0.2, 'C': 0.3, 'D': 0.4, 'E': 0.5, 'BIS': 0.05}

def calcular_peso_direccion(dir_text):
    texto = limpiar_texto(dir_text)
    match = re.search(r'(\d+)\s*(BIS|[A-I])?', texto)
    peso = float(match.group(1)) + VALOR_SUFIJOS.get(match.group(2), 0.0) if match else 0.0
    if "SUR" in texto: peso -= 5000 
    return peso

# --- GENERADOR PDF HORIZONTAL (ESTILO CORPORATIVO) ---
class PDFListado(FPDF):
    def header(self):
        self.set_fill_color(0, 51, 102) # Azul #003366
        self.rect(0, 0, 297, 20, 'F') # Barra superior azul
        self.set_font('Arial', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 5)
        self.cell(0, 10, 'UT ITA RADIAN - CONTROL DE RUTA OPERATIVA', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def crear_pdf_horizontal(df, tecnico, col_map):
    pdf = PDFListado(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"GESTOR: {tecnico} | FECHA: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
    
    # Encabezados
    headers = ['CUENTA', 'MEDIDOR', 'BARRIO', 'DIRECCION', 'CLIENTE']
    widths = [30, 30, 50, 90, 70]
    
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font('Arial', 'B', 9)
    for h, w in zip(headers, widths):
        pdf.cell(w, 8, h, 1, 0, 'C', 1)
    pdf.ln()
    
    # Datos
    pdf.set_font('Arial', '', 8)
    for _, row in df.iterrows():
        for h, w in zip(headers, widths):
            # Buscamos la columna real usando el mapa
            col_real = col_map.get(h, None)
            valor = str(row[col_real])[:50] if col_real and col_real in df.columns else ""
            try:
                valor_encoded = valor.encode('latin-1', 'replace').decode('latin-1')
            except:
                valor_encoded = valor
            pdf.cell(w, 7, valor_encoded, 1, 0, 'L')
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# --- APP PRINCIPAL ---
pdf_file = st.file_uploader("1. Subir PDF (Pólizas)", type="pdf")
excel_file = st.file_uploader("2. Subir Base de Datos", type=["xlsx", "csv"])

if pdf_file and excel_file:
    if st.button("🚀 Generar Paquetes Blindados"):
        # 1. CARGA SEGURA DE EXCEL
        try:
            if excel_file.name.endswith('.csv'):
                df = pd.read_csv(excel_file, sep=None, engine='python', encoding='utf-8-sig')
            else:
                df = pd.read_excel(excel_file)
            
            # Limpieza de encabezados
            cols_orig = df.columns.tolist()
            mapa_cols = {limpiar_texto(c): c for c in cols_orig}
            
            # Buscador de Columnas (Si no existen, se crean por defecto)
            def find_col(keys):
                for k in keys:
                    for clean_c in mapa_cols:
                        if k in clean_c: return mapa_cols[clean_c]
                return None

            col_cta = find_col(['CUENTA', 'POLIZA', 'NRO', 'CONTRATO'])
            col_tec = find_col(['TECNICO', 'GESTOR', 'OPERARIO'])
            col_barrio = find_col(['BARRIO', 'SECTOR', 'ZONA'])
            col_dir = find_col(['DIRECCION', 'DIR', 'UBICACION'])
            
            # Validación Crítica: Cuenta es obligatoria
            if not col_cta:
                st.error("❌ ERROR: No se encontró columna de 'CUENTA' o 'POLIZA'.")
                st.stop()
            
            # REPARACIÓN DE COLUMNAS FALTANTES (Evita el KeyError)
            if not col_tec:
                df['TECNICO_AUTO'] = 'POR_ASIGNAR'
                col_tec = 'TECNICO_AUTO'
                st.warning("⚠️ No se encontró columna TÉCNICO. Se usará 'POR_ASIGNAR'.")
            
            if not col_barrio:
                df['BARRIO_AUTO'] = 'SIN_BARRIO'
                col_barrio = 'BARRIO_AUTO'
            
            # Mapa para el PDF Horizontal
            col_map_pdf = {
                'CUENTA': col_cta,
                'MEDIDOR': find_col(['MEDIDOR', 'APA', 'SERIE']),
                'BARRIO': col_barrio,
                'DIRECCION': col_dir,
                'CLIENTE': find_col(['CLIENTE', 'NOMBRE', 'SUSCRIPTOR'])
            }

        except Exception as e:
            st.error(f"Error leyendo archivo: {e}")
            st.stop()

        # 2. PROCESAMIENTO DE PDF
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        mapa_pdfs = {} # {num_poliza: bytes}
        
        i = 0
        while i < len(doc):
            text = doc[i].get_text()
            match = re.search(r"Póliza\s*No:?\s*(\d+)", text, re.IGNORECASE)
            if match:
                pol_id = match.group(1)
                pages = [i]
                # Unir páginas de recortes
                while i + 1 < len(doc):
                    if "Póliza No" not in doc[i+1].get_text():
                        pages.append(i+1)
                        i += 1
                    else: break
                
                sub_doc = fitz.open()
                for p in pages: sub_doc.insert_pdf(doc, from_page=p, to_page=p)
                mapa_pdfs[pol_id] = sub_doc.tobytes()
                sub_doc.close()
            i += 1
        
        # 3. GENERACIÓN DEL ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            
            # --- BASE TOTAL ---
            if col_dir:
                df['PESO_DIR'] = df[col_dir].astype(str).apply(calcular_peso_direccion)
                df = df.sort_values(by=[col_tec, col_barrio, 'PESO_DIR'], ascending=[True, True, False])
            else:
                df = df.sort_values(by=[col_tec, col_barrio])

            # Guardar Excel Completo
            out_total = io.BytesIO()
            with pd.ExcelWriter(out_total, engine='xlsxwriter') as writer:
                df.drop(columns=['PESO_DIR'] if 'PESO_DIR' in df else []).to_excel(writer, index=False)
            zf.writestr("BASE_GENERAL/Base_Total_Organizada.xlsx", out_total.getvalue())
            
            # Guardar TODOS los PDFs divididos
            for pid, pbytes in mapa_pdfs.items():
                zf.writestr(f"BASE_GENERAL/PDFS_SUELTOS/Poliza_{pid}.pdf", pbytes)

            # --- CARPETAS POR TÉCNICO ---
            for tecnico in df[col_tec].unique():
                tecnico_safe = limpiar_texto(str(tecnico)).replace(" ", "_")
                df_t = df[df[col_tec] == tecnico].copy()
                
                # A. Listado PDF Horizontal (Para firmar)
                pdf_h = crear_pdf_horizontal(df_t, str(tecnico), col_map_pdf)
                zf.writestr(f"TECNICOS/{tecnico_safe}/1_Listado_Firma.pdf", pdf_h)
                
                # B. Excel del Técnico
                out_t = io.BytesIO()
                with pd.ExcelWriter(out_t, engine='xlsxwriter') as writer:
                    df_t.drop(columns=['PESO_DIR'] if 'PESO_DIR' in df_t else []).to_excel(writer, index=False)
                zf.writestr(f"TECNICOS/{tecnico_safe}/2_Base_Digital.xlsx", out_t.getvalue())
                
                # C. Paquete de Impresión (Merge) y Sueltos
                merged = fitz.open()
                found_any = False
                
                for _, row in df_t.iterrows():
                    pol_num = str(row[col_cta])
                    # Buscar PDF (Match flexible)
                    pdf_data = None
                    for k, v in mapa_pdfs.items():
                        if k in pol_num: 
                            pdf_data = v
                            break
                    
                    if pdf_data:
                        found_any = True
                        # Guardar en carpeta Individual
                        zf.writestr(f"TECNICOS/{tecnico_safe}/POLIZAS_INDIVIDUALES/Poliza_{pol_num}.pdf", pdf_data)
                        # Agregar al Merge
                        with fitz.open(stream=pdf_data, filetype="pdf") as tmp:
                            merged.insert_pdf(tmp)
                
                if found_any:
                    zf.writestr(f"TECNICOS/{tecnico_safe}/3_PAQUETE_IMPRESION.pdf", merged.tobytes())
                merged.close()

        st.success("✅ ¡Estructura Completa Generada! Sin errores.")
        st.download_button("⬇️ Descargar Logística Final", zip_buffer.getvalue(), "Logistica_ITA_V101.zip")
