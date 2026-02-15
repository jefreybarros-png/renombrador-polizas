import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import re
import io
import zipfile
import unicodedata
from fpdf import FPDF
from datetime import datetime

# --- CONFIGURACIÓN DE LA APP ---
st.set_page_config(page_title="Logística Exacta V106", layout="wide")
st.title("🚛 Logística ITA RADIAN: Asignación Exacta por Listado")

# --- PANEL DE CONTROL LATERAL ---
st.sidebar.header("🎛️ Configuración de Despacho")
MAX_CUPO = st.sidebar.number_input("📋 Tope de tareas por técnico", value=35, min_value=1)

st.sidebar.subheader("👷 Gestión de Técnicos")
st.sidebar.info("Marca los técnicos que están TRABAJANDO hoy. El sistema reasignará las tareas de los ausentes o llenos a su vecino más cercano.")

# Definimos los técnicos basados en tu archivo (1 al 8 aprox)
OPCIONES_TECNICOS = [f"TECNICO {i}" for i in range(1, 10)]
TECNICOS_ACTIVOS = []
for tec in OPCIONES_TECNICOS:
    if st.sidebar.checkbox(tec, value=True):
        TECNICOS_ACTIVOS.append(tec)

# --- MAPA DE VECINDAD (AJUSTADO A TU LISTADO) ---
# Define quién apoya a quién según la zona geográfica de Barranquilla
VECINOS_LOGICOS = {
    "TECNICO 1": ["TECNICO 6", "TECNICO 7", "TECNICO 2"], # Suroriente -> Suroccidente o Murillo
    "TECNICO 2": ["TECNICO 4", "TECNICO 3", "TECNICO 1"], # Centro/San Felipe -> Prado o Silencio
    "TECNICO 3": ["TECNICO 2", "TECNICO 4", "TECNICO 5"], # Silencio -> San Felipe o Bosque
    "TECNICO 4": ["TECNICO 2", "TECNICO 3", "TECNICO 8"], # Prado -> Centro o Norte
    "TECNICO 5": ["TECNICO 6", "TECNICO 3", "TECNICO 7"], # Bosque -> Suroccidente o Silencio
    "TECNICO 6": ["TECNICO 5", "TECNICO 1", "TECNICO 7"], # Suroccidente (Caribe Verde) -> Bosque
    "TECNICO 7": ["TECNICO 1", "TECNICO 6", "TECNICO 5"], # Murillo -> Suroriente
    "TECNICO 8": ["TECNICO 2", "TECNICO 4", "TECNICO 3"], # Flores -> Norte/Prado
}

# --- FUNCIONES DE LIMPIEZA ---
def limpiar_texto(txt):
    if not txt: return ""
    txt = str(txt).upper().strip()
    return "".join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')

# --- ORDENAMIENTO NOMENCLATURA ---
VALOR_SUFIJOS = {'A': 0.1, 'B': 0.2, 'C': 0.3, 'D': 0.4, 'E': 0.5, 'BIS': 0.05}
def calcular_peso_direccion(dir_text):
    texto = limpiar_texto(dir_text)
    match = re.search(r'(\d+)\s*(BIS|[A-I])?', texto)
    peso = float(match.group(1)) + VALOR_SUFIJOS.get(match.group(2), 0.0) if match else 0.0
    if "SUR" in texto: peso -= 5000 
    return peso

# --- GENERADOR PDF HORIZONTAL ---
class PDFListado(FPDF):
    def header(self):
        self.set_fill_color(0, 51, 102) 
        self.rect(0, 0, 297, 20, 'F')
        self.set_font('Arial', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 5)
        self.cell(0, 10, 'UT ITA RADIAN - HOJA DE RUTA', 0, 1, 'C')
        self.ln(10)

