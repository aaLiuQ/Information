from info.utils.captcha.captcha import captcha
import redis
from config import config
import random

# REDIS_HOST = "47.102.102.179"
# REDIS_PORT = 6379
#
# redis_store = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT)
# name, text, image = captcha.generate_captcha()
# code_id = 'ss'
# redis_store.setex('ImageCode_' + code_id, 300, text)
#
# print(name, text, image)
result = random.randint(0, 999999)
sms_code = '%06d' % result
print(sms_code)
