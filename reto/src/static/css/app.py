# -*- coding: utf-8 -*-

import imghdr
from io import BytesIO
from flask import Flask, jsonify, make_response, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from datetime import datetime, timedelta
import pandas as pd
from werkzeug.utils import secure_filename
from flask_cors import CORS
import xlrd
import os
import pytz
 
class Config:
    SECRET_KEY = b'_5#y2L"F4Q8z\n\xec]/'
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = 'password'
    MYSQL_DB = 'senamac'


app = Flask(__name__)
app.config.from_object(Config)    

mysql = MySQL(app)


""" ----------------INDEX---------------- """
@app.route('/')
def index():
    if 'cargo' in session:
        cargo = session['cargo']
        if cargo == 'Instructor':
            return redirect('/instructores')
        elif cargo == 'Coordinador':
            return redirect('/coordinador')
        elif cargo == 'Porteria':
            return redirect('/asistencia')
    
    return render_template('index.html')


@app.route('/buscar_documento_ajax_handler', methods=['POST'])
def buscar_documento_ajax_handler():
    numero_documento = request.form['numeroDocumento']

    # Consulta SQL para buscar en la base de datos
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT 
            permisos.fecha_hora_salida, 
            permisos.fecha_hora_entrada, 
            permisos.especificacion, 
            personas.nombre,
            permisos.vb_instructor,
            permisos.estado
        FROM 
            permisos 
        JOIN 
            personas ON permisos.personas_id_persona = personas.id_persona 
        WHERE 
            permisos.aprendices_documento = %s
        """, (numero_documento,))
    resultados = cursor.fetchall()

    # Consulta SQL para obtener el nombre del aprendiz
    cursor.execute("""
        SELECT nombre
        FROM aprendices
        WHERE documento = %s
    """, (numero_documento,))
    nombre_aprendiz = cursor.fetchone()

    # Construir la respuesta JSON con los resultados de la consulta
    # Construir la respuesta JSON con los resultados de la consulta
    respuesta = []
    for row in resultados:
        # Determinar el estado según las condiciones especificadas
        if row[4] == 0 and row[5] == "activo":
            estado = "Pendiente"
        elif row[4] == 1 and row[5] == "activo":
            estado = "Aprobado"
        elif row[4] == 0 and row[5] == "inactivo":
            estado = "Rechazado"
        else:
            estado = "Terminado"  # Estado no reconocido
    
        # Obtener el nombre del aprendiz si está presente, de lo contrario, dejarlo vacío
        nombre_Aprendiz = nombre_aprendiz[0] if nombre_aprendiz else ""
    
        respuesta.append({
            'fecha_hora_salida': row[0].strftime('%d/%m/%Y %H:%M:%S') if row[0] is not None else None,
            'fecha_hora_entrada': row[1].strftime('%d/%m/%Y %H:%M:%S') if row[1] is not None else None,
            'especificacion': row[2],
            'nombre': row[3],
            'estado': estado,
            'nombre_Aprendiz' : nombre_Aprendiz
        })


    return jsonify(respuesta)





""" ------------------LOGIN------------------------- """

import hashlib

@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        id_persona = request.form['usuario']
        password = request.form['password']

        # Encriptar la contraseña
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM personas WHERE id_persona = %s AND contraseña = %s', (id_persona, hashed_password))
        user = cursor.fetchone()
        cursor.close()

        if user:
            id_usuario = user[0]
            nombre_usuario = user[1]
            cargo = user[2]
            password = user[3]
            
            session['id_persona'] = id_usuario
            session['cargo'] = cargo
            session['usuario_nombre'] = nombre_usuario
            session['password'] = password
            
            if cargo == 'Instructor':
                return jsonify({'redirect': url_for('instructores')})
            elif cargo == 'Coordinador':
                return jsonify({'redirect': url_for('coordinador')})
            elif cargo == 'Porteria':
                return jsonify({'redirect': url_for('asistencia')})
            else:
                return jsonify({'error': 'Usuario no permitido'})
        else:
            return jsonify({'error': 'Usuario o contraseña incorrecta'})
    
    return redirect('/')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


""" ---------------------GENERAR PERMISOS---------------------- """

@app.route('/permisos')
def permisos():
    return render_template('permisos.html')


@app.route('/buscar_instructores', methods=['GET'])
def buscar_instructores():
    term = request.args.get('nombre', '')
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT nombre FROM personas WHERE nombre LIKE %s", ('%' + term + '%',))
    instructores = cursor.fetchall()
    cursor.close()

    # Formatear la respuesta como una lista de nombres
    instructores_list = [instructor[0] for instructor in instructores]

    if len(instructores_list) == 0:
        return jsonify({'mensaje': 'Instructor no encontrado'})

    return jsonify(instructores_list)

@app.route('/consultapermiso', methods=['GET', 'POST'])
def consultapermiso():
    numero_documento_permisos = ""  
    nombre_aprendiz = ""  
    numero_ficha = ""  
    mensaje = ""  
    icon = ""

    if request.method == 'POST':
        numero_documento_permisos = request.form['numero_documento_permisos']
        if not numero_documento_permisos:
            mensaje = "Ingresar Documento"
            icon = "info"
        else:
            cursor = mysql.connection.cursor()
            query = "SELECT * FROM aprendices WHERE documento = %s"
            cursor.execute(query, (numero_documento_permisos,))
            usuario = cursor.fetchone()
            cursor.close()
            if usuario:
                nombre_aprendiz = usuario[1]
                numero_ficha = usuario[2]
            else:
                nombre_aprendiz = "NO REGISTRADO"
                numero_ficha = "NO REGISTRADO"
                mensaje = "Documento del Aprendiz no registrado"
                icon = "error"

    return render_template('permisos.html', mensaje=mensaje,icon=icon , nombre_aprendiz=nombre_aprendiz, numero_ficha=numero_ficha, numero_documento=numero_documento_permisos)

 

ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}


# Función para verificar si la extensión del archivo es permitida
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/guardar_permiso', methods=['POST'])
def guardar_permiso():
    try:
        if request.method == 'POST':
            print("Recibiendo solicitud POST")
            mensaje = ""  
            icon = ""
            
            # Depuración: Imprimir todos los datos del formulario para ver qué valores están llegando
            print(f"Datos del formulario recibidos: {request.form}")

            documento_aprendiz_permisos = request.form.get('documento_aprendiz_permisos')
            nombre_instructor_permisos = request.form.get('nombre_instructor_permisos')

            print(f"Documento del aprendiz: {documento_aprendiz_permisos}")
            print(f"Nombre del instructor: {nombre_instructor_permisos}")

            if not documento_aprendiz_permisos or not nombre_instructor_permisos:
                mensaje = "¡Campos vacíos!, verifique que tenga los datos completos"
                icon = "info"
                flash(mensaje, icon)
                return redirect(url_for('permisos'))

            cursor = mysql.connection.cursor()
            cursor.execute("SELECT id_persona FROM personas WHERE nombre = %s", (nombre_instructor_permisos,))
            result = cursor.fetchone()
            cursor.close()

            if not result:
                mensaje = "Instructor no encontrado"
                icon = "error"
                flash(mensaje, icon)
                return redirect(url_for('permisos'))
            
            id_instructor = result[0]

            tipo = request.form.get('service-type')
            tipo_permiso = request.form.get('tipoPermiso')
            permiso = request.form.get('permiso')

            fecha_hora_salida = None
            fecha_hora_entrada = None

            if tipo == '1':
                hora_entrada = request.form.get('horaEntrada')
                if hora_entrada:
                    fecha_hora_entrada = datetime.strptime(hora_entrada, "%Y-%m-%dT%H:%M")
            elif tipo == '2':
                hora_salida = request.form.get('horaSalida')
                if hora_salida:
                    fecha_hora_salida = datetime.strptime(hora_salida, "%Y-%m-%dT%H:%M")
            elif tipo == '3':
                fecha = request.form.get('fecha')
                hora_salida = request.form.get('horaSalidas')
                hora_entrada = request.form.get('horaEntradas')
                if fecha and hora_salida and hora_entrada:
                    fecha_hora_salida = datetime.strptime(f"{fecha} {hora_salida}", "%Y-%m-%d %H:%M")
                    fecha_hora_entrada = datetime.strptime(f"{fecha} {hora_entrada}", "%Y-%m-%d %H:%M")
            else:
                mensaje = "Tipo de permiso no válido"
                icon = "error"
                flash(mensaje, icon)
                return redirect(url_for('permisos'))

            archivo = request.files.get('archivo')

            try:
                cursor = mysql.connection.cursor()
                if archivo and allowed_file(archivo.filename):
                    # Realiza la inserción en la base de datos con el archivo adjunto
                    cursor.execute("INSERT INTO permisos (fecha_hora_salida, fecha_hora_entrada, tipo_permiso, especificacion, soporte, aprendices_documento, estado, personas_id_persona, vb_instructor, ok_vigilante_salida, ok_vigilante_entrada) VALUES (%s, %s, %s, %s, %s, %s, 'activo', %s, 0, 0, 0)",
                                   (fecha_hora_salida, fecha_hora_entrada, tipo_permiso, permiso, archivo.read(), documento_aprendiz_permisos, id_instructor))
                else:
                    # Realiza la inserción en la base de datos sin archivo adjunto
                    cursor.execute("INSERT INTO permisos (fecha_hora_salida, fecha_hora_entrada, tipo_permiso, especificacion, soporte, aprendices_documento, estado, personas_id_persona, vb_instructor, ok_vigilante_salida, ok_vigilante_entrada) VALUES (%s, %s, %s, %s, %s, %s, 'activo', %s, 0, 0, 0)",
                                   (fecha_hora_salida, fecha_hora_entrada, tipo_permiso, permiso, None, documento_aprendiz_permisos, id_instructor))
                mysql.connection.commit()
                cursor.close()
                mensaje = "Permiso enviado exitosamente"
                icon = "success"
                flash(mensaje, icon)
                return redirect(url_for('index'))
            except Exception as e:
                print(f"Error al insertar en la base de datos: {e}")
                mensaje = f"Error al insertar en la base de datos: {e}"
                icon = "error"
                flash(mensaje, icon)
                return redirect(url_for('permisos'))
    except Exception as e:
        print(f"Error: {e}")
        flash(f"Error: {e}", "error")
        return redirect(url_for('permisos'))



""" ---------------------INSTRUCTORES------------------------"""

@app.route('/instructores', methods=['GET', 'POST'])
def instructores():
    if 'cargo' in session and session['cargo'] == 'Instructor':
        usuario_nombre = session.get('usuario_nombre')  # Obtener el nombre del usuario de la sesión
        
        usuario_nombre = usuario_nombre.split()[0] if usuario_nombre else 'Usuario'

        cur = mysql.connection.cursor()
        id_persona = session.get('id_persona')  # Obtener el ID de la persona de la sesión
        
        cur.execute("""
            SELECT p.id_solicitud, 
            COALESCE(p.aprendices_documento, 'No aplica') AS aprendices_documento, 
            aprendices.fichas_id_ficha,  
            personas.nombre AS nombre_instructor,
            COALESCE(especificacion, 'No aplica') AS especificacion, 
            aprendices.nombre AS nombre_aprendiz, 
            COALESCE(p.fecha_hora_salida, 'No aplica') AS fecha_hora_salida, 
            COALESCE(p.fecha_hora_entrada, 'No aplica') AS fecha_hora_entrada,
            COALESCE(TO_BASE64(p.soporte), 'No aplica') AS soporte_base64
            FROM permisos p
            JOIN personas ON p.personas_id_persona = personas.id_persona
            JOIN aprendices ON p.aprendices_documento = aprendices.documento
            WHERE p.vb_instructor = 0 
            AND personas.id_persona = %s
            AND p.estado = 'activo'; -- Agrega esta condición para filtrar por estado activo
        """, (id_persona,))
        resultados = cur.fetchall()
        
        cur.close()

        response = make_response(render_template('instructores.html', usuario_nombre=usuario_nombre, resultados=resultados))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # Deshabilitar la caché
        return response
    else:
        flash('Acceso no autorizado', 'error')
        return redirect('/')

@app.route('/confirmar_solicitud', methods=['POST'])
def confirmar_solicitud():
    if 'cargo' in session and session['cargo'] == 'Instructor':
        if request.method == 'POST':
            cur = mysql.connection.cursor()
            id_solicitud = request.form.get('id_solicitud')
            try:
                cur.execute("UPDATE permisos SET vb_instructor = 1 WHERE id_solicitud = %s", (id_solicitud,))
                mysql.connection.commit()
                print("Actualización exitosa en la base de datos.")
            except Exception as e:
                print(f"Error al actualizar en la base de datos: {e}")
                mysql.connection.rollback()
            cur.close()
        return redirect('/instructores') 

@app.route('/cancelar_solicitud', methods=['POST'])
def cancelar_solicitud():
    if 'cargo' in session and session['cargo'] == 'Instructor':
        if request.method == 'POST':
            cur = mysql.connection.cursor()
            id_solicitud = request.form.get('id_solicitud')
            try:
                cur.execute("UPDATE permisos SET estado = 'inactivo' WHERE id_solicitud = %s", (id_solicitud,))
                mysql.connection.commit()
                print("Actualización exitosa en la base de datos.")
            except Exception as e:
                print(f"Error al actualizar en la base de datos: {e}")
                mysql.connection.rollback()
            cur.close()
        return redirect('/instructores') 

@app.route('/cambiar_contraseña', methods=['POST'])
def cambiar_contraseña():
    if request.method == 'POST':
        mensaje = ""
        icon = ""
        id_usuario = session.get('id_persona')
        confirmar_contraseña = request.form.get('contraseña_confirmar')
        actual_contraseña = request.form.get('actual_contraseña')
        

        password_actual = hashlib.sha256(actual_contraseña.encode()).hexdigest()
        hashed_password = hashlib.sha256(confirmar_contraseña.encode()).hexdigest()

        
        if password_actual == session['password']:

            try:
                cur = mysql.connection.cursor()
                cur.execute("UPDATE personas SET contraseña = %s WHERE id_persona= %s", (hashed_password, id_usuario))
                mysql.connection.commit()
                cur.close()
                mensaje = "Contraseña cambiada con éxito"  
                icon = "success"
            except Exception as e: 
                mensaje = f"Error al actualizar la contraseña: {e}"  
                icon = "error"
        else:
            mensaje = "La contraseña actual no coincide"
            icon = "error"

        return render_template('instructores.html', mensaje=mensaje, icon=icon)
    return redirect('/')
    

@app.route('/instructorpermisos')
def instructorpermisos():
    if 'cargo' in session and session['cargo'] == 'Instructor':
        id_persona = session['id_persona']
        usuario_nombre = session['usuario_nombre']
        usuario_nombre = usuario_nombre.split()[0] if usuario_nombre else 'Usuario'
        cur = mysql.connection.cursor()

        if request.method == 'POST':
            id_solicitud = request.form.get('id_solicitud')
            try:
                cur.execute("UPDATE permisos SET vb_instructor = 1 WHERE id_solicitud = %s", (id_solicitud,))
                mysql.connection.commit()
                print("Actualización exitosa en la base de datos.")
            except Exception as e:
                print(f"Error al actualizar en la base de datos: {e}")
                mysql.connection.rollback()

        cur.execute("""
            SELECT p.id_solicitud, p.aprendices_documento, personas.nombre AS nombre_instructor,
            especificacion, aprendices.nombre AS nombre_aprendiz, p.fecha_hora_salida, p.fecha_hora_entrada,
            tipo_permiso, p.soporte
            FROM permisos p
            JOIN personas ON p.personas_id_persona = personas.id_persona
            JOIN aprendices ON p.aprendices_documento = aprendices.documento
            WHERE p.vb_instructor = 1 AND personas.id_persona = %s
        """, (id_persona,))
        resultados = cur.fetchall()

        cur.close()
        response = make_response(render_template('instructorpermisos.html', usuario_nombre=usuario_nombre, resultados=resultados))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # Deshabilitar la caché
        return response
        
    else:
        flash('Acceso no autorizado', 'error')
        return redirect('/')
        
@app.route('/descargar_soporte', methods=['POST'])
def descargar_soporte():
    id_solicitud = request.form.get('id_solicitud')
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT soporte FROM permisos WHERE id_solicitud = %s", (id_solicitud,))
    resultado = cur.fetchone()
    cur.close()

    if resultado:
        soporte_blob = resultado[0]

        # Verificar que soporte_blob no sea None
        if soporte_blob is None:
            flash('No se encontró el soporte', 'error')
            return redirect('/instructorpermisos')

        # Determinar el tipo de contenido
        content_type = 'application/pdf'
        extension = '.pdf'
        
        # Verificar si el blob es una imagen
        if imghdr.what(None, soporte_blob):
            content_type = 'image/jpeg'
            extension = '.jpg'

        # Crear una respuesta
        response = make_response(soporte_blob)
        response.headers['Content-Type'] = content_type
        response.headers['Content-Disposition'] = f'attachment; filename=soporte{extension}'
        
        return response
    else:
        flash('No se encontró el soporte', 'error')
        return redirect('/instructorpermisos')

@app.route('/buscar_ficha/<int:num_ficha>', methods=['GET'])
def buscar_ficha(num_ficha):
    cursor = mysql.connection.cursor()

    try:
        cursor.execute("SELECT programa FROM fichas WHERE id_ficha = %s", (num_ficha,))
        programa = cursor.fetchone()

        if programa:
            return jsonify({'programa': programa[0]})
        else:
            return jsonify({'error': 'Número de ficha no encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        
@app.route('/guardar_permiso_ficha', methods=['POST'])
def guardar_permiso_ficha():
    if request.method == 'POST':
        # Obtén los datos del formulario
        ficha_id = request.form['fichas_id_ficha']
        
        fecha_hora_salida = request.form['fecha_hora_salida']
        fecha_hora_entrada = request.form['fecha_hora_entrada']
        detalle = request.form['detalle']

        # Obtén el id_persona de la sesión
        id_persona = session['id_persona']

        # Convierte las fechas de cadena a objetos datetime si es necesario
        if fecha_hora_salida:
            fecha_hora_salida = datetime.strptime(fecha_hora_salida, '%Y-%m-%dT%H:%M')
        if fecha_hora_entrada:
            fecha_hora_entrada = datetime.strptime(fecha_hora_entrada, '%Y-%m-%dT%H:%M')

        if not fecha_hora_salida:
            fecha_hora_salida = None
        if not fecha_hora_entrada:
            fecha_hora_entrada = None

        # Verifica si la ficha_id existe en la base de datos
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT id_ficha FROM fichas WHERE id_ficha = %s', (ficha_id,))
        ficha_existente = cursor.fetchone()
        cursor.close()

        if not ficha_existente:
            flash('La ficha especificada no existe.', 'error')
            return jsonify({'status': 'error', 'message': 'La ficha especificada no existe'})

        # Realiza la inserción en la base de datos
        cursor = mysql.connection.cursor()
        try:
            cursor.execute(
                'INSERT INTO permisos_fichas (fecha_hora_salida, fecha_hora_entrada, detalle, fichas_id_ficha, personas_id_persona) VALUES (%s, %s, %s, %s, %s)',
                (fecha_hora_salida, fecha_hora_entrada, detalle, ficha_id, id_persona)
            )
            mysql.connection.commit()

            # Mostrar mensaje de éxito si la inserción fue exitosa
            flash('Permiso enviado exitosamente', 'success')
            return jsonify({'status': 'success'})

        except Exception as e:
            print(f"Error al insertar en la base de datos: {e}")
            mysql.connection.rollback()
            flash('Ocurrió un error al enviar el permiso. Por favor, inténtalo de nuevo.', 'error')
            return jsonify({'status': 'error', 'message': 'Ocurrió un error al enviar el permiso. Por favor, inténtalo de nuevo.'})

        finally:
            cursor.close()


""" -------------------------------------------------------------------- """


""" ----------------------COORDINADOR------------------------------------- """

@app.route('/coordinador')
def coordinador():
    if 'cargo' in session and session['cargo'] == 'Coordinador':
        usuario_datos = session['usuario_nombre']
        response = make_response(render_template('coordinador.html', usuario_nombre=usuario_datos))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # Deshabilitar la caché
        return response
    else:
        flash('Acceso no autorizado', 'error')
        return redirect('/')
    
@app.route('/coorasistencia')
def coorasistencia():
    if 'cargo' in session and session['cargo'] == 'Coordinador':
        usuario_datos = session['usuario_nombre']

        cur = mysql.connection.cursor()

        cur.execute("""
            SELECT p.id_solicitud, p.aprendices_documento, aprendices.fichas_id_ficha, personas.nombre AS nombre_instructor,
            especificacion, aprendices.nombre AS nombre_aprendiz, p.fecha_hora_salida,
            p.fecha_hora_entrada, p.fecha_hora_regreso, tipo_permiso, retraso, p.soporte
            FROM permisos p
            JOIN personas ON p.personas_id_persona = personas.id_persona
            JOIN aprendices ON p.aprendices_documento = aprendices.documento
            WHERE p.ok_vigilante_salida = 1 OR p.ok_vigilante_entrada = 1;
        """)

        resultados = cur.fetchall()

        cur.close()


        response = make_response(render_template('coorasistencia.html', usuario_nombre=usuario_datos, resultados=resultados))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # Deshabilitar la caché
        return response

    else:
        flash('Acceso no autorizado', 'error')
        return redirect('/')

@app.route('/coorpermisos')
def coorpermisos():
    if 'cargo' in session and session['cargo'] == 'Coordinador':
        usuario_datos = session['usuario_nombre']
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT ia.*, ap.nombre AS nombre_aprendiz, ap.fichas_id_ficha
            FROM ingresos_aprendices ia
            JOIN aprendices ap ON ia.aprendices_documento = ap.documento;
        """)
        resultados = cur.fetchall()
        cur.close()
        
        response = make_response(render_template('coorpermisos.html', usuario_nombre=usuario_datos, resultados=resultados))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # Deshabilitar la caché
        return response
    else:
        flash('Acceso no autorizado', 'error')
        return redirect('/')

