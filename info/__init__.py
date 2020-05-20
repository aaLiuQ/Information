from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import redis
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_session import Session
import logging
from logging.handlers import RotatingFileHandler

from info.utils.common import do_index_class
from config import config

# 配置数据库
db = SQLAlchemy()
# 配置redis
redis_store = None


def create_app(config_name):
    """通过传入不同的配置名字，初始化其对应配置的应用实例"""
    setup_log(config_name)
    app = Flask(__name__)

    # 配置
    app.config.from_object(config[config_name])
    # 配置数据库
    db.init_app(app)
    # 配置redis
    global redis_store
    redis_store = redis.StrictRedis(host=config[config_name].REDIS_HOST, port=config[config_name].REDIS_PORT,
                                    decode_responses=True)
    # 开启csrf保护
    # CSRFProtect(app)
    #
    # @app.after_request
    # def set_csrf_token(response):
    #     """补充csrf_token的逻辑"""
    #
    #     # 1.生成csrf_token随机值
    #     csrf_token = generate_csrf()
    #     # 2.获取响应对象，统一设置csrf_token值到cookie中
    #     response.set_cookie("csrf_token", csrf_token)
    #     # 3.返回响应对象
    #     return response

    # 通过app对象将函数添加到系统过滤器中
    app.add_template_filter(do_index_class, "ranklist_class")

    # 设置session保存位置
    Session(app)

    # 注册蓝图
    from info.modules.index import index_blu
    app.register_blueprint(index_blu)
    # 验证码
    from info.modules.passport import passport_blu
    app.register_blueprint(passport_blu)

    return app


def setup_log(config_name):
    """配置日志"""

    # 设置日志的记录等级
    logging.basicConfig(level=config[config_name].LOG_LEVEL)  # 调试debug级
    # 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小、保存的日志文件个数上限
    file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024 * 1024 * 100, backupCount=10)
    # 创建日志记录的格式 日志等级 输入日志信息的文件名 行数 日志信息
    formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')
    # 为刚创建的日志记录器设置日志记录格式
    file_log_handler.setFormatter(formatter)
    # 为全局的日志工具对象（flask app使用的）添加日志记录器
    logging.getLogger().addHandler(file_log_handler)
