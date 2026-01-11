from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuración de PostgreSQL para Railway - Versión robusta
def get_database_url():
    # Intentar diferentes nombres de variables de entorno comunes en Railway
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        db_url = os.environ.get('POSTGRESQL_URL')
    if not db_url:
        db_url = os.environ.get('PG_URL')
    if not db_url:
        db_url = os.environ.get('POSTGRES_URL')
    
    # Si no hay URL de PostgreSQL, usar SQLite para desarrollo
    if not db_url:
        print("ADVERTENCIA: No se encontró DATABASE_URL. Usando SQLite para desarrollo.")
        return 'sqlite:///app.db'
    
    # Asegurar que la URL use postgresql:// en lugar de postgres://
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    
    return db_url

app.config['SQLALCHEMY_DATABASE_URI'] = get_database_url()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True,
}

db = SQLAlchemy(app)

# Modelos de base de datos
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    rol = db.Column(db.String(20), nullable=False, default='user')
    
    def set_password(self, password):
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password, password)

# Decorador para requerir login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Decorador para requerir rol admin
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

@app.route('/')
def index():
    return redirect(url_for('login'))

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
    if session.get('rol') == 'admin':
        return redirect(url_for('admin'))
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

# API para verificar login (para usar en JS)
@app.route('/api/check-auth')
def check_auth():
    if 'user_id' in session:
        return jsonify({
            'authenticated': True,
            'username': session.get('username'),
            'rol': session.get('rol')
        })
    return jsonify({'authenticated': False})

# Ruta para crear usuario admin inicial
@app.route('/create-admin')
def create_admin():
    try:
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', rol='admin')
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            return f'Admin creado: usuario=admin, contraseña=admin123<br>Usando DB: {app.config["SQLALCHEMY_DATABASE_URI"][:50]}...'
        return 'Admin ya existe'
    except Exception as e:
        return f'Error creando admin: {str(e)}'

# Ruta para verificar conexión a DB
@app.route('/db-status')
def db_status():
    try:
        # Intentar contar usuarios para verificar conexión
        count = User.query.count()
        return jsonify({
            'status': 'ok',
            'database_url': app.config['SQLALCHEMY_DATABASE_URI'][:100] + '...' if len(app.config['SQLALCHEMY_DATABASE_URI']) > 100 else app.config['SQLALCHEMY_DATABASE_URI'],
            'user_count': count,
            'message': 'Conexión exitosa a la base de datos'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'database_url': app.config['SQLALCHEMY_DATABASE_URI'],
            'message': f'Error de conexión: {str(e)}'
        }), 500

def create_tables():
    """Crear tablas si no existen"""
    with app.app_context():
        try:
            db.create_all()
            print("Tablas creadas exitosamente")
            
            # Crear usuario admin si no existe
            if not User.query.filter_by(username='admin').first():
                admin_user = User(username='admin', rol='admin')
                admin_user.set_password('admin123')
                db.session.add(admin_user)
                db.session.commit()
                print("Usuario admin creado: admin/admin123")
        except Exception as e:
            print(f"Error creando tablas: {e}")

if __name__ == '__main__':
    create_tables()
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting server on port {port}")
    print(f"Database URL: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
    app.run(debug=True, host='0.0.0.0', port=port)
