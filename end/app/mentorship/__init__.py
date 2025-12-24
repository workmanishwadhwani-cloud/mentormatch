from flask import Blueprint

bp = Blueprint('mentorship', __name__, template_folder='templates')

from app.mentorship import routes
