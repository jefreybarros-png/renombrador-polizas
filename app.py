#################################################################################
#                                                                               #
#   SISTEMA DE GESTIÓN LOGÍSTICA ITA - PLATAFORMA INTEGRAL (WEB + GESTIÓN)      #
#   VERSIÓN: 7.0 PLATINUM (BLINDAJE TOTAL DE ROLES Y DINAMISMO)                 #
#   AUTOR: YEFREY                                                               #
#                                                                               #
#   ARQUITECTURA DE SEGURIDAD:                                                  #
#   1.  El sistema inicia "Agnóstico" (Sin saber nombres de técnicos).          #
#   2.  Al cargar el MAESTRO, el sistema aprende los nombres automáticamente.   #
#   3.  El Panel de Asistencia (Sidebar) solo aparece si hay datos cargados.    #
#   4.  Los Técnicos tienen "Ceguera Total" sobre el panel administrativo.      #
#   5.  Mantiene intactas todas las lógicas de ZIP, PDF y Ordenamiento.         #
#                                                                               #
#################################################################################

import streamlit as st
import fitz  # Librería PyMuPDF para manipulación de PDFs complejos
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
import base64

# ===============================================================================
# SECCIÓN 1: CONFIGURACIÓN VISUAL Y DE SEGURIDAD (CSS AVANZADO)
# ===============================================================================

st.set_page_config(
    page_title="Logística ITA | v7.0 Platinum",
    layout="wide",
    page_icon="🚛",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "Sistema Logístico ITA - Versión 7.0 Platinum Blindada"
    }
)

