from codecs import ignore_errors
from unittest import result
import requests, re, os, time, json, operator, time

class GenshinWishStatistics:

    def __init__(self, mode, fiddler_url = ''):
        self.xian_ding_chi = []
        self.chang_zhu_chi = []
        self.wu_qi_chi = []
        self.hun_he_chi = []
        self.xin_shou_chi = []
        self.id_local_table = []
        self.mode = mode
        remote_record_count = 0
    
        if self.load_local_record():
            
            f = False
            if mode == '1':
                f = self.get_wish_url_mode_1()
            elif mode == '2':
                f = self.get_wish_url_mode_2(fiddler_url)
            elif mode == '3':
                f = True

            if f:
                if mode == '1' or mode == '2':
                    remote_record_count = self.get_remote_record()      # 祈愿记录增量条数
                else:
                    remote_record_count = 0

                self.show_xian_ding_chi_record()
                self.show_chang_zhu_chi_record()
                self.show_wu_qi_chi_record()
                self.show_hun_he_chi_record()
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
                elif wish['gacha_type'] == '500':                                   # 500是混池
                    self.hun_he_chi.append(wish)
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
    def get_wish_url_mode_1(self):
        
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
    
    def get_wish_url_mode_2(self, fiddler_url):
        res = re.search(r'(https://public-operation-hk4e\.mihoyo\.com/gacha_info/api/getGachaLog\?.+?)&gacha_type', fiddler_url)
        if res:
            self.wish_url_main = res.group(1)
            return True
        else:
            print('[ERROR] 提供的从fiddler中获取的url不正确')
            return False

    # 获取官方保存的抽卡记录（6个月），目前为增量获取，返回增量获取的祈愿条数
    def get_remote_record(self):
        count = 0
        count += self.get_remote_record_with_type(301)
        count += self.get_remote_record_with_type(200)
        count += self.get_remote_record_with_type(302)
        count += self.get_remote_record_with_type(500)
        count += self.get_remote_record_with_type(100)
        print('\r[INFO] 成功增量获取官方抽卡记录，共%d条                      \n\n' % count)
        return count


    # 返回增量获取的祈愿条数
    def get_remote_record_with_type(self, type):
        end_id = 0
        page = 1
        count = 0

        while True:
            if self.mode == '1':
                main_param = re.search(r'index.html\?(win_mode=.+?hk4e_cn)#/log', self.wish_url).group(1)
            elif self.mode == '2':
                main_param = self.wish_url_main

            url = 'https://hk4e-api.mihoyo.com/event/gacha_info/api/getGachaLog?{}&gacha_type={}&page={}&size=5&end_id={}'.format(main_param, type, page, end_id)
            
            if type == 301:
                type_str = '限定池'
            elif type == 200:
                type_str = '常驻池'
            elif type == 302:
                type_str = '武器池'
            elif type == 500:
                type_str = '混合池'
            elif type == 100:
                type_str = '新手池'
            print('\r[INFO] 正在获取{}第{}页抽卡记录......'.format(type_str, page), end='')

            time.sleep(0.3)
            res = requests.get(url)
            data = res.json()

            if not data['data']:
                print('\n[ERROR] {}'.format(data['message']))
                exit()

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
                elif type == 500:
                    f_continue = self.remove_dup_append(self.hun_he_chi, wish)
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
        
        chang_zhu = ['迪卢克', '刻晴', '莫娜', '七七', '琴', '提纳里']        # 未考虑常驻角色可能会UP的情况，如3.0提纳里。

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


    # 统计混合池数据
    def show_hun_he_chi_record(self):
        print('{}混合池{}'.format('=' * 27, '=' * 27))
        self.hun_he_chi = sorted(self.hun_he_chi, key=operator.itemgetter('id'), reverse=True)

        temp = 0
        five_star_character_count = 0
        zui_ou_count = 999
        zui_fei_count = -1
        last_five_star_index = 0

        for i in range(len(self.hun_he_chi) - 1, -1, -1):
            temp += 1
            wish = self.hun_he_chi[i]
            if wish['rank_type'] == '5':
                print('【%s】%s%.2d' % (wish['name'], ' '*(16-2*len(wish['name'])), temp), ' '*6, wish['time'])
                five_star_character_count += 1
                last_five_star_index = len(self.hun_he_chi) - i

                if temp > zui_fei_count:
                    zui_fei_count = temp
                if temp < zui_ou_count:
                    zui_ou_count = temp
                temp = 0

        print('{}统计{}'.format('=' * 28, '=' * 28))
        print('总抽数：        {:<14d}'.format(len(self.hun_he_chi)), end='')
        print('已垫抽数：        %d' % (len(self.hun_he_chi) - last_five_star_index))
        print('五星个数：      {:<14d}'.format(five_star_character_count), end='')
        if five_star_character_count != 0:
            print('平均五星抽数：    %.2f' % (len(self.hun_he_chi) / five_star_character_count))
            print('最欧抽数：      {:<14d}最非抽数：        {}'.format(zui_ou_count, zui_fei_count))
        else:
            print('平均五星抽数：    INF')
            print('最欧抽数：      INF           最非抽数：        INF')
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
        all_wish_list = self.xian_ding_chi + self.chang_zhu_chi + self.wu_qi_chi + self.hun_he_chi + self.xin_shou_chi
        all_wish_list = sorted(all_wish_list, key=operator.itemgetter('id'), reverse=True)
        all_wish_json = json.dumps(all_wish_list, ensure_ascii=False, indent=4)

        local_record_file = 'WishLog_%d.json' % self.uid
        with open(local_record_file, 'w', encoding='utf-8')as f:
            f.write(all_wish_json)
        
        print('\r[INFO] 成功增量存储官方抽卡记录             ')



