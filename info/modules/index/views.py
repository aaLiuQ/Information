from . import index_blu
from flask import render_template, current_app, session, jsonify, request

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


# 新闻列表
@index_blu.route('/news_list')
def get_news_list():
    args_list = request.args
    page = args_list.get('p', '1')
    per_page = args_list.get('per_page', constants.HOME_PAGE_MAX_NEWS)
    category_id = args_list.get('cid', 1)
    try:
        page = int(page)
        per_page = int(per_page)
    except Exception as e:
        current_app.logger.eror(e)
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')
    filtes = []
    if category_id != "1":
        filtes.append(News.category_id == category_id)
    try:
        paginate = News.query.filter(*filtes).order_by(News.create_time.desc()).paginate(page, per_page, False)
        items = paginate.items
        total_page = paginate.pages
        current_page = paginate.page
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='数据查询失败')

    news_list = []
    for news in items:
        news_list.append(news.to_basic_dict())

    return jsonify(errno=RET.OK, errmsg="OK", totalPage=total_page, currentPage=current_page, newsList=news_list,
                   cid=category_id)