@app.route('/coorregistrar')
def coorregistrar():
    if 'cargo' in session and session['cargo'] == 'Coordinador':
        usuario_datos = session['usuario_nombre']
        response = make_response(render_template('coorregistrar.html', usuario_nombre=usuario_datos))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # Deshabilitar la caché
        return response
    else:
        flash('Acceso no autorizado', 'error')
        return redirect('/')

@app.route('/procesar', methods=['POST'])
def procesar():
    mensaje = ""  
    icon = ""
    if 'cargo' in session and session['cargo'] == 'Coordinador':
        if 'archivo' not in request.files:
            mensaje = "No se ha seleccionado ningun archivo"
            icon = "error"
            return render_template('coorregistrar.html', mensaje=mensaje,icon=icon)
        
        
        archivo = request.files['archivo']

        if archivo.filename == '':
            mensaje = "No se ha seleccionado ningun archivo"
            icon = "error"
            return render_template('coorregistrar.html', mensaje=mensaje,icon=icon)

        if archivo:
            try:
            # Utilizando pandas y xlrd para archivos .xls
                df = pd.read_excel(archivo, engine='xlrd')

            # Ejemplo de procesamiento de datos
                info_celda_C3 = df.iloc[1, 2]  # C3
                info_celda_C6 = df.iloc[4, 2]  # C6

            # Asegurar que el valor sea de tipo datetime antes de aplicar strftime
                info_celda_C8 = df.iloc[6, 2].strftime('%Y-%m-%d')
                info_celda_C9 = df.iloc[7, 2].strftime('%Y-%m-%d') #Queda datetime para validar

                fecha_sin_hora = None  # Asignación inicial
                fecha_actual = datetime.now().date()

                if isinstance(info_celda_C9, float):
                    fecha_python = xlrd.xldate_as_datatime(info_celda_C9, 0)
                    fecha_sin_hora = fecha_python.date()
                else:
                    try:
                        fecha_sin_hora = datetime.strptime(info_celda_C9, '%Y-%m-%d').date()
                    except ValueError:
                    # Manejar el caso en el que info_celda_C9 no se puede convertir a fecha
                        pass

                if fecha_sin_hora is not None:  # Solo si se encontró una fecha válida
                    fecha_fin = fecha_sin_hora - timedelta(days=185)

                    if fecha_actual > fecha_fin:
                        print(fecha_fin)
                        mensaje = "No se permiten fichas inactivas"
                        icon = "error"
                        return render_template('coorregistrar.html', mensaje=mensaje,icon=icon)
                else:
                    # Tratar el caso en el que info_celda_C9 no es un float
                    pass
                print(fecha_fin)

    
                # Verificar si info_celda_C10 es "VIRTUAL"
                info_celda_C10 = df.iloc[8, 2]  # C10

                if info_celda_C10 == "VIRTUAL":
                        mensaje = "No se permiten fichas virtuales"
                        icon = "error"
                        return render_template('coorregistrar.html', mensaje=mensaje,icon=icon)
                else:
                    pass

            # Adaptación del bloque de código proporcionado
                datos = []  # Usar una lista para almacenar todas las filas
                valores_unicos = set()  # Usar un conjunto para almacenar valores únicos de la columna B

                for row in df.itertuples(index=False):
                    fila = [getattr(row, f'_{i}') for i in range(1, len(row))]
                    # Verificar si la columna E contiene "EN FORMACION" o "EN INDUCCION"
                    if fila[3] in ["EN FORMACION", "INDUCCION"]:  # Columna E es la posición 3 en la lista
                        # Verificar si el valor de la columna B es único antes de agregar la fila
                        if fila[0] not in valores_unicos:
                            valores_unicos.add(fila[0])
                            datos.append(fila)

                return render_template('excel.html', datos=datos, info_celda_C3=info_celda_C3,
                                    info_celda_C6=info_celda_C6, info_celda_C8=info_celda_C8, info_celda_C9=info_celda_C9)

            except Exception as e:
                return f"Error al procesar el archivo: {e}"
        # Ruta para manejar la solicitud de agregar datos

            
        else:
            flash('Acceso no autorizado', 'error')
            return redirect('/')
    
    else:
        flash('Acceso no autorizado', 'error')
        return redirect('/')
    