if __name__ == '__main__':
    choice = input('请选择工作模式：\n1) 挂假代理多次点击《历史记录》后运行此脚本\n2) 手动使用fiddler获取形如“hk4e-api.mihoyo.com/event/gacha_info/api/getGachaLog”的url\n3) 仅查看本地数据\n你的选择：')
    if choice == '1':
        app = GenshinWishStatistics(choice)
    elif choice == '2':
        fiddler_url = input('请输入使用fiddler获取的url：')
        # 例如： https://hk4e-api.mihoyo.com/event/gacha_info/api/getGachaLog?win_mode=fullscreen&authkey_ver=1&sign_type=2&auth_appid=webview_gacha&init_type=301&gacha_id=4157ddbd5d5fb886f55ca7b111a3e568e663f3be&timestamp=1677627587&lang=zh-cn&device_type=pc&game_version=CNRELWin3.5.0_R13415299_S13402347_D13449934&plat_type=pc&region=cn_gf01&authkey=BBYXzHu3xASwYrF4XPT22QkU5JQlFILjZ%2bDYrqXwpaoCYaqHExizEZril%2bm5XzVGchwWh%2fFxcp4Uw9tDKvbrSDp90EwFyfN1p7uFwShsaFGI4mD9TEF%2bsnqsqUFiIyQL7Kx6%2b9okwDsBwW8CKgRkfdp7GVNDuJub1TwCr15iEad%2fODA1ne0B6%2bUYQgYCJH%2fVXnAFuzTu6%2ffmj0fhMhRsTqjRgo0ZNOpL7T%2boC7bhkFdui1g1gAZxt%2bgSO0eMER2FnCLr416hrw26TKkpis%2bzSf4FDO1247MPELmQahM0DQwOWzZ%2bGTKyUEF7D2TC81QEtU0GNRB7z0J8J5w3EfXrd8tP7HbxOwl0tdq3mhyLbBrjVPCFsf6G8cyF2Bo0pasRQtsL94MOilEQVnfBb4PlTJdYEpXgMSaS75SEulwPJNTY4qfkZUZO1a6Om6iy0%2fJ8rzFStNPrH7ZHjVHeVLz6AlqT3oFzdqFcWeOwJYhyhoiGt58xYhs59OP%2fyiEBRWMCQIeQTWmLXxdJrKYsOKGAQHI7u%2flE1qpUvtXW0Bd%2fe3p6XXgv5a%2b30VevAfLEpl5Mkbrgwzcy5As%2fNFkvzjHXm4JM7xNKGsKImXCfpBtshIqNv3uiuAtsSDcJXxXxQsoR69rAiyNOy7BaZxQ6O94SrWc4DgKsgKG%2fWrhNYhgVssosrEO6prj7nVwEYeFt8o7D%2fLVsQ089jFd4nrvT6grCZpI%2bipTEuiwabbDtXnWkWSUTwkpPYhzl0KNgTZZ8h4iLAN0Y%2bn6Z3Dx6pRjsRMWjwP6vlHi6HSAxJK9fy9Ovl7WXQq24YGYuVqc6gr3vNEzjhCr%2f%2f4ojPT%2fjO9uPOfksqPOdp5f%2bnUBm8EtHFcHAG8WPQcl2OHp5%2fEik%2bZeZo%2fUsWox1kOBC2pu%2fHJlY6MyoE6PwDfG1z%2bVEcWDOh1sJzrWDaa0c%2fKZ8D8w4mfhn%2fSHLTd7venTUftKIKUNvdj6EafPCKypSbLnPfNzP0HUZ8DNi5LztFqjdDZGsGwWvyNOu&game_biz=hk4e_cn&gacha_type=301&page=2&size=5&end_id=1677301560000984863
        app = GenshinWishStatistics(choice, fiddler_url)
    elif choice == '3':
        app = GenshinWishStatistics(choice)