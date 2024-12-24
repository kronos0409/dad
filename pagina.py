import pandas as pd
import streamlit as st
import os
import time
import warnings
import io
import numpy as np
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=pd.errors.SettingWithCopyWarning)
st.header("Empezando pruebas")
if "accion" not in st.session_state:
    st.session_state.accion = None
if "texto" not in st.session_state:
    st.session_state.texto = ''
def procesar_hojas(archivo,tramo):
    xls = pd.read_excel(archivo,sheet_name=None)
    output = io.BytesIO()
    if tramo != '':
        hojas_procesadas = [dividir_en_tramos(df, tramo) for df in xls.values()]
        df_consolidado = hojas_procesadas[0]
        progreso = st.progress(0)
        patron = len(hojas_procesadas)
        patron = int(np.round(100/(patron)))
        n = 0
        st.write(hojas_procesadas[1:])
        for hoja in hojas_procesadas[1:]:
            n+=1
            df_consolidado = pd.merge(df_consolidado, hoja, on=['HOLEID', 'From', 'To'], how='outer')
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_consolidado.to_excel(writer, index=False)
            output.seek(0)
            progress =n*patron
            progreso.progress(progress)
        progreso.progress(100)
        return output
def dividir_en_tramos(df, tramo_size):
    filas_tramos = []
    for holeid in df['HOLEID'].unique():
        sub_df = df[df['HOLEID'] == holeid]
        max_to = sub_df['To'].max()  # Usamos el valor máximo de 'To' solo al final de cada HOLEID
        current_from = 0  # Iniciar 'From' en 0 para cada HOLEID
        
        while current_from < max_to:
            current_to = current_from + tramo_size
            mensaje = ''  # Reiniciar mensaje en cada tramo
            
            # Filtrar filas dentro del rango actual
            mask = (sub_df['From'] < current_to) & (sub_df['To'] > current_from)
            matching_rows = sub_df[mask]
            
            if not matching_rows.empty:
                row_principal,mensaje_ERROR = obtener_holeid_principal(matching_rows, current_from, current_to)
                
                # Agregar el mensaje si es el último tramo que supera el max_to
                to_actual = matching_rows.iloc[0]['To']
                if current_to>to_actual:
                    mensaje = mensaje_ERROR
                if current_to > max_to:
                    current_to = max_to  # Limitar current_to solo si ya es el último tramo del HOLEID
                    mensaje= mensaje_ERROR
                nueva_fila = [holeid, current_from, current_to] + row_principal.iloc[3:].to_list()[:len(df.columns) - 3] + [mensaje]
            else:
                nueva_fila = [holeid, current_from, current_to] + [None] * (len(df.columns) - 3) + [mensaje]
            
            filas_tramos.append(nueva_fila)
            current_from = current_to  # Avanzar al siguiente tramo
    
    columnas = ['HOLEID', 'From', 'To'] + df.columns[3:].to_list()[:len(df.columns)-3] + ['mensaje']
    return pd.DataFrame(filas_tramos, columns=columnas)
def obtener_holeid_principal(matching_rows, current_from, current_to):
    matching_rows['covered_range'] = matching_rows.apply(lambda row: min(row['To'], current_to) - max(row['From'], current_from), axis=1)
    max_covered_range = matching_rows['covered_range'].max()
    top_rows = matching_rows[matching_rows['covered_range'] == max_covered_range]
    if len(top_rows) > 1:
        combined_row = top_rows.iloc[0].copy()
        for col in top_rows.columns[3:]:  
            combined_values = "/".join(top_rows[col].astype(str).unique())
            combined_row[col] = combined_values
        return combined_row, "ERROR 50%"
    if len(matching_rows) == 1:
        return top_rows.iloc[0], ""
    return top_rows.iloc[0], "2 o mas"
def Menu():
    
    st.subheader("El codigo esta diseñado pensando en que tengas una hoja extra sin informacion que actua como una clase de leyenda, si no tienes esa hoja, agrega una vacia porfavor y asegurate que esta este al ultimo")
    st.write("Tambien si tienes la columna 'length' o una columna que actue como sustituto, porfavor eliminala")
    st.write("Cuando tengas la optimizacion hecha, subelo a la pagina")
    funcion=st.radio("Selecciona lo que desees hacer",index=None ,options = ["1-Filtrado", "2-Optimizacion", "3-Tramos (no ejecutar sin antes optimizar)"])
    if funcion == '1-Filtrado' :
        funcion = 1
    elif funcion == "2-Optimizacion":
        funcion = 2
    elif funcion == "3-Tramos (no ejecutar sin antes optimizar)":
        funcion=3
    else:
        funcion = 0
    aplicar = st.button("Aplicar función")
    return aplicar,funcion
def Conseguir_archivo():
    tramo = st.toggle("Tienes la optimizacion hecha?")
    return st.file_uploader("introduce tu archivo", accept_multiple_files=tramo),tramo
