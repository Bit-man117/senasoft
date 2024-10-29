import hashlib
import imghdr
from io import BytesIO
from flask import Flask, jsonify, make_response, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from datetime import datetime, timedelta
import pandas as pd
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from flask_cors import CORS
import xlrd
import os
import pytz
import base64
import re
import random
from flask import Response
 
class Config:
    SECRET_KEY = b'_5#y2L"F4Q8z\n\xec]/'
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = 'password'
    MYSQL_DB = 'senabike'

app = Flask(__name__)
app.config.from_object(Config)    
mysql = MySQL(app)

@app.route('/')
def index():
    if 'rol' in session:
        cargo = session['rol']
        if cargo == 3:   
            return redirect('/admin')
        else:
            return redirect('/usuarios')
    
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM eventos')
    data = cur.fetchall()
    cur.close()

    # Convertir el longblob a base64
    eventos_con_imagen = []
    for evento in data:
        # Asumiendo que el campo de la imagen es el 4to (índice 4)
        imagen_base64 = base64.b64encode(evento[4]).decode('utf-8')
        # Añadir la información del evento junto con la imagen en base64
        eventos_con_imagen.append((evento[0], evento[1], evento[2], imagen_base64))  # id, nombre, fecha, imagen

    return render_template('index.html', info=eventos_con_imagen)
@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        id_persona = request.form['usuario']
        password = request.form['password']

        # Encriptar la contraseña
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE cedula = %s AND contrasena = %s', (id_persona, hashed_password))
        user = cursor.fetchone()
        cursor.close()

        if user:
            id_usuario = user[0]
            nombre_usuario = user[1]
            cargo = user[3]  # Rol del usuario (entero)
            
            # Comprobar si el cargo es 4
            if cargo == 4:
                return jsonify({'error': 'Acceso denegado. No tienes permiso para ingresar.'})

            session['cedula'] = id_usuario
            session['rol'] = cargo  # Guardar el rol como entero
            session['nombre'] = nombre_usuario
            
            # Redirigir según el rol
            if cargo == 3:  # Verificar rol como entero
                return jsonify({'redirect': url_for('admin')})
            else:
                return jsonify({'redirect': url_for('users')})
        else:
            return jsonify({'error': 'Usuario o contraseña incorrecta'})

    return redirect('/')





@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')



@app.route('/usuarios')
def users():
    if 'rol' in session and session['rol'] != 3:
        usuario_nombre = session.get('nombre')
        usuario_nombre = usuario_nombre.split()[0] if usuario_nombre else 'Usuario'
        
        # Conexión a la base de datos y recuperación de bicicletas activas
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id_bicicleta, marca, color, tarifa, estado, id_centro, foto FROM bicicletas WHERE estado = 1")
        bicicletas = cursor.fetchall()
        cursor.close()

        # Crear una lista nueva para almacenar las bicicletas con la imagen en base64
        bicicletas_base64 = []
        for bici in bicicletas:
            # Convertir la imagen a base64
            foto_base64 = base64.b64encode(bici[6]).decode('utf-8')  # Convertir la imagen a base64
            # Agregar a la nueva lista como un nuevo elemento
            bicicletas_base64.append((bici[0], bici[1], bici[2], bici[3], bici[4], bici[5], foto_base64))
        
        # Preparar la respuesta para renderizar la plantilla
        response = make_response(render_template('usuarios.html', nombre=usuario_nombre, bicis=bicicletas_base64))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # Deshabilitar la caché
        return response
    else:
        flash('Acceso no autorizado', 'error')
        return redirect('/')
 

@app.route('/disponibles')
def disponibles():
    try:
        # Conexión a la base de datos y recuperación de bicicletas activas
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id_bicicleta, marca, color, tarifa, estado, id_centro, foto FROM bicicletas WHERE estado = 1")
        bicicletas = cursor.fetchall()
    except Exception as e:
        print(f"Error al obtener las bicicletas: {e}")
        return "Error en la base de datos", 500
    finally:
        cursor.close()

    # Crear una lista nueva para almacenar las bicicletas con la imagen en base64
    bicicletas_base64 = []
    for bici in bicicletas:
        # Verificar si la imagen está presente
        foto_base64 = base64.b64encode(bici[6]).decode('utf-8') if bici[6] else None
        # Agregar a la nueva lista como un nuevo elemento
        bicicletas_base64.append((bici[0], bici[1], bici[2], bici[3], bici[4], bici[5], foto_base64))

    # Preparar la respuesta para renderizar la plantilla
    response = make_response(render_template('disponibles.html', bicis=bicicletas_base64))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # Deshabilitar la caché
    return response

    
