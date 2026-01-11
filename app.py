from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import sys
from functools import wraps

app = Flask(__name__)

# Configuración
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Configuración de base de datos - Versión robusta
def get_database_url():
    # Probar diferentes nombres de variables
    for env_var in ['DATABASE_URL', 'POSTGRESQL_URL', 'PG_URL', 'POSTGRES_URL']:
        db_url = os.environ.get(env_var)
        if db_url:
            print(f"📦 Encontrada variable {env_var}: {db_url[:50]}...")
            if db_url.startswith('postgres://'):
                db_url = db_url.replace('postgres://', 'postgresql://', 1)
            return db_url
    
    # Fallback para desarrollo
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

# Ruta para inicializar la base de datos
@app.route('/init-db')
def init_db():
    try:
        db.create_all()
        
        # Crear usuario admin si no existe
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', rol='admin')
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            return '''
            <h1>✅ Base de datos inicializada</h1>
            <p><strong>Usuario admin creado:</strong></p>
            <ul>
                <li><strong>Usuario:</strong> admin</li>
                <li><strong>Contraseña:</strong> admin123</li>
            </ul>
            <p><a href="/login">Ir al login</a></p>
            <p style="color: red;"><strong>⚠️ ADVERTENCIA:</strong> Cambia esta contraseña inmediatamente.</p>
            '''
        return '✅ Base de datos ya inicializada. <a href="/login">Ir al login</a>'
    except Exception as e:
        return f'❌ Error: {str(e)}'

# Ruta para verificar estado
@app.route('/check')
def check():
    try:
        # Intentar consultar la base de datos
        user_count = User.query.count()
        return jsonify({
            'status': 'ok',
            'port': os.environ.get('PORT', 'No configurado'),
            'python_version': sys.version,
            'database': 'conectada',
            'user_count': user_count
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'port': os.environ.get('PORT', 'No configurado'),
            'python_version': sys.version,
            'database': 'error',
            'error': str(e)
        })

# Inicializar base de datos cuando se inicia la aplicación
def init_database():
    try:
        with app.app_context():
            db.create_all()
            # Crear admin si no existe
            if not User.query.filter_by(username='admin').first():
                admin_user = User(username='admin', rol='admin')
                admin_user.set_password('admin123')
                db.session.add(admin_user)
                db.session.commit()
                print("✅ Base de datos inicializada - admin creado")
    except Exception as e:
        print(f"❌ Error inicializando BD: {e}")

# Solo para ejecución local
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    print("=" * 50)
    print(f"🚀 Iniciando aplicación Flask")
    print(f"📊 Puerto: {port}")
    print(f"🐍 Python: {sys.version}")
    print("=" * 50)
    
    # Inicializar base de datos
    init_database()
    
    app.run(host='0.0.0.0', port=port, debug=False)