def Filtrado(archivo):
    data = {}
    xlsx = pd.ExcelFile(archivo)
    progreso = st.progress(0)
    patron = len(xlsx.sheet_names[:-1])
    patron = int(np.round(100/((patron*2)+1)))
    n = 0
    for sheet in xlsx.sheet_names[:-1]:
        n+=1
        start = time.time()
        df = pd.read_excel(xlsx, sheet_name=sheet)
        df['traslapo'] = (df['To'] > df['From'].shift(-1)) & (df['HOLEID'] == df['HOLEID'].shift(-1))
        df['traslapo'] = df['traslapo'].apply(lambda x: 'T' if x else 'F')
        df['vacio'] = (df['To'] < df['From'].shift(-1)) & (df['HOLEID'] == df['HOLEID'].shift(-1))
        df['vacio'] = df['vacio'].apply(lambda x: 'T' if x else 'F')
        df['cuadro vacio'] = df.isnull().any(axis=1).apply(lambda x: 'T' if x else 'F')
        df['revisar'] = "F"
        for i in range(len(df) - 1):
            if df.loc[i, 'traslapo']=='T' or df.loc[i,'vacio']== 'T':
                df.loc[i, 'revisar'] = 'T'
                df.loc[i + 1, 'revisar'] = 'T'
        data[sheet] = df
        progress =n*patron
        progreso.progress(progress)
    start_escritura = time.time()
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet, df in data.items():
            n+=1
            start = time.time()      
            df.to_excel(writer, sheet_name=sheet, index=False)
            output.seek(0)
            fin = time.time()
            progress =n*patron
            progreso.progress(progress)
    progreso.progress(100)
    return output
def Optimizacion(archivo):
    data={}
    xlsx = pd.ExcelFile(archivo)
    progreso = st.progress(0)
    patron = len(xlsx.sheet_names[:-1])
    patron = int(np.round(100/((patron*2)+1)))
    n = 0  
    for sheet in xlsx.sheet_names[:-1]:
        n+=1
        start = time.time()
        df = pd.read_excel(xlsx, sheet_name=sheet)
        result = []
        fila_inicial= df.iloc[0].copy()
        for i in range(1,len(df)):
            fila_siguiente=df.iloc[i]
            if (fila_inicial['HOLEID'] == fila_siguiente['HOLEID']) and fila_inicial[3:].equals(fila_siguiente[3:]):
                fila_inicial['From']= min(fila_inicial['From'], fila_siguiente['From'])
                fila_inicial['To'] = max(fila_inicial['To'], fila_siguiente['To'])
            else:
                result.append(fila_inicial)
                fila_inicial= fila_siguiente.copy()
        result.append(fila_inicial)
        optimizado = pd.DataFrame(result)
        data[sheet] = optimizado
        progress =n*patron
        progreso.progress(progress)
    output = io.BytesIO()
    start_escritura = time.time()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet, df in data.items():
            n +=1
            start = time.time()      
            df.to_excel(writer, sheet_name=sheet, index=False)
            output.seek(0)
            progress =n*patron
            progreso.progress(progress)
    progreso.progress(100)
    return output 
archivo,opti = Conseguir_archivo()
if type(archivo) == list:
    for i in range(0,len(archivo)):
        if archivo[i].name == "Optimizado.xlsx":
            posicion_opti = i
            if i == 0:
                posicion = 1
            else:
                posicion = 0
if archivo != [] and archivo != None:
    seguir,funcion = Menu()
    if seguir == True:
        if funcion == 1:
            st.session_state.accion = ""
            if type(archivo) == list and len(archivo)!=1:
                archivo_filtrado = Filtrado(archivo[posicion])
                if len(archivo) == 1:
                    st.warning("Solo has ingresado 1 archivo, desactiva 'Tienes la optimizacion hecha?'")
                    archivo_filtrado=''
            else:
                archivo_filtrado = Filtrado(archivo)
            if archivo_filtrado!='':
                st.download_button("Descarga tus archivos aca",file_name="Filtrado.xlsx" ,data=archivo_filtrado,mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        elif funcion == 2:
            st.session_state.accion = ""
            if type(archivo) == list and len(archivo)!=1:
                archivo_optimizado = Optimizacion(archivo[posicion])
                if len(archivo) == 1:
                    st.warning("Solo has ingresado 1 archivo, desactiva 'Tienes la optimizacion hecha?'")
                    archivo_optimizado=''
            else:
                archivo_optimizado = Optimizacion(archivo)
            if archivo_optimizado!='': 
                st.download_button("Descarga tus archivos aca",file_name="Optimizado.xlsx" ,data=archivo_optimizado,mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        elif funcion == 3:
            st.session_state.accion = "tramos"

    if st.session_state.accion == "tramos" and funcion==3 and opti == True:
        st.session_state.texto = st.text_input("dime la cantidad que seran los tramos:",value=st.session_state.texto)
        tramo = st.session_state.texto
        if st.session_state.texto:
            if type(archivo) == list and tramo !='':
                with st.spinner("Dividiendo Tramos"):
                    archivo_tramos=procesar_hojas(archivo[posicion_opti],float(tramo))
                st.download_button("Descarga tus archivos aca",file_name="Tramos.xlsx" ,data=archivo_tramos,mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                st.session_state.accion = ""
    else:
        if st.session_state.accion == "tramos" and funcion==3:
            if archivo.name == "Optimizado.xlsx":
                st.warning("Activa 'Tienes la optimizacion hecha?'")
            else:
                st.error("Asegurate de que hayas ingresado el archivo 'Optimizacion.xlsx'")
