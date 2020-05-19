from flask import current_app, jsonify
from flask import make_response
from flask import request, session
import re
import random

from . import passport_blu
from info import constants, redis_store, db
from info.utils.captcha.captcha import captcha
from info.utils.response_code import RET
from info.models import User
from info.lib.yuntongxun.sms import CCP


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


@passport_blu.route('/sms_code', methods=["post"])
def send_sms():
    """
       1. 接收参数并判断是否有值
       2. 校验手机号是正确
       3. 通过传入的图片编码去redis中查询真实的图片验证码内容
       4. 进行验证码内容的比对
       5. 生成发送短信的内容并发送短信
       6. redis中保存短信验证码内容
       7. 返回发送成功的响应
       :return:
    """
    param_dict = request.json
    mobile = param_dict.get('mobile')
    image_code = param_dict.get('image_code')
    image_code_id = param_dict.get('image_code_id')
    # print(image_code_id)
    if not all([mobile, image_code, image_code_id]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不全')
    if not re.match("^1[3578][0-9]{9}$", mobile):
        return jsonify(errno=RET.DATAERR, errmsg='手机号不正确')
    try:
        real_image_code = redis_store.get('ImageCode_' + image_code_id)
        if real_image_code:
            real_image_code = real_image_code.decode()
            redis_store.delete('ImageCode_' + image_code_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='获取图片验证码失败')
    if not real_image_code:
        return jsonify(errno=RET.NODATA, errmsg='图片验证码过期')
    if image_code.lower() != real_image_code.lower():
        return jsonify(errno=RET.DBERR, errmsg='验证码输入错误')
    # print('验证码正确')
    try:
        user = User.query.filter(User.mobile == mobile).first()
        print('user:{}'.format(user))
    except Exception as e:
        # print(e)
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='数据库查询错误')
    if user:
        return jsonify(errno=RET.DATAEXIST, errmsg='该手机号已注册')
    result = random.randint(0, 999999)
    sms_code = '%06d' % result
    current_app.logger.debug('短信验证码内容：{}'.format(sms_code))
    result = CCP().send_template_sms(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES / 60], "1")
    if result != 0:
        return jsonify(errno=RET.THIRDERR, errmsg='发送短信失败')
    try:
        redis_store.set("SMS_" + mobile, sms_code, constants.SMS_CODE_REDIS_EXPIRES)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='保存短信验证码失败')
    return jsonify(errno=RET.OK, errmsg='发送成功')


@passport_blu.route('/register', methods=['POST'])
def register():
    """
        1. 获取参数和判断是否有值
        2. 从redis中获取指定手机号对应的短信验证码的
        3. 校验验证码
        4. 初始化 user 模型，并设置数据并添加到数据库
        5. 保存当前用户的状态
        6. 返回注册的结果
        :return:
    """
    json_data = request.json
    mobile = json_data.get('mobile')
    sms_code = json_data.get('sms_code')
    password = json_data.get('password')
    if not all([mobile, sms_code, password]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不齐')
    try:
        real_sms_code = redis_store.get("SMS_" + mobile)
    except Exception as e:
        current_app.logger.error(e)
        # 获取本地验证码失败
        return jsonify(errno=RET.DBERR, errmsg="获取本地验证码失败")
    if not real_sms_code:
        return jsonify(errno=RET.NODATA, errmsg='短信验证码过期')
    if sms_code != real_sms_code:
        return jsonify(errno=RET.DATAERR, errmsg='验证码错误')
    try:
        redis_store.delete("SMS_" + mobile)
    except Exception as e:
        current_app.logger.error(e)
    user = User()
    user.nick_name = mobile
    user.mobile = mobile
    user.password = password
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg='数据保存错误')
    session['user_id'] = user.id
    session["nick_name"] = user.nick_name
    session["mobile"] = user.mobile

    # 6. 返回注册结果
    return jsonify(errno=RET.OK, errmsg="OK")
