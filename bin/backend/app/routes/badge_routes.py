from flask import Blueprint, request
from app.decorators.internal_request import is_trusted_internal_request
from app.hr.routes import HR_ROLES, principal, require
from app.hr.service import HRError


def register_badge_routes(service,prefix):
    bp=Blueprint('badges',__name__)
    @bp.route(prefix+'/badges/',methods=['GET'])
    @require()
    def listing():return service.get_badges(request.args)
    @bp.route(prefix+'/badges/<badge_id>',methods=['GET'])
    @require()
    def detail(badge_id):return service.get_badge_by_id(badge_id)
    @bp.route(prefix+'/badges/',methods=['POST'])
    def create():
        if not is_trusted_internal_request():
            actor=principal()
            if actor['role'] not in HR_ROLES:raise HRError('Vraag een correctie aan via Mijn uren.',403)
            raise HRError('Gebruik Registratie aanvullen met een verplichte reden in het HR-scherm.',409)
        return service.create_badge_log(request.get_json() or {})
    @bp.route(prefix+'/badges/<badge_id>',methods=['PUT','DELETE'])
    @require(*HR_ROLES)
    def immutable(badge_id):raise HRError('Bronregistraties blijven bewaard. Gebruik een HR-correctie met reden.',409)
    @bp.route(prefix+'/badges/bulk/mark-processed',methods=['POST'])
    @require(*HR_ROLES)
    def processed():raise HRError('Gebruik de goedkeuring van een medewerkerperiode.',409)
    return bp