# INYECCIÓN DE CSS PARA INTERFAZ PREMIUM Y OCULTAMIENTO DE ELEMENTOS NATIVOS
st.markdown("""
    <style>
    /* 1. ESTÉTICA GENERAL (FONDO Y FUENTES) */
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');
    
    .stApp { 
        background-color: #0F172A; /* Azul Oscuro Profundo (Slate 900) */
        color: #F1F5F9; /* Texto Claro (Slate 100) */
        font-family: 'Roboto', sans-serif;
    }
    
    /* 2. BARRA LATERAL (SIDEBAR) PERSONALIZADA */
    section[data-testid="stSidebar"] {
        background-color: #1E293B; /* Slate 800 */
        border-right: 1px solid #334155;
    }
    
    /* 3. PESTAÑAS (TABS) ESTILIZADAS */
    .stTabs [data-baseweb="tab-list"] { 
        gap: 10px; 
        background-color: #1E293B;
        padding: 10px 10px 0px 10px;
        border-radius: 12px 12px 0 0;
    }
    .stTabs [data-baseweb="tab"] { 
        height: 55px; 
        background-color: transparent; 
        color: #94A3B8; 
        border: none;
        font-weight: 600;
        font-size: 16px;
        transition: color 0.3s;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #3B82F6; /* Azul Brillante */
        color: white; 
        border-radius: 8px 8px 0 0;
    }
    
    /* 4. BOTONES DE ACCIÓN (GRADIENTES) */
    div.stButton > button:first-child { 
        background: linear-gradient(90deg, #2563EB 0%, #3B82F6 100%);
        color: white; 
        border-radius: 8px; 
        height: 55px; 
        width: 100%; 
        font-size: 18px; 
        font-weight: 700; 
        border: none;
        box-shadow: 0 4px 10px rgba(37, 99, 235, 0.3);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    div.stButton > button:first-child:hover { 
        background: linear-gradient(90deg, #1D4ED8 0%, #2563EB 100%);
        box-shadow: 0 6px 15px rgba(37, 99, 235, 0.5);
        transform: translateY(-2px);
    }
    
    /* 5. BOTONES DE DESCARGA (VERDES) */
    div.stDownloadButton > button:first-child { 
        background: linear-gradient(90deg, #059669 0%, #10B981 100%);
        color: white; 
        border-radius: 8px; 
        height: 60px; 
        width: 100%; 
        font-size: 18px; 
        font-weight: 700; 
        border: 1px solid #047857;
        box-shadow: 0 4px 10px rgba(16, 185, 129, 0.2);
    }
    div.stDownloadButton > button:first-child:hover { 
        background: linear-gradient(90deg, #047857 0%, #059669 100%);
    }

    /* 6. LOGOTIPO Y ENCABEZADOS */
    .logo-box {
        text-align: center;
        padding: 20px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        margin-bottom: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .logo-img {
        max-width: 120px;
        filter: drop-shadow(0 0 10px rgba(56, 189, 248, 0.6));
    }
    
    .tech-header {
        font-size: 2.5rem;
        font-weight: 800;
        text-align: center;
        background: -webkit-linear-gradient(0deg, #34D399, #38BDF8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1.5rem;
    }

    /* 7. TARJETAS DE INFORMACIÓN */
    .info-card {
        background-color: #1E293B;
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #3B82F6;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 15px;
    }
    .info-card h4 { margin: 0; color: #60A5FA; font-size: 1.1rem; }
    .info-card p { margin: 5px 0 0 0; color: #CBD5E1; font-size: 0.9rem; }
    
    /* 8. ALERTA DE INACTIVIDAD */
    .inactive-warning {
        background-color: #450a0a;
        color: #fca5a5;
        padding: 10px;
        border-radius: 8px;
        border: 1px solid #7f1d1d;
        font-size: 0.85rem;
        text-align: center;
        margin-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# ===============================================================================
# SECCIÓN 2: GESTIÓN DE ARCHIVOS Y DIRECTORIOS (PERSISTENCIA)
# ===============================================================================

CARPETA_PUBLICA = "public_files"

def gestionar_directorio_publico(accion="iniciar"):
    """
    Controlador robusto del sistema de archivos para la web.
    Garantiza que la carpeta exista y esté limpia para evitar colisiones.
    """
    if accion == "iniciar":
        if not os.path.exists(CARPETA_PUBLICA):
            try:
                os.makedirs(CARPETA_PUBLICA)
            except OSError as e:
                st.error(f"Error crítico de sistema de archivos: {e}")
                
    elif accion == "limpiar":
        # Borrado seguro con reintento por si Windows/Linux bloquea el archivo
        if os.path.exists(CARPETA_PUBLICA):
            try:
                shutil.rmtree(CARPETA_PUBLICA)
                time.sleep(0.1) # Pequeña pausa técnica
                os.makedirs(CARPETA_PUBLICA)
            except Exception as e:
                # Si falla borrar la carpeta raíz, intentamos borrar el contenido
                try:
                    for filename in os.listdir(CARPETA_PUBLICA):
                        file_path = os.path.join(CARPETA_PUBLICA, filename)
                        if os.path.isfile(file_path): os.unlink(file_path)
                        elif os.path.isdir(file_path): shutil.rmtree(file_path)
                except:
                    pass # Si falla, seguimos (no bloqueante)
        else:
            os.makedirs(CARPETA_PUBLICA)

# Inicializamos al arrancar
gestionar_directorio_publico("iniciar")

# ===============================================================================
# SECCIÓN 3: BIBLIOTECA DE FUNCIONES DE UTILIDAD (CORE)
# ===============================================================================

def limpiar_estricto(txt):
    """
    Normalización de texto para búsquedas exactas.
    Elimina tildes, espacios y convierte a mayúsculas.
    """
    if not txt: return ""
    txt = str(txt).upper().strip()
    txt = "".join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    return txt

def normalizar_numero(txt):
    """
    Limpia números de póliza/cuenta/celular.
    Maneja el formato decimal de Excel (123.0 -> 123).
    """
    if not txt: return ""
    txt_str = str(txt)
    if txt_str.endswith('.0'): txt_str = txt_str[:-2]
    nums = re.sub(r'\D', '', txt_str)
    return str(int(nums)) if nums else ""

def natural_sort_key(txt):
    """
    Algoritmo de ordenamiento humano (Natural Sort).
    Clave para que las direcciones se ordenen lógicamente (Calle 2 antes que Calle 10).
    """
    if not txt: return tuple()
    txt = str(txt).upper()
    return tuple(int(s) if s.isdigit() else s for s in re.split(r'(\d+)', txt))

# ===============================================================================
# SECCIÓN 4: LÓGICA DE NEGOCIO (CARGA, BÚSQUEDA Y PDF)
# ===============================================================================

def buscar_tecnico_exacto(barrio_input, mapa_barrios):
    """
    Motor de búsqueda de asignación.
    Intenta coincidencia exacta, luego flexible (sin prefijos) y luego parcial segura.
    """
    if not barrio_input: return "SIN_ASIGNAR"
    
    b_raw = limpiar_estricto(str(barrio_input))
    if not b_raw: return "SIN_ASIGNAR"
    
    # 1. Exacto
    if b_raw in mapa_barrios: return mapa_barrios[b_raw]
    
    # 2. Flexible (sin palabras clave comunes)
    patrones = r'\b(BARRIO|URB|URBANIZACION|SECTOR|ETAPA|VILLA|CIUDADELA|RESIDENCIAL|CONJUNTO)\b'
    b_flex = re.sub(patrones, '', b_raw).strip()
    if b_flex in mapa_barrios: return mapa_barrios[b_flex]
    
    # 3. Parcial (Contención)
    for k, v in mapa_barrios.items():
        if len(k) > 4 and k in b_raw: return v
            
    return "SIN_ASIGNAR"

def cargar_maestro_dinamico(file):
    """
    Lee el archivo maestro y devuelve el diccionario {Barrio: Tecnico}.
    Se adapta a CSV o Excel.
    """
    mapa = {}
    try:
        if file.name.endswith('.csv'): 
            df = pd.read_csv(file, sep=None, engine='python')
        else: 
            df = pd.read_excel(file)
            
        # Normalizar cabeceras
        df.columns = [str(c).upper().strip() for c in df.columns]
        
        # Validar estructura mínima
        if len(df.columns) < 2: return {}
            
        c_barrio = df.columns[0]
        c_tecnico = df.columns[1]

        for _, row in df.iterrows():
            b = limpiar_estricto(str(row[c_barrio]))
            t = str(row[c_tecnico]).upper().strip()
            
            if t and t != "NAN" and b: 
                mapa[b] = t
                
    except Exception as e:
        st.error(f"Error leyendo maestro: {str(e)}")
        return {}
        
    return mapa

def procesar_pdf_polizas_avanzado(file_obj):
    """
    Desglosa un PDF grande en PDFs individuales por número de póliza/cuenta.
    Detecta anexos automáticamente.
    """
    file_obj.seek(0)
    doc = fitz.open(stream=file_obj.read(), filetype="pdf")
    diccionario_extraido = {}
    
    total_paginas = len(doc)
    
    for i in range(total_paginas):
        texto_pagina = doc[i].get_text()
        matches = re.findall(r'(?:Póliza|Poliza|Cuenta)\D{0,20}(\d{4,15})', texto_pagina, re.IGNORECASE)
        
        if matches:
            sub_doc = fitz.open()
            sub_doc.insert_pdf(doc, from_page=i, to_page=i)
            
            # Chequeo de anexo en página siguiente
            if i + 1 < total_paginas:
                texto_siguiente = doc[i+1].get_text()
                if not re.search(r'(?:Póliza|Poliza|Cuenta)', texto_siguiente, re.IGNORECASE):
                    sub_doc.insert_pdf(doc, from_page=i+1, to_page=i+1)
            
            pdf_bytes = sub_doc.tobytes()
            sub_doc.close()
            
            for m in matches:
                diccionario_extraido[normalizar_numero(m)] = pdf_bytes
                
    return diccionario_extraido

# --- CLASE FPDF PERSONALIZADA (DISEÑO ITA) ---
class PDFListado(FPDF):
    def header(self):
        self.set_fill_color(0, 51, 102) # Azul oscuro
        self.rect(0, 0, 297, 20, 'F') # Fondo cabecera
        self.set_font('Arial', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 5)
        self.cell(0, 10, 'UT ITA RADIAN - HOJA DE RUTA DE OPERACIONES', 0, 1, 'C')
        self.ln(10)

def crear_pdf_lista_final(df, tecnico, col_map):
    pdf = PDFListado(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    # Subtítulo
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    fecha = datetime.now().strftime('%d/%m/%Y')
    pdf.cell(0, 10, f"GESTOR: {tecnico} | FECHA: {fecha} | TOTAL VISITAS: {len(df)}", 0, 1)
    
    # Tabla
    headers = ['#', 'CUENTA', 'MEDIDOR', 'BARRIO', 'DIRECCION', 'CLIENTE']
    widths = [10, 25, 25, 65, 85, 60]
    
    pdf.set_fill_color(220, 220, 220)
    pdf.set_font('Arial', 'B', 9)
    for h, w in zip(headers, widths): pdf.cell(w, 8, h, 1, 0, 'C', 1)
    pdf.ln()
    
    # Datos
    pdf.set_font('Arial', '', 8)
    for idx, (_, row) in enumerate(df.iterrows(), start=1):
        # Color Rojo para Apoyos
        barrio_txt = str(row[col_map['BARRIO']])
        if pd.notna(row.get('ORIGEN_REAL')):
            barrio_txt = f"[APOYO] {barrio_txt}"
            pdf.set_text_color(200, 0, 0)
        else:
            pdf.set_text_color(0, 0, 0)

        def get_s(k):
            c = col_map.get(k)
            return str(row[c]) if c and c != "NO TIENE" else ""

        row_data = [
            str(idx), 
            get_s('CUENTA'), 
            get_s('MEDIDOR')[:15], 
            barrio_txt[:38], 
            get_s('DIRECCION')[:60], 
            get_s('CLIENTE')[:30]
        ]
        
        for val, w in zip(row_data, widths):
            try: val_e = val.encode('latin-1', 'replace').decode('latin-1')
            except: val_e = val
            pdf.cell(w, 7, val_e, 1, 0, 'L')
        pdf.ln()
        
    return pdf.output(dest='S').encode('latin-1')

# ===============================================================================
# SECCIÓN 6: GESTIÓN DE VARIABLES DE SESIÓN (PERSISTENCIA ENTRE CLICS)
# ===============================================================================

if 'mapa_actual' not in st.session_state: st.session_state['mapa_actual'] = {}
if 'df_simulado' not in st.session_state: st.session_state['df_simulado'] = None
if 'col_map_final' not in st.session_state: st.session_state['col_map_final'] = None
if 'mapa_polizas_cargado' not in st.session_state: st.session_state['mapa_polizas_cargado'] = {}
if 'zip_admin_ready' not in st.session_state: st.session_state['zip_admin_ready'] = None
if 'zip_polizas_only' not in st.session_state: st.session_state['zip_polizas_only'] = None
# Variable clave para la asistencia
if 'tecnicos_activos_manual' not in st.session_state: st.session_state['tecnicos_activos_manual'] = []

# ===============================================================================
# SECCIÓN 7: BARRA LATERAL INTELIGENTE (EL CEREBRO DE NAVEGACIÓN)
# ===============================================================================

with st.sidebar:
    # 1. LOGOTIPO CORPORATIVO
    st.markdown("""
        <div class="logo-box">
            <img src="https://cdn-icons-png.flaticon.com/512/2942/2942813.png" class="logo-img">
            <h3 style="margin-top:10px; color:white;">ITA RADIAN</h3>
        </div>
    """, unsafe_allow_html=True)
    
    # 2. SELECTOR DE ROL (DEFINE QUÉ VE EL USUARIO)
    modo_acceso = st.selectbox(
        "Selecciona tu Perfil", 
        ["👷 SOY TÉCNICO", "⚙️ ADMINISTRADOR"],
        index=0 # Por defecto Técnico (Menos fricción)
    )
    
    st.divider()
    
    # 3. MÓDULO DE ASISTENCIA (DINÁMICO Y PROTEGIDO)
    # Solo aparece si: Eres Admin Y Ya cargaste la base de datos
    if modo_acceso == "⚙️ ADMINISTRADOR":
        
        if st.session_state['mapa_actual']:
            st.markdown("### 📋 Control de Asistencia")
            st.info("Desmarca a los técnicos ausentes. El sistema redistribuirá su carga automáticamente.")
            
            # Obtener lista única de técnicos desde el maestro cargado
            todos_tecnicos = sorted(list(set(st.session_state['mapa_actual'].values())))
            
            # Widget Multiselect (Por defecto todos activos)
            # Usamos session_state para recordar la selección si recarga
            seleccion_activos = st.multiselect(
                "Técnicos Activos Hoy:",
                options=todos_tecnicos,
                default=todos_tecnicos,
                key="widget_asistencia"
            )
            
            # Guardamos la selección en una variable persistente
            st.session_state['tecnicos_activos_manual'] = seleccion_activos
            
            # Cálculo de inactivos para feedback visual
            num_total = len(todos_tecnicos)
            num_activos = len(seleccion_activos)
            num_inactivos = num_total - num_activos
            
            if num_inactivos > 0:
                st.markdown(f"""
                    <div class="inactive-warning">
                        ⚠️ <b>{num_inactivos}</b> Técnicos marcados como <b>INACTIVOS</b>.<br>
                        Sus zonas serán repartidas.
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.caption("✅ Cuadrilla completa (Todos activos)")
        
        else:
            # Mensaje guía si aún no carga el maestro
            st.caption("ℹ️ Carga el 'Maestro de Operarios' en la Pestaña 1 para ver la lista de técnicos aquí.")

    elif modo_acceso == "👷 SOY TÉCNICO":
        # Mensaje motivacional o info simple para el técnico
        st.info("Bienvenido al portal de autogestión. Descarga tu ruta segura.")

    st.markdown("---")
    st.caption("v7.0 Platinum Edition")

# ===============================================================================
# SECCIÓN 8: VISTA DEL TÉCNICO (PORTAL MINIMALISTA)
# ===============================================================================

if modo_acceso == "👷 SOY TÉCNICO":
    # Header Limpio
    st.markdown('<div class="tech-header">ZONA DE DESCARGAS</div>', unsafe_allow_html=True)
    
    # Verificar si hay archivos publicados
    if os.path.exists(CARPETA_PUBLICA):
        tecnicos_list = sorted([d for d in os.listdir(CARPETA_PUBLICA) if os.path.isdir(os.path.join(CARPETA_PUBLICA, d))])
    else:
        tecnicos_list = []
        
    if not tecnicos_list:
        st.warning("⏳ Aún no hay rutas publicadas. Intenta más tarde.")
        if st.button("🔄 Actualizar Página"): st.rerun()
    else:
        # Selector Central Grande
        c_spacer, c_main, c_spacer2 = st.columns([1, 2, 1])
        with c_main:
            seleccion = st.selectbox("👇 SELECCIONA TU NOMBRE PARA INGRESAR:", ["-- Seleccionar --"] + tecnicos_list)
        
        if seleccion != "-- Seleccionar --":
            st.markdown("---")
            st.markdown(f"<h3 style='text-align:center;'>Hola, <span style='color:#34D399'>{seleccion}</span></h3>", unsafe_allow_html=True)
            
            ruta_base = os.path.join(CARPETA_PUBLICA, seleccion)
            f_ruta = os.path.join(ruta_base, "1_HOJA_DE_RUTA.pdf")
            f_leg = os.path.join(ruta_base, "3_PAQUETE_LEGALIZACION.pdf")
            
            col_a, col_b = st.columns(2)
            
            # Botón Ruta
            with col_a:
                st.markdown('<div class="info-card"><h4>📍 Hoja de Ruta</h4><p>Tus visitas del día ordenadas.</p></div>', unsafe_allow_html=True)
                if os.path.exists(f_ruta):
                    with open(f_ruta, "rb") as f:
                        st.download_button("⬇️ DESCARGAR RUTA", f, f"Ruta_{seleccion}.pdf", "application/pdf", key="dl1")
                else: st.error("No disponible")
            
            # Botón Legalización
            with col_b:
                st.markdown('<div class="info-card"><h4>📂 Legalización</h4><p>Pólizas y documentos.</p></div>', unsafe_allow_html=True)
                if os.path.exists(f_leg):
                    with open(f_leg, "rb") as f:
                        st.download_button("⬇️ DESCARGAR PAQUETE", f, f"Leg_{seleccion}.pdf", "application/pdf", key="dl2")
                else: st.info("Hoy no tienes pólizas.")

# ===============================================================================
# SECCIÓN 9: VISTA DEL ADMINISTRADOR (PANEL DE MANDO)
# ===============================================================================

elif modo_acceso == "⚙️ ADMINISTRADOR":
    st.markdown("## ⚙️ Panel de Control Logístico")
    
    password = st.text_input("🔑 Contraseña de Admin:", type="password")
    
    if password == "ita2026":
        
        # DEFINICIÓN DE TABS
        tab1, tab2, tab3, tab4 = st.tabs([
            "1. Base & Config", 
            "2. Carga & Balanceo", 
            "3. Ajuste Manual", 
            "4. Publicación"
        ])
        
        # --- TAB 1: BASE DE OPERARIOS ---
        with tab1:
            st.markdown("### 🗃️ Carga del Maestro de Operarios")
            st.write("Sube el archivo que contiene la relación Barrio - Técnico.")
            
            f_maestro = st.file_uploader("Archivo Maestro (Excel/CSV)", type=["xlsx", "csv"])
            
            if f_maestro:
                with st.spinner("Analizando estructura de barrios..."):
                    st.session_state['mapa_actual'] = cargar_maestro_dinamico(f_maestro)
                
                if st.session_state['mapa_actual']:
                    st.success(f"✅ Maestro cargado exitosamente: {len(st.session_state['mapa_actual'])} zonas identificadas.")
                    # Trigger para recargar la sidebar y mostrar el widget de asistencia
                    # st.rerun() # Opcional, a veces Streamlit lo hace solo, si no, descomentar.
                else:
                    st.error("❌ El archivo no tiene el formato correcto (Barrio, Tecnico).")

        # --- TAB 2: CARGA Y BALANCEO ---
        with tab2:
            st.markdown("### ⚖️ Procesamiento Diario")
            
            c_pdf, c_xls = st.columns(2)
            with c_pdf:
                up_pdf = st.file_uploader("1. PDF Pólizas (Opcional)", type="pdf")
            with c_xls:
                up_xls = st.file_uploader("2. Excel Ruta (Obligatorio)", type=["xlsx", "csv"])
            
            # Validación de requisitos
            if not st.session_state['mapa_actual']:
                st.warning("⚠️ Primero debes cargar el Maestro en la Pestaña 1.")
            elif up_xls:
                # Lectura preliminar
                try:
                    if up_xls.name.endswith('.csv'): df = pd.read_csv(up_xls, sep=None, engine='python', encoding='utf-8-sig')
                    else: df = pd.read_excel(up_xls)
                    cols = list(df.columns)
                    
                    st.divider()
                    st.markdown("#### ⚙️ Configuración de Asignación")
                    
                    # 1. Definir quiénes trabajan hoy (Logica de Asistencia)
                    # Si el usuario modificó la sidebar, usamos esa lista. Si no, todos.
                    if 'tecnicos_activos_manual' in st.session_state and st.session_state['tecnicos_activos_manual']:
                        tecnicos_hoy = st.session_state['tecnicos_activos_manual']
                    else:
                        tecnicos_hoy = sorted(list(set(st.session_state['mapa_actual'].values())))
                    
                    if len(tecnicos_hoy) == 0:
                        st.error("⛔ ¡Alerta! No hay técnicos activos seleccionados. Revisa la barra lateral.")
                    else:
                        # 2. Tabla de Cupos (Solo para los presentes)
                        df_cupos = pd.DataFrame({"Técnico": tecnicos_hoy, "Cupo": [35]*len(tecnicos_hoy)})
                        ed_cupos = st.data_editor(df_cupos, column_config={"Cupo": st.column_config.NumberColumn(min_value=1)}, hide_index=True, use_container_width=True)
                        LIMITES = dict(zip(ed_cupos["Técnico"], ed_cupos["Cupo"]))
                        
                        # 3. Mapeo de Columnas
                        def ix(k): 
                            for i,c in enumerate(cols): 
                                for x in k: 
                                    if x in str(c).upper(): return i
                            return 0
                        
                        cc1, cc2, cc3 = st.columns(3)
                        sb = cc1.selectbox("Barrio", cols, index=ix(['BARRIO']))
                        sd = cc2.selectbox("Dirección", cols, index=ix(['DIR','DIRECCION']))
                        sc = cc3.selectbox("Cuenta", cols, index=ix(['CUENTA']))
                        sm = st.selectbox("Medidor", ["NO TIENE"]+cols, index=ix(['MEDIDOR'])+1)
                        sl = st.selectbox("Cliente", ["NO TIENE"]+cols, index=ix(['CLIENTE'])+1)
                        cmap = {'BARRIO': sb, 'DIRECCION': sd, 'CUENTA': sc, 'MEDIDOR': sm if sm!="NO TIENE" else None, 'CLIENTE': sl if sl!="NO TIENE" else None}
                        
                        st.divider()
                        
                        # BOTÓN DE BALANCEO
                        if st.button("🚀 INICIAR BALANCEO INTELIGENTE", type="primary"):
                            
                            # A. Auto-scan PDF si es necesario
                            if up_pdf and not st.session_state['mapa_polizas_cargado']:
                                with st.spinner("Escaneando pólizas automáticamente..."):
                                    st.session_state['mapa_polizas_cargado'] = procesar_pdf_polizas_avanzado(up_pdf)
                            
                            # B. Lógica de Asignación
                            with st.spinner("Calculando rutas óptimas..."):
                                df_proc = df.copy()
                                
                                # Asignación Ideal (Mapa completo)
                                df_proc['TECNICO_IDEAL'] = df_proc[sb].apply(lambda x: buscar_tecnico_exacto(x, st.session_state['mapa_actual']))
                                
                                # Manejo de Inactivos: Si el técnico ideal NO vino hoy, asignamos temporalmente a "VACANTE"
                                df_proc['TECNICO_FINAL'] = df_proc['TECNICO_IDEAL'].apply(lambda x: x if x in tecnicos_hoy else "VACANTE")
                                df_proc['ORIGEN_REAL'] = None
                                
                                # Marcar origen real para los que cayeron en VACANTE
                                mask_vacante = df_proc['TECNICO_FINAL'] == "VACANTE"
                                df_proc.loc[mask_vacante, 'ORIGEN_REAL'] = df_proc.loc[mask_vacante, 'TECNICO_IDEAL']
                                
                                # Ordenamiento
                                df_proc['S'] = df_proc[sd].astype(str).apply(natural_sort_key)
                                df_proc = df_proc.sort_values(by=[sb, 'S'])
                                
                                # C. Repartir VACANTES (Huérfanos por inasistencia)
                                huerfanos = df_proc[df_proc['TECNICO_FINAL'] == "VACANTE"]
                                if not huerfanos.empty:
                                    # Estrategia: Repartir al que menos tenga
                                    for idx_h, _ in huerfanos.iterrows():
                                        # Recalcular conteo actual de los presentes
                                        conteo_live = df_proc[df_proc['TECNICO_FINAL'].isin(tecnicos_hoy)]['TECNICO_FINAL'].value_counts()
                                        # Asegurar que todos los presentes estén en el conteo (incluso con 0)
                                        for t in tecnicos_hoy:
                                            if t not in conteo_live: conteo_live[t] = 0
                                        
                                        # Asignar al mas libre
                                        mejor_opcion = conteo_live.idxmin()
                                        df_proc.at[idx_h, 'TECNICO_FINAL'] = mejor_opcion
                                
                                # D. Balanceo de Excedentes (Cupos)
                                conteo = df_proc['TECNICO_FINAL'].value_counts()
                                for tech in [t for t in tecnicos_hoy if conteo.get(t,0) > LIMITES.get(t,35)]:
                                    tope = LIMITES.get(tech, 35)
                                    rows = df_proc[df_proc['TECNICO_FINAL'] == tech]
                                    exc = len(rows) - tope
                                    
                                    if exc > 0:
                                        mov = rows.index[-exc:]
                                        now = df_proc['TECNICO_FINAL'].value_counts()
                                        for t in tecnicos_hoy: 
                                            if t not in now: now[t]=0
                                        
                                        best = sorted([t for t in tecnicos_hoy if t!=tech], key=lambda x: now.get(x,0))[0]
                                        df_proc.loc[mov, 'TECNICO_FINAL'] = best
                                        df_proc.loc[mov, 'ORIGEN_REAL'] = tech
                                
                                st.session_state['df_simulado'] = df_proc.drop(columns=['S'])
                                st.session_state['col_map_final'] = cmap
                                st.success("✅ Balanceo Terminado (Asistencia Aplicada).")

                except Exception as e: st.error(f"Error: {e}")

        # --- TAB 3: AJUSTE MANUAL ---
        with tab3:
            st.markdown("### 🛠️ Corrección Fina")
            if st.session_state['df_simulado'] is not None:
                df = st.session_state['df_simulado']
                cbar = st.session_state['col_map_final']['BARRIO']
                # Solo mostrar técnicos que tienen carga
                activos_con_carga = sorted(df['TECNICO_FINAL'].unique())
                
                # Lista destino: Todos los que vinieron hoy
                destinos_posibles = st.session_state.get('tecnicos_activos_manual', [])

                c1, c2, c3, c4 = st.columns([1.5, 1.5, 1.5, 1])
                with c1: org = st.selectbox("De:", ["-"]+list(activos_con_carga))
                with c2: 
                    if org!="-":
                        brs = df[df['TECNICO_FINAL']==org][cbar].value_counts()
                        bar = st.selectbox("Barrio:", [f"{k} ({v})" for k,v in brs.items()])
                    else: bar=None
                with c3: dst = st.selectbox("Para:", ["-"]+destinos_posibles)
                with c4:
                    st.write("")
                    if st.button("Mover"):
                        if bar and dst!="-":
                            rb = bar.rsplit(" (",1)[0]
                            msk = (df['TECNICO_FINAL']==org) & (df[cbar]==rb)
                            df.loc[msk, 'TECNICO_FINAL'] = dst
                            df.loc[msk, 'ORIGEN_REAL'] = org
                            st.session_state['df_simulado'] = df; st.rerun()
                
                # Cards
                cls = st.columns(2)
                for i, t in enumerate(activos_con_carga):
                    with cls[i%2]:
                        s = df[df['TECNICO_FINAL']==t]
                        r = s.groupby([cbar, 'ORIGEN_REAL'], dropna=False).size().reset_index(name='N')
                        r['B'] = r.apply(lambda x: f"⚠️ {x[cbar]}" if pd.notna(x['ORIGEN_REAL']) else x[cbar], axis=1)
                        with st.expander(f"👷 {t} ({len(s)})"): st.dataframe(r[['B','N']], hide_index=True, use_container_width=True)
            else: st.info("Sin datos.")

        # --- TAB 4: PUBLICAR ---
        with tab4:
            st.markdown("### 🌍 Distribución")
            if st.session_state['df_simulado'] is not None:
                dff = st.session_state['df_simulado']
                cmf = st.session_state['col_map_final']
                pls = st.session_state['mapa_polizas_cargado']
                tfin = [t for t in dff['TECNICO_FINAL'].unique() if "SIN_" not in t]
                
                if st.button("📢 PUBLICAR EN WEB", type="primary"):
                    gestionar_directorio_publico("limpiar")
                    pg = st.progress(0)
                    for i, t in enumerate(tfin):
                        dt = dff[dff['TECNICO_FINAL']==t].copy()
                        dt['S'] = dt[cmf['DIRECCION']].astype(str).apply(natural_sort_key)
                        dt = dt.sort_values(by=[cmf['BARRIO'], 'S']).drop(columns=['S'])
                        
                        safe = str(t).replace(" ","_")
                        pto = os.path.join(CARPETA_PUBLICA, safe); os.makedirs(pto, exist_ok=True)
                        
                        # Ruta
                        with open(os.path.join(pto, "1_HOJA_DE_RUTA.pdf"), "wb") as f:
                            f.write(crear_pdf_lista_final(dt, t, cmf))
                        
                        # Legalizacion
                        if pls:
                            mg = fitz.open(); n=0
                            for _,r in dt.iterrows():
                                c = normalizar_numero(str(r[cmf['CUENTA']]))
                                if c in pls:
                                    with fitz.open(stream=pls[c], filetype="pdf") as x: mg.insert_pdf(x)
                                    n+=1
                            if n>0:
                                with open(os.path.join(pto, "3_PAQUETE_LEGALIZACION.pdf"), "wb") as f: f.write(mg.tobytes())
                            mg.close()
                        pg.progress((i+1)/len(tfin))
                    st.success("✅ Publicado")
                
                st.divider()
                
                if st.button("📦 GENERAR ZIP TOTAL"):
                    bf = io.BytesIO()
                    with zipfile.ZipFile(bf,"w") as z:
                        # 0. Banco
                        if pls:
                            for k,v in pls.items(): z.writestr(f"00_BANCO_DE_POLIZAS_TOTAL/{k}.pdf", v)
                        
                        # 0. Excel
                        out = io.BytesIO(); 
                        with pd.ExcelWriter(out, engine='xlsxwriter') as w: dff.to_excel(w, index=False)
                        z.writestr("00_CONSOLIDADO.xlsx", out.getvalue())
                        
                        # Carpetas
                        for t in tfin:
                            safe = str(t).replace(" ","_")
                            dt = dff[dff['TECNICO_FINAL']==t].copy()
                            dt['S'] = dt[cmf['DIRECCION']].astype(str).apply(natural_sort_key)
                            dt = dt.sort_values(by=[cmf['BARRIO'], 'S']).drop(columns=['S'])
                            
                            z.writestr(f"{safe}/1_HOJA_DE_RUTA.pdf", crear_pdf_lista_final(dt, t, cmf))
                            
                            ot = io.BytesIO()
                            with pd.ExcelWriter(ot, engine='xlsxwriter') as w: dt.to_excel(w, index=False)
                            z.writestr(f"{safe}/2_TABLA_DIGITAL.xlsx", ot.getvalue())
                            
                            if pls:
                                mg = fitz.open(); n=0
                                for _,r in dt.iterrows():
                                    c = normalizar_numero(str(r[cmf['CUENTA']]))
                                    if c in pls:
                                        z.writestr(f"{safe}/4_POLIZAS_INDIVIDUALES/{c}.pdf", pls[c])
                                        with fitz.open(stream=pls[c], filetype="pdf") as x: mg.insert_pdf(x)
                                        n+=1
                                if n>0: z.writestr(f"{safe}/3_PAQUETE_LEGALIZACION.pdf", mg.tobytes())
                                mg.close()
                                
                    st.session_state['zip_admin_ready'] = bf.getvalue()
                    st.success("Listo")
                
                if st.session_state['zip_admin_ready']:
                    st.download_button("⬇️ ZIP", st.session_state['zip_admin_ready'], "Logistica_Total.zip", "application/zip")

    elif password:
        st.error("Contraseña incorrecta")
