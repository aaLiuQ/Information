from . import index_blu
from flask import render_template, current_app, session, jsonify

from info.models import User, News, Category
from info import constants
from info.utils.response_code import RET


@index_blu.route('/')
def index():
    # 获取到当前登录用户的id
    user_id = session.get("user_id")
    # 通过id获取用户信息
    user = None
    if user_id:
        try:
            user = User.query.get(user_id)
        except Exception as e:
            current_app.logger.error(e)

    # 获取点击排行数据
    news_list = None
    try:
        news_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)

    click_news_list = []
    for news in news_list if news_list else []:
        click_news_list.append(news.to_basic_dict())

    # 新闻分类
    try:
        categories = Category.query.all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")
    # 将新闻分类对象转换成列表
    category_dict_list = []
    for category in categories if categories else []:
        categorys = category.to_dict()
        category_dict_list.append(categorys)
    data = {
        "user_info": user.to_dict() if user else None,
        "click_news_list": click_news_list,
        "categories": category_dict_list
    }
    return render_template('news/index.html', data=data)


@index_blu.route('/favicon.ico')
def favicon():
    return current_app.send_static_file('news/favicon.ico')