def crear_pdf_horizontal(df, tecnico, col_map):
    pdf = PDFListado(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"GESTOR: {tecnico} | FECHA: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
    
    headers = ['CUENTA', 'MEDIDOR', 'BARRIO', 'DIRECCION', 'CLIENTE']
    widths = [30, 30, 60, 90, 60]
    
    pdf.set_fill_color(220, 220, 220)
    pdf.set_font('Arial', 'B', 10)
    for h, w in zip(headers, widths):
        pdf.cell(w, 8, h, 1, 0, 'C', 1)
    pdf.ln()
    
    pdf.set_font('Arial', '', 9)
    for _, row in df.iterrows():
        for h, w in zip(headers, widths):
            col_real = col_map.get(h)
            valor = str(row[col_real])[:45] if col_real else ""
            try: val_enc = valor.encode('latin-1', 'replace').decode('latin-1')
            except: val_enc = valor
            pdf.cell(w, 8, val_enc, 1, 0, 'L')
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFAZ DE CARGA ---
col1, col2, col3 = st.columns(3)
with col1: pdf_file = st.file_uploader("1. PDF (Pólizas)", type="pdf")
with col2: excel_file = st.file_uploader("2. Base Operativa (Cuentas)", type=["xlsx", "csv"])
with col3: maestro_file = st.file_uploader("3. Listado Barrios (Tu Excel)", type=["xlsx", "csv"])

if pdf_file and excel_file and maestro_file:
    if st.button("🚀 Ejecutar Asignación Exacta"):
        try:
            # 1. CARGAR MAESTRO DE BARRIOS (CEREBRO DINÁMICO)
            if maestro_file.name.endswith('.csv'):
                df_maestro = pd.read_csv(maestro_file, sep=None, engine='python', encoding='utf-8-sig')
            else:
                df_maestro = pd.read_excel(maestro_file)
            
            # Crear diccionario {BARRIO: TECNICO} exacto
            # Asumimos que columna 0 es Barrio y columna 1 es Tecnico
            MAPA_EXACTO = {}
            for _, row in df_maestro.iterrows():
                b = limpiar_texto(str(row.iloc[0]))
                t = limpiar_texto(str(row.iloc[1]))
                MAPA_EXACTO[b] = t
            
            st.success(f"✅ Cerebro cargado con {len(MAPA_EXACTO)} barrios exactos.")

            # 2. CARGAR BASE OPERATIVA
            if excel_file.name.endswith('.csv'):
                df = pd.read_csv(excel_file, sep=None, engine='python', encoding='utf-8-sig')
            else:
                df = pd.read_excel(excel_file)
            df.columns = [limpiar_texto(c) for c in df.columns]

            # Detectar columnas
            def find_col(k_list):
                for k in k_list:
                    for c in df.columns:
                        if k in c: return c
                return None
            col_cta = find_col(['CUENTA', 'POLIZA', 'NRO'])
            col_barrio = find_col(['BARRIO', 'SECTOR', 'ZONA'])
            col_dir = find_col(['DIRECCION', 'DIR'])

            if not col_cta or not col_barrio:
                st.error("Faltan columnas clave en la Base Operativa.")
                st.stop()

            # 3. ASIGNACIÓN INICIAL EXACTA
            def get_tecnico_maestro(row):
                barrio_orden = limpiar_texto(str(row[col_barrio]))
                # Búsqueda exacta
                if barrio_orden in MAPA_EXACTO: return MAPA_EXACTO[barrio_orden]
                # Búsqueda parcial (ej: "LOS OLIVOS" en "OLIVOS")
                for b_key, t_val in MAPA_EXACTO.items():
                    if b_key in barrio_orden: return t_val
                return "SIN_ASIGNAR"
            
            df['TECNICO_IDEAL'] = df.apply(get_tecnico_maestro, axis=1)

            # 4. ALGORITMO DE BALANCEO (Max Cupo + Vecindad)
            conteo = {t: 0 for t in TECNICOS_ACTIVOS}
            asignacion_final = []

            # Ordenamos por Tecnico Ideal y luego Barrio para llenar en orden
            df = df.sort_values(by=['TECNICO_IDEAL', col_barrio])

            for _, row in df.iterrows():
                ideal = row['TECNICO_IDEAL']
                asignado = "SIN_ASIGNAR"

                # Lógica de despacho
                if ideal in TECNICOS_ACTIVOS:
                    if conteo[ideal] < MAX_CUPO:
                        asignado = ideal
                        conteo[ideal] += 1
                    else:
                        # Lleno -> Buscar vecino
                        vecinos = VECINOS_LOGICOS.get(ideal, [])
                        encontrado = False
                        for v in vecinos:
                            if v in TECNICOS_ACTIVOS and conteo[v] < MAX_CUPO:
                                asignado = f"{v} (APOYO)"
                                conteo[v] += 1
                                encontrado = True
                                break
                        if not encontrado: asignado = f"{ideal} (EXTRA)"
                
                elif "TECNICO" in ideal: # El ideal existe pero NO vino hoy
                    vecinos = VECINOS_LOGICOS.get(ideal, [])
                    encontrado = False
                    for v in vecinos:
                        if v in TECNICOS_ACTIVOS and conteo[v] < MAX_CUPO:
                            asignado = f"{v} (COBERTURA)"
                            conteo[v] += 1
                            encontrado = True
                            break
                    if not encontrado: asignado = "SIN_GESTOR_ACTIVO"
                
                else:
                    asignado = "ZONA_DESCONOCIDA" # Barrio no estaba en tu Excel

                asignacion_final.append(asignado)
            
            df['TECNICO_REAL'] = asignacion_final
            df['CARPETA'] = df['TECNICO_REAL'].apply(lambda x: x.split(" (")[0]) # Limpiar nombre

            # Mapa PDF
            col_map = {
                'CUENTA': col_cta, 'MEDIDOR': find_col(['MEDIDOR']), 'BARRIO': col_barrio,
                'DIRECCION': col_dir, 'CLIENTE': find_col(['CLIENTE', 'NOMBRE'])
            }

            # 5. PROCESAR PDF
            doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
            mapa_pdfs = {}
            i = 0
            while i < len(doc):
                text = doc[i].get_text()
                match = re.search(r"Póliza\s*No:?\s*(\d+)", text, re.IGNORECASE)
                if match:
                    pid = match.group(1)
                    pages = [i]
                    while i+1 < len(doc):
                        if "Póliza No" not in doc[i+1].get_text(): pages.append(i+1); i+=1
                        else: break
                    sub = fitz.open()
                    for p in pages: sub.insert_pdf(doc, from_page=p, to_page=p)
                    mapa_pdfs[pid] = sub.tobytes()
                    sub.close()
                i += 1
            
            # 6. GENERAR ZIP
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                # Base Total
                out_tot = io.BytesIO()
                with pd.ExcelWriter(out_tot, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False)
                zf.writestr("0_CONSOLIDADO.xlsx", out_tot.getvalue())

                # Carpetas Técnicos
                for tec in df['CARPETA'].unique():
                    if "SIN_" in tec or "ZONA_" in tec: continue
                    safe_tec = limpiar_texto(tec).replace(" ", "_")
                    df_t = df[df['CARPETA'] == tec].copy()
                    
                    # Ordenar por Dirección (Barranquilla)
                    if col_dir:
                        df_t['PESO'] = df_t[col_dir].astype(str).apply(calcular_peso_direccion)
                        df_t = df_t.sort_values(by=[col_barrio, 'PESO'], ascending=[True, False])

                    # a. PDF Firma
                    pdf_h = crear_pdf_horizontal(df_t, tec, col_map)
                    zf.writestr(f"{safe_tec}/1_LISTADO.pdf", pdf_h)

                    # b. Excel
                    out_t = io.BytesIO()
                    with pd.ExcelWriter(out_t, engine='xlsxwriter') as writer:
                        df_t.drop(columns=['PESO'] if 'PESO' in df_t else []).to_excel(writer, index=False)
                    zf.writestr(f"{safe_tec}/2_DIGITAL.xlsx", out_t.getvalue())

                    # c. Impresión
                    merge = fitz.open()
                    found = False
                    for _, row in df_t.iterrows():
                        cta = str(row[col_cta])
                        pdf_data = None
                        for k, v in mapa_pdfs.items():
                            if k in cta: pdf_data = v; break
                        if pdf_data:
                            found = True
                            zf.writestr(f"{safe_tec}/POLIZAS/Poliza_{cta}.pdf", pdf_data)
                            with fitz.open(stream=pdf_data, filetype="pdf") as tmp: merge.insert_pdf(tmp)
                    if found:
                        zf.writestr(f"{safe_tec}/3_IMPRESION.pdf", merge.tobytes())
                    merge.close()

            st.success("✅ ¡Despacho Completado!")
            
            # 7. ESTADÍSTICAS
            st.write("📊 **Balance de Cargas:**")
            st.bar_chart(df['TECNICO_REAL'].value_counts())
            
            st.download_button("⬇️ Descargar Paquete", zip_buffer.getvalue(), "Logistica_Final.zip")

        except Exception as e:
            st.error(f"Error: {e}")
