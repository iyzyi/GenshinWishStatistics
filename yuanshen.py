import requests, re, os, time


def get_log_url():
    #log_path = r'%USERPROFILE%\AppData\LocalLow\miHoYo\原神\output_log.txt'
    log_path = os.path.join(os.environ['USERPROFILE'], r"AppData\LocalLow\miHoYo\原神\output_log.txt")

    if not os.path.exists(log_path):
        print('日志文件不存在')
    else:
        with open(log_path, 'r', encoding='utf-8')as f:
            log = f.read()
        log_url = re.search(r'https://webstatic.mihoyo.com.+?#/log', log)
        if not log_url:
            print('日志文件中未找到抽卡log记录的网址，请先在游戏中祈愿界面点击一次“历史记录”再运行本程序')
        else:
            log_url = log_url.group()
            #print(log_url)
            return log_url


def to_time_stamp(time_str):
    time_array = time.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    return int(time.mktime(time_array))


# 从云端获取抽卡记录
def search_record(access_key, type):
    card_lists = []
    end_id = 0
    page = 1

    while True:
        url = 'https://hk4e-api.mihoyo.com/event/gacha_info/api/getGachaLog?{}&gacha_type={}&page={}&size=6&end_id={}'.format(access_key, type, page, end_id)
        res = requests.get(url)
        data = res.json()

        if not data['data']['list']:
            break

        for list in data['data']['list']:
            name = list['name']
            _time = to_time_stamp(list['time'])
            star = list['rank_type']
            card_data = {'name': name, 'time': _time, 'star': star}
            card_lists.append(card_data)

            end_id = list['id']

        time.sleep(0.6)
        page += 1

    card_lists = card_lists[::-1]
    # for card in card_lists:
    #     print(card)
    # print(len(card_lists))
    return card_lists


# 分析抽卡记录
def analyse_record(card_lists):
    num = 1
    wuxing_baodi = 90
    sixing_baodi = 10
    gold_num = 0

    for card in card_lists:
        if card['star'] == '5':
            print('【{}】({})'.format(card['name'], num))
            wuxing_baodi = 90
            gold_num += 1
        else:
            wuxing_baodi -= 1
        
        if card['star'] == '4' or card['star'] == '5':
            sixing_baodi = 10
        else:
            sixing_baodi -= 1

        num += 1

    print('共{}抽，{}金'.format(len(card_lists), gold_num))
    print('距离四星保底还有{}抽'.format(sixing_baodi))
    print('距离五星保底还有{}抽\n'.format(wuxing_baodi))
    
        
    
def yuanshen_cards_analyse(access_key, type):
    card_lists = search_record(access_key, type)
    if type == 301:
        print('UP池：')
        analyse_record(card_lists)
    elif type == 200:
        print('常驻池：')
        analyse_record(card_lists)
    elif type == 400:
        print('武器池：')
        analyse_record(card_lists)
    elif type == 100:
        print('新手池：')
        analyse_record(card_lists)


if __name__ == '__main__':
    log_url = get_log_url()
    print('日志网址：{}\n'.format(log_url))

    if log_url:
        access_key = re.search(r'index.html\?(authkey.+?)#/log', log_url).group(1)

        # 角色活动祈愿与角色活动祈愿-2
        yuanshen_cards_analyse(access_key, 301)

        # 常驻祈愿
        yuanshen_cards_analyse(access_key, 200)

        # 武器活动祈愿
        yuanshen_cards_analyse(access_key, 400)

        # 新手祈愿
        yuanshen_cards_analyse(access_key, 100)