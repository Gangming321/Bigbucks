import functools
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash
from .database.db import get_db


bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin_code = request.form['admin_code']
        db = get_db()
        error = None

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'

        if admin_code == 'admin':
            admin_resgitration = 1
        else:   
            admin_resgitration = 0

        if error is None:
            try:
                db.execute(
                    "INSERT INTO user (username, password, balance, is_admin) VALUES (?, ?, ?, ?)",
                    (username, generate_password_hash(password), 1000000, admin_resgitration),
                )
                db.commit()
            except db.IntegrityError:
                error = f"User {username} is already registered."
            else:
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template('auth/register.html')


@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM user WHERE username = ?', (username,)
        ).fetchone()

        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            session['is_admin'] = user['is_admin']  # Store is_admin status in the session
            
            # Directly set g.admin based on the user's is_admin column
            g.admin = user['is_admin'] == 1
            
            if not g.admin:
                return redirect(url_for('homepage.index'))  # Ensure this is the correct endpoint for non-admin users
            else:
                return redirect(url_for('admin.admin'))  # Ensure this is the correct endpoint for admin users

        flash(error)

    return render_template('auth/login.html')


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    g.user = None
    g.admin = False  # Default to False

    if user_id is not None:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()
        # Use the is_admin value from the session instead of a new database query
        g.admin = session.get('is_admin', 0) == 1
          
        
@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            error = 'Login Required'
            flash(error)
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view


def admin_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        print(g.admin)
        if not g.admin:
            error = 'Admin Required'
            flash(error)
            return redirect(url_for('homepage.index'))
        return view(**kwargs)
    return wrapped_view

