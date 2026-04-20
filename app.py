#########################################################################################
#                                                                                       #
#   PLATAFORMA INTEGRAL DE LOGÍSTICA ITA - VERSIÓN 14.3 "ORDEN REAL & BOLSA PRO"        #
#   AUTOR: YEFREY                                                                       #
#   FECHA: MARZO 2026                                                                   #
#                                                                                       #
#   NOTAS DE ESTA VERSIÓN (NO REDUCIDA, CÓDIGO ÍNTEGRO):                                #
#   - CORRECCIÓN: La "Tabla Digital" extrae el Número de Orden REAL del Excel de ruta.  #
#   - MULTI-PDF: Soporte para procesar múltiples archivos de pólizas simultáneamente.   #
#   - CSS desplegado línea por línea para fácil edición.                                #
#   - Compatibilidad total con "OPERARIOS REINSTALACION" (Nombre Unidad/Funcionario).   #
#   - BOLSAS INTELIGENTES: Subdivisión por dueño original mostrando MOTIVO de envío.    #
#   - BOTONES NARANJAS exclusivos para identificar la carga en la bolsa pendiente.      #
#   - Botón MASIVO NARANJA para reasignar toda la bolsa de un técnico a otro.           #
#   - Botones rojos para traslado masivo de cargas completas de técnicos activos.       #
#   - "Tabla Digital" (Excel) forzada y garantizada a solo 5 columnas exactas.          #
#   - Reporte TXT automático de cruce documental (Pólizas faltantes).                   #
#   - CONSERVACIÓN DE ORDEN (V74): Mantiene intacto el orden original del maestro.      #
#   - MEJORA VISUAL: Cuadrícula simétrica estricta, botones de altura fija alineados.   #
#                                                                                       #
#########################################################################################

# =======================================================================================
# IMPORTACIÓN DE LIBRERÍAS
# =======================================================================================
import streamlit as st
import fitz  # PyMuPDF: Motor avanzado de procesamiento de PDFs
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

# =======================================================================================
# SECCIÓN 1: CONFIGURACIÓN VISUAL Y VARIABLES DE SESIÓN
# =======================================================================================

# Configuración principal de la página
st.set_page_config(
    page_title="Logística ITA | v14.3 Pro",
    layout="wide",
    page_icon="🚚",
    initial_sidebar_state="expanded"
)

# Inicialización detallada de Variables de Sesión
if 'admin_logged_in' not in st.session_state:
    st.session_state['admin_logged_in'] = False

if 'mapa_actual' not in st.session_state:
    st.session_state['mapa_actual'] = {}

if 'mapa_telefonos' not in st.session_state:
    st.session_state['mapa_telefonos'] = {}

if 'df_simulado' not in st.session_state:
    st.session_state['df_simulado'] = None

if 'col_map_final' not in st.session_state:
    st.session_state['col_map_final'] = None

if 'mapa_polizas_cargado' not in st.session_state:
    st.session_state['mapa_polizas_cargado'] = {}

if 'zip_admin_ready' not in st.session_state:
    st.session_state['zip_admin_ready'] = None

if 'tecnicos_activos_manual' not in st.session_state:
    st.session_state['tecnicos_activos_manual'] = []

if 'ultimo_archivo_procesado' not in st.session_state:
    st.session_state['ultimo_archivo_procesado'] = None

if 'limites_cupo' not in st.session_state:
    st.session_state['limites_cupo'] = {}

