from flask import Flask
from flask_login import LoginManager
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from dotenv import load_dotenv
from app.models import db, User, Admin as AdminModel, Message, Contribution, Event
from config import Config

login_manager = LoginManager()
admin = Admin(name='Birthday App Admin', template_mode='bootstrap4')

@login_manager.user_loader
def load_user(user_id):
    return AdminModel.query.get(int(user_id))

def create_app(config_class=Config):
    app = Flask(__name__)
    load_dotenv() 
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    admin.init_app(app)
    
    # Set up login configuration
    login_manager.login_view = 'admin_panel.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Register blueprints
    from app.routes.user_routes import user_bp
    from app.routes.admin_routes import admin_bp
    
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # Set up admin views
    from flask_login import current_user
    
    class SecureModelView(ModelView):
        def is_accessible(self):
            return current_user.is_authenticated
    
    # Provide explicit endpoint names to avoid naming conflicts with blueprints
    admin.add_view(SecureModelView(User, db.session, name='Users', endpoint='admin_users'))
    admin.add_view(SecureModelView(Message, db.session, name='Messages', endpoint='admin_messages'))
    admin.add_view(SecureModelView(Contribution, db.session, name='Contributions', endpoint='admin_contributions'))
    admin.add_view(SecureModelView(Event, db.session, name='Events', endpoint='admin_events'))
    
    # Create database tables
    with app.app_context():
        db.create_all()
        # Create admin user if doesn't exist
        if not AdminModel.query.filter_by(username=app.config['ADMIN_USERNAME']).first():
            admin_user = AdminModel(
                username=app.config['ADMIN_USERNAME']
            )
            admin_user.set_password(app.config['ADMIN_PASSWORD'])
            db.session.add(admin_user)
            db.session.commit()
    
    return app