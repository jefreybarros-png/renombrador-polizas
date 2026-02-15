###############################################################################
#                                                                             #
#   PLATAFORMA INTEGRAL DE LOGÍSTICA ITA (WEB + GESTIÓN)                      #
#   VERSION: 4.0 (MASTER FULL CODE)                                           #
#   AUTOR: YEFREY                                                             #
#                                                                             #
#   MÓDULOS INCLUIDOS:                                                        #
#   1. CARGA DE MAESTROS Y RUTAS                                              #
#   2. BALANCEO AUTOMÁTICO DE CARGAS                                          #
#   3. AJUSTE MANUAL DE BARRIOS (VISOR DE MOVIMIENTOS)                        #
#   4. GENERACIÓN DE ZIP ADMINISTRATIVO (ESTRUCTURA COMPLETA 4 CARPETAS)      #
#   5. PORTAL WEB PARA TÉCNICOS (SOLO HOJA DE RUTA Y LEGALIZACIÓN)            #
#                                                                             #
###############################################################################

import streamlit as st
import fitz  # Librería PyMuPDF para manejar PDFs
import pandas as pd
import re
import io
import zipfile
import unicodedata
from fpdf import FPDF
from datetime import datetime
import os
import shutil
import time

# =============================================================================
# 1. CONFIGURACIÓN INICIAL DE LA PÁGINA Y ESTILOS VISUALES
# =============================================================================

st.set_page_config(
    page_title="Logística ITA V4.0",
    layout="wide",
    page_icon="🚛",
    initial_sidebar_state="expanded"
)

