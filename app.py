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
    __tablename__ = 'usuarios'  # Nombre de tabla más específico
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

# FUNCIÓN MEJORADA para inicializar base de datos CON TODOS LOS USUARIOS
def initialize_database():
    """Intenta inicializar la base de datos con reintentos y crea todos los usuarios"""
    max_retries = 3
    retry_delay = 2  # segundos
    
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
                
                # Verificar si el usuario ya existe
                user_exists = db.session.execute(
                    db.select(User).filter_by(username=username)
                ).scalar_one_or_none()
                
                if not user_exists:
                    # Crear nuevo usuario
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
            
            print(f"ℹ️  {usuarios_existentes} usuarios ya existían")
            print(f"📊 Total de usuarios en sistema: {User.query.count()}")
            
            # Mostrar resumen de usuarios
            print("\n📋 RESUMEN DE USUARIOS CREADOS:")
            print("=" * 40)
            print("👑 ADMINISTRADORES (rol: admin):")
            admin_users = User.query.filter_by(rol='admin').all()
            for user in admin_users:
                print(f"   • {user.username}")
            
            print("\n👥 USUARIOS REGULARES (rol: user):")
            regular_users = User.query.filter_by(rol='user').all()
            for user in regular_users:
                print(f"   • {user.username}")
            
            print("=" * 40)
            
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
            db.session.rollback()  # Rollback en caso de error
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
    # Obtener lista de usuarios para mostrar en panel admin
    usuarios = User.query.all()
    return render_template('admin.html', usuarios=usuarios)

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
            # Obtener lista de usuarios creados
            usuarios = User.query.all()
            
            html_response = '''
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>CURIMINING - Base de Datos Inicializada</title>
                <style>
                    body {
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background: linear-gradient(135deg, #1B4079 0%, #4D7C8A 100%);
                        color: white;
                        min-height: 100vh;
                        margin: 0;
                        padding: 20px;
                    }
                    .container {
                        max-width: 800px;
                        margin: 0 auto;
                        background: rgba(255, 255, 255, 0.1);
                        backdrop-filter: blur(10px);
                        border-radius: 15px;
                        padding: 30px;
                        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
                    }
                    h1 {
                        color: #CBDF90;
                        text-align: center;
                        margin-bottom: 30px;
                    }
                    .success {
                        background: rgba(76, 175, 80, 0.2);
                        border: 2px solid #4CAF50;
                        border-radius: 10px;
                        padding: 20px;
                        margin-bottom: 30px;
                    }
                    .warning {
                        background: rgba(255, 193, 7, 0.2);
                        border: 2px solid #FFC107;
                        border-radius: 10px;
                        padding: 20px;
                        margin-bottom: 30px;
                    }
                    .user-list {
                        display: grid;
                        grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
                        gap: 15px;
                        margin: 20px 0;
                    }
                    .user-card {
                        background: rgba(255, 255, 255, 0.1);
                        border-radius: 8px;
                        padding: 15px;
                        border-left: 4px solid;
                    }
                    .admin-card {
                        border-left-color: #FF5722;
                    }
                    .user-card {
                        border-left-color: #2196F3;
                    }
                    .badge {
                        display: inline-block;
                        padding: 4px 8px;
                        border-radius: 12px;
                        font-size: 12px;
                        font-weight: bold;
                        margin-right: 10px;
                    }
                    .badge-admin {
                        background: #FF5722;
                        color: white;
                    }
                    .badge-user {
                        background: #2196F3;
                        color: white;
                    }
                    .btn {
                        display: inline-block;
                        background: #4CAF50;
                        color: white;
                        text-decoration: none;
                        padding: 12px 24px;
                        border-radius: 6px;
                        font-weight: bold;
                        margin-top: 20px;
                        transition: background 0.3s;
                    }
                    .btn:hover {
                        background: #45a049;
                    }
                    .credentials {
                        background: rgba(0, 0, 0, 0.2);
                        padding: 10px;
                        border-radius: 6px;
                        margin: 5px 0;
                        font-family: monospace;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>✅ Base de Datos Inicializada EXITOSAMENTE</h1>
                    
                    <div class="success">
                        <h2>🔄 Sistema CURIMINING Listo</h2>
                        <p>Se han creado todas las tablas y usuarios necesarios para el sistema.</p>
                    </div>
                    
                    <div class="warning">
                        <h3>⚠️ ADVERTENCIA DE SEGURIDAD</h3>
                        <p>Cambia las contraseñas por defecto inmediatamente después del primer acceso.</p>
                        <p>Las credenciales iniciales son iguales al nombre de usuario (ej: usuario: ANDRES, contraseña: ANDRES).</p>
                    </div>
                    
                    <h2>📋 Usuarios Creados</h2>
                    <div class="user-list">
            '''
            
            # Agregar tarjetas de usuarios
            for usuario in usuarios:
                badge_class = "badge-admin" if usuario.rol == "admin" else "badge-user"
                badge_text = "ADMIN" if usuario.rol == "admin" else "USER"
                card_class = "admin-card" if usuario.rol == "admin" else "user-card"
                
                html_response += f'''
                <div class="user-card {card_class}">
                    <div style="margin-bottom: 10px;">
                        <span class="badge {badge_class}">{badge_text}</span>
                        <strong style="font-size: 18px;">{usuario.username}</strong>
                    </div>
                    <div class="credentials">
                        <div><strong>Usuario:</strong> {usuario.username}</div>
                        <div><strong>Contraseña:</strong> {usuario.username}</div>
                        <div><strong>Rol:</strong> {usuario.rol}</div>
                    </div>
                </div>
                '''
            
            html_response += '''
                    </div>
                    
                    <div style="text-align: center; margin-top: 30px;">
                        <a href="/login" class="btn">🚀 Ir al Login</a>
                    </div>
                    
                    <div style="margin-top: 30px; padding: 15px; background: rgba(0,0,0,0.2); border-radius: 8px;">
                        <h3>📊 Resumen de Usuarios</h3>
                        <p><strong>Total de usuarios:</strong> ''' + str(len(usuarios)) + '''</p>
                        <p><strong>Administradores:</strong> ''' + str(len([u for u in usuarios if u.rol == 'admin'])) + '''</p>
                        <p><strong>Usuarios regulares:</strong> ''' + str(len([u for u in usuarios if u.rol == 'user'])) + '''</p>
                    </div>
                </div>
            </body>
            </html>
            '''
            
            return html_response
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
        
        # Verificar si existe la tabla 'usuarios'
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

