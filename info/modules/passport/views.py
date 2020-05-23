from . import passport_bp
from flask import request, abort, make_response, jsonify, current_app, session


from info import redis_store, constants, db
from info.response_code import RET
import re
import random
from datetime import datetime

from info.models import User
from info.lib.yuntongxun.sms import CCP


# 192.168.163.141：5000/passport/image_code?code_id=UUID编号
# 生成图片验证码后端接口
@passport_bp.route('/image_code')
def get_image_code():
    # 获取参数code_id UUID唯一编号
    code_id = request.args.get("code_id")
    # 校验，是否为空
    if not code_id:
        return abort(404)
    # 调用工具类中的captcha生成图形验证码图片,验证码图片名字，有效性，二进制文件
    from utils.captcha.captcha import captcha
    image_name, real_image_code, image_data = captcha.generate_captcha()
    # 以code_id作为key作为存储图形验证码的真实性，存储到redis
    redis_store.setex('imageCode_%s' % code_id, constants.IMAGE_CODE_REDIS_EXPIRES, real_image_code)
    # 返回图片数据
    response = make_response(image_data)
    # 注意：如果不设置响应数据格式，返回的就是普通文件数据，不能兼容所有浏览器
    response.headers["Content-Type"] = "png/image"
    return response


# 发送短信验证码的后端接口
@passport_bp.route('/sms_code', methods=["post"])
def send_sms_code():
    """
    /passport/sms_code
    传入参数：JSON格式:mobile,image_code,image_code_id(uuid)
    :return:errno,errmsg
    """
    param_dict = request.json
    mobile = param_dict.get("mobile")
    image_code = param_dict.get("image_code")
    image_code_id = param_dict.get("image_code_id")
    # 非空判断
    if not all([mobile, image_code, image_code_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")
    if not re.match(r'1[3-9]\d{9}', mobile):
        return jsonify(errno=RET.PARAMERR, errmsg="手机号码格式错误")
    # 根据image_code_id去redis中获取图形验证码的值
    try:
        real_image_code = redis_store.get("imageCode_%s" % image_code_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据异常")
    # 图形验证码有值，将值删除，避免多次重复验证
    if real_image_code:
        redis_store.delete("imageCode_%s" % image_code_id)
    else:
        # 没有值即代表过期
        return jsonify(errno=RET.NODATA, errmsg="图形验证码过期")
    # 将图片验证码进行对比
    if image_code.lower() != real_image_code.lower():
        return jsonify(errno=RET.DATAERR, errmsg="图片验证码输入错误")
    # 图片验证码输入正确，数据库查询电话号码有没有被注册过
    try:
        user = User.query.filter(User.mobile == mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="数据库查询异常")
    if user:
        return jsonify(errno=RET.DATAEXIST, errmsg="此号码已经注册过")
    # 发送短信
    # 生成随机的六位数
    real_sms_code = random.randint(0, 999999)
    real_sms_code = "%6d" % real_sms_code
    print(real_sms_code)
    # 调用CCP类发送短信验证码
    ccp = CCP()
    try:
        result = ccp.send_template_sms(mobile, [real_sms_code, constants.SMS_CODE_REDIS_EXPIRES / 60], 1)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="云通信发送短信验证码异常")

    if result == -1:
        return jsonify(errno=RET.THIRDERR, errmsg="云通信发送短信验证码异常")
    # 将短信验证码保存到数据库以备后续
    try:
        redis_store.setex("SMS_%s" % mobile, constants.SMS_CODE_REDIS_EXPIRES, real_sms_code)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="保存短信验证码值异常")

    # 4.1 发送短信验证码成功
    return jsonify(errno=RET.OK, errmsg="发送短信验证码成功")


# 用户注册
@passport_bp.route('/register', methods=["post"])
def register():
    """
    url:/passport/register
    传入参数：mobile,smscode,password
    :return:errno,errmsg
    """
    param_dict = request.json
    mobile = param_dict.get("mobile")
    sms_code = param_dict.get("sms_code")
    password = param_dict.get("password")
    if not all([mobile, sms_code, password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")
    if not re.match(r'1[3-9]\d{9}', mobile):
        return jsonify(errno=RET.PARAMERR, errmsg="电话号码格式错误")
    # 拿手机号码前去redis获取短信验证码
    try:
        real_sms_code = redis_store.get("SMS_%s" % mobile)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="查询短信验证码异常")
    # 有值，删除短信验证码
    if real_sms_code:
        redis_store.delete("SMS_%s" % mobile)
    else:
        return jsonify(errno=RET.NODATA, errmsg="短信验证码过期了")
    # 验证短信验证码
    if sms_code.lower() != real_sms_code.lower():
        return jsonify(errno=RET.DATAERR, errmsg="短信验证码有误")
    # 注册，创建用户对象
    user = User()
    user.nick_name = mobile
    user.mobile = mobile
    user.password = password
    user.last_login = datetime.now()
    # 保存到数据库
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="数据库保存异常")
    # 注册成功，及代表登陆成功,使用session保存用户信息
    session["nick_name"] = user.nick_name
    session["mobile"] = user.mobile
    session["user_id"] = user.id

    return jsonify(errno=RET.OK, errmsg="注册成功")


# 用户登陆
@passport_bp.route('/login', methods=["post"])
def login():
    """
    mobile,password
    :return:
    """
    param_dict = request.json
    mobile = param_dict.get("mobile")
    password = param_dict.get("password")
    if not all([mobile, password]):
        return jsonify(errno=RET.NODATA, errmsg="参数不足")
    # 根据手机号码查询用户对象
    try:
        user = User.query.filter(User.mobile == mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库异常")
    if not user:
        return jsonify(errno=RET.USERERR, errmsg="用户不存在")
    # 用户存在，校验密码
    if not user.check_password(password):
        return jsonify(errno=RET.DATAERR, errmsg="密码错误")
    user.last_login = datetime.now()
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="数据库保存异常")
    # 注册成功，及代表登陆成功,使用session保存用户信息
    session["nick_name"] = user.nick_name
    session["mobile"] = user.mobile
    session["user_id"] = user.id

    return jsonify(errno=RET.OK, errmsg="登陆成功")


# 退出登陆
@passport_bp.route('/login_out', methods=["post"])
def login_out():
    """
    删除session中的用户信息
    :return:
    """
    session.pop("user_id", None)
    session.pop("mobile", None)
    session.pop("nick_name", None)
    session.pop('is_admin', None)
    return jsonify(errno=RET.OK, errmsg="退出登陆成功")