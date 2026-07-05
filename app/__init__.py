import os
from flask import Flask, render_template
from config import config_map
from app.extensions import db, login_manager, migrate, mail, csrf, limiter


def create_app(config_name=None):
    config_name = config_name or os.environ.get('FLASK_CONFIG', 'development')
    app = Flask(__name__)
    app.config.from_object(config_map.get(config_name, config_map['default']))

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Init extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.auth.routes import auth_bp
    from app.admin.routes import admin_bp
    from app.faculty.routes import faculty_bp
    from app.student.routes import student_bp
    from app.parent.routes import parent_bp
    from app.api.routes import api_bp
    from app.main.routes import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(faculty_bp, url_prefix='/faculty')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(parent_bp, url_prefix='/parent')
    app.register_blueprint(api_bp, url_prefix='/api')

    # Exempt REST API from CSRF (uses session auth already; JSON POSTs)
    csrf.exempt(api_bp)

    # Error handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # Template context: unread notifications count
    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        from app.models import Notification
        unread_count = 0
        if current_user.is_authenticated:
            unread_count = Notification.query.filter_by(
                user_id=current_user.id, is_read=False
            ).count()
        return dict(unread_notifications=unread_count)

    return app