@app.route('/admin')
def admin():
    if 'rol' in session and session['rol'] == 3:  # Esto permite el acceso a los administradores
        usuario_datos = session.get('nombre')
        # Renderiza la plantilla de administradores
        response = make_response(render_template('administrador.html', usuario_nombre=usuario_datos))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response
    else:
        flash('Acceso no autorizado', 'error')
        return redirect('/') 
     

@app.route('/totalventas')
def totalventas():
    if 'rol' in session and session['rol'] == 3:  # Esto permite el acceso a los administradores
        usuario_datos = session.get('nombre')
        response = make_response(render_template('total_ventas.html', usuario_nombre=usuario_datos))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # Deshabilitar la caché
        return response
    else:
        flash('Acceso no autorizado', 'error')
        return redirect('/')


@app.route('/coorregistrar')
def coorregistrar():
    if 'rol' in session and session['rol'] == 3:  # Esto permite el acceso a los administradores
        usuario_datos = session.get('nombre')
        response = make_response(render_template('coorregistrar.html', usuario_nombre=usuario_datos))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # Deshabilitar la caché
        return response
    else:
        flash('Acceso no autorizado', 'error')
        return redirect('/')

@app.route('/coorpersonas')
def coorpersonas():
    if 'rol' in session and session['rol'] == 3:  # Esto permite el acceso a los administradores
        usuario_datos = session.get('nombre')
        cur = mysql.connection.cursor()

        # Obtener datos de usuarios
        cur.execute("SELECT cedula, nombre, rol FROM usuarios")
        data = cur.fetchall()

        # Obtener datos de centros
        cur.execute("SELECT id_centro, nombre FROM centros")
        centros = cur.fetchall()

        cur.close()        

        response = make_response(render_template('coorpersonas.html', usuario_nombre=usuario_datos, data=data, centros=centros))  # Pasar los centros al template
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # Deshabilitar la caché
        return response
    else:
        flash('Acceso no autorizado', 'error')
        return redirect('/')


@app.route('/ubicaciones')
def ubicaciones():
    if 'rol' in session and session['rol'] == 3:  # Esto permite el acceso a los administradores
        usuario_datos = session.get('nombre')
        


        
        response = make_response(render_template('ubicaciones.html', usuario_nombre=usuario_datos))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # Deshabilitar la caché
        return response
    else:
        flash('Acceso no autorizado', 'error')
        return redirect('/')
    
@app.route('/alquileres')
def alquileres():
    if 'rol' in session and session['rol'] == 3:
        usuario_nombre = session.get('nombre')
        usuario_nombre = usuario_nombre.split()[0] if usuario_nombre else 'Usuario'
        
        # Conexión a la base de datos y recuperación de bicicletas activas
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id_bicicleta, marca, color, tarifa, estado, id_centro, foto FROM bicicletas WHERE estado = 0")
        bicicletas = cursor.fetchall()
        cursor.close()

        # Crear una lista nueva para almacenar las bicicletas con la imagen en base64
        bicicletas_base64 = []
        for bici in bicicletas:
            # Convertir la imagen a base64
            foto_base64 = base64.b64encode(bici[6]).decode('utf-8')  # Convertir la imagen a base64
            # Agregar a la nueva lista como un nuevo elemento
            bicicletas_base64.append((bici[0], bici[1], bici[2], bici[3], bici[4], bici[5], foto_base64))
        
        # Preparar la respuesta para renderizar la plantilla
        response = make_response(render_template('alquileres.html', nombre=usuario_nombre, bicis=bicicletas_base64))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # Deshabilitar la caché
        return response
    else:
        flash('Acceso no autorizado', 'error')
        return redirect('/')


@app.route('/devolver', methods=['POST'])
def devolver_bicicleta():
    data = request.get_json()
    id_bicicleta = data['id_bicicleta']

    try:
        # Obtener la fecha y hora actual
        fecha_fin = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Crear un cursor y ejecutar las consultas
        cursor = mysql.connection.cursor()

        # Actualizar la tabla de alquileres para marcar la fecha de finalización
        cursor.execute("""
            UPDATE alquileres
            SET fecha_fin = %s
            WHERE id_bicicleta = %s AND fecha_fin IS NULL
        """, (fecha_fin, id_bicicleta))

        # Actualizar el estado de la bicicleta a 1 (disponible)
        cursor.execute("""
            UPDATE bicicletas
            SET estado = 1
            WHERE id_bicicleta = %s
        """, (id_bicicleta,))

        # Confirmar los cambios
        mysql.connection.commit()

        return jsonify({'success': True})

    except Exception as e:
        mysql.connection.rollback()
        print(f"Error al devolver la bicicleta: {e}")
        return jsonify({'success': False})

    finally:
        cursor.close()

