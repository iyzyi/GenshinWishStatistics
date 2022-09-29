from codecs import ignore_errors
from unittest import result
import requests, re, os, time, json, operator

class GenshinWishStatistics:

    def __init__(self):
        self.xian_ding_chi = []
        self.chang_zhu_chi = []
        self.wu_qi_chi = []
        self.xin_shou_chi = []
        self.id_local_table = []
        remote_record_count = 0
    
        if self.load_local_record():
            if self.get_wish_url():
                remote_record_count = self.get_remote_record()      # 祈愿记录增量条数

            self.show_xian_ding_chi_record()
            self.show_chang_zhu_chi_record()
            self.show_wu_qi_chi_record()
            self.show_xin_shou_chi_record()

            if remote_record_count > 0:
                self.save_wish_json()


    # 获取本地保存的抽卡记录
    def load_local_record(self):
        user_path = os.environ['USERPROFILE']
        game_cache_path = r'AppData\LocalLow\miHoYo\原神'
        uid_file = os.path.join(user_path, game_cache_path, 'UidInfo.txt')

        if not os.path.exists(uid_file):
            print('[ERROR] %s不存在' % uid_file)
            return False

        with open(uid_file)as f:
            self.uid = int(f.read())

        local_record_file = 'WishLog_%d.json' % self.uid

        if not os.path.exists(local_record_file):
            print('[INFO] 本地无保存的抽卡记录%s' % local_record_file)
        else:
            with open(local_record_file, 'r', encoding='utf-8')as f:
                data = f.read()
            wish_list = json.loads(data)
            for wish in wish_list:
                if wish['gacha_type'] == '301' or wish['gacha_type'] == '400':      # 301是up池，400是up-2池
                    self.xian_ding_chi.append(wish)
                    self.id_local_table.append(wish['id'])
                elif wish['gacha_type'] == '200':                                   # 200是常驻池
                    self.chang_zhu_chi.append(wish)
                    self.id_local_table.append(wish['id'])
                elif wish['gacha_type'] == '302':                                   # 302是武器池
                    self.wu_qi_chi.append(wish)
                    self.id_local_table.append(wish['id'])
                elif wish['gacha_type'] == '100':                                   # 100是新手池
                    self.xin_shou_chi.append(wish)
                    self.id_local_table.append(wish['id'])
                else:
                    print('[DEBUG] 居然出现未知类型')
                    print(wish)

            print('[INFO] 成功读取本地抽卡记录，共%d条' % len(wish_list))

        return True                             # 没有本地抽卡记录也返回True


    # 获取祈愿抽卡记录的网址
    def get_wish_url(self):
        
        #log_path = r'C:\Users\iyzyi\AppData\LocalLow\miHoYo\原神\output_log.txt'

        user_path = os.environ['USERPROFILE']
        game_cache_path = r'AppData\LocalLow\miHoYo\原神'
        log_path = os.path.join(user_path, game_cache_path, 'output_log.txt')

        if not os.path.exists(log_path):
            print('[ERROR] %s不存在' % log_path)
            return False

        with open(log_path, 'r', encoding='utf-8', errors='ignore')as f:
            log = f.read()
        wish_url = re.search(r'https://webstatic.mihoyo.com.+?#/log', log)

        if not wish_url:
            print('[ERROR] 本地日志中未找到祈愿抽卡记录的网址，以下仅显示本地保存的祈愿抽卡记录数据。如需查看最新祈愿记录，请在游戏中打开祈愿界面，挂假代理导致间接断网后多次点击历史记录，出现灰色空白页面时则为成功。\n\n')
            return False
        else:
            self.wish_url = wish_url.group()
            print('[INFO] 成功获取祈愿记录网址：%s' % self.wish_url)
            return True


    # 获取官方保存的抽卡记录（6个月），目前为增量获取，返回增量获取的祈愿条数
    def get_remote_record(self):
        count = 0
        count += self.get_remote_record_with_type(301)
        count += self.get_remote_record_with_type(200)
        count += self.get_remote_record_with_type(302)
        count += self.get_remote_record_with_type(100)
        print('\r[INFO] 成功增量获取官方抽卡记录，共%d条                      \n\n' % count)
        return count


    # 返回增量获取的祈愿条数
    def get_remote_record_with_type(self, type):
        end_id = 0
        page = 1
        count = 0

        while True:
            main_param = re.search(r'index.html\?(win_mode=.+?hk4e_cn)#/log', self.wish_url).group(1)
            url = 'https://hk4e-api.mihoyo.com/event/gacha_info/api/getGachaLog?{}&gacha_type={}&page={}&size=5&end_id={}'.format(main_param, type, page, end_id)
            
            if type == 301:
                type_str = '限定池'
            elif type == 200:
                type_str = '常驻池'
            elif type == 302:
                type_str = '武器池'
            elif type == 100:
                type_str = '新手池'
            print('\r[INFO] 正在获取{}第{}页抽卡记录......'.format(type_str, page), end='')

            res = requests.get(url)
            data = res.json()

            if not data['data']['list']:
                break

            f_continue = True
            wish_data = data['data']['list']
            for wish in wish_data:
                if type == 301:
                    f_continue = self.remove_dup_append(self.xian_ding_chi, wish)
                elif type == 200:
                    f_continue = self.remove_dup_append(self.chang_zhu_chi, wish)
                elif type == 302:
                    f_continue = self.remove_dup_append(self.wu_qi_chi, wish)
                elif type == 100:
                    f_continue = self.remove_dup_append(self.xin_shou_chi, wish)
                if not f_continue:
                    break
                else:
                    count += 1
            
            if not f_continue:
                break

            end_id = wish_data[len(wish_data) - 1]['id']

            time.sleep(0.3)
            page += 1
        return count

    # 去重添加，将从官方获取的祈愿记录添加到本程序中，当本地已存在某条祈愿记录时不添加并返回False
    def remove_dup_append(self, list, wish):
        if wish['id'] not in self.id_local_table:
            list.append(wish)
            return True
        else:
            return False


    # 统计限定池数据
    def show_xian_ding_chi_record(self):
        print('{}限定池{}'.format('=' * 27, '=' * 27))
        self.xian_ding_chi = sorted(self.xian_ding_chi, key=operator.itemgetter('id'), reverse=True)
        
        chang_zhu = ['迪卢克', '刻晴', '莫娜', '七七', '琴']        # 未考虑常驻角色可能会UP的情况，如3.0提纳里。

        temp = 0
        five_star_character_count = 0
        xiao_bao_di_count = 0
        wai_xiao_bao_di_count = 0
        last_is_chang_zhu = False
        xian_ding_five_star_character_count = 0
        zui_ou_count = 999
        zui_fei_count = -1
        last_five_star_index = 0

        for i in range(len(self.xian_ding_chi) - 1, -1, -1):
            temp += 1
            wish = self.xian_ding_chi[i]
            if wish['rank_type'] == '5':
                print('【%s】%s%.2d' % (wish['name'], ' '*(16-2*len(wish['name'])), temp), ' '*6, wish['time'])
                five_star_character_count += 1
                last_five_star_index = len(self.xian_ding_chi) - i
                                
                if not last_is_chang_zhu:
                    xiao_bao_di_count += 1
                    if wish['name'] in chang_zhu:
                        wai_xiao_bao_di_count += 1
                
                if wish['name'] not in chang_zhu:
                    xian_ding_five_star_character_count += 1
                    last_is_chang_zhu = False
                else:
                    last_is_chang_zhu = True

                if temp > zui_fei_count:
                    zui_fei_count = temp
                if temp < zui_ou_count:
                    zui_ou_count = temp
                temp = 0

        print('{}统计{}'.format('=' * 28, '=' * 28))
        print('总抽数：        {:<14d}'.format(len(self.xian_ding_chi)), end='')
        if last_is_chang_zhu:
            bao_di_type = '大保底'
        else:
            bao_di_type = '小保底'
        print('已垫抽数：        %s%d抽' % (bao_di_type, len(self.xian_ding_chi) - last_five_star_index))

        print('五星个数：      {:<14d}限定五星个数：    {}'.format(five_star_character_count, xian_ding_five_star_character_count))
        print('小保底次数：    {:<14d}歪小保底次数：    {}'.format(xiao_bao_di_count, wai_xiao_bao_di_count))
        if five_star_character_count != 0:
            print('平均五星抽数：  %.2f' % (len(self.xian_ding_chi) / five_star_character_count), end='         ')
        else:
            print('平均五星抽数：  INF', end='           ')
        if xian_ding_five_star_character_count != 0:
            print('平均限定五星抽数：%.2f' % (len(self.xian_ding_chi) / xian_ding_five_star_character_count))
        else:
            print('平均限定五星抽数：INF')
        print('最欧抽数：      {:<14d}最非抽数：        {}'.format(zui_ou_count, zui_fei_count))
        print('\n\n')


    # 统计常驻池数据
    def show_chang_zhu_chi_record(self):
        print('{}常驻池{}'.format('=' * 27, '=' * 27))
        self.chang_zhu_chi = sorted(self.chang_zhu_chi, key=operator.itemgetter('id'), reverse=True)

        temp = 0
        five_star_character_count = 0
        zui_ou_count = 999
        zui_fei_count = -1
        last_five_star_index = 0 

        for i in range(len(self.chang_zhu_chi) - 1, -1, -1):
            temp += 1
            wish = self.chang_zhu_chi[i]
            if wish['rank_type'] == '5':
                print('【%s】%s%.2d' % (wish['name'], ' '*(16-2*len(wish['name'])), temp), ' '*6, wish['time'])
                five_star_character_count += 1
                last_five_star_index = len(self.chang_zhu_chi) - i

                if temp > zui_fei_count:
                    zui_fei_count = temp
                if temp < zui_ou_count:
                    zui_ou_count = temp
                temp = 0

        print('{}统计{}'.format('=' * 28, '=' * 28))
        print('总抽数：        {:<14d}'.format(len(self.chang_zhu_chi)), end='')
        print('已垫抽数：        %d' % (len(self.chang_zhu_chi) - last_five_star_index))
        print('五星个数：      {:<14d}'.format(five_star_character_count), end='')
        if five_star_character_count != 0:
            print('平均五星抽数：    %.2f' % (len(self.chang_zhu_chi) / five_star_character_count))
        else:
            print('平均五星抽数：    INF')
        print('最欧抽数：      {:<14d}最非抽数：        {}'.format(zui_ou_count, zui_fei_count))
        print('\n\n')


    # 统计武器池数据
    def show_wu_qi_chi_record(self):
        print('{}武器池{}'.format('=' * 27, '=' * 27))
        self.wu_qi_chi = sorted(self.wu_qi_chi, key=operator.itemgetter('id'), reverse=True)

        temp = 0
        five_star_wu_qi_count = 0
        zui_ou_count = 999
        zui_fei_count = -1
        last_five_star_index = 0

        for i in range(len(self.wu_qi_chi) - 1, -1, -1):
            temp += 1
            wish = self.wu_qi_chi[i]
            if wish['rank_type'] == '5':
                print('【%s】%s%.2d' % (wish['name'], ' '*(16-2*len(wish['name'])), temp), ' '*6, wish['time'])
                five_star_wu_qi_count += 1
                last_five_star_index = len(self.wu_qi_chi) - i

                if temp > zui_fei_count:
                    zui_fei_count = temp
                if temp < zui_ou_count:
                    zui_ou_count = temp
                temp = 0

        print('{}统计{}'.format('=' * 28, '=' * 28))
        print('总抽数：        {:<14d}'.format(len(self.wu_qi_chi)), end='')
        print('已垫抽数：        %d' % (len(self.wu_qi_chi) - last_five_star_index))
        print('五星个数：      {:<14d}'.format(five_star_wu_qi_count), end='')
        if five_star_wu_qi_count != 0:
            print('平均五星抽数：    %.2f' % (len(self.wu_qi_chi) / five_star_wu_qi_count))
        else:
            print('平均五星抽数：    INF')
        print('最欧抽数：      {:<14d}最非抽数：        {}'.format(zui_ou_count, zui_fei_count))
        print('\n\n')


    # 统计新手池数据
    def show_xin_shou_chi_record(self):
        print('{}新手池{}'.format('=' * 27, '=' * 27))
        self.xin_shou_chi = sorted(self.xin_shou_chi, key=operator.itemgetter('id'), reverse=True)

        temp = 0
        five_star_character_count = 0
        zui_ou_count = 999
        zui_fei_count = -1
        last_five_star_index = 0

        for i in range(len(self.xin_shou_chi) - 1, -1, -1):
            temp += 1
            wish = self.xin_shou_chi[i]
            if wish['rank_type'] == '5':
                print('【%s】%s%.2d' % (wish['name'], ' '*(16-2*len(wish['name'])), temp), ' '*6, wish['time'])
                five_star_character_count += 1
                last_five_star_index = len(self.xin_shou_chi) - i

                if temp > zui_fei_count:
                    zui_fei_count = temp
                if temp < zui_ou_count:
                    zui_ou_count = temp
                temp = 0

        print('{}统计{}'.format('=' * 28, '=' * 28))
        print('总抽数：        {:<14d}'.format(len(self.xin_shou_chi)), end='')
        print('已垫抽数：        %d' % (len(self.xin_shou_chi) - last_five_star_index))
        print('五星个数：      {:<14d}'.format(five_star_character_count), end='')
        if five_star_character_count != 0:
            print('平均五星抽数：    %.2f' % (len(self.xin_shou_chi) / five_star_character_count))
            print('最欧抽数：      {:<14d}最非抽数：        {}'.format(zui_ou_count, zui_fei_count))
        else:
            print('平均五星抽数：    INF')
            print('最欧抽数：      INF           最非抽数：        INF')
        

    def save_wish_json(self):
        print('\n\n\n[INFO] 正在增量存储官方抽卡记录......', end='')
        all_wish_list = self.xian_ding_chi + self.chang_zhu_chi + self.wu_qi_chi + self.xin_shou_chi
        all_wish_list = sorted(all_wish_list, key=operator.itemgetter('id'), reverse=True)
        all_wish_json = json.dumps(all_wish_list, ensure_ascii=False, indent=4)

        local_record_file = 'WishLog_%d.json' % self.uid
        with open(local_record_file, 'w', encoding='utf-8')as f:
            f.write(all_wish_json)
        
        print('\r[INFO] 成功增量存储官方抽卡记录             ')



if __name__ == '__main__':
    app = GenshinWishStatistics()