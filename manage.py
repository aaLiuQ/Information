from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import redis
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)


class Config(object):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "mysql://root:mysql@47.102.102.179:3306/information"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REDIS_HOST = "47.102.102.179"
    REDIS_PORT = 6379


app.config.from_object(Config)
db = SQLAlchemy(app)
redis_store = redis.StrictRedis(host=Config.REDIS_HOST, port=Config.REDIS_PORT)
CSRFProtect(app)


@app.route('/index')
def index():
    return 'index'


if __name__ == '__main__':
    app.run(port=5000, host='0.0.0.0')
    # port=8888, host='0.0.0.0'