def calcular_precio_bicicleta(bicicleta_id, alquiler_id):
    
    try:
        cursor = mysql.connection.cursor()

        # Consultar la tarifa de la bicicleta
        cursor.execute("SELECT tarifa FROM bicicletas WHERE id = %s", (bicicleta_id,))
        tarifa = cursor.fetchone()

        if tarifa is None:
            print("Bicicleta no encontrada.")
            return None

        tarifa = tarifa[0]

        # Consultar la fecha de inicio y fin del alquiler
        cursor.execute("SELECT fecha_inicio, fecha_fin FROM alquileres WHERE id = %s", (alquiler_id,))
        alquiler = cursor.fetchone()

        if alquiler is None:
            print("Alquiler no encontrado.")
            return None

        fecha_inicio, fecha_fin = alquiler

        # Calcular la diferencia en horas
        diferencia_horas = (fecha_fin - fecha_inicio).total_seconds() / 3600

        # Calcular el total
        total = tarifa * diferencia_horas

        # Consultar el estrato del usuario
        cursor.execute("""
            SELECT estrato FROM usuarios 
            WHERE id = (SELECT usuario_id FROM alquileres WHERE id = %s)
        """, (alquiler_id,))
        usuario = cursor.fetchone()

        if usuario is None:
            print("Usuario no encontrado.")
            return None

        estrato = usuario[0]

        # Aplicar descuento según el estrato
        if estrato in [1, 2]:
            descuento = total * 0.10
        elif estrato in [3, 4]:
            descuento = total * 0.05
        else:
            descuento = 0

        total_con_descuento = total - descuento

        # Retornar resultados en lugar de imprimir, si es parte de una app web
        return {
            'total_sin_descuento': total,
            'total_con_descuento': total_con_descuento
        }

    except Exception as e:
        print(f"Error: {e}")
        return None

    finally:
        cursor.close()  # Cerrar cursor


@app.route('/registromasivo')
def registromasivo():
    if 'rol' in session and session['rol'] == 3:  # Esto permite el acceso a los administradores
        usuario_datos = session.get('nombre')
        response = make_response(render_template('registromasivo.html', usuario_nombre=usuario_datos))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # Deshabilitar la caché
        return response
    else:
        flash('Acceso no autorizado', 'error')
        return redirect('/')

@app.route('/procesar', methods=['POST'])
def procesar():
    mensaje = ""  
    icon = ""
    if 'rol' in session and session['rol'] == 3: 
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
                info_celda_C3 = df.iloc[10, 2]  # C3
                info_celda_C6 = df.iloc[10, 2]  # C6

                # Extraer solo números de info_celda_C3
                solo_numeros_C3 = re.sub(r'[^0-9]', '', str(info_celda_C3))  # Elimina todo lo que no sea números

                # Extraer solo letras de info_celda_C6
                solo_letras_C6 = re.sub(r'[^a-zA-Z\s]', '', str(info_celda_C6))

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

                return render_template('excel.html', datos=datos, info_celda_C3=solo_numeros_C3,
                                       info_celda_C6=solo_letras_C6, info_celda_C8=info_celda_C8, info_celda_C9=info_celda_C9)

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
        cur = mysql.connection.cursor()
        data = request.get_json()
        
        # Make sure the key names match
        id_ficha = data.get('id_ficha')
        datos_aprendices = data['datosAprendices']
        rol = data['jornada']  # 1 para Aprendices, 2 para Funcionarios
        id_centro = data.get('id_ficha')  # Adjust if necessary

        for aprendiz in datos_aprendices:
            documento = aprendiz['documento']
            nombre = aprendiz['nombre']
            contrasena = hashlib.sha256(documento.encode()).hexdigest()
            estrato = random.randint(1, 6)

            cur.execute("INSERT INTO usuarios (cedula, nombre, contrasena, rol, estrato, id_centro) VALUES (%s, %s, %s, %s, %s, %s)",
                        (documento, nombre, contrasena, rol, estrato, id_centro))
            mysql.connection.commit()

        cur.close()
        return jsonify({"mensaje": "Datos agregados exitosamente"})
    
    except Exception as e:
        print("Error en agregar_datos:", str(e))
        return jsonify({"error": f"Hubo un error en el servidor: {str(e)}"}), 400


@app.route('/actualizar-rol', methods=['POST'])
def actualizar_rol():
    data = request.get_json()
    cedula = data.get('cedula')
    nuevo_rol = data.get('nuevo_rol')

    try:
        # Conectar a la base de datos y obtener el cursor
        cursor = mysql.connection.cursor()
        
        # Actualizar el rol en la base de datos
        cursor.execute("UPDATE usuarios SET rol = %s WHERE cedula = %s", (nuevo_rol, cedula))
        mysql.connection.commit()  # Usa mysql.connection para el commit
        return jsonify(success=True)
    except Exception as e:
        mysql.connection.rollback()  # Usa mysql.connection para rollback
        return jsonify(success=False, error=str(e))
    finally:
        cursor.close()  # Cerrar el cursor



