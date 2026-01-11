from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-this')

# Configuración de base de datos - Versión robusta
def get_database_url():
    # Probar diferentes nombres de variables
    for env_var in ['DATABASE_URL', 'POSTGRESQL_URL', 'PG_URL', 'POSTGRES_URL']:
        db_url = os.environ.get(env_var)
        if db_url:
            if db_url.startswith('postgres://'):
                db_url = db_url.replace('postgres://', 'postgresql://', 1)
            return db_url
    
    # Fallback para desarrollo
    print("ADVERTENCIA: Usando SQLite local (modo desarrollo)")
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

# Ruta de prueba simple
@app.route('/')
def index():
    port = os.environ.get('PORT', 'No configurado')
    db_url = app.config['SQLALCHEMY_DATABASE_URI']
    return f'''
    <h1>Aplicación Flask en Railway</h1>
    <p>Puerto: {port}</p>
    <p>Base de datos: {db_url[:50]}...</p>
    <p><a href="/login">Ir al login</a></p>
    <p><a href="/health">Verificar salud</a></p>
    <p><a href="/init-db">Inicializar BD</a></p>
    '''

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
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
            <h1>Base de datos inicializada</h1>
            <p>Usuario admin creado:</p>
            <p><strong>Usuario:</strong> admin</p>
            <p><strong>Contraseña:</strong> admin123</p>
            <p><a href="/login">Ir al login</a></p>
            <p><strong>ADVERTENCIA:</strong> Cambia esta contraseña inmediatamente.</p>
            '''
        return 'Base de datos ya inicializada. <a href="/login">Ir al login</a>'
    except Exception as e:
        return f'Error: {str(e)}'

# Ruta de verificación
@app.route('/health')
def health():
    try:
        db.session.execute('SELECT 1')
        db_status = 'ok'
    except:
        db_status = 'error'
    
    return jsonify({
        'status': 'ok',
        'port': os.environ.get('PORT', 'No configurado'),
        'database': db_status,
        'python_version': os.sys.version.split()[0]
    })

# Inicializar base de datos al inicio
@app.before_first_request
def initialize_database():
    try:
        db.create_all()
        # Crear admin si no existe
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', rol='admin')
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            print("Base de datos inicializada - admin creado")
    except Exception as e:
        print(f"Error inicializando BD: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Iniciando aplicación en puerto {port}")
    print(f"🔗 URL de BD: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
    app.run(host='0.0.0.0', port=port, debug=False)
