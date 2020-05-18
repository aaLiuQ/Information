from . import index_blu
from flask import render_template, current_app
from info.models import User, News, Category
from info import constants


@index_blu.route('/')
def index():
    # 获取点击排行数据
    news_list = None
    try:
        news_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)

    click_news_list = []
    for news in news_list if news_list else []:
        click_news_list.append(news.to_basic_dict())

    data = {
        # "user_info": user.to_dict() if user else None,
        "click_news_list": click_news_list,
    }
    return render_template('news/index.html', data=data)


@index_blu.route('/favicon.ico')
def favicon():
    return current_app.send_static_file('news/favicon.ico')