# Inyección de CSS (Expandida línea por línea)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700;900&display=swap');
    
    /* Tipografía global */
    .stApp { 
        font-family: 'Roboto', sans-serif; 
    }
    
    /* Contenedor del Logo en la barra lateral */
    .logo-container {
        display: flex; 
        flex-direction: column; 
        align-items: center; 
        justify-content: center;
        padding: 25px; 
        background: linear-gradient(180deg, rgba(100, 116, 139, 0.1) 0%, rgba(15, 23, 42, 0) 100%);
        border-radius: 16px; 
        border: 1px solid rgba(100, 116, 139, 0.2); 
        margin-bottom: 25px;
    }
    
    /* Imagen del logo */
    .logo-img { 
        width: 100px; 
        height: auto; 
        filter: drop-shadow(0 0 10px rgba(56, 189, 248, 0.4)); 
        transition: transform 0.3s ease; 
    }
    
    .logo-img:hover { 
        transform: scale(1.05); 
    }
    
    /* Texto del logo */
    .logo-text { 
        font-family: 'Roboto', sans-serif; 
        font-weight: 900; 
        font-size: 26px; 
        background: -webkit-linear-gradient(45deg, #0284C7, #4F46E5); 
        -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent; 
        margin-top: 10px; 
        letter-spacing: 1.5px; 
    }
    
    /* Botones primarios generales */
    div.stButton > button:first-child { 
        background: linear-gradient(135deg, #2563EB 0%, #1E40AF 100%); 
        color: white !important; 
        border-radius: 10px; 
        height: 52px; 
        width: 100%; 
        font-size: 16px; 
        font-weight: 700; 
        border: 1px solid #1D4ED8; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.2); 
        text-transform: uppercase; 
    }
    
    div.stButton > button:first-child:hover { 
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%); 
        transform: translateY(-1px); 
    }
    
    /* Botones de descarga */
    div.stDownloadButton > button:first-child { 
        background: linear-gradient(135deg, #059669 0%, #047857 100%); 
        color: white !important; 
        border-radius: 10px; 
        height: 58px; 
        width: 100%; 
        font-size: 17px; 
        font-weight: 700; 
        border: 1px solid #059669; 
    }
    
    div.stDownloadButton > button:first-child:hover { 
        background: linear-gradient(135deg, #10B981 0%, #059669 100%); 
    }

    /* ========================================================================= */
    /* CSS RECONSTRUIDO PARA CUADRÍCULA PERFECTA (BLOQUES SIMÉTRICOS)            */
    /* ========================================================================= */
    
    /* Botones AZULES para los operarios activos */
    .btn-barrio > button:first-child {
        background: transparent !important;
        color: #0284C7 !important;
        border: 1px solid #0284C7 !important; 
        border-radius: 4px !important;
        height: 42px !important; /* ALTURA ESTRICTAMENTE FIJA PARA ALINEACIÓN */
        min-height: 42px !important;
        max-height: 42px !important;
        padding: 2px 4px !important; 
        font-size: 11px !important; 
        line-height: 1.2 !important;
        text-transform: none !important;
        font-weight: 600 !important;
        margin-bottom: 4px !important;
        box-shadow: none !important;
        width: 100% !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        align-items: center !important;
        overflow: hidden !important; /* Evita que el texto extra deforme la cuadrícula */
    }
    
    .btn-barrio > button:first-child:hover {
        background: #F0F9FF !important;
        transform: scale(1.02) !important;
    }

    /* Botones NARANJAS para barrios en la Bolsa Pendiente */
    .btn-bolsa-naranja > button:first-child {
        background: transparent !important;
        color: #EA580C !important;
        border: 1px solid #EA580C !important;
        border-radius: 4px !important;
        height: 42px !important; /* ALTURA ESTRICTAMENTE FIJA PARA ALINEACIÓN */
        min-height: 42px !important;
        max-height: 42px !important;
        padding: 2px 4px !important;
        font-size: 11px !important;
        line-height: 1.2 !important;
        text-transform: none !important;
        font-weight: 600 !important;
        margin-bottom: 4px !important;
        box-shadow: none !important;
        width: 100% !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        align-items: center !important;
        overflow: hidden !important; /* Evita que el texto extra deforme la cuadrícula */
    }
    
    .btn-bolsa-naranja > button:first-child:hover {
        background: #FFF7ED !important;
        transform: scale(1.02) !important;
    }

    /* Botón MASIVO NARANJA OSCURO */
    .btn-masivo-naranja > button:first-child {
        background: #C2410C !important;
        color: white !important;
        font-size: 11px !important;
        height: 32px !important; /* Altura reducida y fija */
        min-height: 32px !important;
        margin-bottom: 8px !important;
        padding: 0px 5px !important;
        border: 1px solid #9A3412 !important;
        border-radius: 4px !important;
        font-weight: 800 !important;
        width: 100% !important;
    }
    
    .btn-masivo-naranja > button:first-child:hover { 
        background: #9A3412 !important; 
        transform: translateY(-1px);
    }

    /* Botón ROJO de traslado masivo para técnicos activos */
    .btn-masivo > button:first-child {
        background: #DC2626 !important;
        color: white !important;
        font-size: 11px !important;
        height: 32px !important; /* Altura reducida y fija */
        min-height: 32px !important;
        margin-bottom: 8px !important;
        padding: 0px 5px !important;
        border: 1px solid #991B1B !important;
        border-radius: 4px !important;
        font-weight: 800 !important;
        width: 100% !important;
    }
    
    .btn-masivo > button:first-child:hover { 
        background: #B91C1C !important; 
        transform: translateY(-1px);
    }
    /* ========================================================================= */
    
    /* Tarjeta informativa de la Bolsa Inteligente */
    .bolsa-card {
        background-color: #FFF7ED;
        color: #9A3412;
        padding: 12px 15px;
        border-radius: 8px;
        border-left: 6px solid #EA580C;
        font-weight: bold;
        margin-bottom: 12px;
        font-size: 14px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    /* Alertas de bloqueo y desbloqueo */
    .locked-msg { 
        background-color: #FEE2E2; 
        color: #991B1B; 
        padding: 15px; 
        border-radius: 8px; 
        border: 1px solid #F87171; 
        text-align: center; 
        font-weight: bold; 
    }
    
    .unlocked-msg { 
        background-color: #D1FAE5; 
        color: #065F46; 
        padding: 10px; 
        border-radius: 8px; 
        border: 1px solid #34D399; 
        text-align: center; 
        margin-top: 10px; 
        font-weight: bold; 
    }
    
    /* Encabezado del área de técnicos */
    .tech-header { 
        font-size: 32px; 
        font-weight: 800; 
        background: -webkit-linear-gradient(0deg, #0284C7, #4F46E5); 
        -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent; 
        text-align: center; 
        margin-bottom: 20px; 
        border-bottom: 2px solid #38BDF8; 
        padding-bottom: 10px; 
    }
    </style>
""", unsafe_allow_html=True)

# =======================================================================================
# SECCIÓN 2: DIÁLOGOS INTERACTIVOS (MODALES)
# =======================================================================================

@st.dialog("🔄 Trasladar Visitas (Unitario)")
def modal_traslado(origen, barrio_limpio, max_cant, opciones_destino, df_estado, cbar_name):
    """
    Modal para mover un barrio específico de un técnico a otro, o de la bolsa a un técnico.
    Mantiene el rastreo del dueño original (ORIGEN_REAL).
    """
    st.markdown(f"### Moviendo barrio: **{barrio_limpio}**")
    st.info(f"Origen actual: **{origen}**")
    
    dst = st.selectbox("¿A qué técnico se lo vas a asignar?", ["-- Seleccionar --"] + opciones_destino)
    cant = st.number_input(f"Cantidad a mover (Máximo disponible: {max_cant}):", min_value=1, max_value=max_cant, value=max_cant)
    
    if st.button("CONFIRMAR TRASLADO", type="primary"):
        if dst != "-- Seleccionar --" and dst != origen:
            df_work = df_estado.copy()
            
            # Localizar los índices exactos a mover
            mascara = (df_work['TECNICO_FINAL'] == origen) & (df_work[cbar_name] == barrio_limpio)
            idx_to_move = df_work[mascara].head(cant).index
            
            for idx in idx_to_move:
                # Lógica de rastreo de origen
                if dst != "⚠️ BOLSA PENDIENTE" and origen == "⚠️ BOLSA PENDIENTE":
                    # Si sale de la bolsa, guardamos quién era su técnico ideal
                    df_work.loc[idx, 'ORIGEN_REAL'] = df_work.loc[idx, 'TECNICO_IDEAL']
                elif dst != "⚠️ BOLSA PENDIENTE" and origen != "⚠️ BOLSA PENDIENTE":
                    # Si se lo paso de un compañero a otro
                    df_work.loc[idx, 'ORIGEN_REAL'] = origen
                    
                # Aplicamos el cambio final
                df_work.loc[idx, 'TECNICO_FINAL'] = dst
                
            # === REORGANIZACIÓN AUTOMÁTICA (Conserva Orden Motor V74) ===
            df_work = reordenar_operacion_global(df_work, st.session_state.get('col_map_final', {}))
            
            # Actualizamos la memoria global y refrescamos
            st.session_state['df_simulado'] = df_work
            st.rerun()
        else:
            st.error("Por favor, selecciona un destino válido que sea distinto al origen actual.")

@st.dialog("🚀 Traslado Masivo (Vaciado de Carga)")
def modal_masivo(tecnico_origen, opciones_destino, df_estado):
    """
    Modal de emergencia para mover absolutamente TODA la carga de un TÉCNICO ACTIVO
    a un compañero o a la bolsa en un solo clic.
    """
    st.warning(f"⚠️ ESTÁS A PUNTO DE MOVER TODAS LAS VISITAS ASIGNADAS A: **{tecnico_origen}**")
    st.write("Esta acción trasladará todos los barrios de este operario al destino seleccionado.")
    
    dst = st.selectbox("Seleccionar Operario Destino:", ["-- Seleccionar --"] + opciones_destino)
    
    if st.button("EJECUTAR VACIADO TOTAL", type="primary"):
        if dst != "-- Seleccionar --" and dst != tecnico_origen:
            df_work = df_estado.copy()
            
            # Buscar todo lo que le pertenece al técnico de origen
            idx_to_move = df_work[df_work['TECNICO_FINAL'] == tecnico_origen].index
            
            for idx in idx_to_move:
                # Guardamos la huella de que le pertenecía a él originalmente
                df_work.loc[idx, 'ORIGEN_REAL'] = tecnico_origen
                # Asignamos al nuevo destino
                df_work.loc[idx, 'TECNICO_FINAL'] = dst
                
            # === REORGANIZACIÓN AUTOMÁTICA (Conserva Orden Motor V74) ===
            df_work = reordenar_operacion_global(df_work, st.session_state.get('col_map_final', {}))
            
            st.session_state['df_simulado'] = df_work
            st.rerun()
        else:
            st.error("Por favor, selecciona un operario de destino válido.")

@st.dialog("🚀 Reasignar Bolsa Completa")
def modal_reasignar_bolsa(dueno_original, opciones_destino, df_estado):
    """
    Modal para mover TODA la bolsa pendiente que le pertenecía a un técnico inactivo.
    """
    st.warning(f"⚠️ Vas a reasignar TODA la carga pendiente que era originalmente de: **{dueno_original}**")
    st.write("Se enviarán todos estos barrios al operario que selecciones.")
    
    dst = st.selectbox("Seleccionar Nuevo Operario Destino:", ["-- Seleccionar --"] + opciones_destino)
    
    if st.button("EJECUTAR REASIGNACIÓN TOTAL", type="primary"):
        # No permitimos mover a la misma bolsa
        if dst != "-- Seleccionar --" and dst != "⚠️ BOLSA PENDIENTE":
            df_work = df_estado.copy()
            
            # Buscar todo lo que esté en la bolsa Y que pertenezca a este dueño ideal
            mask = (df_work['TECNICO_FINAL'] == "⚠️ BOLSA PENDIENTE") & (df_work['TECNICO_IDEAL'] == dueno_original)
            idx_to_move = df_work[mask].index
            
            for idx in idx_to_move:
                # Guardamos el origen real (de dónde viene verdaderamente)
                df_work.loc[idx, 'ORIGEN_REAL'] = dueno_original
                # Asignamos al nuevo destino
                df_work.loc[idx, 'TECNICO_FINAL'] = dst
                
            # === REORGANIZACIÓN AUTOMÁTICA (Conserva Orden Motor V74) ===
            df_work = reordenar_operacion_global(df_work, st.session_state.get('col_map_final', {}))
            
            st.session_state['df_simulado'] = df_work
            st.rerun()
        else:
            st.error("Por favor, selecciona un operario destino válido (No puedes enviarlo a la bolsa de nuevo).")

# =======================================================================================
# SECCIÓN 3: GESTIÓN DEL SISTEMA DE ARCHIVOS Y CARPETAS PÚBLICAS
# =======================================================================================

CARPETA_PUBLICA = "public_files"

def gestionar_sistema_archivos(accion="iniciar"):
    """
    Controla la creación y limpieza de la carpeta donde se publican 
    los archivos para que los técnicos los descarguen en su móvil.
    """
    if accion == "iniciar":
        if not os.path.exists(CARPETA_PUBLICA):
            try: 
                os.makedirs(CARPETA_PUBLICA)
            except OSError as e: 
                st.error(f"Error al crear sistema de archivos: {e}")
    elif accion == "limpiar":
        if os.path.exists(CARPETA_PUBLICA):
            try:
                shutil.rmtree(CARPETA_PUBLICA)
                time.sleep(0.3) # Pequeña pausa para asegurar liberación de memoria
                os.makedirs(CARPETA_PUBLICA)
            except Exception:
                # Método de borrado alternativo si rmtree falla por bloqueos de Windows
                try:
                    for filename in os.listdir(CARPETA_PUBLICA):
                        file_path = os.path.join(CARPETA_PUBLICA, filename)
                        if os.path.isfile(file_path): 
                            os.unlink(file_path)
                        elif os.path.isdir(file_path): 
                            shutil.rmtree(file_path)
                except: 
                    pass
        else: 
            os.makedirs(CARPETA_PUBLICA)

# Iniciar sistema de archivos al cargar el script
gestionar_sistema_archivos("iniciar")

# =======================================================================================
# SECCIÓN 4: FUNCIONES DE LÓGICA CORE Y NORMALIZACIÓN DE DATOS
# =======================================================================================

def limpiar_estricto(txt):
    """Limpia tildes, espacios extra y convierte a mayúsculas para un match perfecto."""
    if pd.isna(txt) or not txt: 
        return ""
    txt = str(txt).upper().strip()
    # Normalización para eliminar acentos diacríticos
    txt = "".join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    return txt

def normalizar_numero(txt):
    """Extrae únicamente los caracteres numéricos de una cadena, ideal para cuentas y celulares."""
    if pd.isna(txt) or not txt: 
        return ""
    txt_str = str(txt)
    if txt_str.endswith('.0'): 
        txt_str = txt_str[:-2]
    nums = re.sub(r'\D', '', txt_str)
    return str(int(nums)) if nums else ""

def natural_sort_key(txt):
    """Permite ordenar direcciones alfanuméricas de forma lógica humana (ej: Calle 2 antes que Calle 10)."""
    if pd.isna(txt) or not txt: 
        return tuple()
    txt = str(txt).upper()
    return tuple(int(s) if s.isdigit() else s for s in re.split(r'(\d+)', txt))

def buscar_tecnico_exacto(barrio_input, mapa_barrios):
    """
    Motor de asignación de barrios. 
    Intenta coincidencia exacta, si falla, usa eliminación de prefijos.
    """
    if pd.isna(barrio_input) or not barrio_input: 
        return "SIN_ASIGNAR"
        
    b_raw = limpiar_estricto(str(barrio_input))
    if not b_raw: 
        return "SIN_ASIGNAR"
    
    # 1. Intento de coincidencia exacta
    if b_raw in mapa_barrios: 
        return mapa_barrios[b_raw]
    
    # 2. Intento eliminando palabras genéricas que suelen estorbar
    patrones = r'\b(BARRIO|URB|URBANIZACION|SECTOR|ETAPA|VILLA|CIUDADELA|RESIDENCIAL|CONJUNTO|ZONA|UNIDAD)\b'
    b_flex = re.sub(patrones, '', b_raw).strip()
    if b_flex in mapa_barrios: 
        return mapa_barrios[b_flex]
    
    # 3. Búsqueda por subcadena (fallback)
    for k, v in mapa_barrios.items():
        if len(k) > 4 and k in b_raw: 
            return v
            
    return "SIN_ASIGNAR"

def cargar_maestro_dinamico(file):
    """
    Lee el archivo maestro.
    Reconoce el archivo 'OPERARIOS REINSTALACION' buscando columnas 
    como 'Nombre Unidad' (como Barrio) y 'Nombre funcionarios' (como Técnico).
    """
    mapa = {}
    telefonos = {}
    try:
        if file.name.endswith('.csv'): 
            df = pd.read_csv(file, sep=None, engine='python', encoding='utf-8-sig')
        else: 
            df = pd.read_excel(file)
            
        # Limpiar nombres de columnas
        df.columns = [str(c).upper().strip() for c in df.columns]
        
        # Diccionario ampliado de sinónimos para detectar las columnas correctas
        col_barrio = next((c for c in df.columns if 'BARRIO' in c or 'ZONA' in c or 'UNIDAD' in c), None)
        col_tecnico = next((c for c in df.columns if 'TECNICO' in c or 'OPERARIO' in c or 'NOMBRE FUNCIONARIO' in c or 'FUNCIONARIO' in c), None)
        col_celular = next((c for c in df.columns if 'CEL' in c or 'TEL' in c or 'MOVIL' in c), None)

        if not col_barrio or not col_tecnico:
            st.error("❌ Error: No se encontraron las columnas clave. El maestro debe tener algo parecido a 'Barrio/Unidad' y 'Técnico/Funcionario'.")
            return {}, {}

        # Llenar el diccionario de cruce
        for _, row in df.iterrows():
            b = limpiar_estricto(str(row[col_barrio]))
            t = str(row[col_tecnico]).upper().strip()
            
            if t and t != "NAN" and b: 
                mapa[b] = t
                if col_celular and pd.notna(row[col_celular]):
                    tel = normalizar_numero(row[col_celular])
                    if tel: 
                        telefonos[t] = tel
                        
    except Exception as e:
        st.error(f"Error crítico leyendo el archivo maestro: {str(e)}")
        return {}, {}
        
    return mapa, telefonos

def procesar_pdf_polizas_avanzado(file_obj):
    """
    Usa PyMuPDF (fitz) para escanear el PDF hoja por hoja buscando números de cuenta o póliza.
    Retorna un diccionario: { "Cuenta123": <Bytes_Del_PDF_Separado>, ... }
    """
    file_obj.seek(0)
    doc = fitz.open(stream=file_obj.read(), filetype="pdf")
    diccionario_extraido = {}
    total_paginas = len(doc)
    
    for i in range(total_paginas):
        texto_pagina = doc[i].get_text()
        
        # Regex tolerante para encontrar la cuenta
        matches = re.findall(r'(?:Póliza|Poliza|Cuenta)\D{0,20}(\d{4,15})', texto_pagina, re.IGNORECASE)
        
        if matches:
            # Crear un nuevo documento PDF en memoria solo con esta página
            sub_doc = fitz.open()
            sub_doc.insert_pdf(doc, from_page=i, to_page=i)
            
            # Revisar si la siguiente página también pertenece a esta póliza (Ej: anexos o revesos)
            if i + 1 < total_paginas:
                texto_siguiente = doc[i+1].get_text()
                # Si la página siguiente NO tiene la palabra "Cuenta", asumimos que es continuación
                if not re.search(r'(?:Póliza|Poliza|Cuenta)', texto_siguiente, re.IGNORECASE):
                    sub_doc.insert_pdf(doc, from_page=i+1, to_page=i+1)
                    
            pdf_bytes = sub_doc.tobytes()
            sub_doc.close()
            
            # Guardar en el diccionario asociándolo a la cuenta encontrada
            for m in matches: 
                cuenta_limpia = normalizar_numero(m)
                diccionario_extraido[cuenta_limpia] = pdf_bytes
                
    return diccionario_extraido

def preparar_tabla_digital_excel(df_tec, col_map):
    """
    FUNCIÓN ESTRICTA DE 5 COLUMNAS CON ORDEN REAL:
    Garantiza que el Excel que recibe el operario SOLO tenga las columnas solicitadas en la imagen,
    pero esta vez extrae el número de Orden real seleccionado por el usuario en lugar de inventar uno.
    [Cuenta, Dirección, Barrio, Orden, TECNICOS]
    """
    df_mini = df_tec.copy().reset_index(drop=True)
    
    # 2. Definir el mapeo de los nombres reales de la ruta vs los nombres estéticos para el técnico
    mapping = {
        col_map['CUENTA']: 'Cuenta',
        col_map['DIRECCION']: 'Dirección',
        col_map['BARRIO']: 'Barrio',
        col_map['ORDEN']: 'Orden',       # AHORA MAPEA LA COLUMNA DE ORDEN VERDADERA
        'TECNICO_FINAL': 'TECNICOS'
    }
    
    # 3. Filtrar para evitar errores si alguna columna de ruta no existe
    cols_presentes = {k: v for k, v in mapping.items() if k in df_mini.columns}
    
    # 4. Renombrar
    df_final = df_mini[list(cols_presentes.keys())].rename(columns=cols_presentes)
    
    # 5. Ordenar las columnas explícitamente según requerimiento de la imagen
    orden_deseado = ['Cuenta', 'Dirección', 'Barrio', 'Orden', 'TECNICOS']
    df_resultado = df_final[[c for c in orden_deseado if c in df_final.columns]]
    
    return df_resultado

def reordenar_operacion_global(df_estado, col_map):
    """
    Organiza automáticamente los registros conservando el orden original del Motor V74
    (que venía en la planilla de Excel), agrupando primero por Técnico y luego por Barrio.
    Garantiza que no se desorganice ninguna ruta al mover barrios de la bolsa.
    """
    df_w = df_estado.copy()
    if col_map and 'BARRIO' in col_map:
        col_barrio = col_map['BARRIO']
        
        # Garantizar que se respete el orden nativo con el que subieron el archivo
        if 'ORDEN_ORIGINAL' in df_w.columns:
            df_w = df_w.sort_values(by=['TECNICO_FINAL', col_barrio, 'ORDEN_ORIGINAL'])
        else:
            df_w = df_w.sort_values(by=['TECNICO_FINAL', col_barrio])
            
        df_w = df_w.reset_index(drop=True)
    return df_w

# =======================================================================================
# SECCIÓN 5: GENERACIÓN DE HOJA DE RUTA FÍSICA (PDF)
# =======================================================================================

class PDFListado(FPDF):
    def header(self):
        # Fondo del encabezado azul oscuro institucional
        self.set_fill_color(0, 51, 102) 
        self.rect(0, 0, 297, 20, 'F')
        self.set_font('Arial', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 5)
        self.cell(0, 10, 'UT ITA RADIAN - HOJA DE RUTA DE OPERACIONES', 0, 1, 'C')
        self.ln(10)

def crear_pdf_lista_final(df, tecnico, col_map):
    pdf = PDFListado(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    # Metadatos del Gestor
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    fecha = datetime.now().strftime('%d/%m/%Y')
    pdf.cell(0, 10, f"GESTOR: {tecnico} | FECHA: {fecha} | TOTAL VISITAS ASIGNADAS: {len(df)}", 0, 1)
    
    # Definición de tabla
    headers = ['#', 'CUENTA', 'MEDIDOR', 'BARRIO', 'DIRECCION', 'CLIENTE']
    widths = [10, 25, 25, 65, 85, 60]
    
    # Pintar Cabeceras
    pdf.set_fill_color(220, 220, 220)
    pdf.set_font('Arial', 'B', 9)
    for h, w in zip(headers, widths): 
        pdf.cell(w, 8, h, 1, 0, 'C', 1)
    pdf.ln()
    
    # Llenar datos
    pdf.set_font('Arial', '', 8)
    for idx, (_, row) in enumerate(df.iterrows(), start=1):
        barrio_txt = str(row[col_map['BARRIO']])
        
        # Alerta visual: Si la visita es de apoyo (vino de otro técnico), se marca en ROJO
        if pd.notna(row.get('ORIGEN_REAL')) and str(row.get('ORIGEN_REAL')) != tecnico:
            barrio_txt = f"[APOYO] {barrio_txt}"
            pdf.set_text_color(200, 0, 0) # Letra roja
        else:
            pdf.set_text_color(0, 0, 0) # Letra negra

        # Helper para evitar nulos y truncar largos
        def get_s(k):
            c = col_map.get(k)
            return str(row[c]) if c and c in df.columns and c != "NO TIENE" else ""

        row_data = [
            str(idx), 
            get_s('CUENTA'), 
            get_s('MEDIDOR')[:15], 
            barrio_txt[:38], 
            get_s('DIRECCION')[:60], 
            get_s('CLIENTE')[:30]
        ]
        
        # Escritura celda por celda manejando codificación latin-1 para FPDF
        for val, w in zip(row_data, widths):
            try: 
                val_e = val.encode('latin-1', 'replace').decode('latin-1')
            except: 
                val_e = val
            pdf.cell(w, 7, val_e, 1, 0, 'L')
        pdf.ln()
        
    return pdf.output(dest='S').encode('latin-1')

# =======================================================================================
# SECCIÓN 6: BARRA LATERAL, PERFILES Y ASISTENCIA
# =======================================================================================

with st.sidebar:
    st.markdown("""
        <div class="logo-container">
            <img src="https://cdn-icons-png.flaticon.com/512/2942/2942813.png" class="logo-img">
            <p class="logo-text">ITA RADIAN</p>
        </div>
    """, unsafe_allow_html=True)
    
    modo_acceso = st.selectbox("SELECCIONA TU PERFIL", ["👷 TÉCNICO", "⚙️ ADMINISTRADOR"], index=0)
    st.markdown("---")
    
    if modo_acceso == "⚙️ ADMINISTRADOR":
        # Control de Sesión Admin
        if st.session_state.get('admin_logged_in', False):
            # Widget de Asistencia Dinámica
            if st.session_state['mapa_actual']:
                st.markdown("### 📋 Gestión de Asistencia")
                st.info("Desmarca a los técnicos ausentes del día.")
                
                todos_tecnicos = sorted(list(set(st.session_state['mapa_actual'].values())))
                
                seleccion_activos = st.multiselect(
                    "Técnicos Habilitados Hoy:", 
                    options=todos_tecnicos, 
                    default=todos_tecnicos, 
                    key="widget_asistencia_dinamico"
                )
                st.session_state['tecnicos_activos_manual'] = seleccion_activos
                
                inactivos = len(todos_tecnicos) - len(seleccion_activos)
                if inactivos > 0: 
                    st.error(f"🔴 Atención: {inactivos} Técnicos INACTIVOS")
                else: 
                    st.success("🟢 Cuadrilla Completa")
            else:
                st.caption("ℹ️ Debes cargar el Maestro en la Pestaña 1 para habilitar el panel de asistencia.")
        else:
            st.markdown("""<div class="locked-msg">🔒 ACCESO RESTRINGIDO<br>Inicia sesión como administrador.</div>""", unsafe_allow_html=True)

    elif modo_acceso == "👷 TÉCNICO":
        st.info("Bienvenido al Portal de Autogestión Documental v14.3")

    st.markdown("---")
    st.caption("Plataforma Logística Integral ITA | 2026")

# =======================================================================================
# SECCIÓN 7: INTERFAZ DEL TÉCNICO (DESCARGAS)
# =======================================================================================

if modo_acceso == "👷 TÉCNICO":
    st.markdown('<div class="tech-header">ZONA DE DESCARGAS</div>', unsafe_allow_html=True)
    
    tecnicos_list = []
    if os.path.exists(CARPETA_PUBLICA):
        tecnicos_list = sorted([d for d in os.listdir(CARPETA_PUBLICA) if os.path.isdir(os.path.join(CARPETA_PUBLICA, d))])
    
    if not tecnicos_list:
        col_c1, col_c2, col_c3 = st.columns([1, 2, 1])
        with col_c2:
            st.warning("⏳ La operación del día aún no ha sido liberada por el despacho.")
            if st.button("🔄 Actualizar Vista", type="secondary"): 
                st.rerun()
    else:
        col_espacio1, col_centro, col_espacio2 = st.columns([1, 2, 1])
        with col_centro: 
            seleccion = st.selectbox("👇 BUSCA TU NOMBRE EN LA LISTA:", ["-- Seleccionar --"] + tecnicos_list)
        
        if seleccion != "-- Seleccionar --":
            path_tec = os.path.join(CARPETA_PUBLICA, seleccion)
            f_ruta = os.path.join(path_tec, "1_HOJA_DE_RUTA.pdf")
            f_excel = os.path.join(path_tec, "2_TABLA_DIGITAL.xlsx")
            f_leg = os.path.join(path_tec, "3_PAQUETE_LEGALIZACION.pdf")
            
            st.markdown(f"<h3 style='text-align:center; color:#0284C7; margin-top:20px;'>Hola, <span>{seleccion}</span></h3>", unsafe_allow_html=True)
            st.write("")
            
            c_izq, c_cen, c_der = st.columns(3)
            
            with c_izq:
                st.markdown("""<div style='background:#1E293B; padding:15px; border-radius:10px; border-left:5px solid #38BDF8;'><h5 style='color:#38BDF8; margin:0;'>📄 1. Ruta PDF</h5></div>""", unsafe_allow_html=True)
                st.write("")
                if os.path.exists(f_ruta):
                    with open(f_ruta, "rb") as f: 
                        st.download_button("⬇️ DESCARGAR PDF", f, f"Ruta_{seleccion}.pdf", "application/pdf", key="d_ruta", use_container_width=True)
                else: 
                    st.error("No disponible")
            
            with c_cen:
                st.markdown("""<div style='background:#1E293B; padding:15px; border-radius:10px; border-left:5px solid #FBBF24;'><h5 style='color:#FBBF24; margin:0;'>📊 2. Tabla Excel</h5></div>""", unsafe_allow_html=True)
                st.write("")
                if os.path.exists(f_excel):
                    with open(f_excel, "rb") as f: 
                        st.download_button("⬇️ DESCARGAR EXCEL", f, f"Tabla_{seleccion}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="d_excel", use_container_width=True)
                else: 
                    st.info("No disponible")
                
            with c_der:
                st.markdown("""<div style='background:#1E293B; padding:15px; border-radius:10px; border-left:5px solid #34D399;'><h5 style='color:#34D399; margin:0;'>📂 3. Pólizas</h5></div>""", unsafe_allow_html=True)
                st.write("")
                if os.path.exists(f_leg):
                    with open(f_leg, "rb") as f: 
                        st.download_button("⬇️ DESCARGAR PÓLIZAS", f, f"Leg_{seleccion}.pdf", "application/pdf", key="d_leg", use_container_width=True)
                else: 
                    st.info("No tienes pólizas asignadas hoy.")

# =======================================================================================
# SECCIÓN 8: VISTA DEL ADMINISTRADOR (DESPACHO Y LOGÍSTICA)
# =======================================================================================

elif modo_acceso == "⚙️ ADMINISTRADOR":
    
    # LOGIN
    if not st.session_state.get('admin_logged_in', False):
        col_login_spacer1, col_login, col_login_spacer2 = st.columns([1, 1, 1])
        with col_login:
            st.markdown("<h2 style='text-align: center; color:#1E3A8A;'>🔐 Panel de Control</h2>", unsafe_allow_html=True)
            password = st.text_input("Ingresa la clave maestra:", type="password", placeholder="********")
            if st.button("ACCEDER AL SISTEMA", type="primary"):
                if password == "ita2026":
                    st.session_state['admin_logged_in'] = True
                    st.success("✅ Acceso Concedido. Iniciando módulos...")
                    time.sleep(0.5)
                    st.rerun()
                else: 
                    st.error("❌ Contraseña Incorrecta.")
    
    # SISTEMA PRINCIPAL ADMINISTRADOR
    else:
        col_tit, col_logout = st.columns([4, 1])
        with col_tit: 
            st.markdown("## ⚙️ Centro de Comando Logístico v14.3")
        with col_logout:
            if st.button("Cerrar Sesión Segura"):
                st.session_state['admin_logged_in'] = False
                st.rerun()
        
        tab1, tab2, tab3, tab4 = st.tabs([
            "1. 🗃️ Base de Zonas", 
            "2. ⚖️ Carga de Ruta", 
            "3. 🛠️ Tablero de Operación", 
            "4. 🌍 Generación y Entrega"
        ])
        
        # -------------------------------------------------------------------------------
        # TAB 1: CARGA DE MAESTRO ZONIFICACIÓN
        # -------------------------------------------------------------------------------
        with tab1:
            st.markdown("### Acciones de Mantenimiento de Base")
            col_reset, col_explain = st.columns([1, 2])
            
            with col_reset:
                if st.button("🗑️ REINICIAR SISTEMA (LIMPIAR MEMORIA)", type="primary"):
                    st.session_state['mapa_actual'] = {}
                    st.session_state['mapa_telefonos'] = {}
                    st.session_state['df_simulado'] = None
                    st.session_state['col_map_final'] = None
                    st.session_state['mapa_polizas_cargado'] = {}
                    st.session_state['zip_admin_ready'] = None
                    st.session_state['tecnicos_activos_manual'] = []
                    st.session_state['ultimo_archivo_procesado'] = None
                    st.session_state['limites_cupo'] = {}
                    st.success("✅ Sistema purgado y listo para un nuevo día.")
                    time.sleep(1)
                    st.rerun()
                    
            with col_explain:
                st.caption("⚠️ Obligatorio usar antes de subir archivos de un día nuevo para evitar mezclar datos.")

            st.divider()
            st.markdown("### Cargar Asignación de Zonas (Maestro)")
            st.info("Soporta archivo clásico y archivo 'OPERARIOS REINSTALACION'")
            
            f_maestro = st.file_uploader("Selecciona el archivo Maestro (Excel o CSV)", type=["xlsx", "csv"])
            
            if f_maestro:
                if st.session_state.get('ultimo_archivo_procesado') != f_maestro.name:
                    with st.spinner("Leyendo estructura y mapeando zonas..."):
                        nuevo_mapa, nuevos_telefonos = cargar_maestro_dinamico(f_maestro)
                        if nuevo_mapa:
                            st.session_state['mapa_actual'] = nuevo_mapa
                            st.session_state['mapa_telefonos'] = nuevos_telefonos
                            st.session_state['df_simulado'] = None 
                            st.session_state['tecnicos_activos_manual'] = []
                            st.session_state['ultimo_archivo_procesado'] = f_maestro.name
                            st.success(f"✅ Lectura exitosa: {len(nuevo_mapa)} zonas/barrios registrados en el sistema.")
                            time.sleep(1)
                            st.rerun() 
                        else: 
                            st.error("❌ Falla en la lectura. Revisa que el archivo contenga las columnas correctas.")
                else: 
                    st.info(f"El archivo '{f_maestro.name}' está actualmente cargado en memoria.")
            
            if st.session_state['mapa_actual']:
                st.write(f"**Total Entidades Zonales (Barrios/Unidades):** {len(st.session_state['mapa_actual'])}")
                st.write(f"**Total Plantilla de Operarios:** {len(set(st.session_state['mapa_actual'].values()))}")

        # -------------------------------------------------------------------------------
        # TAB 2: PROCESAMIENTO DE ARCHIVOS DIARIOS
        # -------------------------------------------------------------------------------
        with tab2:
            st.markdown("### Ingesta de Archivos Diarios")
            
            c_pdf, c_xls = st.columns(2)
            
            with c_pdf:
                st.markdown("**Paso 1: Digitalización de Pólizas (PDF)**")
                up_pdfs = st.file_uploader("Arrastra los archivos PDF del banco de pólizas", type="pdf", accept_multiple_files=True)
                if up_pdfs and st.button("EJECUTAR ESCÁNER PDF"):
                    with st.spinner("Analizando documentos, extrayendo cuentas y fragmentando páginas..."):
                        diccionario_global_polizas = {}
                        for pdf_obj in up_pdfs:
                            resultado_parcial = procesar_pdf_polizas_avanzado(pdf_obj)
                            diccionario_global_polizas.update(resultado_parcial)
                        
                        st.session_state['mapa_polizas_cargado'] = diccionario_global_polizas
                        st.success(f"✅ Escaneo finalizado: {len(st.session_state['mapa_polizas_cargado'])} Pólizas procesadas desde {len(up_pdfs)} archivo(s).")

            with c_xls:
                st.markdown("**Paso 2: Carga de Ruta Diaria (Excel)**")
                up_xls = st.file_uploader("Arrastra el Excel exportado del sistema", type=["xlsx", "csv"])
            
            # Verificar técnicos activos desde el menú lateral
            if 'tecnicos_activos_manual' in st.session_state and st.session_state['tecnicos_activos_manual']:
                tecnicos_hoy = st.session_state['tecnicos_activos_manual']
            elif st.session_state['mapa_actual']:
                tecnicos_hoy = sorted(list(set(st.session_state['mapa_actual'].values())))
            else: 
                tecnicos_hoy = []

            if up_xls and tecnicos_hoy:
                # Leer ruta
                if up_xls.name.endswith('.csv'): 
                    df_ruta = pd.read_csv(up_xls, sep=None, engine='python', encoding='utf-8-sig')
                else: 
                    df_ruta = pd.read_excel(up_xls)
                
                # Filtrar columnas
                cols_limpias = []
                for col in df_ruta.columns:
                    col_str = str(col).strip()
                    if col_str not in cols_limpias: 
                        cols_limpias.append(col_str)
                
                st.divider()
                st.markdown("#### Configuración de Restricciones (Cupo Máximo)")
                st.info("Ajusta la capacidad de cada operario. Todo lo que supere este número se enviará a la Bolsa Pendiente.")
                
                df_cupos = pd.DataFrame({
                    "Técnico": tecnicos_hoy, 
                    "Cupo": [35] * len(tecnicos_hoy) # Default 35
                })
                
                editor_cupos = st.data_editor(
                    df_cupos, 
                    column_config={"Cupo": st.column_config.NumberColumn(min_value=1, step=1)}, 
                    hide_index=True, 
                    use_container_width=True
                )
                diccionario_limites = dict(zip(editor_cupos["Técnico"], editor_cupos["Cupo"]))
                
                # Auto-detector de columnas
                def buscar_columna_inteligente(palabras_clave, opcional=False):
                    for i, nombre_col in enumerate(cols_limpias):
                        for palabra in palabras_clave:
                            if palabra in nombre_col.upper():
                                return i + 1 if opcional else i
                    return 0
                
                st.markdown("#### Mapeo de Columnas Principales")
                
                col_sel_1, col_sel_2, col_sel_3, col_sel_4 = st.columns(4)
                
                sel_barrio = col_sel_1.selectbox("Columna Barrio", cols_limpias, index=buscar_columna_inteligente(['BARRIO', 'ZONA', 'UNIDAD']))
                sel_dir = col_sel_2.selectbox("Columna Dirección", cols_limpias, index=buscar_columna_inteligente(['DIR','DIRECCION', 'UBICACION']))
                sel_cuenta = col_sel_3.selectbox("Columna Cuenta", cols_limpias, index=buscar_columna_inteligente(['CUENTA', 'CONTRATO', 'CODIGO']))
                sel_orden = col_sel_4.selectbox("Columna Orden (Real)", cols_limpias, index=buscar_columna_inteligente(['ORDEN', 'PEDIDO', 'TICKET', 'SERVICIO']))
                
                st.markdown("#### Columnas Opcionales")
                opciones_nulas = ["NO TIENE"] + cols_limpias
                col_sel_5, col_sel_6 = st.columns(2)
                sel_medidor = col_sel_5.selectbox("Columna Medidor", opciones_nulas, index=buscar_columna_inteligente(['MEDIDOR', 'APARATO', 'SERIAL'], True))
                sel_cliente = col_sel_6.selectbox("Columna Cliente", opciones_nulas, index=buscar_columna_inteligente(['CLIENTE', 'NOMBRE', 'USUARIO'], True))
                
                mapa_columnas = {
                    'BARRIO': sel_barrio, 
                    'DIRECCION': sel_dir, 
                    'CUENTA': sel_cuenta, 
                    'ORDEN': sel_orden,
                    'MEDIDOR': sel_medidor if sel_medidor != "NO TIENE" else None, 
                    'CLIENTE': sel_cliente if sel_cliente != "NO TIENE" else None
                }
                
                # BOTÓN DE EJECUCIÓN PRINCIPAL
                if st.button("🚀 INICIAR ALGORITMO DE DISTRIBUCIÓN", type="primary"):
                    if up_pdfs and not st.session_state['mapa_polizas_cargado']:
                        diccionario_global_polizas = {}
                        for pdf_obj in up_pdfs:
                            resultado_parcial = procesar_pdf_polizas_avanzado(pdf_obj)
                            diccionario_global_polizas.update(resultado_parcial)
                        st.session_state['mapa_polizas_cargado'] = diccionario_global_polizas
                    
                    st.session_state['limites_cupo'] = diccionario_limites
                    df_procesamiento = df_ruta.copy()
                    
                    # 1. Asignación Primaria (El Deber Ser)
                    df_procesamiento['TECNICO_IDEAL'] = df_procesamiento[sel_barrio].apply(lambda x: buscar_tecnico_exacto(x, st.session_state['mapa_actual']))
                    df_procesamiento['TECNICO_FINAL'] = df_procesamiento['TECNICO_IDEAL']
                    df_procesamiento['ORIGEN_REAL'] = None
                    df_procesamiento['ORDEN_ORIGINAL'] = range(len(df_procesamiento))
                    
                    # 2. Ordenamiento Geográfico (Respetando el motor V74 original)
                    df_procesamiento = df_procesamiento.sort_values(by=[sel_barrio, 'ORDEN_ORIGINAL'])

                    # 3. Aplicación de Reglas de Negocio (Ausencias)
                    mascara_ausentes = ~df_procesamiento['TECNICO_FINAL'].isin(tecnicos_hoy)
                    df_procesamiento.loc[mascara_ausentes, 'ORIGEN_REAL'] = "TÉCNICO INACTIVO/AUSENTE"
                    df_procesamiento.loc[mascara_ausentes, 'TECNICO_FINAL'] = "⚠️ BOLSA PENDIENTE"
                    
                    # 4. Aplicación de Reglas de Negocio (Sobrecarga / Cupos)
                    for tecnico_activo in tecnicos_hoy:
                        capacidad_max = diccionario_limites.get(tecnico_activo, 35)
                        indices_del_tecnico = df_procesamiento[df_procesamiento['TECNICO_FINAL'] == tecnico_activo].index
                        
                        if len(indices_del_tecnico) > capacidad_max:
                            excedente_cantidad = len(indices_del_tecnico) - capacidad_max
                            
                            df_tec_temp = df_procesamiento.loc[indices_del_tecnico].copy()
                            mapa_vol = df_tec_temp[sel_barrio].value_counts().to_dict()
                            df_tec_temp['VOL_TEMP'] = df_tec_temp[sel_barrio].map(mapa_vol)
                            indices_del_tecnico = df_tec_temp.sort_values(by=['VOL_TEMP', sel_barrio], ascending=[False, True]).index.tolist()

                            indices_a_mover = indices_del_tecnico[-excedente_cantidad:]
                            
                            df_procesamiento.loc[indices_a_mover, 'ORIGEN_REAL'] = "EXCEDE CUPO MÁXIMO"
                            df_procesamiento.loc[indices_a_mover, 'TECNICO_FINAL'] = "⚠️ BOLSA PENDIENTE"

                    # === REORGANIZACIÓN GLOBAL AUTOMÁTICA ===
                    df_final_procesado = reordenar_operacion_global(df_procesamiento, mapa_columnas)

                    # Guardar en memoria
                    st.session_state['df_simulado'] = df_final_procesado
                    st.session_state['col_map_final'] = mapa_columnas
                    st.success("✅ Algoritmo completado respetando Orden V74. Dirígete a la Pestaña 3 para el Ajuste Logístico Manual.")

            elif not tecnicos_hoy and st.session_state['mapa_actual']:
                st.error("⚠️ La lista de técnicos activos está vacía. Verifica el panel lateral.")

        # -------------------------------------------------------------------------------
        # TAB 3: TABLERO INTERACTIVO KANBAN (GESTIÓN DE CARGA)
        # -------------------------------------------------------------------------------
        with tab3:
            st.markdown("### 🛠️ Matriz Operativa de Traslados")
            st.info("💡 Interfaz: Haz clic en el botón de un barrio para mover la cantidad deseada, o usa el botón para mover cargas completas.")
            
            if st.session_state['df_simulado'] is not None:
                dataframe_matriz = st.session_state['df_simulado']
                columna_barrio_nombre = st.session_state['col_map_final']['BARRIO']
                dicc_limites = st.session_state.get('limites_cupo', {})
                
                if 'tecnicos_activos_manual' in st.session_state and st.session_state['tecnicos_activos_manual']:
                    cuadrilla_presente = sorted(st.session_state['tecnicos_activos_manual'])
                else:
                    cuadrilla_presente = sorted(list(set(st.session_state['mapa_actual'].values())))

                opciones_para_destino = ["⚠️ BOLSA PENDIENTE"] + cuadrilla_presente

                # -------------------------------------------------------------------
                # SECCIÓN 3.1: BOLSA PENDIENTE INTELIGENTE (AGRUPADA, NARANJA Y CON BOTÓN MASIVO)
                # -------------------------------------------------------------------
                visitas_huerfanas = dataframe_matriz[dataframe_matriz['TECNICO_FINAL'] == "⚠️ BOLSA PENDIENTE"]
                
                if not visitas_huerfanas.empty:
                    st.markdown("#### 🚨 Carga Pendiente en Despacho")
                    
                    agrupacion_bolsas = visitas_huerfanas.groupby('TECNICO_IDEAL')
                    
                    for dueno_maestro, datos_bolsa_dueno in agrupacion_bolsas:
                        
                        lista_motivos = [str(m) for m in datos_bolsa_dueno['ORIGEN_REAL'].unique() if pd.notna(m)]
                        motivos_unidos = " y ".join(lista_motivos) if lista_motivos else "Asignación Manual a Bolsa"
                        
                        with st.expander(f"📦 ZONA MAESTRA: {dueno_maestro} ({len(datos_bolsa_dueno)} visitas en espera)", expanded=True):
                            st.markdown(f'<div class="bolsa-card"><b>Origen:</b> Zona de {dueno_maestro}<br><b>Motivo de retención:</b> {motivos_unidos}</div>', unsafe_allow_html=True)
                            
                            st.markdown('<div class="btn-masivo-naranja">', unsafe_allow_html=True)
                            if st.button(f"🚀 REASIGNAR TODA LA BOLSA DE {dueno_maestro}", key=f"btn_masivo_bolsa_{dueno_maestro}"):
                                modal_reasignar_bolsa(dueno_maestro, cuadrilla_presente, dataframe_matriz)
                            st.markdown('</div>', unsafe_allow_html=True)
                            
                            resumen_agrupado = datos_bolsa_dueno.groupby([columna_barrio_nombre]).size().reset_index(name='TOTAL')
                            columnas_grid_bolsa = st.columns(6)
                            
                            for indice_b, fila_barrio in resumen_agrupado.iterrows():
                                nombre_b = fila_barrio[columna_barrio_nombre]
                                cantidad_b = fila_barrio['TOTAL']
                                
                                with columnas_grid_bolsa[indice_b % 6]:
                                    st.markdown('<div class="btn-bolsa-naranja">', unsafe_allow_html=True)
                                    if st.button(f"{nombre_b} ({cantidad_b})", key=f"btn_bolsa_dinamica_{dueno_maestro}_{indice_b}"):
                                        modal_traslado("⚠️ BOLSA PENDIENTE", nombre_b, cantidad_b, opciones_para_destino, dataframe_matriz, columna_barrio_nombre)
                                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.success("🎉 ¡Excelente! La Bolsa Pendiente está en cero. Toda la ruta está asignada.")
                
                st.divider()
                
                # -------------------------------------------------------------------
                # SECCIÓN 3.2: CUADRILLA ACTIVA (TABLERO PRINCIPAL CON BOTONES AZULES Y ROJOS)
                # -------------------------------------------------------------------
                st.markdown("#### 👷 Asignación Actual en Terreno")
                
                grid_tecnicos = st.columns(3)
                for index_tecnico, nombre_tecnico in enumerate(cuadrilla_presente):
                    with grid_tecnicos[index_tecnico % 3]:
                        
                        data_tecnico = dataframe_matriz[dataframe_matriz['TECNICO_FINAL'] == nombre_tecnico]
                        visitas_asignadas = len(data_tecnico)
                        capacidad_tecnico = dicc_limites.get(nombre_tecnico, 35)
                        
                        if visitas_asignadas == 0:
                            titulo_acordeon = f"🟢 {nombre_tecnico} (DESOCUPADO - 0 / {capacidad_tecnico})"
                        elif visitas_asignadas > capacidad_tecnico:
                            titulo_acordeon = f"🔴 {nombre_tecnico} ({visitas_asignadas} / {capacidad_tecnico} - SOBRECARGA)"
                        else:
                            titulo_acordeon = f"👷 {nombre_tecnico} ({visitas_asignadas} / {capacidad_tecnico})"
                            
                        with st.expander(titulo_acordeon, expanded=(visitas_asignadas > 0)):
                            if visitas_asignadas > 0:
                                
                                st.markdown('<div class="btn-masivo">', unsafe_allow_html=True)
                                if st.button(f"🔴 TRASLADAR TODA LA CARGA DE {nombre_tecnico}", key=f"btn_masivo_vaciar_{nombre_tecnico}"):
                                    modal_masivo(nombre_tecnico, opciones_para_destino, dataframe_matriz)
                                st.markdown('</div>', unsafe_allow_html=True)
                                
                                agrupacion_barrios_tecnico = data_tecnico.groupby([columna_barrio_nombre]).size().reset_index(name='CANTIDAD')
                                
                                # SE APLICAN 2 COLUMNAS INTERNAS PARA IMITAR LA CUADRÍCULA DE LA IMAGEN 1
                                grid_barrios = st.columns(2) 
                                
                                for index_barrio, fila_b_tecnico in agrupacion_barrios_tecnico.iterrows():
                                    texto_barrio = fila_b_tecnico[columna_barrio_nombre]
                                    numero_barrio = fila_b_tecnico['CANTIDAD']
                                    
                                    with grid_barrios[index_barrio % 2]:
                                        st.markdown('<div class="btn-barrio">', unsafe_allow_html=True)
                                        if st.button(f"📍 {texto_barrio}\n({numero_barrio})", key=f"btn_mover_{nombre_tecnico}_{index_barrio}"):
                                            modal_traslado(nombre_tecnico, texto_barrio, numero_barrio, opciones_para_destino, dataframe_matriz, columna_barrio_nombre)
                                        st.markdown('</div>', unsafe_allow_html=True)
                            else:
                                st.caption("Este operario no tiene asignaciones. Listo para recibir apoyo.")
            else: 
                st.info("Esperando datos de ruta. Completa el Paso 2.")

        # -------------------------------------------------------------------------------
        # TAB 4: GENERACIÓN, REPORTES Y DESCARGAS GLOBALES
        # -------------------------------------------------------------------------------
        with tab4:
            st.markdown("### 🌍 Consolidación y Exportación de Operación")
            if st.session_state['df_simulado'] is not None:
                dataframe_final = st.session_state['df_simulado']
                
                # Filtro de seguridad
                volumen_pendiente = len(dataframe_final[dataframe_final['TECNICO_FINAL'] == "⚠️ BOLSA PENDIENTE"])
                if volumen_pendiente > 0:
                    st.error(f"🛑 CRÍTICO: Tienes {volumen_pendiente} visitas atascadas en la 'Bolsa Pendiente'. Debes regresar a la Pestaña 3 y asignarlas a los operarios activos antes de ejecutar la publicación.")
                else:
                    conf_columnas = st.session_state['col_map_final']
                    conf_polizas = st.session_state['mapa_polizas_cargado']
                    lista_tecnicos_con_carga = [t for t in dataframe_final['TECNICO_FINAL'].unique() if "SIN_" not in t and "⚠️" not in t]
                    
                    columna_btn1, columna_btn2 = st.columns(2)
                    
                    # ---- BOTÓN 1: PUBLICAR EN LA WEB PARA LOS TÉCNICOS ----
                    with columna_btn1:
                        st.markdown("#### ☁️ Portal Web Movil")
                        st.info("Sube los archivos a la nube para que los técnicos puedan descargarlos desde su celular.")
                        if st.button("📢 ENVIAR ARCHIVOS AL PORTAL", type="primary"):
                            gestionar_sistema_archivos("limpiar")
                            barra_progreso = st.progress(0)
                            
                            for iterador, nombre_operario in enumerate(lista_tecnicos_con_carga):
                                # Copia limpia para este técnico
                                dt_operario = dataframe_final[dataframe_final['TECNICO_FINAL'] == nombre_operario].copy()
                                
                                # Aplicamos orden V74 original en lugar de destructivo natural_sort_key
                                if 'ORDEN_ORIGINAL' in dt_operario.columns:
                                    dt_operario = dt_operario.sort_values(by=[conf_columnas['BARRIO'], 'ORDEN_ORIGINAL'])
                                else:
                                    dt_operario = dt_operario.sort_values(by=[conf_columnas['BARRIO']])
                                
                                carpeta_segura = str(nombre_operario).replace(" ","_")
                                ruta_carpeta = os.path.join(CARPETA_PUBLICA, carpeta_segura)
                                os.makedirs(ruta_carpeta, exist_ok=True)
                                
                                # ARTEFACTO 1: Hoja de Ruta PDF
                                with open(os.path.join(ruta_carpeta, "1_HOJA_DE_RUTA.pdf"), "wb") as f_pdf_ruta:
                                    f_pdf_ruta.write(crear_pdf_lista_final(dt_operario, nombre_operario, conf_columnas))
                                
                                # ARTEFACTO 2: Tabla Digital Excel
                                df_5_columnas = preparar_tabla_digital_excel(dt_operario, conf_columnas)
                                with pd.ExcelWriter(os.path.join(ruta_carpeta, "2_TABLA_DIGITAL.xlsx"), engine='xlsxwriter') as w_excel: 
                                    df_5_columnas.to_excel(w_excel, index=False)
                                
                                # ARTEFACTO 3: Consolidado de Pólizas PDF
                                if conf_polizas:
                                    motor_fusion = fitz.open()
                                    contador_polizas = 0
                                    
                                    for _, fila_dato in dt_operario.iterrows():
                                        num_cuenta = normalizar_numero(str(fila_dato[conf_columnas['CUENTA']]))
                                        if num_cuenta in conf_polizas:
                                            with fitz.open(stream=conf_polizas[num_cuenta], filetype="pdf") as pdf_individual: 
                                                motor_fusion.insert_pdf(pdf_individual)
                                            contador_polizas += 1
                                            
                                    if contador_polizas > 0:
                                        with open(os.path.join(ruta_carpeta, "3_PAQUETE_LEGALIZACION.pdf"), "wb") as f_pdf_pol: 
                                            f_pdf_pol.write(motor_fusion.tobytes())
                                    motor_fusion.close()
                                
                                barra_progreso.progress((iterador + 1) / len(lista_tecnicos_con_carga))
                                
                            st.success("✅ Operación completada. Los operarios ya pueden entrar a descargar.")
                            st.balloons()
                    
                    # ---- BOTÓN 2: GENERAR ZIP Y REPORTE TXT PARA OFICINA ----
                    with columna_btn2:
                        st.markdown("#### 📦 Archivo Físico Despacho")
                        st.info("Genera el archivo ZIP con todas las rutas, excels y el **Reporte de Pólizas Faltantes**.")
                        
                        if st.button("DESCARGAR ZIP MAESTRO (CON REPORTE)"):
                            buffer_zip = io.BytesIO()
                            
                            with zipfile.ZipFile(buffer_zip, "w") as archivo_z:
                                
                                # 1. CONSOLIDADO GENERAL INTACTO
                                buffer_excel_maestro = io.BytesIO() 
                                # Ocultamos el ORDEN_ORIGINAL del Excel final ya que es uso interno
                                df_export_maestro = dataframe_final.drop(columns=['ORDEN_ORIGINAL']) if 'ORDEN_ORIGINAL' in dataframe_final.columns else dataframe_final
                                with pd.ExcelWriter(buffer_excel_maestro, engine='xlsxwriter') as wr_maestro: 
                                    df_export_maestro.to_excel(wr_maestro, index=False)
                                archivo_z.writestr("00_CONSOLIDADO_GENERAL.xlsx", buffer_excel_maestro.getvalue())
                                
                                # ---------------------------------------------------------------------
                                # 2. LÓGICA DE CRUCE DOCUMENTAL (EL REPORTE TXT SOLICITADO)
                                # ---------------------------------------------------------------------
                                string_reporte = f"REPORTE OFICIAL DE CRUCE DOCUMENTAL - PÓLIZAS FALTANTES\n"
                                string_reporte += f"FECHA DE GENERACIÓN: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                                string_reporte += "="*85 + "\n\n"
                                
                                if not conf_polizas:
                                    string_reporte += "ALERTA DEL SISTEMA: No se ingresó ningún documento PDF con pólizas.\n"
                                    string_reporte += "Asumiendo que toda la operación carece de soportes documentales.\n"
                                else:
                                    conjunto_cuentas_pdf = set(conf_polizas.keys())
                                    df_analisis_cruce = dataframe_final.copy()
                                    df_analisis_cruce['CUENTA_MATCH'] = df_analisis_cruce[conf_columnas['CUENTA']].astype(str).apply(normalizar_numero)
                                    
                                    df_sin_poliza = df_analisis_cruce[
                                        ~df_analisis_cruce['CUENTA_MATCH'].isin(conjunto_cuentas_pdf) & 
                                        (df_analisis_cruce['CUENTA_MATCH'] != '')
                                    ]
                                    
                                    if df_sin_poliza.empty:
                                        string_reporte += "ESTADO: EXCELENTE (0 FALTANTES)\n"
                                        string_reporte += "Todas las visitas planificadas cuentan con su póliza respectiva en el sistema.\n"
                                    else:
                                        string_reporte += f"ESTADO: REQUIERE ATENCIÓN - Faltan {len(df_sin_poliza)} documentos físicos.\n\n"
                                        string_reporte += "LISTADO DETALLADO POR OPERARIO Y ZONA:\n"
                                        string_reporte += "-"*85 + "\n"
                                        string_reporte += f"{'CUENTA'.ljust(15)} | {'TÉCNICO'.ljust(25)} | {'BARRIO'}\n"
                                        string_reporte += "-"*85 + "\n"
                                        
                                        df_sin_poliza = df_sin_poliza.sort_values(by=['TECNICO_FINAL', conf_columnas['BARRIO']])
                                        
                                        for _, fila_cruce in df_sin_poliza.iterrows():
                                            t_cuenta = str(fila_cruce['CUENTA_MATCH']).ljust(15)
                                            t_tecnico = str(fila_cruce['TECNICO_FINAL'])[:23].ljust(25)
                                            t_barrio = str(fila_cruce[conf_columnas['BARRIO']])[:40]
                                            string_reporte += f"{t_cuenta} | {t_tecnico} | {t_barrio}\n"
                                
                                archivo_z.writestr("00_REPORTE_POLIZAS_FALTANTES.txt", string_reporte.encode('utf-8'))
                                # ---------------------------------------------------------------------

                                # 3. GENERAR CARPETAS INDIVIDUALES
                                for tech_name in lista_tecnicos_con_carga:
                                    folder_name = str(tech_name).replace(" ","_")
                                    datos_tech = dataframe_final[dataframe_final['TECNICO_FINAL'] == tech_name].copy()
                                    
                                    # Aplicamos orden V74 original
                                    if 'ORDEN_ORIGINAL' in datos_tech.columns:
                                        datos_tech = datos_tech.sort_values(by=[conf_columnas['BARRIO'], 'ORDEN_ORIGINAL'])
                                    else:
                                        datos_tech = datos_tech.sort_values(by=[conf_columnas['BARRIO']])
                                    
                                    # Ruta PDF
                                    archivo_z.writestr(f"{folder_name}/1_HOJA_DE_RUTA.pdf", crear_pdf_lista_final(datos_tech, tech_name, conf_columnas))
                                    
                                    # Tabla Digital 5 Columnas
                                    buffer_tech_xls = io.BytesIO()
                                    df_tech_5col = preparar_tabla_digital_excel(datos_tech, conf_columnas)
                                    with pd.ExcelWriter(buffer_tech_xls, engine='xlsxwriter') as wr_tech: 
                                        df_tech_5col.to_excel(wr_tech, index=False)
                                    archivo_z.writestr(f"{folder_name}/2_TABLA_DIGITAL.xlsx", buffer_tech_xls.getvalue())
                                    
                                    # Pólizas
                                    if conf_polizas:
                                        motor_poliza = fitz.open()
                                        num_inserts = 0
                                        for _, r_data in datos_tech.iterrows():
                                            cuenta_clean = normalizar_numero(str(r_data[conf_columnas['CUENTA']]))
                                            if cuenta_clean in conf_polizas:
                                                with fitz.open(stream=conf_polizas[cuenta_clean], filetype="pdf") as px: 
                                                    motor_poliza.insert_pdf(px)
                                                num_inserts += 1
                                        if num_inserts > 0: 
                                            archivo_z.writestr(f"{folder_name}/3_PAQUETE_LEGALIZACION.pdf", motor_poliza.tobytes())
                                        motor_poliza.close()
                                        
                            st.session_state['zip_admin_ready'] = buffer_zip.getvalue()
                            st.success("✅ Archivo ZIP Creado Exitosamente. Incluye Reporte de Faltantes.")
                        
                        # Botón persistente de descarga
                        if st.session_state.get('zip_admin_ready'):
                            st.download_button(
                                label="⬇️ DESCARGAR SISTEMA COMPLETO (ZIP)", 
                                data=st.session_state['zip_admin_ready'], 
                                file_name=f"Logistica_ITA_{datetime.now().strftime('%Y%m%d_%H%M')}.zip", 
                                mime="application/zip", 
                                use_container_width=True
                            )

            else: 
                st.info("Para exportar, primero debes procesar la información en la Pestaña 2.")