@app.route('/agregar_datos', methods=['POST'])
def agregar_datos():
    try:
        # Obtén la conexión a la base de datos
        cur = mysql.connection.cursor()

        # Extrae los datos del formulario
        data = request.get_json()
        programa = data['programa']
        id_ficha = data['id_ficha']
        fecha_inicio = data['fecha_inicio']
        fecha_fin = data['fecha_fin']
        jornada = data['jornada']
        estado = "ACTIVA"
        print(id_ficha)
        cur.execute("SELECT id_ficha FROM fichas WHERE id_ficha = %s", (id_ficha,))
        existencia_ficha = cur.fetchone()

        if existencia_ficha:
    # La ficha ya existe, entonces actualiza los datos
            cur.execute("UPDATE fichas SET programa = %s, fecha_inicio = %s, fecha_fin = %s, jornada = %s, estado = %s WHERE id_ficha = %s",
                        (programa, fecha_inicio, fecha_fin, jornada, estado, id_ficha))
        else:
            # La ficha no existe, entonces inserta los datos
            cur.execute("INSERT INTO fichas (programa, id_ficha, fecha_inicio, fecha_fin, jornada, estado) VALUES (%s, %s, %s, %s, %s, %s)",
                        (programa, id_ficha, fecha_inicio, fecha_fin, jornada, estado))
            mysql.connection.commit()

            
        # Finalmente, confirma los cambios en la base de datos

        # Obtén el ID de la ficha recién insertada
       

        try:
            # Maneja los datos de los aprendices
            datos_aprendices = data['datosAprendices']
            print(datos_aprendices)
            
            for aprendiz in datos_aprendices:
                documento = aprendiz['documento']
                nombre = aprendiz['nombre']
                
                
                cur.execute("SELECT documento, fichas_id_ficha FROM aprendices WHERE documento =%s", (documento,))
                aprendiz_existente = cur.fetchone()

                if aprendiz_existente:
                        if aprendiz_existente[1] != id_ficha:
                            # Actualiza la ficha del aprendiz
                            cur.execute("UPDATE aprendices SET fichas_id_ficha = %s WHERE documento = %s", (id_ficha, documento))
                            mysql.connection.commit()
                            # Puedes añadir un mensaje para indicar que se ha actualizado la ficha del aprendiz
                            print(f"Ficha del aprendiz con documento {documento} actualizada a {id_ficha}")
                else:
                    # Inserta los datos de cada aprendiz en la tabla Aprendiz asociada a la ficha recién creada
                    cur.execute("INSERT INTO aprendices (documento, nombre, fichas_id_ficha) VALUES (%s, %s, %s)",
                                    (documento, nombre, id_ficha)) 
                    mysql.connection.commit()


            cur.close()

            return jsonify({"mensaje": "Datos agregados exitosamente"})
            
        except Exception as e:
            print("Error en agregar_datos:", str(e))
            return jsonify({"error": f"Hubo un error en el servidor: {str(e)}"}), 400
    except Exception as e:
        print("Error en agregar_datos:", str(e))
        return jsonify({"error": f"Hubo un error en el servidor: {str(e)}"}), 400



