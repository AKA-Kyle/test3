
import os
import time
import urllib.parse
import requests
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import uuid as uuid_util
from config_parse import ConfigParser
import file_util


config_parser = ConfigParser("config.txt")

name = config_parser.get_value('name')
password = config_parser.get_value('password')

chrome_options = Options()
# chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

print("打开浏览器")

driver = webdriver.Chrome(chrome_options=chrome_options, executable_path=config_parser.get_value("driver"))
driver.get(config_parser.get_value("domain")+config_parser.get_value("login_path"))

time.sleep(2)

# 填充账户密码登录
user_name = driver.find_element_by_id("normal_login_account")
user_name.send_keys(config_parser.get_value("user_name"))

user_name = driver.find_element_by_id("normal_login_password")
user_name.send_keys(config_parser.get_value("pass_word"))

buttons = driver.find_elements_by_tag_name("button")

buttons[0].click()

time.sleep(3)

#保存cookie信息。
cookies=driver.get_cookies()

session =requests.session()
c = requests.cookies.RequestsCookieJar()
for item in cookies:
    c.set(item["name"],item["value"])
session.cookies.update(c)

payload_header={
    'Content-Type': 'application/json'
}
#创建文件夹
upload_model_path = config_parser.get_value("upload_model_path")
node_path = config_parser.get_value("domain")+ config_parser.get_value("node_path")
node_create_path = ""
print("尝试创建路径")
path_array = upload_model_path.split("/")
for path in path_array[1:]:
    if path is not None and len(path.strip()) >0:
        node_parent_path = node_create_path
        node_create_path += "/" + path
        print("创建路径", node_create_path)
        response = session.post(node_path
                                ,data=json.dumps(dict(path=node_parent_path,name=path))
                                ,headers=payload_header
                                )
        print(response.text)

content_url = config_parser.get_value("domain")+ config_parser.get_value("content_path") + "?path=" + str(urllib.parse.quote(upload_model_path))
driver.get(content_url)

upload_model_url = config_parser.get_value("lite_domain") + config_parser.get_value("lite_policy_path")

model_local_path_list = []

# 筛选文件
ext_list = []
ext_array = config_parser.get_value("upload_local_model_ext").split(",")
for ext in ext_array:
    ext = "." + ext.replace(".", "")
    ext_list.append(ext)
model_dir = config_parser.get_value("upload_local_model_path")
for path in os.listdir(model_dir):
    if file_util.get_file_ext(path) in ext_list:
        path = os.path.join(model_dir,file_util.get_file_base_name(path))
        model_local_path_list.append(path)

fail_model_list = []
unfinish_model_list = []
print("准备转换的文件：",model_local_path_list)
for model_local_path in model_local_path_list:
    driver.get(content_url)
    print("准备上传文件",model_local_path)
    scene_uuid = uuid_util.uuid4()
    upload_params=dict(
        uuid=scene_uuid,
        scene_uuid=scene_uuid,
        scene_name = file_util.filename_no_suffix(model_local_path),
        name = file_util.get_file_base_name(model_local_path),
        path = upload_model_path,
        uv = int(config_parser.get_value("project_uv")),
        clear = int(config_parser.get_value("clear_flag")),
        type = int(config_parser.get_value("reduce_flag")),
        reduce = int(config_parser.get_value("reduce_percent")),
    )



    resp = session.get(url=upload_model_url, params=upload_params)
    policy_info = resp.json().get('info')
    if resp.json().get('code') != 10000:
        print('获取上传代理失败:'+str(json.dumps(resp.json())),model_local_path)
        continue
        # raise Exception('获取上传代理失败:'+str(json.dumps(resp.json())))
    print("正在上传文件",model_local_path)
    file_data = open(model_local_path, 'rb')
    files = {'file': ('cake.zip', file_data)}
    up_data = {
        'name':(None, name),
        'key':(None, policy_info.get('dir') + str(scene_uuid)),
        'policy':(None, policy_info.get('policy')),
        'OSSAccessKeyId':(None, policy_info.get('accessid')),
        'success_action_status':(None,200),
        'callback':(None, policy_info.get('callback')),
        'signature':(None, policy_info.get('signature')),
    }
    response = session.post(url=policy_info['host'], data=up_data, files=files)
    print(response)
    ali_response  = response.json()
    if 'data' not in ali_response:
        raise Exception('上传文件失败:' + str(json.dumps(ali_response)))
    time.sleep(1)
    driver.get(content_url)
    job_uid = ali_response['data']['job_uid']
    job_url = config_parser.get_value('lite_domain')+config_parser.get_value('upload_status_path')
    unfinish = True
    for i in range(int(config_parser.get_value("upload_wait_time"))):
        response = session.post(job_url ,data=json.dumps(dict(job_uids=[job_uid])),headers=payload_header).json()
        if response['list']['data'][0]['status'] < 0:
            fail_model_list.append(model_local_path)
            unfinish = False
            break
        elif response['list']['data'][0]['status'] == 2:
            unfinish = False
            break
        time.sleep(1)
    if unfinish:
        unfinish_model_list.append(model_local_path)
    time.sleep(1)

if len(unfinish_model_list)>0:
    print("用时超过2分钟，没有继续等待的模型列表：")
    print("\n".join(unfinish_model_list))
if len(fail_model_list)>0:
    print("转换出错的模型列表：")
    print("\n".join(fail_model_list))
print("转换完成")