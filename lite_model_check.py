import time
import urllib.request
import requests
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from config_parse import ConfigParser

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

fail_convert_model_list = []
converting_model_list = []
edit_broken_model_list = []

def visit(dir,index=0):
    if index > 5:
        return
    node_path  = config_parser.get_value("domain") + config_parser.get_value("node_path")

    params = dict(
        path=dir
    )

    response = session.get(node_path,params=params)
    # print(response.text)
    resp_json = json.loads(response.text)
    if resp_json['code'] != 10000:
        raise Exception("访问出错url："+node_path)

    node_list = resp_json['list']['data']
    if node_list is None or len(node_list)==0:
        return
    print("开始检查编辑页的正确性")
    for node in node_list:
        category = node['category']
        job_status = node.get('job_status',0)
        if job_status == -1:
            fail_convert_model_list.append(str(node.get('path','')))
            continue
        elif job_status == 1:
            converting_model_list.append(str(node.get('path','')))
        if category == 0:
            visit(node['path'],index+1)
        elif category==1:
            content_uid = node['content_uid']
            check_url = config_parser.get_value("lite_domain") + "/editor/" + str(content_uid)
            try:
                driver.get(check_url)
                time.sleep(int(config_parser.get_value('check_model_load_time')))
                print("正在检查",check_url)
                browser_log = driver.get_log('browser')
                for log in browser_log:
                    level = log.get('level')
                    if level not in ['WARNING']:
                        edit_broken_model_list.append(check_url)
                        print("发现错误日志：",log)
                        break
            except:
                edit_broken_model_list.append(check_url)

            # print(index,check_url)
    return

visit(config_parser.get_value("check_dir"))

print("正在转换的模型列表：")
print("\n".join(converting_model_list))
print("转换失败的模型列表：")
print("\n".join(fail_convert_model_list))
print("编辑页存在问题的模型：")
print("\n".join(edit_broken_model_list))

driver.close()

