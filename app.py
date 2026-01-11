from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import sys
import time
from functools import wraps
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy import or_

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
            
            # NO crear datos de ejemplo - la BD se alimentará desde la aplicación
            
            # Commit todos los cambios
            if usuarios_creados > 0:
                db.session.commit()
                print(f"✅ {usuarios_creados} usuarios nuevos creados")
            
            print(f"📊 Total de usuarios en sistema: {User.query.count()}")
            print(f"📊 Total de aspectos en sistema: {AspectoAmbiental.query.count()}")
            
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
                    return redirect(url_for('admin'))
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

@app.route('/admin')
@admin_required
def admin():
    usuarios = User.query.all()
    aspectos = AspectoAmbiental.query.order_by(AspectoAmbiental.created_at.desc()).all()
    
    # Estadísticas detalladas
    total_actividades_canva = AspectoAmbiental.query.filter_by(fuente='canva').count()
    total_actividades_foda_ext = AspectoAmbiental.query.filter_by(fuente='foda_ext').count()
    total_actividades_foda_int = AspectoAmbiental.query.filter_by(fuente='foda_int').count()
    
    return render_template('admin.html', 
                         usuarios=usuarios, 
                         aspectos=aspectos,
                         total_usuarios=len(usuarios),
                         total_aspectos=len(aspectos),
                         total_canva=total_actividades_canva,
                         total_foda_ext=total_actividades_foda_ext,
                         total_foda_int=total_actividades_foda_int)

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
    aspectos = AspectoAmbiental.query.all()
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

# ==================== RUTAS ESPECÍFICAS PARA FODA INTERNO ====================

@app.route('/fodaint')
@login_required
def fodaint():
    """Página para análisis FODA Interno"""
    # Similar a fodaext pero para interno
    aspectos_lista = AspectoAmbiental.query.filter_by(
        fuente='foda_int'
    ).order_by(AspectoAmbiental.created_at.desc()).all()
    
    return render_template('fodaint.html', aspectos_lista=aspectos_lista)

# ==================== RUTAS ESPECÍFICAS PARA FODA CRUZADO ====================

@app.route('/cruzado')
@login_required
def cruzado():
    """Página para análisis FODA Cruzado"""
    # Aquí podríamos combinar datos de foda_int y foda_ext
    aspectos_foda_ext = AspectoAmbiental.query.filter_by(fuente='foda_ext').all()
    aspectos_foda_int = AspectoAmbiental.query.filter_by(fuente='foda_int').all()
    
    return render_template('cruzado.html', 
                         aspectos_foda_ext=aspectos_foda_ext,
                         aspectos_foda_int=aspectos_foda_int)

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
    if request.is_json:
        data = request.get_json()
        
        # Crear nuevo aspecto ambiental específico para CANVA
        nuevo_aspecto = AspectoAmbiental(
            actividad=data['actividad'],
            tipo=data['tipo'],  # Este será el bloque CANVA (ej: "Mapeo de Actores...")
            aspecto=data['aspecto'],  # Este será "Positivo: ..." o "Negativo: ..."
            fuente='canva',  # Marcamos que viene del CANVA
            created_by=session['user_id']  # Usamos el ID del usuario en sesión
        )
        
        try:
            db.session.add(nuevo_aspecto)
            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Actividad guardada correctamente',
                'id': nuevo_aspecto.id
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
    
    return jsonify({'success': False, 'message': 'Solicitud inválida'}), 400

@app.route('/limpiar_canva', methods=['POST'])
@login_required
def limpiar_canva():
    # Solo administradores pueden limpiar el CANVA
    if session.get('rol') != 'admin':
        return jsonify({'success': False, 'message': 'No autorizado. Solo administradores pueden limpiar el CANVA.'}), 403
    
    try:
        # Eliminar todas las actividades con fuente='canva'
        AspectoAmbiental.query.filter_by(fuente='canva').delete()
        db.session.commit()
        return jsonify({'success': True, 'message': 'CANVA limpiado correctamente'})
    except Exception as e:
        db.session.rollback()
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
        
    except Exception as e:
        db_status = f'error: {str(e)[:100]}'
        user_count = 0
        aspecto_count = 0
        aspecto_foda_ext = 0
        aspecto_canva = 0
        aspecto_foda_int = 0
    
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat(),
        'database': db_status,
        'users': user_count,
        'aspectos_total': aspecto_count,
        'aspectos_foda_ext': aspecto_foda_ext,
        'aspectos_canva': aspecto_canva,
        'aspectos_foda_int': aspecto_foda_int,
        'port': os.environ.get('PORT', '3000'),
        'python_version': sys.version.split()[0]
    })

# ==================== MANEJO DE ERRORES ====================

# Ruta para guardar actividades arrastradas desde CANVA
@app.route('/guardar_matriz_foda', methods=['POST'])
def guardar_matriz_foda():
    data = request.json
    actividades = data.get('actividades', [])
    
    for actividad in actividades:
        # Crear nuevo registro en la tabla de FODA externo
        nueva_actividad = FODAExterno(
            actividad=actividad['actividad'],
            tipo=actividad['tipo'],
            aspecto=actividad['aspecto_nuevo'],  # El nuevo aspecto asignado
            fuente='foda_ext',  # Siempre como FODA externo
            empresa_id=current_user.empresa_id
        )
        db.session.add(nueva_actividad)
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Actividades guardadas en la matriz FODA'})

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

# ==================== INICIALIZACIÓN ====================

print("=" * 60)
print("🚀 INICIANDO SISTEMA DE GESTIÓN AMBIENTAL MINERA - CURIMINING")
print("=" * 60)
print("📊 Versión: 2.1 (Responsive + Historial Mixto)")
print("📅 Fecha: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
print("=" * 60)
print("📱 Características:")
print("  ✅ Responsive total (mobile, tablet, desktop)")
print("  ✅ Historial mixto (foda_ext + canvas)")
print("  ✅ Orden por aspecto: POLITICO, ECONOMICO, SOCIAL, TECNOLOGICO, ECOLOGICO, LEGAL")
print("  ✅ 9 usuarios pre-creados")
print("=" * 60)

# Inicializar base de datos
with app.app_context():
    try:
        print("🔄 Inicializando base de datos...")
        if initialize_database():
            print("✅ Base de datos inicializada correctamente")
            print("✅ Sistema optimizado para todos los dispositivos")
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
    print(f"📱 Modo: Responsive Completo")
    print(f"📏 Soporte: Mobile (320px+) | Tablet (768px+) | Desktop (1024px+)")
    print("=" * 60)
    
    # Configurar para producción
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    app.run(
        host='0.0.0.0', 
        port=port, 
        debug=debug_mode,
        threaded=True  # Mejor rendimiento para múltiples conexiones
    )
