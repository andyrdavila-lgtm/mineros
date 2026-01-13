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

# Tabla: Estrategias FODA Cruzado (actualizada con campos de eje)
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
    eje_id = db.Column(db.String(50), nullable=True)  # Nuevo campo: ID del eje estratégico
    eje_texto = db.Column(db.String(200), nullable=True)  # Nuevo campo: texto del eje
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    creador_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    
    # Relación
    creador = db.relationship('User', backref=db.backref('estrategias_foda', lazy=True))

# ==================== MODELOS PARA ACTIVIDADES Y TAREAS ====================

# Modelo para Actividades de Estrategias
class ActividadEstrategia(db.Model):
    __tablename__ = 'actividades_estrategia'
    
    id = db.Column(db.Integer, primary_key=True)
    estrategia_id = db.Column(db.Integer, db.ForeignKey('estrategias_foda_cruzado.id'), nullable=False)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    responsable = db.Column(db.String(100), nullable=True)
    fecha_inicio = db.Column(db.Date, nullable=True)
    fecha_fin = db.Column(db.Date, nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    creador_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    
    # Relaciones
    estrategia = db.relationship('EstrategiaFodaCruzado', backref=db.backref('actividades_estrategia', lazy=True, cascade='all, delete-orphan'))
    creador = db.relationship('User', backref=db.backref('actividades_estrategia_creadas', lazy=True))

# Modelo para Tareas de Actividades
class TareaActividad(db.Model):
    __tablename__ = 'tareas_actividad'
    
    id = db.Column(db.Integer, primary_key=True)
    actividad_id = db.Column(db.Integer, db.ForeignKey('actividades_estrategia.id'), nullable=False)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    responsable = db.Column(db.String(100), nullable=True)
    fecha_inicio = db.Column(db.Date, nullable=True)
    fecha_fin = db.Column(db.Date, nullable=True)
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, en_progreso, completada
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    creador_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    
    # Relaciones
    actividad = db.relationship('ActividadEstrategia', backref=db.backref('tareas_actividad', lazy=True, cascade='all, delete-orphan'))
    creador = db.relationship('User', backref=db.backref('tareas_actividad_creadas', lazy=True))

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

# ==================== FUNCIÓN DE INICIALIZACIÓN DE BD MEJORADA ====================

def initialize_database():
    """Intenta inicializar la base de datos con reintentos y migraciones"""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            print(f"🔄 Intento {attempt + 1} de {max_retries} para inicializar BD...")
            
            # Crear todas las tablas si no existen
            db.create_all()
            print("✅ Tablas creadas/verificadas exitosamente")
            
            # ==================== MIGRACIÓN PARA COLUMNAS FALTANTES ====================
            try:
                # Verificar si las columnas eje_id y eje_texto existen en estrategias_foda_cruzado
                connection = db.engine.connect()
                
                # Para PostgreSQL
                check_query = """
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'estrategias_foda_cruzado' 
                    AND column_name IN ('eje_id', 'eje_texto')
                """
                
                result = connection.execute(check_query).fetchall()
                existing_columns = [row[0] for row in result]
                
                # Agregar columnas faltantes
                if 'eje_id' not in existing_columns:
                    print("🔄 Agregando columna 'eje_id' a estrategias_foda_cruzado...")
                    connection.execute("ALTER TABLE estrategias_foda_cruzado ADD COLUMN eje_id VARCHAR(50)")
                    print("✅ Columna 'eje_id' agregada")
                
                if 'eje_texto' not in existing_columns:
                    print("🔄 Agregando columna 'eje_texto' a estrategias_foda_cruzado...")
                    connection.execute("ALTER TABLE estrategias_foda_cruzado ADD COLUMN eje_texto VARCHAR(200)")
                    print("✅ Columna 'eje_texto' agregada")
                
                connection.close()
                print("✅ Migración de columnas completada")
                
            except Exception as migration_error:
                print(f"⚠️  Nota: No se pudo verificar/agregar columnas: {migration_error}")
                print("ℹ️  Continuando sin migración de columnas...")
            # ==================== FIN DE MIGRACIÓN ====================
            
            # Verificar que las nuevas tablas de actividades y tareas existen
            try:
                # Intentar contar actividades y tareas
                actividades_count = ActividadEstrategia.query.count()
                tareas_count = TareaActividad.query.count()
                print(f"📊 Total de actividades de estrategias: {actividades_count}")
                print(f"📊 Total de tareas: {tareas_count}")
            except Exception as count_error:
                print(f"⚠️  Nota: No se pudieron contar actividades/tareas: {count_error}")
                print("ℹ️  Las tablas se crearán automáticamente cuando se agregue la primera actividad.")
            
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
            
            try:
                # Intentar contar estrategias FODA
                estrategias_count = EstrategiaFodaCruzado.query.count()
                print(f"📊 Total de estrategias FODA cruzado: {estrategias_count}")
            except Exception as count_error:
                print(f"⚠️  No se pudo contar estrategias: {count_error}")
                print("ℹ️  La tabla existe pero puede faltar alguna columna")
            
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

# ==================== NUEVAS RUTAS PARA LAS PESTAÑAS ADICIONALES ====================

@app.route('/estrategias')
@login_required
def estrategias():
    """Página de Estrategias"""
    try:
        # Obtener todas las estrategias con ejes
        estrategias = EstrategiaFodaCruzado.query.order_by(
            EstrategiaFodaCruzado.fecha_creacion.desc()
        ).all()
        
        # Obtener estadísticas por eje
        ejes = {
            'educacion': {'nombre': 'EDUCACIÓN', 'icono': 'fas fa-graduation-cap', 'count': 0},
            'salud': {'nombre': 'SALUD', 'icono': 'fas fa-heartbeat', 'count': 0},
            'empleabilidad': {'nombre': 'EMPLEABILIDAD', 'icono': 'fas fa-briefcase', 'count': 0},
            'desarrollo_economico': {'nombre': 'DESARROLLO ECONÓMICO', 'icono': 'fas fa-chart-line', 'count': 0},
            'sostenibilidad_ambiental': {'nombre': 'SOSTENIBILIDAD AMBIENTAL (AGUA)', 'icono': 'fas fa-tint', 'count': 0},
            'comunicacion': {'nombre': 'COMUNICACIÓN', 'icono': 'fas fa-bullhorn', 'count': 0},
            'institucional': {'nombre': 'INSTITUCIONAL', 'icono': 'fas fa-landmark', 'count': 0}
        }
        
        # Contar estrategias por eje
        for estrategia in estrategias:
            if estrategia.eje_id and estrategia.eje_id in ejes:
                ejes[estrategia.eje_id]['count'] += 1
        
        # Convertir a lista para template
        ejes_lista = [ejes[key] for key in ejes]
        
        return render_template('estrategias.html', 
                             estrategias=estrategias,
                             ejes=ejes_lista,
                             total_estrategias=len(estrategias))
    except Exception as e:
        print(f"Error en estrategias: {e}")
        # Si hay error, devolver página vacía
        return render_template('estrategias.html', 
                             estrategias=[],
                             ejes=[],
                             total_estrategias=0)

@app.route('/red')
@login_required
def red():
    """Página de Mapa de Red"""
    try:
        # Obtener datos para el mapa de red
        estrategias = EstrategiaFodaCruzado.query.all()
        
        # Preparar datos para visualización de red
        nodos = []
        enlaces = []
        
        # Agregar nodos por eje
        ejes_unicos = set()
        for estrategia in estrategias:
            if estrategia.eje_id:
                ejes_unicos.add((estrategia.eje_id, estrategia.eje_texto))
        
        # Crear nodos de ejes
        eje_ids = {}
        for i, (eje_id, eje_texto) in enumerate(ejes_unicos):
            eje_ids[eje_id] = i
            nodos.append({
                'id': i,
                'name': eje_texto,
                'group': 'eje',
                'size': 20,
                'color': get_eje_color(eje_id)
            })
        
        # Agregar nodos de estrategias y enlaces
        for i, estrategia in enumerate(estrategias):
            nodo_id = i + len(ejes_unicos)
            nodos.append({
                'id': nodo_id,
                'name': f"{estrategia.tipo_cruce} - {estrategia.estrategia[:30]}...",
                'group': 'estrategia',
                'size': 10,
                'color': get_tipo_cruce_color(estrategia.tipo_cruce)
            })
            
            # Crear enlace con eje si existe
            if estrategia.eje_id and estrategia.eje_id in eje_ids:
                enlaces.append({
                    'source': eje_ids[estrategia.eje_id],
                    'target': nodo_id,
                    'value': 2
                })
        
        return render_template('red.html',
                             total_nodos=len(nodos),
                             total_enlaces=len(enlaces),
                             total_estrategias=len(estrategias),
                             nodos_json=jsonify(nodos).get_data(as_text=True),
                             enlaces_json=jsonify(enlaces).get_data(as_text=True))
    except Exception as e:
        print(f"Error en red: {e}")
        # Si hay error, devolver página vacía
        return render_template('red.html',
                             total_nodos=0,
                             total_enlaces=0,
                             total_estrategias=0,
                             nodos_json='[]',
                             enlaces_json='[]')

# Funciones auxiliares para colores
def get_eje_color(eje_id):
    colores = {
        'educacion': '#4CAF50',
        'salud': '#FF6B6B',
        'empleabilidad': '#2196F3',
        'desarrollo_economico': '#FF9800',
        'sostenibilidad_ambiental': '#00BCD4',
        'comunicacion': '#9C27B0',
        'institucional': '#795548'
    }
    return colores.get(eje_id, '#607D8B')

def get_tipo_cruce_color(tipo_cruce):
    colores = {
        'FO': '#4CAF50',
        'DO': '#2196F3',
        'FA': '#FF9800',
        'DA': '#9C27B0'
    }
    return colores.get(tipo_cruce, '#607D8B')

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

# ==================== RUTAS PARA ESTRATEGIAS FODA CRUZADO CON EJES ====================

@app.route('/guardar_estrategia_foda', methods=['POST'])
@login_required
def guardar_estrategia_foda():
    """Guardar una estrategia FODA cruzado (versión original, sin eje obligatorio)"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Formato no soportado'}), 400
        
        data = request.get_json()
        
        # Validar campos requeridos (los originales, sin eje)
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
        
        # Crear nueva estrategia (los ejes pueden ser None)
        nueva_estrategia = EstrategiaFodaCruzado(
            tipo_cruce=data['tipo_cruce'],
            elemento_interno_id=data['elemento_interno_id'],
            elemento_interno_tipo=data['elemento_interno_tipo'],
            elemento_interno_texto=data['elemento_interno_texto'],
            elemento_externo_id=data['elemento_externo_id'],
            elemento_externo_tipo=data['elemento_externo_tipo'],
            elemento_externo_texto=data['elemento_externo_texto'],
            estrategia=data['estrategia'],
            eje_id=data.get('eje_id'),  # Opcional
            eje_texto=data.get('eje_texto'),  # Opcional
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

@app.route('/guardar_estrategia_foda_con_eje', methods=['POST'])
@login_required
def guardar_estrategia_foda_con_eje():
    """Guardar una estrategia FODA cruzado con eje estratégico"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Formato no soportado'}), 400
        
        data = request.get_json()
        
        # Validar campos requeridos
        campos_requeridos = [
            'tipo_cruce', 'elemento_interno_id', 'elemento_interno_tipo',
            'elemento_interno_texto', 'elemento_externo_id', 'elemento_externo_tipo',
            'elemento_externo_texto', 'estrategia', 'eje_id', 'eje_texto'
        ]
        
        for campo in campos_requeridos:
            if not data.get(campo):
                return jsonify({'success': False, 'message': f'Campo {campo} es obligatorio'}), 400
        
        # Validar tipo de cruce
        if data.get('tipo_cruce') not in ['FO', 'DO', 'FA', 'DA']:
            return jsonify({'success': False, 'message': 'Tipo de cruce inválido'}), 400
        
        # Validar eje
        ejes_validos = ['educacion', 'salud', 'empleabilidad', 'desarrollo_economico', 
                       'sostenibilidad_ambiental', 'comunicacion', 'institucional']
        if data.get('eje_id') not in ejes_validos:
            return jsonify({'success': False, 'message': 'Eje estratégico inválido'}), 400
        
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
            eje_id=data['eje_id'],
            eje_texto=data['eje_texto'],
            creador_id=session['user_id']
        )
        
        db.session.add(nueva_estrategia)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '✅ Estrategia FODA cruzado guardada correctamente con eje',
            'data': {
                'id': nueva_estrategia.id,
                'tipo_cruce': nueva_estrategia.tipo_cruce,
                'estrategia': nueva_estrategia.estrategia,
                'eje_id': nueva_estrategia.eje_id,
                'eje_texto': nueva_estrategia.eje_texto,
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
    """API para obtener estrategias FODA cruzado (incluye ejes si existen)"""
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
                'eje_id': e.eje_id,
                'eje_texto': e.eje_texto,
                'fecha': e.fecha_creacion.isoformat() if e.fecha_creacion else None,
                'creador': e.creador.username if e.creador else None
            })
        
        return jsonify({'success': True, 'estrategias': estrategias_data})
        
    except Exception as e:
        print(f"Error en api_estrategias_foda: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/estrategias_foda_con_eje')
@login_required
def api_estrategias_foda_con_eje():
    """API para obtener estrategias FODA cruzado con eje"""
    try:
        estrategias = EstrategiaFodaCruzado.query.filter(
            EstrategiaFodaCruzado.eje_id.isnot(None)
        ).order_by(
            EstrategiaFodaCruzado.fecha_creacion.desc()
        ).all()
        
        estrategias_data = []
        for e in estrategias:
            estrategias_data.append({
                'id': e.id,
                'tipo_cruce': e.tipo_cruce,
                'elemento_interno_id': e.elemento_interno_id,
                'elemento_interno_tipo': e.elemento_interno_tipo,
                'elemento_interno_texto': e.elemento_interno_texto,
                'elemento_externo_id': e.elemento_externo_id,
                'elemento_externo_tipo': e.elemento_externo_tipo,
                'elemento_externo_texto': e.elemento_externo_texto,
                'estrategia': e.estrategia,
                'eje_id': e.eje_id,
                'eje_texto': e.eje_texto,
                'fecha_creacion': e.fecha_creacion.isoformat() if e.fecha_creacion else None,
                'creador': e.creador.username if e.creador else None
            })
        
        return jsonify({'success': True, 'estrategias': estrategias_data})
        
    except Exception as e:
        print(f"Error en api_estrategias_foda_con_eje: {e}")
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

# ==================== RUTAS API PARA ACTIVIDADES Y TAREAS ====================

@app.route('/api/actividades')
@login_required
def api_actividades():
    """API para obtener todas las actividades"""
    try:
        actividades = ActividadEstrategia.query.all()
        actividades_data = []
        for a in actividades:
            actividades_data.append({
                'id': a.id,
                'estrategia_id': a.estrategia_id,
                'nombre': a.nombre,
                'descripcion': a.descripcion,
                'responsable': a.responsable,
                'fecha_inicio': a.fecha_inicio.isoformat() if a.fecha_inicio else None,
                'fecha_fin': a.fecha_fin.isoformat() if a.fecha_fin else None,
                'fecha_creacion': a.fecha_creacion.isoformat() if a.fecha_creacion else None,
                'creador': a.creador.username if a.creador else None
            })
        return jsonify({'success': True, 'actividades': actividades_data})
    except Exception as e:
        print(f"Error en api_actividades: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/tareas')
@login_required
def api_tareas():
    """API para obtener todas las tareas"""
    try:
        tareas = TareaActividad.query.all()
        tareas_data = []
        for t in tareas:
            tareas_data.append({
                'id': t.id,
                'actividad_id': t.actividad_id,
                'nombre': t.nombre,
                'descripcion': t.descripcion,
                'responsable': t.responsable,
                'fecha_inicio': t.fecha_inicio.isoformat() if t.fecha_inicio else None,
                'fecha_fin': t.fecha_fin.isoformat() if t.fecha_fin else None,
                'estado': t.estado,
                'fecha_creacion': t.fecha_creacion.isoformat() if t.fecha_creacion else None,
                'creador': t.creador.username if t.creador else None
            })
        return jsonify({'success': True, 'tareas': tareas_data})
    except Exception as e:
        print(f"Error en api_tareas: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/actividades_estrategia/<int:estrategia_id>')
@login_required
def api_actividades_estrategia(estrategia_id):
    """API para obtener actividades de una estrategia"""
    try:
        # Verificar que la estrategia existe
        estrategia = EstrategiaFodaCruzado.query.get(estrategia_id)
        if not estrategia:
            return jsonify({'success': False, 'message': 'La estrategia no existe'}), 404
        
        actividades = ActividadEstrategia.query.filter_by(
            estrategia_id=estrategia_id
        ).order_by(
            ActividadEstrategia.fecha_creacion.desc()
        ).all()
        
        actividades_data = []
        for a in actividades:
            actividades_data.append({
                'id': a.id,
                'estrategia_id': a.estrategia_id,
                'nombre': a.nombre,
                'descripcion': a.descripcion,
                'responsable': a.responsable,
                'fecha_inicio': a.fecha_inicio.isoformat() if a.fecha_inicio else None,
                'fecha_fin': a.fecha_fin.isoformat() if a.fecha_fin else None,
                'fecha_creacion': a.fecha_creacion.isoformat() if a.fecha_creacion else None,
                'creador': a.creador.username if a.creador else None
            })
        
        return jsonify({'success': True, 'actividades': actividades_data})
        
    except Exception as e:
        print(f"Error en api_actividades_estrategia: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/agregar_actividad', methods=['POST'])
@login_required
def api_agregar_actividad():
    """API para agregar una actividad a una estrategia"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Formato no soportado'}), 400
        
        data = request.get_json()
        
        # Validar campos requeridos
        if not data.get('estrategia_id'):
            return jsonify({'success': False, 'message': 'El ID de la estrategia es obligatorio'}), 400
        
        if not data.get('nombre'):
            return jsonify({'success': False, 'message': 'El nombre de la actividad es obligatorio'}), 400
        
        # Verificar que la estrategia existe
        estrategia = EstrategiaFodaCruzado.query.get(data['estrategia_id'])
        if not estrategia:
            return jsonify({'success': False, 'message': 'La estrategia no existe'}), 404
        
        # Crear nueva actividad
        nueva_actividad = ActividadEstrategia(
            estrategia_id=data['estrategia_id'],
            nombre=data['nombre'].strip(),
            descripcion=data.get('descripcion', '').strip(),
            responsable=data.get('responsable', '').strip(),
            fecha_inicio=datetime.strptime(data['fecha_inicio'], '%Y-%m-%d').date() if data.get('fecha_inicio') else None,
            fecha_fin=datetime.strptime(data['fecha_fin'], '%Y-%m-%d').date() if data.get('fecha_fin') else None,
            creador_id=session['user_id']
        )
        
        db.session.add(nueva_actividad)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '✅ Actividad agregada correctamente',
            'actividad_id': nueva_actividad.id
        })
        
    except ValueError as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Formato de fecha inválido. Use YYYY-MM-DD'}), 400
    except Exception as e:
        db.session.rollback()
        print(f"Error en api_agregar_actividad: {e}")
        return jsonify({'success': False, 'message': f'Error del servidor: {str(e)}'}), 500

@app.route('/api/eliminar_actividad/<int:actividad_id>', methods=['DELETE'])
@login_required
def api_eliminar_actividad(actividad_id):
    """API para eliminar una actividad y sus tareas"""
    try:
        actividad = ActividadEstrategia.query.get_or_404(actividad_id)
        
        # Verificar permisos: admin o el creador de la actividad
        if session.get('rol') != 'admin' and actividad.creador_id != session.get('user_id'):
            return jsonify({'success': False, 'message': 'No autorizado'}), 403
        
        # Eliminar la actividad (las tareas se eliminarán en cascada por la relación)
        db.session.delete(actividad)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Actividad eliminada correctamente'})
        
    except Exception as e:
        db.session.rollback()
        print(f"Error en api_eliminar_actividad: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/tareas_actividad/<int:actividad_id>')
@login_required
def api_tareas_actividad(actividad_id):
    """API para obtener tareas de una actividad"""
    try:
        # Verificar que la actividad existe
        actividad = ActividadEstrategia.query.get(actividad_id)
        if not actividad:
            return jsonify({'success': False, 'message': 'La actividad no existe'}), 404
        
        tareas = TareaActividad.query.filter_by(
            actividad_id=actividad_id
        ).order_by(
            TareaActividad.fecha_creacion.desc()
        ).all()
        
        tareas_data = []
        for t in tareas:
            tareas_data.append({
                'id': t.id,
                'actividad_id': t.actividad_id,
                'nombre': t.nombre,
                'descripcion': t.descripcion,
                'responsable': t.responsable,
                'fecha_inicio': t.fecha_inicio.isoformat() if t.fecha_inicio else None,
                'fecha_fin': t.fecha_fin.isoformat() if t.fecha_fin else None,
                'estado': t.estado,
                'fecha_creacion': t.fecha_creacion.isoformat() if t.fecha_creacion else None,
                'creador': t.creador.username if t.creador else None
            })
        
        return jsonify({'success': True, 'tareas': tareas_data})
        
    except Exception as e:
        print(f"Error en api_tareas_actividad: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/agregar_tarea', methods=['POST'])
@login_required
def api_agregar_tarea():
    """API para agregar una tarea a una actividad"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Formato no soportado'}), 400
        
        data = request.get_json()
        
        # Validar campos requeridos
        if not data.get('actividad_id'):
            return jsonify({'success': False, 'message': 'El ID de la actividad es obligatorio'}), 400
        
        if not data.get('nombre'):
            return jsonify({'success': False, 'message': 'El nombre de la tarea es obligatorio'}), 400
        
        # Verificar que la actividad existe
        actividad = ActividadEstrategia.query.get(data['actividad_id'])
        if not actividad:
            return jsonify({'success': False, 'message': 'La actividad no existe'}), 404
        
        # Validar estado
        estado_valido = data.get('estado', 'pendiente')
        if estado_valido not in ['pendiente', 'en_progreso', 'completada']:
            estado_valido = 'pendiente'
        
        # Crear nueva tarea
        nueva_tarea = TareaActividad(
            actividad_id=data['actividad_id'],
            nombre=data['nombre'].strip(),
            descripcion=data.get('descripcion', '').strip(),
            responsable=data.get('responsable', '').strip(),
            fecha_inicio=datetime.strptime(data['fecha_inicio'], '%Y-%m-%d').date() if data.get('fecha_inicio') else None,
            fecha_fin=datetime.strptime(data['fecha_fin'], '%Y-%m-%d').date() if data.get('fecha_fin') else None,
            estado=estado_valido,
            creador_id=session['user_id']
        )
        
        db.session.add(nueva_tarea)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '✅ Tarea agregada correctamente',
            'tarea_id': nueva_tarea.id
        })
        
    except ValueError as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Formato de fecha inválido. Use YYYY-MM-DD'}), 400
    except Exception as e:
        db.session.rollback()
        print(f"Error en api_agregar_tarea: {e}")
        return jsonify({'success': False, 'message': f'Error del servidor: {str(e)}'}), 500

# ==================== RUTAS ADICIONALES ====================

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==================== FUNCIÓN PARA VERIFICAR ESTRUCTURA DE BD ====================

@app.route('/migrate-db')
def migrate_db():
    """Ruta especial para migrar la estructura de la base de datos"""
    try:
        with db.engine.connect() as connection:
            # 1. Verificar estructura de la tabla estrategias_foda_cruzado
            print("🔍 Verificando estructura de la tabla estrategias_foda_cruzado...")
            
            # Para PostgreSQL
            check_columns_query = """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'estrategias_foda_cruzado'
                ORDER BY ordinal_position
            """
            
            columns = connection.execute(check_columns_query).fetchall()
            print("📋 Columnas actuales en estrategias_foda_cruzado:")
            for col in columns:
                print(f"   - {col[0]} ({col[1]}, nullable: {col[2]})")
            
            # 2. Agregar columnas faltantes si es necesario
            column_names = [col[0] for col in columns]
            
            if 'eje_id' not in column_names:
                print("🔄 Agregando columna 'eje_id'...")
                connection.execute("ALTER TABLE estrategias_foda_cruzado ADD COLUMN eje_id VARCHAR(50)")
                print("✅ Columna 'eje_id' agregada")
            
            if 'eje_texto' not in column_names:
                print("🔄 Agregando columna 'eje_texto'...")
                connection.execute("ALTER TABLE estrategias_foda_cruzado ADD COLUMN eje_texto VARCHAR(200)")
                print("✅ Columna 'eje_texto' agregada")
            
            # 3. Verificar tablas de actividades y tareas
            try:
                print("\n🔍 Verificando tabla actividades_estrategia...")
                actividades_count = ActividadEstrategia.query.count()
                print(f"   📋 Total de actividades: {actividades_count}")
            except Exception as e:
                print(f"   ⚠️  Error al verificar actividades: {e}")
                print("   ℹ️  La tabla se creará automáticamente al primer uso.")

            try:
                print("🔍 Verificando tabla tareas_actividad...")
                tareas_count = TareaActividad.query.count()
                print(f"   📋 Total de tareas: {tareas_count}")
            except Exception as e:
                print(f"   ⚠️  Error al verificar tareas: {e}")
                print("   ℹ️  La tabla se creará automáticamente al primer uso.")
            
            # 4. Verificar otras tablas importantes
            print("\n🔍 Verificando tabla usuarios...")
            users_count = User.query.count()
            print(f"   👥 Total de usuarios: {users_count}")
            
            print("🔍 Verificando tabla aspectos_ambientales...")
            aspectos_count = AspectoAmbiental.query.count()
            print(f"   📊 Total de aspectos: {aspectos_count}")
            
            # 5. Intentar contar estrategias para verificar que funciona
            try:
                estrategias_count = EstrategiaFodaCruzado.query.count()
                print(f"   ♟️  Total de estrategias FODA: {estrategias_count}")
            except Exception as e:
                print(f"   ⚠️  Error al contar estrategias: {e}")
                print("   🔧 Intentando corregir estructura...")
                
                # Intentar agregar todas las columnas necesarias
                expected_columns = [
                    'id', 'tipo_cruce', 'elemento_interno_id', 'elemento_interno_tipo',
                    'elemento_interno_texto', 'elemento_externo_id', 'elemento_externo_tipo',
                    'elemento_externo_texto', 'estrategia', 'fecha_creacion', 'creador_id',
                    'eje_id', 'eje_texto'
                ]
                
                for expected_col in expected_columns:
                    if expected_col not in column_names:
                        print(f"   🔄 Agregando columna '{expected_col}'...")
                        # Determinar tipo de dato
                        if expected_col == 'id':
                            connection.execute(f"ALTER TABLE estrategias_foda_cruzado ADD COLUMN {expected_col} SERIAL PRIMARY KEY")
                        elif expected_col in ['elemento_interno_id', 'elemento_externo_id', 'creador_id']:
                            connection.execute(f"ALTER TABLE estrategias_foda_cruzado ADD COLUMN {expected_col} INTEGER")
                        elif expected_col == 'estrategia':
                            connection.execute(f"ALTER TABLE estrategias_foda_cruzado ADD COLUMN {expected_col} TEXT")
                        elif expected_col == 'fecha_creacion':
                            connection.execute(f"ALTER TABLE estrategias_foda_cruzado ADD COLUMN {expected_col} TIMESTAMP")
                        else:
                            connection.execute(f"ALTER TABLE estrategias_foda_cruzado ADD COLUMN {expected_col} VARCHAR(200)")
            
            return '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Migración de Base de Datos</title>
                <style>
                    body { font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }
                    .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                    .success { color: #4CAF50; background: #f1f8e9; padding: 15px; border-radius: 5px; margin: 20px 0; }
                    pre { background: #f8f9fa; padding: 15px; border-radius: 5px; overflow: auto; }
                    a { color: #2196F3; text-decoration: none; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>✅ Migración de Base de Datos Completa</h1>
                    <div class="success">
                        <p>La estructura de la base de datos ha sido verificada y actualizada.</p>
                        <p>Las columnas <strong>eje_id</strong> y <strong>eje_texto</strong> han sido agregadas a la tabla <strong>estrategias_foda_cruzado</strong>.</p>
                        <p>Las tablas <strong>actividades_estrategia</strong> y <strong>tareas_actividad</strong> han sido verificadas.</p>
                    </div>
                    <h3>Estructura Actual:</h3>
                    <pre>''' + "\n".join([f"- {col[0]} ({col[1]}, nullable: {col[2]})" for col in columns]) + '''</pre>
                    <p><a href="/">Volver al inicio</a> | <a href="/init-db">Reinicializar BD</a></p>
                </div>
            </body>
            </html>
            '''
            
    except Exception as e:
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error en Migración</title>
            <style>
                body { font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .error { color: #f44336; background: #ffebee; padding: 15px; border-radius: 5px; margin: 20px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>❌ Error en Migración</h1>
                <div class="error">
                    <p><strong>Error:</strong> {str(e)}</p>
                </div>
                <p>Por favor, verifique los permisos de la base de datos o contacte al administrador.</p>
                <p><a href="/">Volver al inicio</a></p>
            </div>
        </body>
        </html>
        '''

# ==================== RUTAS DE ADMINISTRACIÓN Y SISTEMA ====================

@app.route('/init-db')
def init_db():
    """Inicializar base de datos - Versión mejorada con migración"""
    try:
        if initialize_database():
            usuarios = User.query.all()
            aspectos = AspectoAmbiental.query.all()
            
            # Intentar obtener estrategias (puede fallar si hay problemas de estructura)
            try:
                estrategias = EstrategiaFodaCruzado.query.all()
                estrategias_count = len(estrategias)
            except:
                estrategias_count = 0
                print("⚠️  No se pudieron obtener las estrategias (posible problema de estructura)")
            
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
                    
                    .warning { 
                        background: rgba(255, 193, 7, 0.2);
                        border: 2px solid #FFC107;
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
                        display: inline-block;
                        background: #4CAF50;
                        color: white;
                        text-decoration: none;
                        padding: 12px 20px;
                        border-radius: 8px;
                        margin: 10px 5px;
                        text-align: center;
                        font-weight: bold;
                        transition: background 0.3s, transform 0.3s;
                        border: none;
                        cursor: pointer;
                    }
                    
                    .btn:hover { 
                        background: #45a049;
                        transform: translateY(-2px);
                    }
                    
                    .btn-secondary {
                        background: #2196F3;
                    }
                    
                    .btn-secondary:hover {
                        background: #1976D2;
                    }
                    
                    .btn-container {
                        display: flex;
                        justify-content: center;
                        flex-wrap: wrap;
                        gap: 10px;
                        margin: 25px 0;
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
                        
                        .btn-container {
                            flex-direction: column;
                        }
                        
                        .btn {
                            width: 100%;
                            margin: 5px 0;
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
                        <p>Tablas verificadas: usuarios, aspectos_ambientales, estrategias_foda_cruzado, actividades_estrategia, tareas_actividad</p>
                    </div>
                    
                    ''' + (f'''
                    <div class="warning">
                        <p><strong>⚠️ IMPORTANTE:</strong> Se detectó que la tabla <strong>estrategias_foda_cruzado</strong> necesitaba actualización.</p>
                        <p>Se han agregado las columnas <strong>eje_id</strong> y <strong>eje_texto</strong> para las nuevas funcionalidades.</p>
                    </div>
                    ''' if estrategias_count == 0 else '') + '''
                    
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
                            <span class="stat-number">''' + str(estrategias_count) + '''</span>
                            <span class="stat-label">♟️ Estrategias FODA</span>
                        </div>
                    </div>
                    
                    <div class="btn-container">
                        <a href="/login" class="btn">🚀 Ir al Login</a>
                        <a href="/migrate-db" class="btn btn-secondary">🔄 Verificar/Reparar BD</a>
                    </div>
                    
                    <div style="text-align: center; margin-top: 20px; font-size: 0.9rem; opacity: 0.8;">
                        <p>Sistema CURIMINING v3.0 - Desarrollado por O&R Business Consulting Group</p>
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
            <p style="text-align: center;"><a href="/migrate-db">Intentar reparar BD</a> | <a href="/">Volver</a></p>
            '''
    except Exception as e:
        return f'''
        <h1 style="color: red; text-align: center; margin-top: 50px;">❌ Error crítico</h1>
        <p style="text-align: center;"><strong>Error:</strong> {str(e)}</p>
        <p style="text-align: center;"><a href="/migrate-db">Intentar reparar BD</a> | <a href="/">Volver</a></p>
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
        
        # Intentar contar estrategias (puede fallar si hay problemas de estructura)
        try:
            estrategias_count = EstrategiaFodaCruzado.query.count()
        except:
            estrategias_count = 0
        
        # Intentar contar actividades y tareas
        try:
            actividades_count = ActividadEstrategia.query.count()
            tareas_count = TareaActividad.query.count()
        except:
            actividades_count = 0
            tareas_count = 0
    
    except Exception as e:
        db_status = f'error: {str(e)[:100]}'
        user_count = 0
        aspecto_count = 0
        aspecto_foda_ext = 0
        aspecto_canva = 0
        aspecto_foda_int = 0
        estrategias_count = 0
        actividades_count = 0
        tareas_count = 0
    
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
        'actividades_estrategia': actividades_count,
        'tareas_actividad': tareas_count,
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
        try:
            estrategias_count = EstrategiaFodaCruzado.query.count()
        except:
            estrategias_count = 0
        
        # Contar estrategias por eje
        try:
            estrategias_con_eje = EstrategiaFodaCruzado.query.filter(
                EstrategiaFodaCruzado.eje_id.isnot(None)
            ).count()
        except:
            estrategias_con_eje = 0
        
        # Contar actividades y tareas de estrategias
        try:
            actividades_estrategia_count = ActividadEstrategia.query.count()
            tareas_actividad_count = TareaActividad.query.count()
        except:
            actividades_estrategia_count = 0
            tareas_actividad_count = 0
        
        return jsonify({
            'success': True,
            'estadisticas': {
                'total_actividades': total_actividades,
                'actividades_canva': total_actividades_canva,
                'actividades_foda_ext': total_actividades_foda_ext,
                'actividades_foda_int': total_actividades_foda_int,
                'estrategias_foda_cruzado': estrategias_count,
                'estrategias_con_eje': estrategias_con_eje,
                'actividades_estrategia': actividades_estrategia_count,
                'tareas_actividad': tareas_actividad_count,
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
    try:
        estrategias_count = EstrategiaFodaCruzado.query.count()
    except:
        estrategias_count = 0
    
    # Contar actividades y tareas de estrategias
    try:
        actividades_estrategia_count = ActividadEstrategia.query.count()
        tareas_actividad_count = TareaActividad.query.count()
    except:
        actividades_estrategia_count = 0
        tareas_actividad_count = 0
    
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
                         actividades_estrategia_count=actividades_estrategia_count,
                         tareas_actividad_count=tareas_actividad_count,
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
print("📊 Versión: 3.0 (FODA Cruzado con Ejes y Nuevas Pestañas)")
print("📅 Fecha: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
print("=" * 60)
print("📱 Características:")
print("  ✅ FODA Cruzado completo con sistema de ejes")
print("  ✅ 2 nuevas páginas: Estrategias y Mapa de Red")
print("  ✅ Sistema completo de actividades y tareas para estrategias")
print("  ✅ 7 ejes estratégicos integrados")
print("  ✅ Persistencia de estrategias con ejes")
print("  ✅ Visualización de red interactiva")
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
            print("✅ Tablas adicionales: actividades_estrategia, tareas_actividad")
            print("✅ Campos de eje añadidos a estrategias_foda_cruzado")
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
    print(f"📱 Modo: FODA Cruzado con Ejes y Nuevas Pestañas")
    print("=" * 60)
    
    # Configurar para producción
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    app.run(
        host='0.0.0.0', 
        port=port, 
        debug=debug_mode,
        threaded=True  # Mejor rendimiento para múltiples conexiones
    )