@app.route('/buscar_documento_db', methods=['POST'])
def buscar_documento_db():
    numero_documento = request.json.get('numeroDocumento')
    # Realiza la consulta a la base de datos para buscar el documento
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT ea.id_elementos_ap, ea.marca, ea.serial, ea.descripcion, ia.id_ingresos1 
        FROM elementos_aprendices ea 
        LEFT JOIN ingresos_elementos_ap ia ON ea.id_elementos_ap = ia.elementos_aprendices_id_elementos_ap 
            AND ia.fecha_salida IS NULL 
            AND ia.aprendices_documento = %s 
        WHERE ea.aprendices_documento = %s 
        UNION 
        SELECT ep.id_elementos_per, ep.marca, ep.serial, ep.descripcion, iep.id_ingresos2 
        FROM elementos_personas ep 
        LEFT JOIN ingresos_elementos_personas iep ON ep.id_elementos_per = iep.elementos_personas_id_elementos_per 
            AND iep.fecha_salida IS NULL 
            AND iep.personas_id_persona = %s
        WHERE ep.personas_id_persona = %s
    """, (numero_documento, numero_documento, numero_documento, numero_documento))
    resultados = cursor.fetchall()
    cursor.close()
    # Genera el HTML de la tabla con los resultados
    tabla_html = '<thead>' \
                 '<tr>' \
                 '<th>ID</th>' \
                 '<th>Marca</th>' \
                 '<th>Serial</th>' \
                 '<th>Descripción</th>' \
                 '<th>Acción</th>' \
                 '</tr>' \
                 '</thead>'
    
    tabla_html += '<tbody>'
    for ingreso in resultados:
        tabla_html += '<tr>'
        tabla_html += '<td>' + str(ingreso[0]) + '</td>'
        tabla_html += '<td>' + str(ingreso[1]) + '</td>'
        tabla_html += '<td>' + str(ingreso[2]) + '</td>'
        tabla_html += '<td>' + str(ingreso[3]) + '</td>'
        
        # Verificar si hay un ingreso activo para este elemento
        if ingreso[4] is not None:
            # Si hay un ingreso activo, cambiar el botón a "Salida" y cambiar el color a rojo
            tabla_html += '<td><button style="background-color: red;" onclick="realizarSalida(' + str(ingreso[4]) + ')">Salida</button></td>'
        else:
            # Si no hay un ingreso activo, mostrar botón de ingreso en verde
            tabla_html += '<td><button onclick="realizarIngreso(' + str(ingreso[0]) + ')">Ingreso</button></td>'
        
        tabla_html += '</tr>'
    tabla_html += '</tbody>'
    
    return tabla_html

@app.route('/buscar_documento', methods=['POST'])
def buscar_documento():
    documento = request.form['documento']
    cur = mysql.connection.cursor()
    
    # Buscar en la tabla aprendices
    cur.execute("SELECT nombre FROM aprendices WHERE documento = %s", (documento,))
    aprendiz = cur.fetchone()
    
    # Si no se encontró en aprendices, buscar en la tabla personas
    if not aprendiz:
        cur.execute("SELECT nombre FROM personas WHERE id_persona = %s", (documento,))
        persona = cur.fetchone()
        cur.close()
        if persona:
            return jsonify({'nombre': persona[0]})
        else:
            return jsonify({'nombre': None})
    
    cur.close()
    if aprendiz:
        return jsonify({'nombre': aprendiz[0]})
    else:
        return jsonify({'nombre': None})

@app.route('/realizar_ingreso', methods=['POST'])
def realizar_ingreso():
    datos = request.json
    fecha_ingreso = datetime.now()  # Obtener la fecha y hora actual
    aprendices_documento = datos['aprendices_documento']
    id_elemento_ap = datos['id_elemento_ap']
    
    # Verificar si el aprendices_documento pertenece a la tabla personas
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM personas WHERE id_persona = %s", (aprendices_documento,))
    es_persona = cursor.fetchone()[0]
    cursor.close()
    
    if es_persona:
        # Verificar si ya hay un ingreso con fecha_salida nula en ingresos_elementos_personas
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM ingresos_elementos_personas WHERE elementos_personas_id_elementos_per = %s AND fecha_salida IS NULL", (id_elemento_ap,))
        cantidad_ingresos_personas = cursor.fetchone()[0]
        
        # Si ya hay un ingreso con fecha_salida nula en ingresos_elementos_personas, no permitir guardar otro ingreso
        if cantidad_ingresos_personas > 0:
            cursor.close()
            return jsonify({'error': 'Ya hay un ingreso activo para este elemento.'}), 400
        
        # Insertar los datos en la tabla ingresos_elementos_personas
        cursor.execute("INSERT INTO ingresos_elementos_personas (fecha_ingreso, personas_id_persona, elementos_personas_id_elementos_per) VALUES (%s, %s, %s)", (fecha_ingreso, aprendices_documento, id_elemento_ap))
        mysql.connection.commit()
        cursor.close()
        
        return 'Ingreso registrado exitosamente en ingresos_elementos_personas'
    
    # Verificar si ya hay un ingreso registrado para este elemento con fecha_salida nula en ingresos_elementos_ap
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM ingresos_elementos_ap WHERE elementos_aprendices_id_elementos_ap = %s AND fecha_salida IS NULL", (id_elemento_ap,))
    cantidad_ingresos_ap = cursor.fetchone()[0]
    cursor.close()
    
    # Si ya hay un ingreso con fecha_salida nula en ingresos_elementos_ap, no permitir guardar otro ingreso
    if cantidad_ingresos_ap > 0:
        return jsonify({'error': 'Ya hay un ingreso activo para este elemento.'}), 400
    
    # Insertar los datos en la tabla ingresos_elementos_ap
    cursor = mysql.connection.cursor()
    cursor.execute("INSERT INTO ingresos_elementos_ap (fecha_ingreso, aprendices_documento, elementos_aprendices_id_elementos_ap) VALUES (%s, %s, %s)", (fecha_ingreso, aprendices_documento, id_elemento_ap))
    mysql.connection.commit()
    cursor.close()
    
    return 'Ingreso registrado exitosamente en ingresos_elementos_ap'


@app.route('/realizar_salida', methods=['POST'])
def salir_elemento():
    datos = request.json
    id_ingreso = datos['idIngreso']
    fecha_salida = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Obtener la fecha y hora actual en el formato deseado
    
    # Actualizar la columna fecha_salida en la tabla ingresos_elementos_ap
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE ingresos_elementos_ap SET fecha_salida = %s WHERE id_ingresos1 = %s", (fecha_salida, id_ingreso))
    mysql.connection.commit()
    cursor.close()
    
    # Si no se encontró el ingreso en ingresos_elementos_ap, actualizar en ingresos_elementos_personas
    if cursor.rowcount == 0:
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE ingresos_elementos_personas SET fecha_salida = %s WHERE id_ingresos2 = %s", (fecha_salida, id_ingreso))
        mysql.connection.commit()
        cursor.close()
        
        # Verificar si se actualizó algún registro en ingresos_elementos_personas
        if cursor.rowcount == 0:
            return jsonify({'error': 'No se encontró el ingreso para actualizar.'}), 400
    
    return 'Salida registrada exitosamente'



"""  """
# Definir las jornadas y horas de llegada tarde correspondientes
jornadas = {
    'mañana': {'inicio': '06:05:00', 'dias': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']},
    'tarde': {'inicio': '12:05:00', 'dias': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']},
    'mixta': {'inicio_semana': '18:05:00', 'inicio_sabado': '16:05:00', 'dias_semana': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'], 'dias_sabado': ['Saturday']}
}

@app.route('/ingresoaprendiz', methods=['POST'])
def guardar_en_base_de_datos_aprendices():
    cur = None  # Inicialización al principio
    try:
        if request.method == 'POST':
            numero_documento = request.form['numero_documento']

            cur_verificar = mysql.connection.cursor()
            fecha_actual = datetime.now().date()
            cur_verificar.execute("SELECT COUNT(*) FROM ingresos_aprendices WHERE aprendices_documento = %s AND DATE(fecha_ingreso) = %s", (numero_documento, fecha_actual))
            existe_ingreso = cur_verificar.fetchone()[0]
            if existe_ingreso:
                flash('Este aprendiz ya ha sido ingresado hoy', 'error')
                return redirect(url_for('asistencia'))

            cur_aprendices = mysql.connection.cursor()
            cur_aprendices.execute("SELECT fichas_id_ficha FROM aprendices WHERE documento = %s", (numero_documento,))
            ficha_id = cur_aprendices.fetchone()

            if ficha_id:
                cur_ficha = mysql.connection.cursor()
                cur_ficha.execute("SELECT jornada FROM fichas WHERE id_ficha = %s", (ficha_id,))
                jornada = cur_ficha.fetchone()[0]

                fecha_actual = datetime.now()
                jornada_actual = None
                llegada_tarde = None
                hora_actual = fecha_actual.time()

                if jornada == 'mañana':
                    inicio_jornada = datetime.strptime('06:05:00', '%H:%M:%S').time()
                    fin_jornada = datetime.strptime('12:00:00', '%H:%M:%S').time()
                    if inicio_jornada <= hora_actual <= fin_jornada:
                        jornada_actual = jornada
                        llegada_tarde = datetime.strptime('06:05:00', '%H:%M:%S')
                elif jornada == 'tarde':
                    inicio_jornada = datetime.strptime('12:05:00', '%H:%M:%S').time()
                    fin_jornada = datetime.strptime('18:00:00', '%H:%M:%S').time()
                    if inicio_jornada <= hora_actual <= fin_jornada:
                        jornada_actual = jornada
                        llegada_tarde = datetime.strptime('12:05:00', '%H:%M:%S')
                elif jornada == 'mixta':
                    dia_actual = fecha_actual.strftime('%A')
                    if dia_actual in jornadas['mixta']['dias_semana']:
                        inicio_jornada = datetime.strptime('18:05:00', '%H:%M:%S').time()
                        fin_jornada = datetime.strptime('23:59:59', '%H:%M:%S').time()
                        if inicio_jornada <= hora_actual <= fin_jornada:
                            jornada_actual = jornada
                            llegada_tarde = datetime.strptime('18:05:00', '%H:%M:%S')
                    elif dia_actual in jornadas['mixta']['dias_sabado']:
                        inicio_jornada = datetime.strptime('16:05:00', '%H:%M:%S').time()
                        fin_jornada = datetime.strptime('23:59:59', '%H:%M:%S').time()
                        if inicio_jornada <= hora_actual <= fin_jornada:
                            jornada_actual = jornada
                            llegada_tarde = datetime.strptime('16:05:00', '%H:%M:%S')

                if jornada_actual:
                    llegada_tarde = datetime.combine(fecha_actual.date(), llegada_tarde.time())
                    retraso = fecha_actual - llegada_tarde

                    if retraso.total_seconds() > 0:  # Asegurarse de que el retraso es positivo
                        diferencia_segundos = retraso.seconds
                        diferencia_horas = retraso.seconds // 3600
                        diferencia_minutos = (retraso.seconds % 3600) // 60
                        diferencia_segundos = diferencia_segundos % 60
                        diferencia_tiempo = "{:02}:{:02}:{:02}".format(diferencia_horas, diferencia_minutos, diferencia_segundos)

                        cur = mysql.connection.cursor()
                        cur.execute("INSERT INTO ingresos_aprendices (fecha_ingreso, aprendices_documento, observacion, retraso) VALUES (%s, %s, %s, %s)", (fecha_actual, numero_documento, '', diferencia_tiempo))
                        mysql.connection.commit()
                        flash('Ingreso exitoso', 'success')
                    else:
                        flash('El aprendiz ha llegado a tiempo.', 'success')
                else:
                    flash('El aprendiz no está dentro del horario de su jornada.', 'error')
            else:
                flash('El número de documento no corresponde a un aprendiz', 'error')

    except Exception as e:
        flash(f'Error al procesar el ingreso: {str(e)}', 'error')

    finally:
        if cur:
            cur.close()

    return redirect(url_for('asistencia'))




@app.route('/registromasivo')
def registromasivo():
    if 'cargo' in session and session['cargo'] == 'Coordinador':
        usuario_datos = session['usuario_nombre']
        response = make_response(render_template('registromasivo.html', usuario_nombre=usuario_datos))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # Deshabilitar la caché
        return response
    else:
        flash('Acceso no autorizado', 'error')
        return redirect('/')

@app.route('/registrar_usuarios', methods=['POST'])
def registrar_usuarios():
    try:
        if request.method == 'POST':
            data = request.get_json()

            # Recorre los datos de la tabla y los guarda en la base de datos
            for row in data:
                id_persona = int(row[0])
                nombre = row[1]
                
                # Asegura que la primera letra del cargo esté en mayúscula
                cargo = row[2].capitalize()

                # Verifica si el id_persona ya existe en la base de datos
                cursor = mysql.connection.cursor()
                cursor.execute("SELECT * FROM personas WHERE id_persona = %s", (id_persona,))
                existing_user = cursor.fetchone()
                cursor.close()

                if existing_user:
                    # Si ya existe, puedes manejarlo según tus necesidades (puedes omitir el registro, actualizar, etc.)
                    print(f"Usuario con id_persona {id_persona} ya existe en la base de datos.")
                else:
                    # Contraseña será el id_persona concatenado con 
                    contraseña = f"{id_persona}"

                    # Inserta los datos en la base de datos
                    cursor = mysql.connection.cursor()
                    cursor.execute("INSERT INTO personas (id_persona, nombre, cargo, contraseña) VALUES (%s, %s, %s, %s)",
                                   (id_persona, nombre, cargo, contraseña))
                    mysql.connection.commit()
                    cursor.close()

            return jsonify({"message": "Usuarios registrados exitosamente"})
            
            
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/coorpermisosfichas')
def coorpermisosfichas():
    if 'cargo' in session and session['cargo'] == 'Coordinador':
        usuario_datos = session['usuario_nombre']
        cur = mysql.connection.cursor()
        cur.execute("SELECT pf.*, f.programa, p.nombre, pf.detalle FROM permisos_fichas pf \
                JOIN fichas f ON pf.fichas_id_ficha = f.id_ficha \
                JOIN personas p ON pf.personas_id_persona = p.id_persona WHERE pf.vb_vigilante != 0")
        resultados = cur.fetchall()
        cur.close()

        response = make_response(render_template('coorpermisosfichas.html', usuario_nombre=usuario_datos, resultados=resultados))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # Deshabilitar la caché
        return response
    else:
        flash('Acceso no autorizado', 'error')
        return redirect('/')
    
@app.route('/coorpersonas')
def coorpersonas():
    if 'cargo' in session and session['cargo'] == 'Coordinador':
        usuario_datos = session['usuario_nombre']
        cur = mysql.connection.cursor()
        cur.execute("SELECT id_persona, nombre, cargo FROM personas")
        data = cur.fetchall()
        cur.close()        

        response = make_response(render_template('coorpersonas.html', usuario_nombre=usuario_datos, data = data))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # Deshabilitar la caché
        return response
    else:
        flash('Acceso no autorizado', 'error')
        return redirect('/')

@app.route('/guardar_edicion_ajax', methods=['POST'])
def guardar_edicion_ajax():
    if request.method == 'POST':
        try:
            id_persona = request.form['id']
            nuevo_valor = request.form['value']

            print('ID Persona recibido:', id_persona)
            print('Nuevo Valor recibido:', nuevo_valor)

            cur = mysql.connection.cursor()
            cur.execute("UPDATE personas SET cargo=%s WHERE id_persona=%s", (nuevo_valor, id_persona))
            mysql.connection.commit()
            cur.close()

            print('Actualización exitosa')

            return jsonify({'message': 'Actualización exitosa'})
        except Exception as e:
            print('Error:', str(e))
            return jsonify({'error': 'Error al actualizar'})


import hashlib

@app.route('/agregar_usuario', methods=['POST'])
def agregar_usuario():
    if request.method == 'POST':
        mensaje = ""  
        icon =""
        nombre = request.form['nombre']
        cargo = request.form['cargo']
        # Generar una contraseña basada en el ID + ""
        id_usuario = request.form['id']
        contraseña = f"{id_usuario}"

        # Función para encriptar la contraseña
        def encrypt_password(password):
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            return hashed_password

        # Encriptar la contraseña
        hashed_password = encrypt_password(contraseña) 

        # Insertar el nuevo usuario en la base de datos
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO personas (id_persona, nombre, cargo, contraseña) VALUES (%s, %s, %s, %s)",
                    (id_usuario, nombre, cargo, hashed_password))
        mysql.connection.commit()
        cur.close()

        # Redireccionar a la página principal o a donde sea necesario
        mensaje = "Usuario Registrado"
        icon = "success"
        return render_template('coorregistrar.html', mensaje=mensaje, icon=icon)


""" ---------------------------------------------------------- """

""" -------------------PORTERIA------------------------------- """
@app.route('/asistencia')
def asistencia():
    if 'cargo' in session and session['cargo'] == 'Porteria':
        cur = mysql.connection.cursor()
        cur.execute("SELECT ia.*, a.nombre AS nombre_aprendiz FROM ingresos_aprendices ia \
                     JOIN aprendices a ON ia.aprendices_documento = a.documento")
        ingresos = cur.fetchall()
        cur.close()
        response = make_response(render_template('asistencia.html', ingresos=ingresos))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # Deshabilitar la caché
        return response
    else:
        flash('Acceso no autorizado', 'error')
        return redirect('/')
 
@app.template_filter('datetimeformat')
def datetimeformat(value):
    if value:
        return value.strftime('%d-%m-%Y %I:%M %p')  # Día-Mes-Año Hora:Minuto AM/PM
    return ""


@app.route('/porteria', methods=['GET', 'POST'])
def porteria():
    if 'cargo' in session and session['cargo'] == 'Porteria':
        cur = mysql.connection.cursor()

        # Configurar la zona horaria de Bogotá
        bogota_tz = pytz.timezone('America/Bogota')

        # Obtener la fecha actual en la zona horaria de Bogotá al inicio del día
        fecha_actual = datetime.now(bogota_tz).replace(hour=0, minute=0, second=0, microsecond=0)

        # Actualizar permisos anteriores al día actual para que estén inactivos
        cur.execute("""
            UPDATE permisos
            SET estado = 'inactivo'
            WHERE estado = 'activo' AND (fecha_hora_salida < %s OR fecha_hora_entrada < %s);
        """, (fecha_actual, fecha_actual))
        mysql.connection.commit()

        if request.method == 'POST':
            # Si se envió un formulario POST, procesar la solicitud de cambio de estado
            id_solicitud = request.form.get('id_solicitud')

            # Asegurarnos de manejar adecuadamente errores y validar el id_solicitud
            cur.execute("SELECT id_solicitud, fecha_hora_entrada, fecha_hora_salida, ok_vigilante_salida, ok_vigilante_entrada, fecha_hora_regreso FROM permisos WHERE id_solicitud = %s", (id_solicitud,))
            solicitud = cur.fetchone()
            if solicitud:
                id_solicitud = solicitud[0]
                fecha_hora_entrada = solicitud[1]
                fecha_hora_salida = solicitud[2]
                ok_vigilante_salida = solicitud[3]
                ok_vigilante_entrada = solicitud[4]
                fecha_hora_actual = datetime.now(bogota_tz)  # Obtener la hora actual en Bogotá
                diferencia_tiempo = None  # Definir la variable fuera del bloque if

                # Convertir fechas almacenadas en la base de datos a la zona horaria de Bogotá
                if fecha_hora_entrada:
                    fecha_hora_entrada = fecha_hora_entrada.replace(tzinfo=bogota_tz)
                if fecha_hora_salida:
                    fecha_hora_salida = fecha_hora_salida.replace(tzinfo=bogota_tz)

                if fecha_hora_entrada is not None and fecha_hora_salida is not None and fecha_hora_actual > fecha_hora_entrada:
                    retraso = fecha_hora_actual - fecha_hora_entrada
                    # Obtener la diferencia en horas, minutos y segundos
                    diferencia_segundos = retraso.seconds
                    diferencia_horas = diferencia_segundos // 3600  # Convertir segundos a horas
                    diferencia_minutos = (diferencia_segundos % 3600) // 60  # Obtener el resto de los segundos convertidos a minutos
                    diferencia_segundos = diferencia_segundos % 60  # Obtener el resto de los segundos
                    diferencia_tiempo = "{:02}:{:02}:{:02}".format(diferencia_horas, diferencia_minutos, diferencia_segundos)

                # Validar los casos
                if fecha_hora_entrada is None:
                    # Caso 1: Actualizar ok_vigilante_salida a 1 y eliminar del html
                    cur.execute("UPDATE permisos SET ok_vigilante_salida = 1, estado = 'inactivo' WHERE id_solicitud = %s", (id_solicitud,))
                    mysql.connection.commit()
                    return redirect('/porteria')
                elif fecha_hora_salida is None:
                    cur.execute("UPDATE permisos SET ok_vigilante_entrada = 1, estado = 'inactivo', retraso = %s WHERE id_solicitud = %s", (diferencia_tiempo, id_solicitud,))
                    mysql.connection.commit()
                    return redirect('/porteria')
                elif fecha_hora_entrada is not None and fecha_hora_salida is not None and ok_vigilante_salida == 0:
                    cur.execute("UPDATE permisos SET ok_vigilante_salida = 1 WHERE id_solicitud = %s", (id_solicitud,))
                    mysql.connection.commit()
                elif fecha_hora_entrada is not None and fecha_hora_salida is not None and ok_vigilante_salida == 1 and ok_vigilante_entrada == 0:
                    cur.execute("UPDATE permisos SET ok_vigilante_entrada = 1, estado = 'inactivo', fecha_hora_regreso = %s, retraso = %s WHERE id_solicitud = %s", (fecha_hora_actual, diferencia_tiempo, id_solicitud,))
                    mysql.connection.commit()
                else:
                    # Caso 4: No realizar cambios
                    pass

        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT
                p.id_solicitud,
                p.aprendices_documento,
                personas.nombre AS nombre_instructor,
                aprendices.nombre AS nombre_aprendiz,
                p.fecha_hora_salida,
                p.fecha_hora_entrada,
                CASE
                    WHEN p.fecha_hora_salida IS NOT NULL AND p.fecha_hora_entrada IS NOT NULL AND p.ok_vigilante_salida = 1 THEN 1
                    ELSE 0
                END AS cumple_condiciones
            FROM permisos p
            JOIN personas ON p.personas_id_persona = personas.id_persona
            JOIN aprendices ON p.aprendices_documento = aprendices.documento
            WHERE p.vb_instructor = 1 AND p.estado = 'activo';
        """)
        resultados = cur.fetchall()

        # Cerrar la conexión a la base de datos
        cur.close()

        response = make_response(render_template('porteria.html', resultados=resultados))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # Deshabilitar la caché
        return response
    else:
        flash('Acceso no autorizado', 'error')
        return redirect('/')

    
