from flask import current_app, render_template, session, jsonify, request, g
from info.modules.index import index_bp
from info import redis_store
# 注意：需要在别的文件中导入models中的类，让项目和models有关联
from info.models import User, News, Category
from info import constants

# 2.使用蓝图对象装饰视图函数
# 127.0.0.1:5000/ --> 项目首页
from info.response_code import RET


# 127.0.0.1：5000/news_list?cid=1&p=当前页码&per_page=每一页多少条数据
from info.utils.common import get_user_info


# 获取新闻列表数据
@index_bp.route("/news_list")
def get_news_list():
    """
    URL：/news_list
    cid	        string	是	分类id
    page	    int	    否	页数，不传即获取第1页
    per_page	int	    否	每页多少条数据，如果不传，默认10条
    :return:
    """
    cid = request.args.get("cid")
    p = request.args.get("p", 1)
    per_page = request.args.get("per_page", 10)
    if not cid:
        return jsonify(errng=RET.PARAMERR, merssg="参数不足")
    # 2.2 将参数进行int强制类型转换
    try:
        cid = int(cid)
        p = int(p)
        per_page = int(per_page)
    except Exception as e:
        p = 1
        per_page = 10
        current_app.logger.error(e)

    # 给参数默认值
    news_list = []
    current_page = 1
    total_page = 1
    # 当cid=1时，代表的时最新的新闻数据
    filter_list = [News.status == 0]
    if cid != 1:
        # paginate:分页器（当前页数，多少条数据，出错不打印）
        # paginate = News.query.filter().order_by(News.create_time.desc()).paginate(p, per_page, False)
        # sqlalchemy底层重写了__eq__方法 ==返回的是查询条件
        filter_list.append(News.category_id == cid)
    try:
        paginate = News.query.filter(*filter_list).order_by(News.create_time.desc()).paginate(p, per_page, False)
        # paginate = News.query.filter(*filter_list).order_by(News.create_time.desc()).paginate(p, per_page, False)
        # 提取当前页码所有数据：
        news_list = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询失败")
    news_dict_list = []
    for news in news_list if news_list else []:
        news_dict_list.append(news.to_dict())
    data = {
        "news_list": news_dict_list,
        "current_page": current_page,
        "total_page": total_page
    }

    return jsonify(errno=RET.OK, errmsg="成功", data=data)


# 需要去app中注册蓝图
# 展示新闻首页
@index_bp.route('/')
@get_user_info
def index():
    user = g.user
    # 3.将用户对象转换成字典
    # if user:
    #     user_dict = user.to_dict()
    user_dict = user.to_dict() if user else None
    # TODO 点击排行展示
    try:
        # 降序排序，限制六条
        news_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库查询失败")
    newsrank_dict_list = []
    for news in news_list if news_list else []:
        newsrank_dict_list.append(news.to_dict())

    # TODO 新闻分类展示
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
        "user_info": user_dict,
        "click_news_list": newsrank_dict_list,
        "categories": category_dict_list
    }
    return render_template("news/index.html", data=data)


# 这个函数是浏览器自己调用的方法，返回的是网站的图标
# 内部用来发送静态文件到浏览器的方法： send_static_file
@index_bp.route('/favicon.ico')
def get_faviconico():
    """返回网站的图标"""
    """
    Function used internally to send static files from the static
        folder to the browser
    内部用来发送静态文件到浏览器的方法： send_static_file
    """
    return current_app.send_static_file("news/favicon.ico")



