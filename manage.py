from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand

from info import db, create_app

# 创建 app，并传入配置模式：development / production
app = create_app('development')

manager = Manager(app)
Migrate(app, db)
manager.add_command('db', MigrateCommand)


@app.route('/index')
def index():
    return 'index'


if __name__ == '__main__':
    app.run(port=5000, host='0.0.0.0')
    # port=8888, host='0.0.0.0'
