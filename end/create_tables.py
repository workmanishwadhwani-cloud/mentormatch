"""
Create all database tables using SQLAlchemy's create_all().
Use this in development to initialize schema when migrations are not setup.
"""
from app import create_app, db
from config import Config


def main():
    app = create_app(Config)
    with app.app_context():
        print("Creating database tables for:", app.config['SQLALCHEMY_DATABASE_URI'])
        db.create_all()
        print("Done: created tables (if not present)")


if __name__ == '__main__':
    main()
