from flask import Blueprint, request
from app.decorators.internal_request import is_trusted_internal_request
from app.hr.routes import HR_ROLES, TECH_ROLES, principal, require
from app.hr.service import HRError


def register_user_routes(service,prefix):
    bp=Blueprint('users',__name__)
    def manager(read=False):
        if is_trusted_internal_request():return True
        actor=principal()
        allowed=TECH_ROLES|HR_ROLES if read else TECH_ROLES
        if actor['role'] not in allowed:raise HRError('Geen rechten voor gebruikersbeheer.',403)
        return True
    @bp.route(prefix+'/users/',methods=['GET'])
    def users():manager(True);return service.get_users()
    @bp.route(prefix+'/users/',methods=['POST'])
    def create():manager();return service.create_user(request.get_json() or {})
    @bp.route(prefix+'/users/<username>',methods=['GET'])
    def get(username):
        if not is_trusted_internal_request():
            actor=principal()
            if actor['role'] not in TECH_ROLES|HR_ROLES and actor['username']!=username:raise HRError('Je kunt alleen je eigen profiel bekijken.',403)
        return service.get_user(username)
    @bp.route(prefix+'/users/<username>/block',methods=['PUT'])
    def block(username):manager();return service.block_user(username)
    @bp.route(prefix+'/users/<username>/unblock',methods=['PUT'])
    def unblock(username):manager();return service.unblock_user(username)
    @bp.route(prefix+'/users/<username>',methods=['DELETE'])
    def archive(username):manager();return service.delete_user(username)
    def owner(uid):
        if is_trusted_internal_request():return True
        actor=principal();target=service.user_repository.find_by_id(uid)
        if not target:raise HRError('Medewerker niet gevonden.',404)
        privileged=actor['role'] in TECH_ROLES
        if not privileged and str(target['_id'])!=actor['id']:raise HRError('Je kunt alleen je eigen profiel wijzigen.',403)
        return privileged
    @bp.route(prefix+'/users/<uid>',methods=['PUT'])
    def update(uid):return service.update_user_by_id(uid,request.get_json() or {},allow_privileged_fields=owner(uid))
    @bp.route(prefix+'/users/<uid>/password',methods=['PUT'])
    def password(uid):
        privileged=owner(uid)
        own=not is_trusted_internal_request() and principal()['id']==uid
        return service.update_password_by_id(uid,request.get_json() or {},require_current=own or not privileged)
    return bp
