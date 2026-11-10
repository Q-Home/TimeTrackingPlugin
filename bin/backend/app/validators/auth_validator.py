from app.utils.response import error_response


class AuthValidator:
    @staticmethod
    def validate_login(data):
        if not isinstance(data,dict):return error_response('Vul een gebruikersnaam en wachtwoord in.',400)
        username = data.get("username")
        password = data.get("password")

        if not isinstance(username,str) or not isinstance(password,str) or not username.strip() or not password:
            return error_response("Username and password are required", 400)

        return None
