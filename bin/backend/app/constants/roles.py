class Roles:
    ADMIN = "admin"
    USER = "user"

    HR = "hr"
    TECHNICAL = "technical_admin"
    ALL = [ADMIN, USER, HR, TECHNICAL]
    WEB_LOGIN = {ADMIN, HR, TECHNICAL}
    REGISTRATION_ONLY_MESSAGE = 'Medewerkers hebben geen toegang tot Qtime. Je registraties worden wel bijgehouden; neem voor inzage contact op met HR.'
