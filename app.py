from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import sys
import time
from functools import wraps
from sqlalchemy.exc import OperationalError, ProgrammingError

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

# Nueva tabla: Aspectos Ambientales
class AspectoAmbiental(db.Model):
    __tablename__ = 'aspectos_ambientales'
    id = db.Column(db.Integer, primary_key=True)
    actividad = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(100), nullable=False)
    aspecto = db.Column(db.Text, nullable=False)
    fuente = db.Column(db.String(200), nullable=False)
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
            
            # Datos de ejemplo para aspectos ambientales
            aspectos_ejemplo = [
                {
                    "actividad": "Perforación de roca",
                    "tipo": "Emisión atmosférica",
                    "aspecto": "Generación de polvo en suspensión",
                    "fuente": "Perforadora, voladura"
                },
                {
                    "actividad": "Transporte de material",
                    "tipo": "Consumo de recursos",
                    "aspecto": "Consumo de combustible diesel",
                    "fuente": "Camiones, maquinaria"
                },
                {
                    "actividad": "Procesamiento de mineral",
                    "tipo": "Generación de residuos",
                    "aspecto": "Producción de relaves",
                    "fuente": "Planta concentradora"
                },
                {
                    "actividad": "Manejo de químicos",
                    "tipo": "Riesgo de contaminación",
                    "aspecto": "Derrames de reactivos químicos",
                    "fuente": "Área de almacenamiento"
                }
            ]
            
            # Crear aspectos ambientales de ejemplo si no existen
            for aspecto_info in aspectos_ejemplo:
                aspecto_existe = AspectoAmbiental.query.filter_by(
                    actividad=aspecto_info["actividad"],
                    aspecto=aspecto_info["aspecto"]
                ).first()
                
                if not aspecto_existe:
                    nuevo_aspecto = AspectoAmbiental(**aspecto_info)
                    db.session.add(nuevo_aspecto)
                    print(f"  ✅ Aspecto '{aspecto_info['actividad']}' creado")
            
            # Commit todos los cambios
            if usuarios_creados > 0:
                db.session.commit()
                print(f"✅ {usuarios_creados} usuarios nuevos creados")
            
            db.session.commit()
            print("✅ Datos de ejemplo creados")
            
            print(f"📊 Total de usuarios: {User.query.count()}")
            print(f"📊 Total de aspectos: {AspectoAmbiental.query.count()}")
            
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
    
    return render_template('inicio.html', 
                         total_aspectos=total_aspectos,
                         aspectos_recientes=aspectos_recientes)

@app.route('/admin')
@admin_required
def admin():
    usuarios = User.query.all()
    aspectos = AspectoAmbiental.query.all()
    return render_template('admin.html', 
                         usuarios=usuarios, 
                         aspectos=aspectos,
                         total_usuarios=len(usuarios),
                         total_aspectos=len(aspectos))

# ==================== RUTAS PARA ASPECTOS AMBIENTALES ====================

@app.route('/aspectos')
@login_required
def listar_aspectos():
    """Lista todos los aspectos ambientales"""
    aspectos = AspectoAmbiental.query.order_by(AspectoAmbiental.actividad).all()
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
        'updated_at': a.updated_at.isoformat() if a.updated_at else None
    } for a in aspectos])

# ==================== RUTAS EXISTENTES ====================

@app.route('/canvas')
@login_required
def canvas():
    return render_template('canvas.html')

@app.route('/cruzado')
@login_required
def cruzado():
    return render_template('cruzado.html')

@app.route('/fodaext')
@login_required
def fodaext():
    return render_template('fodaext.html')

@app.route('/fodaint')
@login_required
def fodaint():
    return render_template('fodaint.html')

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
            
            return f'''
            <!DOCTYPE html>
            <html>
            <head><title>Base de Datos Inicializada</title></head>
            <body>
                <h1>✅ Base de Datos Inicializada</h1>
                <p>Usuarios creados: {len(usuarios)}</p>
                <p>Aspectos ambientales creados: {len(aspectos)}</p>
                <p><a href="/login">Ir al Login</a></p>
            </body>
            </html>
            '''
        else:
            return '<h1>❌ Error inicializando BD</h1>'
    except Exception as e:
        return f'<h1>❌ Error: {str(e)}</h1>'

@app.route('/check')
def check():
    """Verificar estado del sistema"""
    try:
        db_status = 'conectada'
        user_count = User.query.count()
        aspecto_count = AspectoAmbiental.query.count()
    except:
        db_status = 'error'
        user_count = 0
        aspecto_count = 0
    
    return jsonify({
        'status': 'ok',
        'database': db_status,
        'users': user_count,
        'aspectos': aspecto_count,
        'port': os.environ.get('PORT', '3000')
    })

# ==================== INICIALIZACIÓN ====================

print("=" * 60)
print("🚀 INICIANDO SISTEMA DE GESTIÓN AMBIENTAL MINERA")
print("=" * 60)

# Inicializar base de datos
with app.app_context():
    try:
        print("🔄 Inicializando base de datos...")
        initialize_database()
        print("✅ Sistema listo")
    except Exception as e:
        print(f"⚠️  Error: {e}")

# ==================== EJECUCIÓN ====================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    print(f"🌐 Servidor ejecutándose en: http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
