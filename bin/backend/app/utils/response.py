from flask import jsonify


def success_response(data=None, message="Success", status_code=200):
    return jsonify({
        "success": True,
        "message": message,
        "data": data
    }), status_code


def error_response(message="Error", status_code=400):
    return jsonify({
        "success": False,
        "error": message
    }), status_code