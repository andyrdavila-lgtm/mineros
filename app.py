from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
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

# Modelo de usuario
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    rol = db.Column(db.String(20), nullable=False, default='user')
    
    def set_password(self, password):
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password, password)

# Decoradores de autenticación
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

# FUNCIÓN MEJORADA para inicializar base de datos
def initialize_database():
    """Intenta inicializar la base de datos con reintentos"""
    max_retries = 3
    retry_delay = 2  # segundos
    
    for attempt in range(max_retries):
        try:
            print(f"🔄 Intento {attempt + 1} de {max_retries} para inicializar BD...")
            
            # Crear todas las tablas
            db.create_all()
            print("✅ Tablas creadas exitosamente")
            
            # Verificar si el usuario admin ya existe
            admin_exists = db.session.execute(
                db.select(User).filter_by(username='admin')
            ).scalar_one_or_none()
            
            if not admin_exists:
                # Crear usuario admin por defecto
                admin_user = User(
                    username='admin',
                    rol='admin'
                )
                admin_user.set_password('admin123')
                db.session.add(admin_user)
                db.session.commit()
                print("✅ Usuario admin creado exitosamente")
            else:
                print("✅ Usuario admin ya existe")
            
            # Verificar que las tablas fueron creadas
            table_check = db.session.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            ).fetchall()
            
            print(f"✅ Tablas en la base de datos: {[t[0] for t in table_check]}")
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
            return False
    
    return False

# Ruta principal - Muestra el login
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
    return render_template('inicio.html')

@app.route('/admin')
@admin_required
def admin():
    return render_template('admin.html')

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

# Ruta MEJORADA para inicializar la base de datos
@app.route('/init-db')
def init_db():
    try:
        if initialize_database():
            return '''
            <h1>✅ Base de datos inicializada EXITOSAMENTE</h1>
            <p><strong>Usuario admin creado:</strong></p>
            <ul>
                <li><strong>Usuario:</strong> admin</li>
                <li><strong>Contraseña:</strong> admin123</li>
            </ul>
            <p><a href="/login">Ir al login</a></p>
            <p style="color: red;"><strong>⚠️ ADVERTENCIA:</strong> Cambia esta contraseña inmediatamente.</p>
            '''
        else:
            return '''
            <h1>❌ Error inicializando base de datos</h1>
            <p>No se pudo conectar a la base de datos o crear las tablas.</p>
            <p>Verifica que:</p>
            <ul>
                <li>La variable DATABASE_URL esté configurada correctamente</li>
                <li>PostgreSQL esté funcionando</li>
                <li>Las credenciales sean correctas</li>
            </ul>
            <p><a href="/">Volver</a></p>
            '''
    except Exception as e:
        return f'''
        <h1>❌ Error crítico</h1>
        <p><strong>Error:</strong> {str(e)}</p>
        <p><a href="/">Volver</a></p>
        '''

# Ruta para verificar estado MEJORADA
@app.route('/check')
def check():
    try:
        # Verificar conexión a base de datos
        db.session.execute("SELECT 1")
        db_connected = True
        
        # Verificar si existe la tabla 'user'
        table_exists = False
        try:
            User.query.first()
            table_exists = True
        except:
            table_exists = False
        
        user_count = 0
        if table_exists:
            user_count = User.query.count()
        
        return jsonify({
            'status': 'ok',
            'port': os.environ.get('PORT', 'No configurado'),
            'python_version': sys.version.split()[0],
            'database': 'conectada' if db_connected else 'error',
            'table_exists': table_exists,
            'user_count': user_count,
            'database_url_prefix': os.environ.get('DATABASE_URL', 'No configurado')[:30] + '...' if os.environ.get('DATABASE_URL') else 'No configurado'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'port': os.environ.get('PORT', 'No configurado'),
            'python_version': sys.version.split()[0],
            'database': 'error',
            'error': str(e)[:100]
        })

# Inicializar base de datos automáticamente al arrancar
print("=" * 50)
print("🚀 Iniciando CURIMINING - Sistema de Gestión Minera")
print("=" * 50)

# Intentar inicializar la base de datos
with app.app_context():
    print("🔄 Intentando inicializar base de datos...")
    if initialize_database():
        print("✅ Base de datos inicializada con éxito")
    else:
        print("⚠️  No se pudo inicializar la base de datos automáticamente")
        print("ℹ️  Visita /init-db para inicializar manualmente")

# Solo para ejecución local
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"🌐 Servidor ejecutándose en: http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
    
