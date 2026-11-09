from flask import Blueprint, jsonify, request
from app.hr.routes import require, TECH_ROLES, principal
from app.hr.service import HRError, clean
from .bridge import SyncError, MESSAGES


def routes(service,prefix):
    bp=Blueprint('loxone_sync',__name__,url_prefix=prefix+'/loxone-sync')
    @bp.after_request
    def no_cache(response):response.headers['Cache-Control']='no-store';return response
    @bp.errorhandler(SyncError)
    def sync_error(exc):return jsonify(success=False,error=MESSAGES.get(exc.code,MESSAGES['response']),code=exc.code),503
    @bp.errorhandler(ValueError)
    @bp.errorhandler(KeyError)
    @bp.errorhandler(TypeError)
    def invalid(exc):return jsonify(success=False,error='Controleer de verplichte instellingen en veldtoewijzingen.'),400
    def reply(value,status=200):return jsonify(success=True,data=clean(value)),status
    def payload():
        value=request.get_json(silent=True)
        if not isinstance(value,dict):raise HRError('Verstuur een geldig instellingenobject.')
        return value
    @bp.route('/config')
    @require(*TECH_ROLES)
    def config():return reply(service.config())
    @bp.route('/config',methods=['POST'])
    @require(*TECH_ROLES)
    def save():return reply(service.save(payload(),principal()['username']))
    @bp.route('/miniservers')
    @require(*TECH_ROLES)
    def miniservers():return reply(service.bridge.call('miniservers'))
    @bp.route('/test',methods=['POST'])
    @require(*TECH_ROLES)
    def test():return reply(service.probe(payload()['slot']))
    @bp.route('/users')
    @require(*TECH_ROLES)
    def users():return reply(service.remote_users())
    @bp.route('/links',methods=['POST'])
    @require(*TECH_ROLES)
    def link():return reply(service.link(payload(),principal()['username']))
    @bp.route('/preview',methods=['POST'])
    @require(*TECH_ROLES)
    def preview():return reply(service.preview())
    @bp.route('/diagnostics')
    @require(*TECH_ROLES)
    def diagnostics():return reply(service.preview(remote=False))
    @bp.route('/run',methods=['POST'])
    @require(*TECH_ROLES)
    def run():return reply(service.request_sync(principal()['username']),202)
    return bp
