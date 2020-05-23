from flask import request, render_template, current_app, session, redirect, url_for, g, abort, jsonify
from info.models import User, News, Category
from info.response_code import RET
from info.utils.pic_store import pic_store
from . import admin_bp
from info.utils.common import get_user_info
import time
from datetime import datetime, timedelta
from info import constants, db


# 展示管理员登陆页面
@admin_bp.route("/login", methods=["GET", "POST"])
def admin_login():
    """
    判断请求，如果是GET请求，则获取已登陆用户信息，判断是否是管理员
    :return:
    """
    if request.method == "GET":
        # 通过session获取用户信息
        user_id = session.get("user_id")
        is_admin = session.get("is_admin", False)
        if user_id and is_admin == True:
            # 重定向，可以直接重定向到某个网址，也可以通过url_for方法重定向到某个函数
            #
            return redirect(url_for("admin.admin_index"))
        else:
            return render_template("admin/login.html")
    # POST 请求，判断账号密码是否正确
    username = request.form.get("username")
    password = request.form.get("password")
    if not all([username, password]):
        return render_template("admin/login.html", errmsg="参数不足")
    admin_user = None  # type: User
    # 查询用户是否存在
    try:
        admin_user = User.query.filter(User.mobile == username, User.is_admin == True).first()
    except Exception as e:
        current_app.logger.error(e)
        return render_template("admin/login.html", errmsg="查询用户异常")
    if not admin_user:
        return render_template("admin/login.html", errmsg="不是管理员")
    if not admin_user.check_password(password):
        return render_template("admin/login.html", errmsg="密码错误")
    session["user_id"] = admin_user.id
    session["nick_name"] = admin_user.nick_name
    session["mobile"] = admin_user.mobile
    session["is_admin"] = True
    return redirect(url_for("admin.admin_index"))


# 展示管理后台首页
@admin_bp.route("/index")
@get_user_info
def admin_index():
    user = g.user
    data = {
        "user_info": user.to_dict() if user else None
    }
    return render_template("admin/index.html", data=data)


# 展示用户统计数据
@admin_bp.route("/user_count")
def user_count():
    # 查询总人数
    total_count = 0
    try:
        total_count = User.query.filter(User.is_admin == False).count()
    except Exception as e:
        current_app.logger.error(e)

    # 查询月增用户
    mon_count = 0
    try:
        # 获取当前时间
        # time.struct_time(tm_year=2019, tm_mon=7, tm_mday=25, tm_hour=20, tm_min=6, tm_sec=14,
        # tm_wday=3, tm_yday=206, tm_isdst=0)
        now = time.localtime()
        mon_begin = '%d-%02d-01' % (now.tm_year, now.tm_mon)
        mon_begin_date = datetime.strptime(mon_begin, "%Y-%m-%d")
        # strptime(): 将字符串转换成时间格式
        mon_count = User.query.filter(User.create_time >= mon_begin_date, User.is_admin == False).count()
    except Exception as e:
        current_app.logger.error(e)

    # 日增用户
    day_count = 0
    try:
        day_begin = "%d-%02d-%02d" % (now.tm_year, now.tm_mon, now.tm_mday)
        day_begin_date = datetime.strptime(day_begin, "%Y-%m-%d")
        day_count = User.query.filter(User.is_admin == False, User.create_time > day_begin_date).count()
    except Exception as e:
        current_app.logger.error(e)
    # 获取到当天零时
    now_date = datetime.strptime(datetime.now().strftime("%Y-%m-%d"), "%Y-%m-%d")
    active_date = []
    active_count = []
    # 获取每一天的活跃数据
    for i in range(0, 31):
        begin_date = now_date - timedelta(days=i)
        end_date = begin_date + timedelta(days=1)
        active_date.append(begin_date.strftime("%Y-%m-%d"))
        count = 0
        try:
            count = User.query.filter(User.is_admin == False, User.last_login >= begin_date,
                                      User.last_login < end_date).count()
        except Exception as e:
            current_app.logger.error(e)
        active_count.append(count)
    # 将列表进行反转，因为是从当天开始加入
    active_count.reverse()
    active_date.reverse()
    data = {
        "total_count": total_count,
        "mon_count": mon_count,
        "day_count": day_count,
        "active_date": active_date,
        "active_count": active_count
    }
    return render_template('admin/user_count.html', data=data)


# 展示用户列表
@admin_bp.route("/user_list")
def user_list():
    p = request.args.get("p", 1)
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1
    user_list = []
    current_page = 1
    total_page = 1
    try:
        paginate = User.query.filter(User.is_admin == False).order_by(User.create_time.desc()).paginate(
            p, constants.ADMIN_USER_PAGE_MAX_COUNT, False
        )
        user_list = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
        return abort(404)
    user_dict_list = []
    for user in user_list if user_list else []:
        user_dict_list.append(user.to_dict())

    data = {
        "users": user_dict_list,
        "current_page": current_page,
        "total_page": total_page
    }
    # 5.返回模板
    return render_template("admin/user_list.html", data=data)


# 新闻审核页面
@admin_bp.route("/news_review")
def news_review():
    p = request.args.get("p", 1)
    # 搜索关键字
    keywords = request.args.get("keywords")
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1
    news_list = []
    current_page = 1
    total_page = 1
    # 自定义过滤条件
    filter_list = [News.status != 0]
    if keywords:
        filter_list.append(News.title.contains(keywords))
    try:
        paginate = News.query.filter(*filter_list).order_by(News.create_time.desc()).paginate(
            p, 10, False
        )
        news_list = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
        return abort(404)
    news_dict_list = []
    for news in news_list if news_list else []:
        news_dict_list.append(news.to_dict())
    data = {
        "news_list": news_dict_list,
        "current_page": current_page,
        "total_page": total_page
    }
    return render_template("admin/news_review.html", data=data)


