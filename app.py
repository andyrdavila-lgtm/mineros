from flask import Flask, render_template, request, redirect, url_for, session, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import sys
import time
import io
import csv
from functools import wraps
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy import or_, and_

app = Flask(__name__)

# Configuración
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Configuración de base de datos - Versión robusta
def get_database_url():
    for env_var in ['DATABASE_URL', 'POSTGRESQL_URL', 'PG_URL', 'POSTGRES_URL']:
        db_url = os.environ.get(env_var)
        if db_url:
            print(f"📦 Encontrada variable {env_var}: {db_url[:50]}...")
            if db_url.startswith('postgres://'):
                db_url = db_url.replace('postgres://', 'postgresql://', 1)
            return db_url
    
    print("⚠️  ADVERTENCIA: No se encontró DATABASE_URL. Usando SQLite.")
    return 'sqlite:///app.db'

app.config['SQLALCHEMY_DATABASE_URI'] = get_database_url()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==================== MODELOS DE BASE DE DATOS ====================

# Modelo de usuario
class User(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    rol = db.Column(db.String(20), nullable=False, default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password, password)

# Tabla: Aspectos Ambientales
class AspectoAmbiental(db.Model):
    __tablename__ = 'aspectos_ambientales'
    id = db.Column(db.Integer, primary_key=True)
    actividad = db.Column(db.String(500), nullable=False)
    tipo = db.Column(db.String(200), nullable=False)  # Para FODA: 'Positivo' o 'Negativo'
    aspecto = db.Column(db.String(500), nullable=False)  # Para FODA: POLITICO, ECONOMICO, etc.
    fuente = db.Column(db.String(200), nullable=False)  # 'foda_ext' o 'canva' o 'foda_int'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    
    # Relación
    creador = db.relationship('User', backref=db.backref('aspectos', lazy=True))

# Tabla: Estrategias FODA Cruzado
class EstrategiaFodaCruzado(db.Model):
    __tablename__ = 'estrategias_foda_cruzado'
    
    id = db.Column(db.Integer, primary_key=True)
    tipo_cruce = db.Column(db.String(10), nullable=False)  # FO, DO, FA, DA
    elemento_interno_id = db.Column(db.Integer, nullable=False)
    elemento_interno_tipo = db.Column(db.String(20), nullable=False)  # fortaleza, debilidad
    elemento_interno_texto = db.Column(db.String(500), nullable=False)
    elemento_externo_id = db.Column(db.Integer, nullable=False)
    elemento_externo_tipo = db.Column(db.String(20), nullable=False)  # oportunidad, amenaza
    elemento_externo_texto = db.Column(db.String(500), nullable=False)
    estrategia = db.Column(db.Text, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    creador_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    
    # Relación
    creador = db.relationship('User', backref=db.backref('estrategias_foda', lazy=True))

# ==================== DECORADORES DE AUTENTICACIÓN ====================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if user.rol != 'admin':
            return redirect(url_for('inicio'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== FUNCIÓN DE INICIALIZACIÓN DE BD ====================

def initialize_database():
    """Intenta inicializar la base de datos con reintentos"""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            print(f"🔄 Intento {attempt + 1} de {max_retries} para inicializar BD...")
            
            # Crear todas las tablas
            db.create_all()
            print("✅ Tablas creadas exitosamente")
            
            # Lista de usuarios a crear
            usuarios = [
                # Administradores (4 usuarios)
                {"username": "MINERA.ADMIN", "password": "MINERA.ADMIN", "rol": "admin"},
                {"username": "ANDRES", "password": "ANDRES", "rol": "admin"},
                {"username": "RICARDO", "password": "RICARDO", "rol": "admin"},
                {"username": "ALEJANDRO", "password": "ALEJANDRO", "rol": "admin"},
                
                # Usuarios normales (5 usuarios)
                {"username": "Minera1", "password": "Minera1", "rol": "user"},
                {"username": "Minera2", "password": "Minera2", "rol": "user"},
                {"username": "Minera3", "password": "Minera3", "rol": "user"},
                {"username": "Minera4", "password": "Minera4", "rol": "user"},
                {"username": "Minera5", "password": "Minera5", "rol": "user"},
            ]
            
            usuarios_creados = 0
            usuarios_existentes = 0
            
            # Crear cada usuario si no existe
            for usuario_info in usuarios:
                username = usuario_info["username"]
                user_exists = User.query.filter_by(username=username).first()
                
                if not user_exists:
                    nuevo_usuario = User(
                        username=username,
                        rol=usuario_info["rol"]
                    )
                    nuevo_usuario.set_password(usuario_info["password"])
                    db.session.add(nuevo_usuario)
                    usuarios_creados += 1
                    print(f"  ✅ Usuario '{username}' creado (rol: {usuario_info['rol']})")
                else:
                    usuarios_existentes += 1
            
            # Commit todos los cambios
            if usuarios_creados > 0:
                db.session.commit()
                print(f"✅ {usuarios_creados} usuarios nuevos creados")
            
            # Verificar que todas las tablas existen
            print(f"📊 Total de usuarios en sistema: {User.query.count()}")
            print(f"📊 Total de aspectos en sistema: {AspectoAmbiental.query.count()}")
            print(f"📊 Total de estrategias FODA cruzado: {EstrategiaFodaCruzado.query.count()}")
            
            return True
            
        except OperationalError as e:
            print(f"❌ Error de conexión (Intento {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                print("🚨 No se pudo conectar a la base de datos después de varios intentos")
                return False
                
        except Exception as e:
            print(f"❌ Error inesperado: {type(e).__name__}: {e}")
            db.session.rollback()
            return False
    
    return False

# ==================== RUTAS PRINCIPALES ====================

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                session['user_id'] = user.id
                session['username'] = user.username
                session['rol'] = user.rol
                
                if user.rol == 'admin':
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('inicio'))
            else:
                return render_template('inicio.html', error='Usuario o contraseña incorrectos')
        except Exception as e:
            print(f"Error en login: {e}")
            return render_template('inicio.html', error='Error de conexión a la base de datos')
    
    return render_template('inicio.html')

@app.route('/inicio')
@login_required
def inicio():
    # Obtener estadísticas para el dashboard
    total_aspectos = AspectoAmbiental.query.count()
    aspectos_recientes = AspectoAmbiental.query.order_by(
        AspectoAmbiental.created_at.desc()
    ).limit(5).all()
    
    # Obtener actividades del CANVA recientes
    aspectos_canva = AspectoAmbiental.query.filter_by(fuente='canva').order_by(
        AspectoAmbiental.created_at.desc()
    ).limit(5).all()
    
    # Obtener actividades de FODA Externo recientes
    aspectos_foda = AspectoAmbiental.query.filter_by(fuente='foda_ext').order_by(
        AspectoAmbiental.created_at.desc()
    ).limit(5).all()
    
    return render_template('inicio.html', 
                         total_aspectos=total_aspectos,
                         aspectos_recientes=aspectos_recientes,
                         aspectos_canva=aspectos_canva,
                         aspectos_foda=aspectos_foda)

# ==================== RUTAS PARA ASPECTOS AMBIENTALES ====================

@app.route('/aspectos')
@login_required
def listar_aspectos():
    """Lista todos los aspectos ambientales"""
    aspectos = AspectoAmbiental.query.order_by(AspectoAmbiental.created_at.desc()).all()
    return render_template('aspectos.html', aspectos=aspectos)

@app.route('/aspectos/crear', methods=['GET', 'POST'])
@login_required
def crear_aspecto():
    """Crear un nuevo aspecto ambiental"""
    if request.method == 'POST':
        try:
            nuevo_aspecto = AspectoAmbiental(
                actividad=request.form.get('actividad'),
                tipo=request.form.get('tipo'),
                aspecto=request.form.get('aspecto'),
                fuente=request.form.get('fuente'),
                created_by=session['user_id']
            )
            db.session.add(nuevo_aspecto)
            db.session.commit()
            return redirect(url_for('listar_aspectos'))
        except Exception as e:
            db.session.rollback()
            return render_template('crear_aspecto.html', error=str(e))
    
    return render_template('crear_aspecto.html')

@app.route('/aspectos/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_aspecto(id):
    """Editar un aspecto ambiental existente"""
    aspecto = AspectoAmbiental.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            aspecto.actividad = request.form.get('actividad')
            aspecto.tipo = request.form.get('tipo')
            aspecto.aspecto = request.form.get('aspecto')
            aspecto.fuente = request.form.get('fuente')
            db.session.commit()
            return redirect(url_for('listar_aspectos'))
        except Exception as e:
            db.session.rollback()
            return render_template('editar_aspecto.html', aspecto=aspecto, error=str(e))
    
    return render_template('editar_aspecto.html', aspecto=aspecto)

@app.route('/aspectos/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_aspecto(id):
    """Eliminar un aspecto ambiental"""
    if session.get('rol') != 'admin':
        return jsonify({'error': 'No autorizado'}), 403
    
    aspecto = AspectoAmbiental.query.get_or_404(id)
    db.session.delete(aspecto)
    db.session.commit()
    return redirect(url_for('listar_aspectos'))

# API para aspectos ambientales (JSON)
@app.route('/api/aspectos')
@login_required
def api_aspectos():
    """API para obtener aspectos en formato JSON"""
    # Filtrar por fuente si se especifica
    fuente = request.args.get('fuente')
    
    query = AspectoAmbiental.query
    
    if fuente:
        query = query.filter_by(fuente=fuente)
    
    aspectos = query.order_by(AspectoAmbiental.created_at.desc()).all()
    
    return jsonify([{
        'id': a.id,
        'actividad': a.actividad,
        'tipo': a.tipo,
        'aspecto': a.aspecto,
        'fuente': a.fuente,
        'created_at': a.created_at.isoformat() if a.created_at else None,
        'updated_at': a.updated_at.isoformat() if a.updated_at else None,
        'creador': a.creador.username if a.creador else None
    } for a in aspectos])

# ==================== RUTAS ESPECÍFICAS PARA FODA EXTERNO ====================

@app.route('/fodaext')
@login_required
def fodaext():
    """Página para análisis FODA Externo"""
    try:
        # Obtener aspectos para FODA Externo (fuente = 'foda_ext') para la matriz
        aspectos_lista = AspectoAmbiental.query.filter_by(
            fuente='foda_ext'
        ).order_by(
            AspectoAmbiental.aspecto,  # Primero orden por aspecto
            AspectoAmbiental.created_at.desc()  # Luego por fecha
        ).all()
        
        # Obtener historial mixto (foda_ext y canva) - últimos 20
        historial_actividades = AspectoAmbiental.query.filter(
            or_(
                AspectoAmbiental.fuente == 'foda_ext',
                AspectoAmbiental.fuente == 'canva'
            )
        ).order_by(
            AspectoAmbiental.created_at.desc()
        ).limit(20).all()
        
        # Crear diccionario para estadísticas
        estadisticas = {
            'total': len(aspectos_lista),
            'positivos': len([a for a in aspectos_lista if a.tipo == 'Positivo']),
            'negativos': len([a for a in aspectos_lista if a.tipo == 'Negativo']),
            'historial_total': len(historial_actividades)
        }
        
        return render_template('fodaext.html', 
                             aspectos_lista=aspectos_lista,
                             historial_actividades=historial_actividades,
                             estadisticas=estadisticas)
        
    except Exception as e:
        print(f"Error en fodaext: {e}")
        return render_template('fodaext.html', 
                             aspectos_lista=[], 
                             historial_actividades=[],
                             estadisticas={'total': 0, 'positivos': 0, 'negativos': 0, 'historial_total': 0})

@app.route('/guardar_foda_ext', methods=['POST'])
@login_required
def guardar_foda_ext():
    """Guardar un aspecto para FODA Externo - Versión mejorada"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Formato no soportado'}), 400
        
        data = request.get_json()
        
        # Validar campos requeridos
        if not data.get('actividad'):
            return jsonify({'success': False, 'message': 'La actividad es obligatoria'}), 400
        
        if not data.get('tipo') or data.get('tipo') not in ['Positivo', 'Negativo']:
            return jsonify({'success': False, 'message': 'Tipo inválido'}), 400
        
        if not data.get('aspecto') or data.get('aspecto') not in [
            'POLITICO', 'ECONOMICO', 'SOCIAL', 'TECNOLOGICO', 'ECOLOGICO', 'LEGAL'
        ]:
            return jsonify({'success': False, 'message': 'Aspecto inválido'}), 400
        
        # Crear nuevo aspecto
        nuevo_aspecto = AspectoAmbiental(
            actividad=data['actividad'].strip(),
            tipo=data['tipo'],
            aspecto=data['aspecto'],
            fuente='foda_ext',  # Siempre foda_ext para esta funcionalidad
            created_by=session['user_id']
        )
        
        db.session.add(nuevo_aspecto)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '✅ Actividad FODA guardada correctamente',
            'data': {
                'id': nuevo_aspecto.id,
                'actividad': nuevo_aspecto.actividad,
                'tipo': nuevo_aspecto.tipo,
                'aspecto': nuevo_aspecto.aspecto,
                'fuente': nuevo_aspecto.fuente,
                'created_at': nuevo_aspecto.created_at.strftime('%d/%m/%Y %H:%M')
            }
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error al guardar actividad fodaext: {e}")
        return jsonify({'success': False, 'message': f'Error del servidor: {str(e)}'}), 500

@app.route('/guardar_matriz_foda', methods=['POST'])
@login_required
def guardar_matriz_foda():
    """Guardar actividades arrastradas desde CANVA a la matriz FODA"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Formato no soportado'}), 400
        
        data = request.get_json()
        actividades = data.get('actividades', [])
        
        if not actividades:
            return jsonify({'success': False, 'message': 'No hay actividades para guardar'}), 400
        
        actividades_guardadas = 0
        
        for actividad_data in actividades:
            # Validar campos requeridos
            if not actividad_data.get('actividad'):
                continue
            
            if not actividad_data.get('tipo') or actividad_data.get('tipo') not in ['Positivo', 'Negativo']:
                continue
            
            if not actividad_data.get('aspecto_nuevo') or actividad_data.get('aspecto_nuevo') not in [
                'POLITICO', 'ECONOMICO', 'SOCIAL', 'TECNOLOGICO', 'ECOLOGICO', 'LEGAL'
            ]:
                continue
            
            # Crear nuevo registro en la tabla de AspectoAmbiental
            nueva_actividad = AspectoAmbiental(
                actividad=actividad_data['actividad'],
                tipo=actividad_data['tipo'],
                aspecto=actividad_data['aspecto_nuevo'],
                fuente='foda_ext',
                created_by=session['user_id']
            )
            db.session.add(nueva_actividad)
            actividades_guardadas += 1
        
        if actividades_guardadas > 0:
            db.session.commit()
            return jsonify({
                'success': True, 
                'message': f'✅ {actividades_guardadas} actividades guardadas en la matriz FODA'
            })
        else:
            return jsonify({
                'success': False, 
                'message': 'No se pudo guardar ninguna actividad (datos inválidos)'
            }), 400
        
    except Exception as e:
        db.session.rollback()
        print(f"Error al guardar matriz FODA: {str(e)}")
        return jsonify({'success': False, 'message': f'Error del servidor: {str(e)}'}), 500

# ==================== RUTAS ESPECÍFICAS PARA FODA INTERNO ====================

@app.route('/fodaint')
@login_required
def fodaint():
    """Página para análisis FODA Interno"""
    try:
        # Obtener aspectos para FODA Interno (fuente = 'foda_int')
        aspectos_lista = AspectoAmbiental.query.filter_by(
            fuente='foda_int'
        ).order_by(
            AspectoAmbiental.aspecto,
            AspectoAmbiental.created_at.desc()
        ).all()
        
        # Obtener historial de CANVA para arrastrar
        historial_actividades = AspectoAmbiental.query.filter_by(
            fuente='canva'
        ).order_by(
            AspectoAmbiental.created_at.desc()
        ).limit(20).all()
        
        # Estadísticas
        estadisticas = {
            'total': len(aspectos_lista),
            'positivos': len([a for a in aspectos_lista if a.tipo == 'Positivo']),
            'negativos': len([a for a in aspectos_lista if a.tipo == 'Negativo']),
            'historial_total': len(historial_actividades)
        }
        
        return render_template('fodaint.html', 
                             aspectos_lista=aspectos_lista,
                             historial_actividades=historial_actividades,
                             estadisticas=estadisticas)
        
    except Exception as e:
        print(f"Error en fodaint: {e}")
        return render_template('fodaint.html', 
                             aspectos_lista=[], 
                             historial_actividades=[],
                             estadisticas={'total': 0, 'positivos': 0, 'negativos': 0, 'historial_total': 0})

@app.route('/guardar_foda_int', methods=['POST'])
@login_required
def guardar_foda_int():
    """Guardar un aspecto para FODA Interno"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Formato no soportado'}), 400
        
        data = request.get_json()
        
        # Validar campos requeridos
        if not data.get('actividad'):
            return jsonify({'success': False, 'message': 'La actividad es obligatoria'}), 400
        
        if not data.get('tipo') or data.get('tipo') not in ['Positivo', 'Negativo']:
            return jsonify({'success': False, 'message': 'Tipo inválido'}), 400
        
        # Validar aspectos internos
        aspectos_validos = [
            'ADMINISTRACIÓN Y GERENCIA',
            'MARKETING Y VENTAS', 
            'OPERACIONES Y LOGÍSTICA',
            'FINANZAS Y CONTABILIDAD',
            'RECURSOS HUMANOS',
            'SISTEMAS DE INFORMACIÓN',
            'TECNOLOGÍA'
        ]
        
        if not data.get('aspecto') or data.get('aspecto') not in aspectos_validos:
            return jsonify({'success': False, 'message': 'Aspecto inválido'}), 400
        
        # Crear nuevo aspecto
        nuevo_aspecto = AspectoAmbiental(
            actividad=data['actividad'].strip(),
            tipo=data['tipo'],
            aspecto=data['aspecto'],
            fuente='foda_int',  # Fuente específica para FODA Interno
            created_by=session['user_id']
        )
        
        db.session.add(nuevo_aspecto)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '✅ Actividad FODA Interno guardada correctamente',
            'data': {
                'id': nuevo_aspecto.id,
                'actividad': nuevo_aspecto.actividad,
                'tipo': nuevo_aspecto.tipo,
                'aspecto': nuevo_aspecto.aspecto,
                'fuente': nuevo_aspecto.fuente,
                'created_at': nuevo_aspecto.created_at.strftime('%d/%m/%Y %H:%M')
            }
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error al guardar actividad fodaint: {e}")
        return jsonify({'success': False, 'message': f'Error del servidor: {str(e)}'}), 500

@app.route('/guardar_matriz_foda_int', methods=['POST'])
@login_required
def guardar_matriz_foda_int():
    """Guardar actividades arrastradas desde CANVA a la matriz FODA Interno"""
    try:
        data = request.get_json()
        actividades = data.get('actividades', [])
        
        if not actividades:
            return jsonify({'success': False, 'message': 'No hay actividades para guardar'})
        
        for actividad_data in actividades:
            # Crear nuevo registro en la tabla de AspectoAmbiental
            nueva_actividad = AspectoAmbiental(
                actividad=actividad_data['actividad'],
                tipo=actividad_data['tipo'],
                aspecto=actividad_data['aspecto_nuevo'],  # El nuevo aspecto asignado
                fuente='foda_int',  # Fuente específica para FODA Interno
                created_by=session['user_id']
            )
            db.session.add(nueva_actividad)
        
        db.session.commit()
        return jsonify({
            'success': True, 
            'message': f'{len(actividades)} actividades guardadas en la matriz FODA Interno'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error al guardar matriz FODA Interno: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/eliminar_foda_ext/<int:id>', methods=['POST'])
@login_required
def eliminar_foda_ext(id):
    """Eliminar una actividad de FODA Externo"""
    try:
        # Verificar que el usuario es admin o el creador del registro
        aspecto = AspectoAmbiental.query.get_or_404(id)
        
        # Solo admin puede eliminar (o el creador en algunos casos)
        if session.get('rol') != 'admin' and aspecto.created_by != session.get('user_id'):
            return jsonify({'success': False, 'message': 'No autorizado'}), 403
        
        # Verificar que es un registro de FODA Externo
        if aspecto.fuente != 'foda_ext':
            return jsonify({'success': False, 'message': 'No es un registro de FODA Externo'}), 400
        
        db.session.delete(aspecto)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Actividad eliminada correctamente'})
        
    except Exception as e:
        db.session.rollback()
        print(f"Error al eliminar fodaext: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== RUTAS PARA ESTRATEGIAS FODA CRUZADO ====================

@app.route('/guardar_estrategia_foda', methods=['POST'])
@login_required
def guardar_estrategia_foda():
    """Guardar una estrategia FODA cruzado"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Formato no soportado'}), 400
        
        data = request.get_json()
        
        # Validar campos requeridos
        campos_requeridos = [
            'tipo_cruce', 'elemento_interno_id', 'elemento_interno_tipo',
            'elemento_interno_texto', 'elemento_externo_id', 'elemento_externo_tipo',
            'elemento_externo_texto', 'estrategia'
        ]
        
        for campo in campos_requeridos:
            if not data.get(campo):
                return jsonify({'success': False, 'message': f'Campo {campo} es obligatorio'}), 400
        
        # Validar tipo de cruce
        if data.get('tipo_cruce') not in ['FO', 'DO', 'FA', 'DA']:
            return jsonify({'success': False, 'message': 'Tipo de cruce inválido'}), 400
        
        # Crear nueva estrategia
        nueva_estrategia = EstrategiaFodaCruzado(
            tipo_cruce=data['tipo_cruce'],
            elemento_interno_id=data['elemento_interno_id'],
            elemento_interno_tipo=data['elemento_interno_tipo'],
            elemento_interno_texto=data['elemento_interno_texto'],
            elemento_externo_id=data['elemento_externo_id'],
            elemento_externo_tipo=data['elemento_externo_tipo'],
            elemento_externo_texto=data['elemento_externo_texto'],
            estrategia=data['estrategia'],
            creador_id=session['user_id']
        )
        
        db.session.add(nueva_estrategia)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '✅ Estrategia FODA cruzado guardada correctamente',
            'data': {
                'id': nueva_estrategia.id,
                'tipo_cruce': nueva_estrategia.tipo_cruce,
                'estrategia': nueva_estrategia.estrategia,
                'fecha_creacion': nueva_estrategia.fecha_creacion.strftime('%d/%m/%Y %H:%M')
            }
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error al guardar estrategia FODA cruzado: {e}")
        return jsonify({'success': False, 'message': f'Error del servidor: {str(e)}'}), 500

@app.route('/api/estrategias_foda')
@login_required
def api_estrategias_foda():
    """API para obtener estrategias FODA cruzado"""
    try:
        estrategias = EstrategiaFodaCruzado.query.order_by(
            EstrategiaFodaCruzado.fecha_creacion.desc()
        ).all()
        
        estrategias_data = []
        for e in estrategias:
            estrategias_data.append({
                'tipo_cruce': e.tipo_cruce,
                'elemento_interno_id': e.elemento_interno_id,
                'elemento_interno_tipo': e.elemento_interno_tipo,
                'elemento_interno_texto': e.elemento_interno_texto,
                'elemento_externo_id': e.elemento_externo_id,
                'elemento_externo_tipo': e.elemento_externo_tipo,
                'elemento_externo_texto': e.elemento_externo_texto,
                'estrategia': e.estrategia,
                'fecha': e.fecha_creacion.isoformat() if e.fecha_creacion else None,
                'creador': e.creador.username if e.creador else None
            })
        
        return jsonify({'success': True, 'estrategias': estrategias_data})
        
    except Exception as e:
        print(f"Error en api_estrategias_foda: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/eliminar_estrategia_foda/<int:id>', methods=['POST'])
@login_required
def eliminar_estrategia_foda(id):
    """Eliminar una estrategia FODA cruzado"""
    try:
        # Verificar que el usuario es admin o el creador del registro
        estrategia = EstrategiaFodaCruzado.query.get_or_404(id)
        
        if session.get('rol') != 'admin' and estrategia.creador_id != session.get('user_id'):
            return jsonify({'success': False, 'message': 'No autorizado'}), 403
        
        db.session.delete(estrategia)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Estrategia eliminada correctamente'})
        
    except Exception as e:
        db.session.rollback()
        print(f"Error al eliminar estrategia FODA: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== RUTAS ESPECÍFICAS PARA FODA CRUZADO ====================

@app.route('/cruzado')
@login_required
def cruzado():
    """Página para análisis FODA Cruzado"""
    try:
        # Obtener aspectos para FODA Externo e Interno
        aspectos_foda_ext = AspectoAmbiental.query.filter_by(fuente='foda_ext').all()
        aspectos_foda_int = AspectoAmbiental.query.filter_by(fuente='foda_int').all()
        
        # Obtener estrategias existentes
        estrategias = EstrategiaFodaCruzado.query.order_by(
            EstrategiaFodaCruzado.fecha_creacion.desc()
        ).all()
        
        return render_template('cruzado.html', 
                             aspectos_foda_ext=aspectos_foda_ext,
                             aspectos_foda_int=aspectos_foda_int,
                             estrategias=estrategias)
        
    except Exception as e:
        print(f"Error en cruzado: {e}")
        return render_template('cruzado.html',
                             aspectos_foda_ext=[],
                             aspectos_foda_int=[],
                             estrategias=[])

# ==================== RUTAS ESPECÍFICAS PARA CANVA ====================

@app.route('/canvas')
@login_required
def canvas():
    # Definir los bloques del CANVA
    bloques_canva = [
        {'nombre': 'Mapeo de Actores y Comunidades Afectadas', 'icono': 'fas fa-users'},
        {'nombre': 'Propuesta de Valor', 'icono': 'fas fa-gem'},
        {'nombre': 'Canales', 'icono': 'fas fa-broadcast-tower'},
        {'nombre': 'Relación con Actores', 'icono': 'fas fa-handshake'},
        {'nombre': 'Fuentes de Ingreso', 'icono': 'fas fa-money-bill-wave'},
        {'nombre': 'Recursos Clave', 'icono': 'fas fa-tools'},
        {'nombre': 'Actividades Clave', 'icono': 'fas fa-tasks'},
        {'nombre': 'Socios Clave', 'icono': 'fas fa-handshake'},
        {'nombre': 'Estructura de Costes', 'icono': 'fas fa-calculator'}
    ]
    
    # Obtener actividades con fuente='canva'
    aspectos_canva = AspectoAmbiental.query.filter_by(fuente='canva').order_by(
        AspectoAmbiental.created_at.desc()
    ).all()
    
    # Obtener estadísticas
    total_actividades = AspectoAmbiental.query.filter_by(fuente='canva').count()
    
    # Contar positivas y negativas basado en el campo "aspecto"
    positivas = AspectoAmbiental.query.filter(
        AspectoAmbiental.fuente == 'canva',
        AspectoAmbiental.aspecto.like('Positivo:%')
    ).count()
    
    negativas = AspectoAmbiental.query.filter(
        AspectoAmbiental.fuente == 'canva',
        AspectoAmbiental.aspecto.like('Negativo:%')
    ).count()
    
    return render_template('canvas.html',
                         bloques_canva=bloques_canva,
                         aspectos_canva=aspectos_canva,
                         total_actividades=total_actividades,
                         positivas=positivas,
                         negativas=negativas)

@app.route('/guardar_actividad_canva', methods=['POST'])
@login_required
def guardar_actividad_canva():
    """Guardar una actividad del CANVA"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Formato no soportado'}), 400
        
        data = request.get_json()
        
        # Validar campos requeridos
        if not data.get('actividad'):
            return jsonify({'success': False, 'message': 'La actividad es obligatoria'}), 400
        
        if not data.get('tipo'):
            return jsonify({'success': False, 'message': 'El tipo de bloque es obligatorio'}), 400
        
        if not data.get('aspecto'):
            return jsonify({'success': False, 'message': 'El aspecto (Positivo/Negativo) es obligatorio'}), 400
        
        # Crear nuevo aspecto ambiental específico para CANVA
        nuevo_aspecto = AspectoAmbiental(
            actividad=data['actividad'].strip(),
            tipo=data['tipo'],  # Este será el bloque CANVA (ej: "Mapeo de Actores...")
            aspecto=data['aspecto'],  # Este será "Positivo: ..." o "Negativo: ..."
            fuente='canva',  # Marcamos que viene del CANVA
            created_by=session['user_id']
        )
        
        db.session.add(nuevo_aspecto)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '✅ Actividad CANVA guardada correctamente',
            'data': {
                'id': nuevo_aspecto.id,
                'actividad': nuevo_aspecto.actividad,
                'tipo': nuevo_aspecto.tipo,
                'aspecto': nuevo_aspecto.aspecto,
                'fuente': nuevo_aspecto.fuente,
                'created_at': nuevo_aspecto.created_at.strftime('%d/%m/%Y %H:%M')
            }
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error al guardar actividad canva: {e}")
        return jsonify({'success': False, 'message': f'Error del servidor: {str(e)}'}), 500

@app.route('/limpiar_canva', methods=['POST'])
@login_required
def limpiar_canva():
    """Limpiar todas las actividades del CANVA (solo administradores)"""
    # Solo administradores pueden limpiar el CANVA
    if session.get('rol') != 'admin':
        return jsonify({'success': False, 'message': 'No autorizado. Solo administradores pueden limpiar el CANVA.'}), 403
    
    try:
        # Eliminar todas las actividades con fuente='canva'
        num_eliminadas = AspectoAmbiental.query.filter_by(fuente='canva').count()
        AspectoAmbiental.query.filter_by(fuente='canva').delete()
        db.session.commit()
        return jsonify({
            'success': True, 
            'message': f'✅ CANVA limpiado correctamente ({num_eliminadas} actividades eliminadas)'
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error al limpiar canva: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== RUTAS ADICIONALES ====================

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==================== RUTAS DE ADMINISTRACIÓN Y SISTEMA ====================

@app.route('/init-db')
def init_db():
    """Inicializar base de datos"""
    try:
        if initialize_database():
            usuarios = User.query.all()
            aspectos = AspectoAmbiental.query.all()
            estrategias = EstrategiaFodaCruzado.query.all()
            
            html_response = '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Base de Datos Inicializada</title>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    * {
                        box-sizing: border-box;
                        margin: 0;
                        padding: 0;
                    }
                    
                    body {
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background: linear-gradient(135deg, #1B4079 0%, #4D7C8A 100%);
                        min-height: 100vh;
                        padding: 20px;
                        color: white;
                        line-height: 1.6;
                    }
                    
                    .container {
                        max-width: 800px;
                        margin: 0 auto;
                        background: rgba(255, 255, 255, 0.1);
                        backdrop-filter: blur(10px);
                        border-radius: 15px;
                        padding: 20px;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                    }
                    
                    h1 { 
                        color: #CBDF90; 
                        text-align: center;
                        margin-bottom: 20px;
                        font-size: 1.8rem;
                    }
                    
                    .success { 
                        background: rgba(76, 175, 80, 0.2);
                        border: 2px solid #4CAF50;
                        border-radius: 10px;
                        padding: 15px;
                        margin: 20px 0;
                    }
                    
                    .stats-grid {
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                        gap: 15px;
                        margin: 20px 0;
                    }
                    
                    .stat-card {
                        background: rgba(255, 255, 255, 0.1);
                        padding: 15px;
                        border-radius: 8px;
                        text-align: center;
                        transition: transform 0.3s;
                    }
                    
                    .stat-card:hover {
                        transform: translateY(-5px);
                        background: rgba(255, 255, 255, 0.15);
                    }
                    
                    .stat-number {
                        font-size: 2rem;
                        font-weight: bold;
                        display: block;
                        margin-bottom: 5px;
                        color: #CBDF90;
                    }
                    
                    .stat-label {
                        font-size: 0.9rem;
                        opacity: 0.9;
                    }
                    
                    .btn {
                        display: block;
                        width: 100%;
                        background: #4CAF50;
                        color: white;
                        text-decoration: none;
                        padding: 15px;
                        border-radius: 8px;
                        margin: 25px 0;
                        text-align: center;
                        font-weight: bold;
                        font-size: 1.1rem;
                        transition: background 0.3s, transform 0.3s;
                        border: none;
                        cursor: pointer;
                    }
                    
                    .btn:hover { 
                        background: #45a049;
                        transform: translateY(-2px);
                    }
                    
                    .info-box {
                        background: rgba(255, 193, 7, 0.2);
                        border: 2px solid #FFC107;
                        border-radius: 10px;
                        padding: 15px;
                        margin-top: 20px;
                    }
                    
                    @media (max-width: 768px) {
                        .container {
                            padding: 15px;
                            margin: 10px;
                        }
                        
                        h1 {
                            font-size: 1.5rem;
                        }
                        
                        .stats-grid {
                            grid-template-columns: 1fr;
                        }
                        
                        .stat-number {
                            font-size: 1.8rem;
                        }
                    }
                    
                    @media (max-width: 480px) {
                        body {
                            padding: 10px;
                        }
                        
                        .container {
                            padding: 12px;
                        }
                        
                        h1 {
                            font-size: 1.3rem;
                        }
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>✅ Base de Datos Inicializada</h1>
                    
                    <div class="success">
                        <h2 style="margin-bottom: 10px;">Sistema CURIMINING Listo</h2>
                        <p>La base de datos ha sido inicializada exitosamente.</p>
                        <p>Tablas creadas: usuarios, aspectos_ambientales, estrategias_foda_cruzado</p>
                    </div>
                    
                    <div class="stats-grid">
                        <div class="stat-card">
                            <span class="stat-number">''' + str(len(usuarios)) + '''</span>
                            <span class="stat-label">👥 Usuarios</span>
                        </div>
                        <div class="stat-card">
                            <span class="stat-number">''' + str(len(aspectos)) + '''</span>
                            <span class="stat-label">📊 Aspectos</span>
                        </div>
                        <div class="stat-card">
                            <span class="stat-number">''' + str(len(estrategias)) + '''</span>
                            <span class="stat-label">♟️ Estrategias FODA</span>
                        </div>
                    </div>
                    
                    <div class="info-box">
                        <p><strong>⚠️ NOTA:</strong> Se han creado usuarios de prueba. Los datos se alimentarán desde la aplicación.</p>
                        <p style="margin-top: 10px;"><strong>🔑 Credenciales de administrador:</strong></p>
                        <p>Usuario: <strong>MINERA.ADMIN</strong></p>
                        <p>Contraseña: <strong>MINERA.ADMIN</strong></p>
                    </div>
                    
                    <a href="/login" class="btn">🚀 Ir al Login</a>
                    
                    <div style="text-align: center; margin-top: 20px; font-size: 0.9rem; opacity: 0.8;">
                        <p>Sistema CURIMINING v2.0 - Desarrollado por O&R Business Consulting Group</p>
                    </div>
                </div>
            </body>
            </html>
            '''
            
            return html_response
        else:
            return '''
            <h1 style="color: red; text-align: center; margin-top: 50px;">❌ Error inicializando base de datos</h1>
            <p style="text-align: center;">Verifica la conexión a la base de datos PostgreSQL.</p>
            <p style="text-align: center;"><a href="/">Volver</a></p>
            '''
    except Exception as e:
        return f'''
        <h1 style="color: red; text-align: center; margin-top: 50px;">❌ Error crítico</h1>
        <p style="text-align: center;"><strong>Error:</strong> {str(e)}</p>
        <p style="text-align: center;"><a href="/">Volver</a></p>
        '''

@app.route('/check')
def check():
    """Verificar estado del sistema"""
    try:
        # Verificar conexión a base de datos
        db.session.execute("SELECT 1")
        db_status = 'conectada'
        
        # Contar registros
        user_count = User.query.count()
        aspecto_count = AspectoAmbiental.query.count()
        aspecto_foda_ext = AspectoAmbiental.query.filter_by(fuente='foda_ext').count()
        aspecto_canva = AspectoAmbiental.query.filter_by(fuente='canva').count()
        aspecto_foda_int = AspectoAmbiental.query.filter_by(fuente='foda_int').count()
        estrategias_count = EstrategiaFodaCruzado.query.count()
        
    except Exception as e:
        db_status = f'error: {str(e)[:100]}'
        user_count = 0
        aspecto_count = 0
        aspecto_foda_ext = 0
        aspecto_canva = 0
        aspecto_foda_int = 0
        estrategias_count = 0
    
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat(),
        'database': db_status,
        'users': user_count,
        'aspectos_total': aspecto_count,
        'aspectos_foda_ext': aspecto_foda_ext,
        'aspectos_canva': aspecto_canva,
        'aspectos_foda_int': aspecto_foda_int,
        'estrategias_foda': estrategias_count,
        'port': os.environ.get('PORT', '3000'),
        'python_version': sys.version.split()[0]
    })

# ==================== RUTAS API PARA ADMIN DASHBOARD ====================

@app.route('/api/admin/estadisticas')
@admin_required
def api_admin_estadisticas():
    """API para obtener estadísticas del dashboard administrativo"""
    try:
        # Obtener estadísticas generales
        total_actividades = AspectoAmbiental.query.count()
        usuarios_count = User.query.count()
        
        # Estadísticas por fuente
        total_actividades_canva = AspectoAmbiental.query.filter_by(fuente='canva').count()
        total_actividades_foda_ext = AspectoAmbiental.query.filter_by(fuente='foda_ext').count()
        total_actividades_foda_int = AspectoAmbiental.query.filter_by(fuente='foda_int').count()
        
        # Contar actividades positivas y negativas
        actividades_positivas = AspectoAmbiental.query.filter_by(tipo='Positivo').count()
        actividades_negativas = AspectoAmbiental.query.filter_by(tipo='Negativo').count()
        
        # Actividades de los últimos 7 días
        fecha_limite = datetime.utcnow() - timedelta(days=7)
        actividades_recientes_7dias = AspectoAmbiental.query.filter(
            AspectoAmbiental.created_at >= fecha_limite
        ).count()
        
        # Contar estrategias FODA cruzado
        estrategias_count = EstrategiaFodaCruzado.query.count()
        
        return jsonify({
            'success': True,
            'estadisticas': {
                'total_actividades': total_actividades,
                'actividades_canva': total_actividades_canva,
                'actividades_foda_ext': total_actividades_foda_ext,
                'actividades_foda_int': total_actividades_foda_int,
                'estrategias_foda_cruzado': estrategias_count,
                'positivas_canva': AspectoAmbiental.query.filter_by(fuente='canva', tipo='Positivo').count(),
                'negativas_canva': AspectoAmbiental.query.filter_by(fuente='canva', tipo='Negativo').count(),
                'positivas_foda_ext': AspectoAmbiental.query.filter_by(fuente='foda_ext', tipo='Positivo').count(),
                'negativas_foda_ext': AspectoAmbiental.query.filter_by(fuente='foda_ext', tipo='Negativo').count(),
                'actividades_recientes_7dias': actividades_recientes_7dias,
                'usuarios_total': usuarios_count,
                'actividades_positivas': actividades_positivas,
                'actividades_negativas': actividades_negativas
            }
        })
        
    except Exception as e:
        print(f"Error en api_admin_estadisticas: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/filtrar_actividades', methods=['POST'])
@admin_required
def api_admin_filtrar_actividades():
    """API para filtrar actividades del dashboard administrativo"""
    try:
        data = request.get_json()
        
        # Obtener parámetros de filtro
        tipo_filtro = data.get('tipo_filtro', 'all')
        bloque_filtro = data.get('bloque_filtro', 'all')
        fuente_filtro = data.get('fuente_filtro', 'all')
        fecha_desde = data.get('fecha_desde')
        fecha_hasta = data.get('fecha_hasta')
        busqueda = data.get('busqueda', '').strip()
        orden_por = data.get('orden_por', 'fecha_desc')
        pagina = data.get('pagina', 1)
        por_pagina = data.get('por_pagina', 25)
        
        # Construir consulta base
        query = AspectoAmbiental.query
        
        # Aplicar filtros
        if tipo_filtro != 'all':
            query = query.filter(AspectoAmbiental.tipo == tipo_filtro)
        
        if bloque_filtro != 'all':
            query = query.filter(AspectoAmbiental.aspecto == bloque_filtro)
        
        if fuente_filtro != 'all':
            query = query.filter(AspectoAmbiental.fuente == fuente_filtro)
        
        if fecha_desde:
            try:
                fecha_desde_dt = datetime.strptime(fecha_desde, '%Y-%m-%d')
                query = query.filter(AspectoAmbiental.created_at >= fecha_desde_dt)
            except ValueError:
                pass
        
        if fecha_hasta:
            try:
                fecha_hasta_dt = datetime.strptime(fecha_hasta, '%Y-%m-%d')
                # Ajustar para incluir todo el día
                fecha_hasta_dt = fecha_hasta_dt.replace(hour=23, minute=59, second=59)
                query = query.filter(AspectoAmbiental.created_at <= fecha_hasta_dt)
            except ValueError:
                pass
        
        if busqueda:
            query = query.filter(
                or_(
                    AspectoAmbiental.actividad.ilike(f'%{busqueda}%'),
                    AspectoAmbiental.aspecto.ilike(f'%{busqueda}%')
                )
            )
        
        # Aplicar ordenamiento
        if orden_por == 'fecha_desc':
            query = query.order_by(AspectoAmbiental.created_at.desc())
        elif orden_por == 'fecha_asc':
            query = query.order_by(AspectoAmbiental.created_at.asc())
        elif orden_por == 'actividad_asc':
            query = query.order_by(AspectoAmbiental.actividad.asc())
        elif orden_por == 'actividad_desc':
            query = query.order_by(AspectoAmbiental.actividad.desc())
        elif orden_por == 'tipo_asc':
            query = query.order_by(AspectoAmbiental.tipo.asc())
        
        # Paginación
        total = query.count()
        total_paginas = (total + por_pagina - 1) // por_pagina
        offset = (pagina - 1) * por_pagina
        actividades = query.offset(offset).limit(por_pagina).all()
        
        # Formatear datos para la respuesta
        actividades_formateadas = []
        for a in actividades:
            # Determinar la descripción basada en la fuente
            if a.fuente == 'canva':
                descripcion = f"Bloque CANVA: {a.tipo}"
            elif a.fuente == 'foda_ext':
                descripcion = f"FODA Externo - {a.aspecto}"
            elif a.fuente == 'foda_int':
                descripcion = f"FODA Interno - {a.aspecto}"
            else:
                descripcion = a.aspecto
            
            actividades_formateadas.append({
                'id': a.id,
                'actividad': a.actividad,
                'tipo': a.tipo,
                'bloque': a.aspecto,
                'aspecto': descripcion,
                'fuente': a.fuente,
                'fecha': a.created_at.strftime('%Y-%m-%d %H:%M:%S') if a.created_at else '',
                'creador': a.creador.username if a.creador else 'Desconocido'
            })
        
        return jsonify({
            'success': True,
            'actividades': actividades_formateadas,
            'total': total,
            'total_paginas': total_paginas,
            'pagina_actual': pagina
        })
        
    except Exception as e:
        print(f"Error en api_admin_filtrar_actividades: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/exportar_datos', methods=['POST'])
@admin_required
def api_admin_exportar_datos():
    """API para exportar datos a CSV"""
    try:
        data = request.get_json()
        
        # Obtener parámetros de filtro (mismos que en filtrar_actividades)
        tipo_filtro = data.get('tipo_filtro', 'all')
        bloque_filtro = data.get('bloque_filtro', 'all')
        fuente_filtro = data.get('fuente_filtro', 'all')
        fecha_desde = data.get('fecha_desde')
        fecha_hasta = data.get('fecha_hasta')
        busqueda = data.get('busqueda', '').strip()
        orden_por = data.get('orden_por', 'fecha_desc')
        
        # Construir consulta (misma lógica que en filtrar_actividades)
        query = AspectoAmbiental.query
        
        if tipo_filtro != 'all':
            query = query.filter(AspectoAmbiental.tipo == tipo_filtro)
        
        if bloque_filtro != 'all':
            query = query.filter(AspectoAmbiental.aspecto == bloque_filtro)
        
        if fuente_filtro != 'all':
            query = query.filter(AspectoAmbiental.fuente == fuente_filtro)
        
        if fecha_desde:
            try:
                fecha_desde_dt = datetime.strptime(fecha_desde, '%Y-%m-%d')
                query = query.filter(AspectoAmbiental.created_at >= fecha_desde_dt)
            except ValueError:
                pass
        
        if fecha_hasta:
            try:
                fecha_hasta_dt = datetime.strptime(fecha_hasta, '%Y-%m-%d')
                fecha_hasta_dt = fecha_hasta_dt.replace(hour=23, minute=59, second=59)
                query = query.filter(AspectoAmbiental.created_at <= fecha_hasta_dt)
            except ValueError:
                pass
        
        if busqueda:
            query = query.filter(
                or_(
                    AspectoAmbiental.actividad.ilike(f'%{busqueda}%'),
                    AspectoAmbiental.aspecto.ilike(f'%{busqueda}%')
                )
            )
        
        # Aplicar ordenamiento
        if orden_por == 'fecha_desc':
            query = query.order_by(AspectoAmbiental.created_at.desc())
        elif orden_por == 'fecha_asc':
            query = query.order_by(AspectoAmbiental.created_at.asc())
        elif orden_por == 'actividad_asc':
            query = query.order_by(AspectoAmbiental.actividad.asc())
        elif orden_por == 'actividad_desc':
            query = query.order_by(AspectoAmbiental.actividad.desc())
        elif orden_por == 'tipo_asc':
            query = query.order_by(AspectoAmbiental.tipo.asc())
        
        actividades = query.all()
        
        # Crear CSV en memoria
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Escribir encabezados
        writer.writerow(['ID', 'Actividad', 'Tipo', 'Aspecto/Bloque', 'Fuente', 'Fecha Creación', 'Creador'])
        
        # Escribir datos
        for a in actividades:
            writer.writerow([
                a.id,
                a.actividad,
                a.tipo,
                a.aspecto,
                a.fuente,
                a.created_at.strftime('%Y-%m-%d %H:%M:%S') if a.created_at else '',
                a.creador.username if a.creador else 'Desconocido'
            ])
        
        # Preparar respuesta
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename=actividades_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        response.headers['Content-type'] = 'text/csv'
        
        return response
        
    except Exception as e:
        print(f"Error en api_admin_exportar_datos: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== NUEVA RUTA PARA DASHBOARD ADMIN ====================

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Dashboard administrativo mejorado con filtros y estadísticas"""
    # Obtener estadísticas iniciales
    total_actividades = AspectoAmbiental.query.count()
    usuarios_count = User.query.count()
    
    # Estadísticas por fuente
    total_actividades_canva = AspectoAmbiental.query.filter_by(fuente='canva').count()
    total_actividades_foda_ext = AspectoAmbiental.query.filter_by(fuente='foda_ext').count()
    total_actividades_foda_int = AspectoAmbiental.query.filter_by(fuente='foda_int').count()
    
    # Contar actividades positivas y negativas
    actividades_positivas = AspectoAmbiental.query.filter_by(tipo='Positivo').count()
    actividades_negativas = AspectoAmbiental.query.filter_by(tipo='Negativo').count()
    
    # Contar estrategias FODA cruzado
    estrategias_count = EstrategiaFodaCruzado.query.count()
    
    # Definir bloques CANVA para los filtros
    bloques_canva = [
        {'nombre': 'Mapeo de Actores y Comunidades Afectadas', 'icono': 'fas fa-users'},
        {'nombre': 'Propuesta de Valor', 'icono': 'fas fa-gem'},
        {'nombre': 'Canales', 'icono': 'fas fa-broadcast-tower'},
        {'nombre': 'Relación con Actores', 'icono': 'fas fa-handshake'},
        {'nombre': 'Fuentes de Ingreso', 'icono': 'fas fa-money-bill-wave'},
        {'nombre': 'Recursos Clave', 'icono': 'fas fa-tools'},
        {'nombre': 'Actividades Clave', 'icono': 'fas fa-tasks'},
        {'nombre': 'Socios Clave', 'icono': 'fas fa-handshake'},
        {'nombre': 'Estructura de Costes', 'icono': 'fas fa-calculator'}
    ]
    
    return render_template('admin_dashboard.html',
                         total_actividades=total_actividades,
                         usuarios_count=usuarios_count,
                         total_actividades_canva=total_actividades_canva,
                         total_actividades_foda_ext=total_actividades_foda_ext,
                         total_actividades_foda_int=total_actividades_foda_int,
                         estrategias_count=estrategias_count,
                         actividades_positivas=actividades_positivas,
                         actividades_negativas=actividades_negativas,
                         bloques_canva=bloques_canva)

# ==================== ACTUALIZAR RUTA ADMIN PRINCIPAL ====================

@app.route('/admin')
@admin_required
def admin():
    """Página principal de administración - Redirige al dashboard"""
    # Redirigir al nuevo dashboard
    return redirect(url_for('admin_dashboard'))

# ==================== MANEJO DE ERRORES ====================

@app.errorhandler(404)
def page_not_found(e):
    """Manejar error 404 - Página no encontrada"""
    # Si la solicitud es para favicon.ico, devolver un 204 (No Content)
    if request.path == '/favicon.ico':
        return '', 204
    
    # Para otras rutas, devolver un mensaje simple
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>404 - Página no encontrada</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 50px;
                background: linear-gradient(135deg, #1B4079 0%, #4D7C8A 100%);
                color: white;
                height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            .container {
                background: rgba(255, 255, 255, 0.1);
                padding: 40px;
                border-radius: 10px;
                backdrop-filter: blur(10px);
            }
            h1 {
                color: #CBDF90;
                font-size: 3rem;
                margin-bottom: 20px;
            }
            p {
                font-size: 1.2rem;
                margin-bottom: 30px;
            }
            a {
                color: #CBDF90;
                text-decoration: none;
                font-weight: bold;
                border: 2px solid #CBDF90;
                padding: 10px 20px;
                border-radius: 5px;
                transition: all 0.3s;
            }
            a:hover {
                background: #CBDF90;
                color: #1B4079;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>404</h1>
            <p>La página que buscas no existe.</p>
            <a href="/">Volver al inicio</a>
        </div>
    </body>
    </html>
    ''', 404

@app.errorhandler(500)
def internal_server_error(e):
    """Manejar error 500 - Error interno del servidor"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>500 - Error interno del servidor</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 50px;
                background: linear-gradient(135deg, #1B4079 0%, #4D7C8A 100%);
                color: white;
                height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            .container {
                background: rgba(255, 255, 255, 0.1);
                padding: 40px;
                border-radius: 10px;
                backdrop-filter: blur(10px);
            }
            h1 {
                color: #ff6b6b;
                font-size: 3rem;
                margin-bottom: 20px;
            }
            p {
                font-size: 1.2rem;
                margin-bottom: 30px;
            }
            a {
                color: #CBDF90;
                text-decoration: none;
                font-weight: bold;
                border: 2px solid #CBDF90;
                padding: 10px 20px;
                border-radius: 5px;
                transition: all 0.3s;
            }
            a:hover {
                background: #CBDF90;
                color: #1B4079;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>500</h1>
            <p>Ha ocurrido un error interno en el servidor.</p>
            <a href="/">Volver al inicio</a>
        </div>
    </body>
    </html>
    ''', 500

# Ruta específica para favicon.ico (evita errores en logs)
@app.route('/favicon.ico')
def favicon():
    """Ruta para favicon.ico - Devuelve un 204 No Content para evitar errores"""
    return '', 204

# ==================== INICIALIZACIÓN ====================

print("=" * 60)
print("🚀 INICIANDO SISTEMA DE GESTIÓN AMBIENTAL MINERA - CURIMINING")
print("=" * 60)
print("📊 Versión: 2.2 (FODA Cruzado Completo)")
print("📅 Fecha: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
print("=" * 60)
print("📱 Características:")
print("  ✅ FODA Cruzado completo con base de datos")
print("  ✅ 4 tipos de cruces: FO, DO, FA, DA")
print("  ✅ Persistencia de estrategias")
print("  ✅ Tabla automática de estrategias_foda_cruzado")
print("  ✅ Responsive total (mobile, tablet, desktop)")
print("  ✅ 9 usuarios pre-creados")
print("=" * 60)

# Inicializar base de datos
with app.app_context():
    try:
        print("🔄 Inicializando base de datos...")
        if initialize_database():
            print("✅ Base de datos inicializada correctamente")
            print("✅ Tablas creadas: usuarios, aspectos_ambientales, estrategias_foda_cruzado")
        else:
            print("⚠️  Advertencia: Problemas con la inicialización de BD")
        print("✅ Sistema listo para recibir conexiones")
    except Exception as e:
        print(f"❌ Error crítico: {e}")

print("=" * 60)

# ==================== EJECUCIÓN ====================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    print(f"🌐 Servidor ejecutándose en: http://0.0.0.0:{port}")
    print(f"📱 Modo: FODA Cruzado Completo")
    print("=" * 60)
    
    # Configurar para producción
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    app.run(
        host='0.0.0.0', 
        port=port, 
        debug=debug_mode,
        threaded=True  # Mejor rendimiento para múltiples conexiones
    )