@app.route('/modificar_observacion', methods=['POST'])
def modificar_observacion():
    id_ingreso = request.form.get('id_ingreso')
    nueva_observacion = request.form.get('nueva_observacion')

    # Realiza la actualización en la base de datos usando el id_ingreso
    cur = mysql.connection.cursor()
    cur.execute("UPDATE ingresos_aprendices SET observacion = %s WHERE id_ingresos1 = %s", (nueva_observacion, id_ingreso))
    mysql.connection.commit()
    cur.close()

    # Devuelve una respuesta JSON para indicar el éxito de la operación
    return jsonify(success=True)

# @app.route('/get_permisos_porteria', methods=['GET'])
# def get_permisos_porteria():
#     # Aquí debes realizar la consulta a la base de datos para obtener los datos necesarios
#     cur = mysql.connection.cursor()
#     cur.execute("""
#             SELECT
#                 p.id_solicitud,
#                 p.aprendices_documento,
#                 personas.nombre AS nombre_instructor,
#                 aprendices.nombre AS nombre_aprendiz,
#                 p.fecha_hora_salida,
#                 p.fecha_hora_entrada,
#                 CASE
#                     WHEN p.fecha_hora_salida IS NOT NULL AND p.fecha_hora_entrada IS NOT NULL AND p.ok_vigilante_salida = 1 THEN 1
#                     ELSE 0
#                 END AS cumple_condiciones
#                 FROM permisos p
#                 JOIN personas ON p.personas_id_persona = personas.id_persona
#                 JOIN aprendices ON p.aprendices_documento = aprendices.documento
#                 WHERE p.vb_instructor = 1 AND p.estado = 'activo';
#             """)
#     resultados = cur.fetchall()
    
