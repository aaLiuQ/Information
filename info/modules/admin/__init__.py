from flask import Blueprint, redirect, url_for

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

from .views import *


# 判断是否是管理员
@admin_bp.before_request
def is_admin():
    user_id = session.get("user_id")
    is_admin = session.get("is_admin", False)
    if request.url.endswith("/admin/login"):
        pass
    else:
        if not user_id and is_admin == False:
            return render_template(url_for("index.index"))
        else:
            pass