# Ruta para listar usuarios (solo admin)
@app.route('/usuarios')
@admin_required
def listar_usuarios():
    usuarios = User.query.all()
    return jsonify([{
        'id': u.id,
        'username': u.username,
        'rol': u.rol
    } for u in usuarios])

# Inicializar base de datos automáticamente al arrancar
print("=" * 60)
print("🚀 INICIANDO CURIMINING - SISTEMA DE GESTIÓN MINERA")
print("=" * 60)
print("👥 USUARIOS A CREAR:")
print("-" * 60)
print("👑 ADMINISTRADORES (4):")
print("  • MINERA.ADMIN")
print("  • ANDRES")
print("  • RICARDO")
print("  • ALEJANDRO")
print()
print("👥 USUARIOS REGULARES (5):")
print("  • Minera1")
print("  • Minera2")
print("  • Minera3")
print("  • Minera4")
print("  • Minera5")
print("=" * 60)

# Intentar inicializar la base de datos
with app.app_context():
    print("🔄 Intentando inicializar base de datos...")
    if initialize_database():
        print("✅ Base de datos inicializada con éxito")
        print("✅ Todos los usuarios creados correctamente")
    else:
        print("⚠️  No se pudo inicializar la base de datos automáticamente")
        print("ℹ️  Visita /init-db para inicializar manualmente")

# Solo para ejecución local
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"🌐 Servidor ejecutándose en: http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