#     # Cerrar la conexión a la base de datos
#     cur.close()
#     # conn.close()
    

    
#     # Renderizar la plantilla HTML con los resultados
#     return render_template('tabla.html', resultados=resultados)



@app.route('/registrar')
def registrar():
    if 'cargo' in session and session['cargo'] == 'Porteria':
      
        response = make_response(render_template('Registrar.html'))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # Deshabilitar la caché
        return response
    else:
        flash('Acceso no autorizado', 'error')
        return redirect('/')
@app.route('/permisosfichas', methods=['GET', 'POST'])
def permisosfichas():
    if 'cargo' in session and session['cargo'] == 'Porteria':
        cur = mysql.connection.cursor()

        # Obtener la fecha actual al inicio del día
        fecha_actual = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Actualizar permisos anteriores al día actual para que estén inactivos
        cur.execute("""
            UPDATE permisos_fichas
            SET estado = 'inactivo'
            WHERE estado = 'activo' AND (fecha_hora_salida < %s OR fecha_hora_entrada < %s);
        """, (fecha_actual, fecha_actual))
        mysql.connection.commit()

        if request.method == 'POST':
            # Obtener el id de la solicitud del formulario enviado
            id_solicitud = request.form.get('id_solicitud')        
            
            # Realizar la actualización en la base de datos
            cur.execute("UPDATE permisos_fichas SET vb_vigilante = 1 WHERE id_permiso = %s", (id_solicitud,))
            mysql.connection.commit()
            cur.close()
        
            # Redirigir a la misma página para reflejar los cambios
            return redirect(url_for('permisosfichas'))

        # Consulta SQL para obtener los datos de la tabla permisos_fichas
        cur.execute("""
            SELECT pf.id_permiso, f.id_ficha, f.programa, pf.fecha_hora_salida, pf.fecha_hora_entrada, p.nombre
            FROM permisos_fichas pf
            JOIN fichas f ON pf.fichas_id_ficha = f.id_ficha
            JOIN personas p ON pf.personas_id_persona = p.id_persona
            WHERE pf.vb_vigilante = 0 AND pf.estado = 'activo';
        """)

        resultados = cur.fetchall()
        cur.close()
        
        response = make_response(render_template('permisosfichas.html', resultados=resultados))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # Deshabilitar la caché
        return response
    else:
        flash('Acceso no autorizado', 'error')
        return redirect('/')