@app.route('/agregar_usuario', methods=['POST'])
def agregar_usuario():
    mensaje = ""
    icon = "info"

    if request.method == 'POST':
        id = request.form['id']
        nombre = request.form['nombre']
        estrato = request.form['estrato']
        centro = request.form['centro']
        rol = request.form['rol']

        # Encriptar la contraseña usando hashlib
        contrasena = hashlib.sha256(id.encode()).hexdigest()  # Usar el id como base para el hash

        # Conectar a la base de datos
        cursor = mysql.connection.cursor()

        # Validar si el usuario ya existe
        cursor.execute("SELECT * FROM usuarios WHERE cedula = %s", (id,))
        usuario_existente = cursor.fetchone()

        if usuario_existente:
            mensaje = 'El usuario ya existe. Por favor, use otro ID.'
            icon = 'danger'
        else:
            # Insertar datos en la tabla usuarios
            try:
                cursor.execute("""
                    INSERT INTO usuarios (cedula, nombre, estrato, id_centro, rol, contrasena)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (id, nombre, estrato, centro, rol, contrasena))
                
                mysql.connection.commit()
                mensaje = 'Usuario agregado correctamente'
                icon = 'success'
            except Exception as e:
                mysql.connection.rollback()
                mensaje = f'Error al agregar el usuario: {e}'
                icon = 'danger'
        
        cursor.close()

        # Redirigir a la misma página con el mensaje
        return render_template('coorregistrar.html', mensaje=mensaje, icon=icon)

    return render_template('coorregistrar.html', mensaje=mensaje, icon=icon) 

    
@app.route('/registrobicis')
def registrobicis():
    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute("SELECT id_centro, nombre FROM centros")
    centros = cursor.fetchall()
    cursor.close()
    return render_template('registro_bici.html', asociar_centro=centros)

@app.route('/register', methods=['POST'])
def register():
    marca = request.form['marca']
    color = request.form['color']
    tarifa = request.form['tarifa']
    estado = request.form['estado']  # Este ahora será '0' o '1' como string
    id_centro = request.form['id_centro']
    foto = request.files['foto']
    
    # Leer la imagen en formato binario
    foto_data = foto.read()

    # Conectar a la base de datos y ejecutar la inserción
    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO bicicletas (marca, color, tarifa, estado, foto, id_centro)
        VALUES (%s, %s, %s, %s, %s, %s)
    ''', (marca, color, tarifa, estado, foto_data, id_centro))
    conn.commit()
    cursor.close()
    return redirect('/registrobicis')

 
@app.route('/alquilar', methods=['POST'])
def alquilar():
    if 'rol' in session and session['rol'] != 3:
        cedula = session.get('cedula')
        data = request.get_json()
        id_bicicleta = data.get('id_bicicleta')

        if not id_bicicleta or not cedula:
            return jsonify({'success': False, 'message': 'Datos inválidos.'}), 400

        cedula_usuario = cedula

        # Obtener la conexión y crear un cursor
        connection = mysql.connection
        try:
            cursor = connection.cursor()

            # Insertar en la tabla alquileres
            fecha_inicio = datetime.now()

            insert_alquiler = """
            INSERT INTO alquileres (cedula, id_bicicleta, fecha_inicio)
            VALUES (%s, %s, %s)
            """
            cursor.execute(insert_alquiler, (cedula_usuario, id_bicicleta, fecha_inicio))

            # Cambiar el estado de la bicicleta a no disponible (estado 0)
            update_bicicleta = """
            UPDATE bicicletas
            SET estado = 0
            WHERE id_bicicleta = %s
            """
            cursor.execute(update_bicicleta, (id_bicicleta,))

            # Confirmar los cambios
            connection.commit()

            return jsonify({'success': True}), 200

        except Exception as e:
            connection.rollback()  # Deshacer cambios en caso de error
            app.logger.error(f"Error al alquilar: {str(e)}")
            return jsonify({'success': False, 'message': str(e)}), 500

        finally:
            cursor.close()

    return jsonify({'success': False, 'message': 'Acceso no autorizado.'}), 403

@app.route('/ingresos')
def ingresos():
    registros, suma_total = obtener_alquileres()
    return render_template('index.html', registros=registros, suma_total=suma_total)




def obtener_alquileres():
    # Conectar a la base de datos
    connection = mysql.connect
    try:
        cursor = connection.cursor()

        # Consulta SQL para obtener todos los registros
        query = "SELECT fecha_fin, total FROM alquileres"
        cursor.execute(query)
        
        # Recuperar todos los registros
        registros = cursor.fetchall()

        # Calcular la suma total
        suma_total = sum(registro[1] for registro in registros)

        return registros, suma_total

    finally:
        cursor.close()
        connection.close()
@app.route("/inicio")
def inicio():
    return render_template("index.html")
 





if __name__ == '__main__':
    app.run(debug=True)