# 新闻审核详情页面
@admin_bp.route("/news_review_detail", methods=["GET", "POST"])
def news_review_detail():
    if request.method == "GET":
        news_id = request.args.get("news_id")
        news = News  # type: News
        if news_id:
            try:
                news = News.query.get(news_id)
            except Exception as e:
                current_app.logger.error(e)
                abort(404)
        news_dict = news.to_dict() if news else None
        data = {
            "news": news_dict
        }
        return render_template("admin/news_review_detail.html", data=data)
    # POST 请求 news_id: 新闻id， action（accept通过,reject）: 审核的行为， reason:拒绝原因
    news_id = request.json.get("news_id")
    action = request.json.get("action")
    reason = request.json.get("reason")
    if not all([news_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")
    if action not in ["accept", "reject"]:
        return jsonify(errno=RET.NODATA, errmsg="参数错误")
    news = None
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询新闻对象异常")
    if not news:
        return jsonify(errno=RET.NODATA, errmsg="新闻对象不存在")
    # 判断审核结果
    if action == "accept":
        news.status = 0
    else:
        if reason:
            news.status = -1
            news.reason = reason
        else:
            return jsonify(errno=RET.PARAMERR, errmsg="请填写审核不通过原因")
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="查询用户对象异常")
    return jsonify(errno=RET.OK, errmsg="OK")


# 新闻版式页面展示
@admin_bp.route("/news_edit")
def news_edit():
    p = request.args.get("p", 1)
    keywords = request.args.get("keywords")
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1
    news_list = []
    current_page = 1
    total_page = 1
    filter_list = []
    if keywords:
        filter_list.append(News.title.contains(keywords))
    try:
        paginate = News.query.filter(*filter_list).order_by(News.create_time.desc()).paginate(
            p, 10, False
        )
        news_list = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
        return abort(404)
    news_dict_list = []
    for news in news_list if news_list else []:
        news_dict_list.append(news.to_dict())
    data = {
        "news_list": news_dict_list,
        "current_page": current_page,
        "total_page": total_page
    }
    return render_template("admin/news_edit.html", data=data)


# 新闻版式编辑详情
@admin_bp.route("/news_edit_detail", methods=["GET", "POST"])
def news_edit_detail():
    if request.method == "GET":
        news_id = request.args.get("news_id")
        news = None  # type: News
        if news_id:
            try:
                news = News.query.get(news_id)
            except Exception as e:
                current_app.logger.error(e)
                return jsonify(errno=RET.DBERR, errmsg="查询异常")
        news_dict = news.to_dict() if news else None
        # 获取新闻分类
        categories = Category.query.all()
        category_dict_list = []
        for category in categories if categories else []:
            category_dict = category.to_dict()
            category_dict["is_selected"] = False
            if category.id == news.category_id:
                category_dict["is_selected"] = True
            category_dict_list.append(category_dict)
        category_dict_list.pop(0)
        data = {
            "news": news_dict,
            "categories": category_dict_list
        }
        return render_template("admin/news_edit_detail.html", data=data)

    # POST 编辑新闻详情
    # title: 新闻标题，category_id: 分类id， digest：新闻摘要
    # index_image: 新闻主图片，content: 新闻内容， news_id: 新闻id对象
    news_id = request.form.get("news_id")
    title = request.form.get("title")
    category_id = request.form.get("category_id")
    digest = request.form.get("digest")
    content = request.form.get("content")
    # 新闻主图片
    index_image = request.files.get("index_image")
    if not all([title, category_id, digest, news_id, content]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")
    try:
        category_id = int(category_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数类型错误")
    # TODO 修改图片及上传七牛云没写
    # 获取新闻对象
    news = None
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询用户异常")
    if not news:
        return jsonify(errno=RET.NODATA, errmsg="新闻对象不存在")
    # 修改新闻属性
    news.title = title
    news.category_id = category_id
    news.digest = digest
    news.content = content
    news.index_image_url = index_image
    try:
        db.session.add(news)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存新闻对象异常")
    return jsonify(errno=RET.OK, errmsg="OK")


# 展示新闻分类数据
@admin_bp.route("/news_type")
def news_type():
    categories = Category.query.all()
    category_dict_list = []
    for category in categories if categories else []:
        category_list = category.to_dict()
        category_dict_list.append(category_list)
    category_dict_list.pop(0)
    data = {
        "categories": category_dict_list
    }
    return render_template("admin/news_type.html", data=data)


# 新增分类
@admin_bp.route("type_edit", methods=["POST"])
def type_edit():
    """
    category_name: 分类的名称， category_id: 分类的id
    :return:
    """
    category_name = request.json.get("category_name")
    category_id = request.json.get("category_id")

    # 2.1 非空判断
    if not category_name:
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")

    #  3.0 根据category_id判断是否有值
    if category_id:
        try:
            category = Category.query.get(category_id)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询分类对象异常")

        if not category:
            return jsonify(errno=RET.NODATA, errmsg="分类不存在不能编辑")
        category.name = category_name
    else:
        #  无值：新增分类：创建分类对象，并赋值
        category = Category()
        category.name = category_name
        db.session.add(category)

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存分类对象异常")

    return jsonify(errno=RET.OK, errmsg="分类操作完成")