@app.route('/agregar_dispositivo', methods=['POST'])
def agregar_dispositivo():
    if request.method == 'POST':
        mensaje = ""  
        icon = ""
        numero_documento = request.form['numero_documento']
        marca = request.form['marca_dispositivo']
        serial = request.form['serial_dispositivo']
        descripcion = request.form['descripcion_dispositivo']
        tipo = request.form['tipo_dispositivo']
        fecha = datetime.now()
        cur = mysql.connection.cursor()

        cur.execute("SELECT serial FROM elementos_aprendices WHERE serial = %s", (serial,))
        serial_a = cur.fetchone()
        cur.execute("SELECT serial FROM elementos_personas WHERE serial = %s", (serial,))
        serial_p = cur.fetchone()

        if serial_a or serial_p:
            
            mensaje = "Ya existe un dispositivo con este serial"  
            icon = "info"
            return render_template('Registrar.html', mensaje=mensaje,icon=icon)
        else:
            pass

        # Verificar si el número de documento pertenece a personas
        cur.execute("SELECT id_persona FROM personas WHERE id_persona = %s", (numero_documento,))
        persona = cur.fetchone()

        # Verificar si el número de documento pertenece a aprendices si no se encuentra en personas
        if not persona:
            cur.execute("SELECT documento FROM aprendices WHERE documento = %s", (numero_documento,))
            aprendiz = cur.fetchone()

        # Insertar datos en la tabla correspondiente
        if persona:
            cur.execute("INSERT INTO elementos_personas (personas_id_persona, marca, serial, descripcion, tipo, fecha_registro) VALUES (%s, %s, %s, %s, %s, %s)", (numero_documento, marca, serial, descripcion, tipo, fecha))
            
        elif aprendiz:
            cur.execute("INSERT INTO elementos_aprendices (aprendices_documento, marca, serial, descripcion, tipo, fecha_registro) VALUES (%s, %s, %s, %s, %s, %s)", (numero_documento, marca, serial, descripcion, tipo, fecha))
        
        mysql.connection.commit()
        cur.close()
        
        # Redireccionar a la página principal o a donde sea necesario
        mensaje = "Dispositivo agregado exitosamente"  
        icon = "success"
        return render_template('Registrar.html', mensaje=mensaje,icon=icon)