# Inyectamos CSS para dar apariencia de aplicación profesional
st.markdown("""
    <style>
    /* Fondo general de la aplicación */
    .stApp { 
        background-color: #0E1117; 
        color: #FAFAFA; 
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Estilos para las pestañas (Tabs) */
    .stTabs [data-baseweb="tab-list"] { 
        gap: 8px; 
    }
    .stTabs [data-baseweb="tab"] { 
        height: 55px; 
        background-color: #1F2937; 
        color: white; 
        border-radius: 8px; 
        border: 1px solid #374151; 
        font-weight: 600;
        font-size: 16px;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #2563EB; 
        color: white; 
        border: 2px solid #60A5FA; 
    }
    
    /* Estilos para Dataframes */
    div[data-testid="stDataFrame"] { 
        background-color: #262730; 
        border-radius: 10px; 
        padding: 10px;
    }
    
    /* Botones de Acción Principal (Azules) */
    div.stButton > button:first-child { 
        background-color: #2563EB; 
        color: white; 
        border-radius: 10px; 
        height: 55px; 
        width: 100%; 
        font-size: 18px; 
        font-weight: bold; 
        border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        transition: transform 0.1s;
    }
    div.stButton > button:first-child:active {
        transform: scale(0.98);
    }
    
    /* Botones de Descarga (Verdes) */
    div.stDownloadButton > button:first-child { 
        background-color: #059669; 
        color: white; 
        border-radius: 10px; 
        height: 60px; 
        width: 100%; 
        font-size: 18px; 
        font-weight: bold; 
        border: 1px solid #34D399;
    }
    div.stDownloadButton > button:first-child:hover {
        background-color: #047857;
    }

    /* Encabezados personalizados */
    .header-tecnico {
        font-size: 32px;
        font-weight: 800;
        color: #34D399;
        text-align: center;
        margin-bottom: 20px;
        border-bottom: 2px solid #34D399;
        padding-bottom: 15px;
    }
    
    .status-box {
        padding: 15px;
        border-radius: 10px;
        background-color: #1F2937;
        border-left: 5px solid #2563EB;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. GESTIÓN DEL SISTEMA DE ARCHIVOS (CARPETA PÚBLICA)
# =============================================================================

# Definimos la carpeta donde se alojarán los archivos para la descarga web
CARPETA_PUBLICA = "public_files"

def inicializar_sistema_archivos():
    """Crea la estructura de carpetas necesaria si no existe."""
    if not os.path.exists(CARPETA_PUBLICA):
        os.makedirs(CARPETA_PUBLICA)

def limpiar_carpeta_publica():
    """
    Borra todo el contenido de la carpeta pública para evitar mezclar
    rutas de días anteriores con las nuevas.
    """
    if os.path.exists(CARPETA_PUBLICA):
        try:
            shutil.rmtree(CARPETA_PUBLICA)
            time.sleep(0.5) # Espera técnica para asegurar el borrado
            os.makedirs(CARPETA_PUBLICA)
        except Exception as e:
            st.error(f"Error limpiando sistema de archivos: {e}")
    else:
        os.makedirs(CARPETA_PUBLICA)

# Ejecutamos la inicialización al arrancar
inicializar_sistema_archivos()

# =============================================================================
# 3. FUNCIONES DE LIMPIEZA Y NORMALIZACIÓN DE DATOS
# =============================================================================

def limpiar_estricto(txt):
    """
    Elimina tildes, caracteres especiales y espacios extra.
    Convierte todo a mayúsculas para comparaciones exactas.
    Ejemplo: "San José " -> "SAN JOSE"
    """
    if not txt: return ""
    txt = str(txt).upper().strip()
    # Normalización Unicode para eliminar acentos (NFD separa caracteres de tildes)
    txt = "".join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    return txt

def normalizar_numero(txt):
    """
    Extrae únicamente los dígitos de una cadena.
    Útil para limpiar números de cuenta, póliza o celular.
    Ejemplo: "300-123.45" -> "30012345"
    """
    if not txt: return ""
    # Primero eliminamos el .0 típico de Excel si existe al final
    txt_str = str(txt)
    if txt_str.endswith('.0'):
        txt_str = txt_str[:-2]
    # Usamos regex para dejar solo dígitos
    nums = re.sub(r'\D', '', txt_str)
    return str(int(nums)) if nums else ""

# =============================================================================
# 4. ALGORITMO DE ORDENAMIENTO NATURAL (CORE DEL SISTEMA)
# =============================================================================

def natural_sort_key(txt):
    """
    Genera una clave de ordenamiento que respeta la numeración humana.
    Evita que "Calle 10" aparezca antes que "Calle 2".
    Devuelve una tupla hashable (compatible con Pandas).
    """
    if not txt: return tuple()
    txt = str(txt).upper()
    # Divide el texto en bloques de números y no-números
    return tuple(int(s) if s.isdigit() else s for s in re.split(r'(\d+)', txt))

# =============================================================================
# 5. FUNCIONES DE LÓGICA DE NEGOCIO (BUSQUEDA Y CARGA)
# =============================================================================

def buscar_tecnico_exacto(barrio_input, mapa_barrios):
    """
    Busca el técnico responsable de un barrio usando el mapa cargado.
    Intenta coincidencia exacta, luego sin prefijos, luego parcial.
    """
    if not barrio_input: return "SIN_ASIGNAR"
    
    # 1. Limpieza inicial
    b_raw = limpiar_estricto(str(barrio_input))
    
    # 2. Búsqueda directa
    if b_raw in mapa_barrios: return mapa_barrios[b_raw]
    
    # 3. Búsqueda flexible (quitando palabras comunes)
    patrones_comunes = r'\b(BARRIO|URB|URBANIZACION|SECTOR|ETAPA|VILLA|CIUDADELA)\b'
    b_flex = re.sub(patrones_comunes, '', b_raw).strip()
    if b_flex in mapa_barrios: return mapa_barrios[b_flex]
    
    # 4. Búsqueda inversa (si el barrio del mapa está contenido en el input)
    for k, v in mapa_barrios.items():
        if k in b_raw and len(k) > 4: # Evitar coincidencias muy cortas
            return v
            
    return "SIN_ASIGNAR"

def cargar_maestro_dinamico(file):
    """
    Lee el archivo Excel/CSV de operarios y construye el diccionario
    Barrio -> Técnico.
    """
    mapa = {}
    try:
        # Lectura según extensión
        if file.name.endswith('.csv'): 
            df = pd.read_csv(file, sep=None, engine='python')
        else: 
            df = pd.read_excel(file)
            
        # Normalizar encabezados a mayúsculas
        df.columns = [str(c).upper().strip() for c in df.columns]
        
        # Asumimos estructura: Columna 0 = Barrio, Columna 1 = Técnico
        col_barrio = df.columns[0]
        col_tecnico = df.columns[1]

        for _, row in df.iterrows():
            b = limpiar_estricto(str(row[col_barrio]))
            t = str(row[col_tecnico]).upper().strip()
            
            # Solo guardamos si hay barrio y técnico válido
            if t and t != "NAN" and b: 
                mapa[b] = t
                
    except Exception as e:
        st.error(f"Error leyendo el maestro: {e}")
        
    return mapa

# =============================================================================
# 6. GENERADOR DE PDF (CLASE FPDF PERSONALIZADA)
# =============================================================================

class PDFListado(FPDF):
    def header(self):
        # Cabecera Azul Institucional
        self.set_fill_color(0, 51, 102) 
        self.rect(0, 0, 297, 20, 'F') # Rectángulo ancho completo (A4 Horizontal)
        
        # Título
        self.set_font('Arial', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 5)
        self.cell(0, 10, 'UT ITA RADIAN - HOJA DE RUTA DE OPERACIONES', 0, 1, 'C')
        self.ln(10)

def crear_pdf_lista(df, tecnico, col_map):
    """
    Crea el PDF de la Hoja de Ruta para un técnico específico.
    Retorna los bytes del archivo PDF.
    """
    # Configuración A4 Horizontal
    pdf = PDFListado(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    # Subtítulo con Info del Técnico
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    fecha_hoy = datetime.now().strftime('%d/%m/%Y')
    pdf.cell(0, 10, f"GESTOR: {tecnico} | FECHA: {fecha_hoy} | TOTAL VISITAS: {len(df)}", 0, 1)
    
    # Configuración de Tabla
    headers = ['#', 'CUENTA', 'MEDIDOR', 'BARRIO', 'DIRECCION', 'CLIENTE']
    widths = [10, 25, 25, 65, 85, 60] # Anchos ajustados para que quepa en A4
    
    # Dibujar Encabezados (Gris)
    pdf.set_fill_color(220, 220, 220)
    pdf.set_font('Arial', 'B', 9)
    for h, w in zip(headers, widths): 
        pdf.cell(w, 8, h, 1, 0, 'C', 1)
    pdf.ln()
    
    # Dibujar Filas
    pdf.set_font('Arial', '', 8)
    
    for idx, (_, row) in enumerate(df.iterrows(), start=1):
        # Lógica para resaltar Apoyos en Rojo
        barrio_txt = str(row[col_map['BARRIO']])
        if pd.notna(row.get('ORIGEN_REAL')):
            # Es un apoyo (viene de otro técnico)
            barrio_txt = f"[APOYO] {barrio_txt}"
            pdf.set_text_color(200, 0, 0) # Rojo oscuro
        else:
            pdf.set_text_color(0, 0, 0) # Negro estándar

        # Obtener valores manejando nulos
        def get_val(key):
            col_name = col_map.get(key)
            if col_name and col_name != "NO TIENE":
                return str(row[col_name])
            return ""

        # Preparar fila de datos
        data_row = [
            str(idx), 
            get_val('CUENTA'), 
            get_val('MEDIDOR')[:15], # Recortar si es muy largo
            barrio_txt[:35], 
            get_val('DIRECCION')[:55], 
            get_val('CLIENTE')[:30]
        ]
        
        # Escribir celdas
        for val, w in zip(data_row, widths):
            try: 
                # Intentar codificar a latin-1 para FPDF
                val_enc = val.encode('latin-1', 'replace').decode('latin-1')
            except: 
                val_enc = val # Si falla, dejar original (aunque puede salir raro)
            
            pdf.cell(w, 7, val_enc, 1, 0, 'L')
        pdf.ln()
        
    # Retornar el PDF como string binario
    return pdf.output(dest='S').encode('latin-1')

# =============================================================================
# 7. GESTIÓN DEL ESTADO DE LA SESIÓN (SESSION STATE)
# =============================================================================

# Inicializamos variables para que no se borren al recargar pestañas
if 'mapa_actual' not in st.session_state: st.session_state['mapa_actual'] = {}
if 'df_simulado' not in st.session_state: st.session_state['df_simulado'] = None
if 'col_map_final' not in st.session_state: st.session_state['col_map_final'] = None
if 'mapa_polizas_cargado' not in st.session_state: st.session_state['mapa_polizas_cargado'] = {}
if 'zip_admin_ready' not in st.session_state: st.session_state['zip_admin_ready'] = None

# =============================================================================
# 8. INTERFAZ PRINCIPAL - BARRA LATERAL (SELECCIÓN DE PERFIL)
# =============================================================================

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2942/2942813.png", width=80)
    st.title("SISTEMA LOGÍSTICO")
    st.markdown("---")
    
    # Selector de Modo
    modo_acceso = st.radio(
        "Selecciona tu Perfil:", 
        ["👷 TÉCNICO", "⚙️ ADMINISTRADOR"],
        index=0 # Por defecto Técnico
    )
    
    st.markdown("---")
    st.info("Plataforma ITA v4.0\nGestión Integral de Rutas")

# =============================================================================
# 9. VISTA DEL TÉCNICO (PORTAL DE DESCARGAS)
# =============================================================================

if modo_acceso == "👷 TÉCNICO":
    st.markdown('<div class="header-tecnico">🚛 ZONA DE DESCARGA DE RUTAS</div>', unsafe_allow_html=True)
    st.write("Bienvenido al portal de autogestión. Busca tu nombre para descargar tu programación del día.")
    
    st.markdown("---")
    
    # Verificar si existen carpetas públicas
    if os.path.exists(CARPETA_PUBLICA):
        # Listar carpetas (cada carpeta es un técnico)
        tecnicos_disponibles = sorted([
            d for d in os.listdir(CARPETA_PUBLICA) 
            if os.path.isdir(os.path.join(CARPETA_PUBLICA, d))
        ])
    else:
        tecnicos_disponibles = []
        
    # Lógica de visualización
    if not tecnicos_disponibles:
        st.warning("⏳ Aún no se han publicado las rutas del día.")
        st.info("Por favor espera a que el Coordinador publique la programación.")
        if st.button("🔄 Consultar Nuevamente"):
            st.rerun()
    else:
        # Selector de Técnico
        seleccion_nombre = st.selectbox(
            "👇 SELECCIONA TU NOMBRE AQUÍ:", 
            ["-- Seleccionar --"] + tecnicos_disponibles
        )
        
        if seleccion_nombre != "-- Seleccionar --":
            # Rutas a los archivos
            ruta_carpeta_tec = os.path.join(CARPETA_PUBLICA, seleccion_nombre)
            archivo_hoja_ruta = os.path.join(ruta_carpeta_tec, "1_HOJA_DE_RUTA.pdf")
            archivo_legalizacion = os.path.join(ruta_carpeta_tec, "3_PAQUETE_LEGALIZACION.pdf")
            
            st.markdown("### 📥 Tus Documentos Disponibles:")
            
            col_ruta, col_leg = st.columns(2)
            
            # --- COLUMNA 1: HOJA DE RUTA ---
            with col_ruta:
                st.markdown("""
                <div class="status-box">
                    <h4>📄 1. Hoja de Ruta</h4>
                    <p>Listado de clientes y direcciones.</p>
                </div>
                """, unsafe_allow_html=True)
                
                if os.path.exists(archivo_hoja_ruta):
                    with open(archivo_hoja_ruta, "rb") as f:
                        st.download_button(
                            label="⬇️ DESCARGAR RUTA",
                            data=f,
                            file_name=f"Ruta_{seleccion_nombre}.pdf",
                            mime="application/pdf",
                            key="dl_ruta"
                        )
                else:
                    st.error("Archivo no encontrado.")

            # --- COLUMNA 2: LEGALIZACIÓN ---
            with col_leg:
                st.markdown("""
                <div class="status-box">
                    <h4>📂 2. Paquete Legalización</h4>
                    <p>Pólizas y documentos de soporte.</p>
                </div>
                """, unsafe_allow_html=True)
                
                if os.path.exists(archivo_legalizacion):
                    with open(archivo_legalizacion, "rb") as f:
                        st.download_button(
                            label="⬇️ DESCARGAR LEGALIZACIÓN",
                            data=f,
                            file_name=f"Legalizacion_{seleccion_nombre}.pdf",
                            mime="application/pdf",
                            key="dl_leg"
                        )
                else:
                    st.info("ℹ️ Hoy no tienes pólizas asignadas.")

# =============================================================================
# 10. VISTA DEL ADMINISTRADOR (PANEL DE GESTIÓN COMPLETO)
# =============================================================================

elif modo_acceso == "⚙️ ADMINISTRADOR":
    st.header("⚙️ Panel de Control Logístico")
    
    # Login simple
    password_input = st.text_input("Ingrese Contraseña de Administrador:", type="password")
    
    if password_input == "ita2026": # CONTRASEÑA FIJA
        
        # PESTAÑAS DE TRABAJO
        tab_base, tab_carga, tab_manual, tab_publicar = st.tabs([
            "1. Base Operarios", 
            "2. Carga y Balanceo", 
            "3. Ajuste Manual", 
            "4. Publicar y Descargar"
        ])
        
        # ---------------------------------------------------------
        # PESTAÑA 1: BASE DE OPERARIOS
        # ---------------------------------------------------------
        with tab_base:
            st.subheader("Configuración de Cuadrilla")
            maestro_upload = st.file_uploader("Subir Maestro de Operarios (Excel/CSV)", type=["xlsx", "csv"])
            
            if maestro_upload:
                st.session_state['mapa_actual'] = cargar_maestro_dinamico(maestro_upload)
                st.success(f"✅ Base de datos actualizada: {len(st.session_state['mapa_actual'])} barrios cargados.")
            
            if st.session_state['mapa_actual']:
                num_tecnicos = len(set(st.session_state['mapa_actual'].values()))
                st.info(f"Actualmente hay {num_tecnicos} técnicos configurados en el sistema.")
            else:
                st.warning("⚠️ Carga primero el archivo maestro para continuar.")

        # ---------------------------------------------------------
        # PESTAÑA 2: CARGA Y BALANCEO AUTOMÁTICO
        # ---------------------------------------------------------
        with tab_carga:
            st.subheader("Procesamiento de Archivos Diarios")
            
            col_up1, col_up2 = st.columns(2)
            with col_up1: 
                pdf_polizas_up = st.file_uploader("1. PDF de Pólizas (Opcional)", type="pdf")
            with col_up2: 
                excel_ruta_up = st.file_uploader("2. Excel de Ruta (Obligatorio)", type=["xlsx", "csv"])
            
            # PROCESAR PDF DE PÓLIZAS (EXTRACCIÓN)
            if pdf_polizas_up:
                if st.button("🔄 Escanear Pólizas del PDF"):
                    with st.spinner("Analizando PDF..."):
                        pdf_polizas_up.seek(0)
                        doc_polizas = fitz.open(stream=pdf_polizas_up.read(), filetype="pdf")
                        diccionario_polizas = {}
                        
                        for i in range(len(doc_polizas)):
                            texto_pag = doc_polizas[i].get_text()
                            # Regex flexible para encontrar números de cuenta/poliza
                            matches = re.findall(r'(?:Póliza|Poliza|Cuenta)\D{0,20}(\d{4,15})', texto_pag, re.IGNORECASE)
                            
                            if matches:
                                sub_doc = fitz.open()
                                sub_doc.insert_pdf(doc_polizas, from_page=i, to_page=i)
                                
                                # Revisar si la siguiente página es anexo (no tiene titulo de poliza)
                                if i + 1 < len(doc_polizas):
                                    texto_siguiente = doc_polizas[i+1].get_text()
                                    if not re.search(r'(?:Póliza|Poliza|Cuenta)', texto_siguiente, re.IGNORECASE):
                                        sub_doc.insert_pdf(doc_polizas, from_page=i+1, to_page=i+1)
                                        
                                bytes_poliza = sub_doc.tobytes()
                                sub_doc.close()
                                
                                for m in matches:
                                    diccionario_polizas[normalizar_numero(m)] = bytes_poliza
                                    
                        st.session_state['mapa_polizas_cargado'] = diccionario_polizas
                        st.success(f"✅ Se extrajeron {len(diccionario_polizas)} pólizas correctamente.")

            # PROCESAR EXCEL DE RUTA
            lista_tecnicos_activos = sorted(list(set(st.session_state['mapa_actual'].values())))
            
            if excel_ruta_up and lista_tecnicos_activos:
                try:
                    if excel_ruta_up.name.endswith('.csv'): 
                        df_ruta = pd.read_csv(excel_ruta_up, sep=None, engine='python', encoding='utf-8-sig')
                    else: 
                        df_ruta = pd.read_excel(excel_ruta_up)
                    
                    columnas_excel = list(df_ruta.columns)
                    
                    st.divider()
                    st.markdown("#### Configuración de Parámetros")
                    
                    # Tabla de Cupos
                    df_cupos = pd.DataFrame({"Técnico": lista_tecnicos_activos, "Cupo": [35]*len(lista_tecnicos_activos)})
                    editor_cupos = st.data_editor(
                        df_cupos, 
                        column_config={"Cupo": st.column_config.NumberColumn(min_value=1, max_value=200)}, 
                        hide_index=True,
                        use_container_width=True
                    )
                    LIMITES_CUPOS = dict(zip(editor_cupos["Técnico"], editor_cupos["Cupo"]))
                    
                    # Mapeo de Columnas
                    def buscar_indice(keywords): 
                        for i, c in enumerate(columnas_excel): 
                            for k in keywords: 
                                if k in str(c).upper(): return i
                        return 0
                    
                    mc1, mc2, mc3 = st.columns(3)
                    sel_barrio = mc1.selectbox("Columna BARRIO", columnas_excel, index=buscar_indice(['BARRIO', 'SECTOR']))
                    sel_direcc = mc2.selectbox("Columna DIRECCION", columnas_excel, index=buscar_indice(['DIR', 'DIRECCION']))
                    sel_cuenta = mc3.selectbox("Columna CUENTA", columnas_excel, index=buscar_indice(['CUENTA', 'POLIZA']))
                    sel_medidor = st.selectbox("Columna MEDIDOR", ["NO TIENE"]+columnas_excel, index=buscar_indice(['MEDIDOR'])+1)
                    sel_cliente = st.selectbox("Columna CLIENTE", ["NO TIENE"]+columnas_excel, index=buscar_indice(['CLIENTE', 'NOMBRE'])+1)
                    
                    mapa_columnas = {
                        'BARRIO': sel_barrio, 
                        'DIRECCION': sel_direcc, 
                        'CUENTA': sel_cuenta, 
                        'MEDIDOR': sel_medidor if sel_medidor!="NO TIENE" else None, 
                        'CLIENTE': sel_cliente if sel_cliente!="NO TIENE" else None
                    }
                    
                    if st.button("🚀 EJECUTAR BALANCEO AUTOMÁTICO", type="primary"):
                        with st.spinner("Asignando zonas y balanceando cargas..."):
                            df = df_ruta.copy()
                            
                            # 1. Asignación Inicial
                            df['TECNICO_IDEAL'] = df[sel_barrio].apply(lambda x: buscar_tecnico_exacto(x, st.session_state['mapa_actual']))
                            df['TECNICO_FINAL'] = df['TECNICO_IDEAL']
                            df['ORIGEN_REAL'] = None # Para marcar apoyos
                            
                            # 2. Ordenamiento Natural (Tuplas)
                            df['SORT_KEY'] = df[sel_direcc].astype(str).apply(natural_sort_key)
                            df = df.sort_values(by=[sel_barrio, 'SORT_KEY'])
                            
                            # 3. Algoritmo de Balanceo
                            conteo_actual = df['TECNICO_IDEAL'].value_counts()
                            
                            for tech in [t for t in lista_tecnicos_activos if conteo_actual.get(t, 0) > LIMITES_CUPOS.get(t, 35)]:
                                limite = LIMITES_CUPOS.get(tech, 35)
                                filas_tech = df[df['TECNICO_FINAL'] == tech]
                                excedente = len(filas_tech) - limite
                                
                                if excedente > 0:
                                    # Tomamos los últimos registros (generalmente los más lejanos)
                                    indices_mover = filas_tech.index[-excedente:]
                                    
                                    # Buscar quien tiene menos carga
                                    conteo_live = df['TECNICO_FINAL'].value_counts()
                                    candidato = sorted([t for t in lista_tecnicos_activos if t != tech], key=lambda x: conteo_live.get(x, 0))[0]
                                    
                                    # Reasignar
                                    df.loc[indices_mover, 'TECNICO_FINAL'] = candidato
                                    df.loc[indices_mover, 'ORIGEN_REAL'] = tech # Marca de donde vino
                            
                            # Guardar resultado
                            st.session_state['df_simulado'] = df.drop(columns=['SORT_KEY'])
                            st.session_state['col_map_final'] = mapa_columnas
                            st.success("✅ Balanceo completado. Revisa la pestaña 'Ajuste Manual' si necesitas cambios.")
                            
                except Exception as e:
                    st.error(f"Error procesando archivo: {e}")

        # ---------------------------------------------------------
        # PESTAÑA 3: AJUSTE MANUAL (MÓDULO RECUPERADO)
        # ---------------------------------------------------------
        with tab_manual:
            st.header("🛠️ Ajuste Manual de Asignaciones")
            st.markdown("Mueve barrios completos de un técnico a otro si el balanceo automático no fue preciso.")
            
            if st.session_state['df_simulado'] is not None:
                df_work = st.session_state['df_simulado']
                cols_map = st.session_state['col_map_final']
                col_barrio_work = cols_map['BARRIO']
                tecnicos_en_ruta = sorted(df_work['TECNICO_FINAL'].unique())

                # --- PANEL DE CONTROL DE MOVIMIENTOS ---
                c_origen, c_barrio, c_destino, c_accion = st.columns([1.5, 1.5, 1.5, 1])
                
                with c_origen:
                    origen_sel = st.selectbox("1. Técnico Origen:", ["-"] + list(tecnicos_en_ruta))
                
                with c_barrio:
                    if origen_sel != "-":
                        # Filtrar barrios que tiene ese técnico
                        barrios_tech = df_work[df_work['TECNICO_FINAL'] == origen_sel][col_barrio_work].value_counts()
                        # Formato: "BARRIO (Cantidad)"
                        opciones_barrio = [f"{k} ({v})" for k, v in barrios_tech.items()]
                        barrio_sel = st.selectbox("2. Barrio a Mover:", opciones_barrio)
                    else:
                        barrio_sel = None
                        st.selectbox("2. Barrio a Mover:", ["-"], disabled=True)

                with c_destino:
                    destino_sel = st.selectbox("3. Técnico Destino:", ["-"] + lista_tecnicos_activos)

                with c_accion:
                    st.write("") # Espaciador
                    st.write("") 
                    if st.button("🔄 MOVER BARRIO", type="primary"):
                        if barrio_sel and destino_sel != "-" and origen_sel != "-":
                            # Extraer nombre limpio del barrio (quitar el conteo)
                            nombre_barrio_real = barrio_sel.rsplit(" (", 1)[0]
                            
                            # Aplicar filtro y cambio
                            mascara = (df_work['TECNICO_FINAL'] == origen_sel) & (df_work[col_barrio_work] == nombre_barrio_real)
                            
                            df_work.loc[mascara, 'TECNICO_FINAL'] = destino_sel
                            df_work.loc[mascara, 'ORIGEN_REAL'] = origen_sel # Marcar como Apoyo
                            
                            # Guardar y Recargar
                            st.session_state['df_simulado'] = df_work
                            st.rerun() # Recarga la página para ver cambios

                st.divider()
                st.subheader("📊 Vista Previa de Cargas")
                
                # Visualización de tarjetas
                cols_grid = st.columns(2)
                for idx, tec in enumerate(tecnicos_en_ruta):
                    with cols_grid[idx % 2]:
                        sub_df = df_work[df_work['TECNICO_FINAL'] == tec]
                        
                        # Agrupar por barrio para resumen
                        resumen_barrios = sub_df.groupby([col_barrio_work, 'ORIGEN_REAL'], dropna=False).size().reset_index(name='Visitas')
                        
                        # Marcar apoyos visualmente
                        resumen_barrios['Barrio'] = resumen_barrios.apply(
                            lambda x: f"⚠️ {x[col_barrio_work]} (APOYO)" if pd.notna(x['ORIGEN_REAL']) else x[col_barrio_work], 
                            axis=1
                        )
                        
                        with st.expander(f"👷 **{tec}** | Total: {len(sub_df)} visitas", expanded=True):
                            st.dataframe(resumen_barrios[['Barrio', 'Visitas']], hide_index=True, use_container_width=True)

            else:
                st.info("⚠️ Primero debes cargar y procesar la ruta en la Pestaña 2.")

        # ---------------------------------------------------------
        # PESTAÑA 4: PUBLICACIÓN Y DESCARGAS
        # ---------------------------------------------------------
        with tab_publicar:
            st.header("🌍 Publicación Final")
            
            if st.session_state['df_simulado'] is not None:
                df_final = st.session_state['df_simulado']
                mapa_cols_final = st.session_state['col_map_final']
                polizas_cargadas = st.session_state['mapa_polizas_cargado']
                
                tecnicos_finales = [t for t in df_final['TECNICO_FINAL'].unique() if "SIN_" not in t]
                
                st.markdown("### 1. Publicar en Portal Web")
                st.info("Esto generará los PDFs y los pondrá disponibles para que los técnicos descarguen.")
                
                if st.button("📢 PUBLICAR RUTAS EN WEB", type="primary"):
                    limpiar_carpeta_publica()
                    barra_progreso = st.progress(0)
                    
                    for i, tec in enumerate(tecnicos_finales):
                        # Filtrar datos del técnico
                        df_t = df_final[df_final['TECNICO_FINAL'] == tec].copy()
                        
                        # RE-ORDENAMIENTO FINAL (Seguridad)
                        df_t['SORT_TEMP'] = df_t[mapa_cols_final['DIRECCION']].astype(str).apply(natural_sort_key)
                        df_t = df_t.sort_values(by=[mapa_cols_final['BARRIO'], 'SORT_TEMP']).drop(columns=['SORT_TEMP'])
                        
                        # Crear carpeta segura
                        nombre_seguro = str(tec).replace(" ", "_")
                        ruta_carpeta_tec = os.path.join(CARPETA_PUBLICA, nombre_seguro)
                        os.makedirs(ruta_carpeta_tec, exist_ok=True)
                        
                        # 1. GENERAR HOJA DE RUTA
                        bytes_hoja = crear_pdf_lista(df_t, tec, mapa_cols_final)
                        with open(os.path.join(ruta_carpeta_tec, "1_HOJA_DE_RUTA.pdf"), "wb") as f:
                            f.write(bytes_hoja)
                        
                        # 2. GENERAR PAQUETE LEGALIZACIÓN (MERGE PÓLIZAS)
                        merger = fitz.open()
                        count_pols = 0
                        for _, row in df_t.iterrows():
                            cta = normalizar_numero(str(row[mapa_cols_final['CUENTA']]))
                            if cta in polizas_cargadas:
                                with fitz.open(stream=polizas_cargadas[cta], filetype="pdf") as tmp:
                                    merger.insert_pdf(tmp)
                                count_pols += 1
                        
                        if count_pols > 0:
                            with open(os.path.join(ruta_carpeta_tec, "3_PAQUETE_LEGALIZACION.pdf"), "wb") as f:
                                f.write(merger.tobytes())
                        merger.close()
                        
                        barra_progreso.progress((i + 1) / len(tecnicos_finales))
                        
                    st.success(f"✅ ¡Publicación Exitosa! {len(tecnicos_finales)} técnicos habilitados.")
                    st.balloons()

                st.divider()
                st.markdown("### 2. Descarga Administrativa (ZIP Completo)")
                st.caption("Descarga el paquete completo con las 4 carpetas (Hoja, Tabla, Legalización, Pólizas).")
                
                if st.button("📦 GENERAR ZIP MAESTRO"):
                    with st.spinner("Compilando estructura completa..."):
                        zip_memoria = io.BytesIO()
                        
                        with zipfile.ZipFile(zip_memoria, "w") as zf:
                            # Iterar por técnico
                            for tec in tecnicos_finales:
                                safe_name = str(tec).replace(" ", "_")
                                df_t = df_final[df_final['TECNICO_FINAL'] == tec].copy()
                                
                                # Ordenar
                                df_t['SORT_TEMP'] = df_t[mapa_cols_final['DIRECCION']].astype(str).apply(natural_sort_key)
                                df_t = df_t.sort_values(by=[mapa_cols_final['BARRIO'], 'SORT_TEMP']).drop(columns=['SORT_TEMP'])
                                
                                # 1_HOJA_DE_RUTA
                                pdf_ruta = crear_pdf_lista(df_t, tec, mapa_cols_final)
                                zf.writestr(f"{safe_name}/1_HOJA_DE_RUTA.pdf", pdf_ruta)
                                
                                # 2_TABLA_DIGITAL
                                excel_buffer = io.BytesIO()
                                with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                                    df_t.to_excel(writer, index=False)
                                zf.writestr(f"{safe_name}/2_TABLA_DIGITAL.xlsx", excel_buffer.getvalue())
                                
                                # 3_PAQUETE Y 4_POLIZAS
                                merger = fitz.open()
                                count_p = 0
                                for _, row in df_t.iterrows():
                                    cta = normalizar_numero(str(row[mapa_cols_final['CUENTA']]))
                                    if cta in polizas_cargadas:
                                        # Guardar Individual en carpeta 4
                                        zf.writestr(f"{safe_name}/4_POLIZAS_INDIVIDUALES/{cta}.pdf", polizas_cargadas[cta])
                                        # Agregar al merge de carpeta 3
                                        with fitz.open(stream=polizas_cargadas[cta], filetype="pdf") as tmp:
                                            merger.insert_pdf(tmp)
                                        count_p += 1
                                
                                if count_p > 0:
                                    zf.writestr(f"{safe_name}/3_PAQUETE_LEGALIZACION.pdf", merger.tobytes())
                                merger.close()
                                
                            # Archivo General
                            excel_total = io.BytesIO()
                            with pd.ExcelWriter(excel_total, engine='xlsxwriter') as w: df_final.to_excel(w, index=False)
                            zf.writestr("00_CONSOLIDADO_GENERAL.xlsx", excel_total.getvalue())

                        st.session_state['zip_admin_ready'] = zip_memoria.getvalue()
                        st.success("ZIP Generado correctamente.")

                if st.session_state['zip_admin_ready']:
                    st.download_button(
                        label="⬇️ DESCARGAR ZIP ADMINISTRATIVO",
                        data=st.session_state['zip_admin_ready'],
                        file_name="Logistica_Completa_ITA.zip",
                        mime="application/zip"
                    )
            else:
                st.info("Procesa la ruta primero.")

    elif password_input:
        st.error("❌ Contraseña Incorrecta")
