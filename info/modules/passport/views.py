from flask import current_app, jsonify
from flask import make_response
from flask import request

from . import passport_blu
from info import constants, redis_store
from info.utils.captcha.captcha import captcha
from info.utils.response_code import RET


@passport_blu.route('/image_code')
def get_image_code():
    # 获取图片验证码
    code_id = request.args.get('code_id')
    name, text, image = captcha.generate_captcha()
    try:
        redis_store.setex('ImageCode_' + code_id, constants.IMAGE_CODE_REDIS_EXPIRES, text)
    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify(error=RET.DATAERR, errmsg='保存图片验证码失败'))
    resp = make_response(image)
    # 注意：如果不设置响应数据格式，返回的就是普通文件数据，不能兼容所有浏览器
    resp.headers['Content-Type'] = 'image/jpg'
    return resp