@app.route('/agregar_usuario2', methods=['POST'])
def agregar_usuario2():
    if request.method == 'POST':
        mensaje = ""
        icon = ""
        nombre = request.form['nombre']
        cargo = request.form['cargo']
        # Generar una contraseña basada en el ID + ""
        id_usuario = request.form['id']
        contraseña = f"{id_usuario}"

        if cargo == 'Administrativo':
           cargo = 'Inactivo'
        else:
            pass

        # Insertar el nuevo usuario en la base de datos
        cur = mysql.connection.cursor()
        cur.execute("SELECT id_persona FROM personas WHERE id_persona=%s", (id_usuario,))

        persona = cur.fetchone()
        if persona:
            mensaje = "Esta usuario ya se encuentra registrado"  
            icon = "info"
            return render_template('Registrar.html', mensaje=mensaje,icon=icon)
        cur.execute("INSERT INTO personas (id_persona, nombre, cargo, contraseña) VALUES (%s, %s, %s, %s)",
                    (id_usuario, nombre, cargo, contraseña))
        mysql.connection.commit()
        cur.close()

        # Redireccionar a la página principal o a donde sea necesario
        mensaje = "Usuario registrado exitosamente"
        icon = "success"  
        return render_template('Registrar.html', mensaje=mensaje,icon=icon)


if __name__ == '__main__':
    app.run(host='0.0.0.0')

