from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuración de PostgreSQL para Railway
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', '').replace('postgres://', 'postgresql://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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

# Ruta para crear usuario admin inicial (solo en desarrollo)
@app.route('/create-admin')
def create_admin():
    if not User.query.filter_by(username='admin').first():
        admin_user = User(username='admin', rol='admin')
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        db.session.commit()
        return 'Admin creado: usuario=admin, contraseña=admin123'
    return 'Admin ya existe'

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
