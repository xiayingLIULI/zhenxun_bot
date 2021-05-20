from nonebot.typing import T_State
from nonebot.adapters.cqhttp import Bot, MessageEvent
from nonebot import on_command
from util.utils import get_message_text, UserExistLimiter, is_number
from .data_source import get_pixiv_urls, download_pixiv_imgs, search_pixiv_urls
import time
from services.log import logger
from nonebot.adapters.cqhttp.exception import NetworkError

__plugin_usage__1 = '''P站排行榜帮助：
可选参数：
类型：
    1. 日排行
    2. 周排行
    3. 月排行
    4. 原创排行
    5. 新人排行
    6. R18日排行
    7. R18周排行
    8. R18受男性欢迎排行
    9. R18重口排行【慎重！】
【使用时选择参数序号即可，R18仅可私聊】
p站排行榜 类型 数量(可选) 日期(可选)
示例：
    p站排行榜   （无参数默认为日榜）
    p站排行榜 1
    p站排行榜 1 5
    p站排行榜 1 5 2018-4-25
【注意空格！！】【在线搜索会较慢】
'''

__plugin_usage__2 = '''P站搜图帮助：
可选参数：
    1.热度排序
    2.时间排序
【使用时选择参数序号即可，R18仅可私聊】 
搜图 关键词 数量(可选) 排序方式(可选) r18(可选)
示例：
    搜图 樱岛麻衣
    搜图 樱岛麻衣 5 1
    搜图 樱岛麻衣 5 2 r18
【默认为 热度排序】
【注意空格！！】【在线搜索会较慢】【数量可能不符】
'''

rank_dict = {
    '1': 'day',
    '2': 'week',
    '3': 'month',
    '4': 'week_original',
    '5': 'week_rookie',
    '6': 'day_r18',
    '7': 'week_r18',
    '8': 'day_male_r18',
    '9': 'week_r18g'
}

_ulmt = UserExistLimiter()

pixiv_rank = on_command('p站排行', aliases={'P站排行榜', 'p站排行榜', 'P站排行榜'}, priority=5, block=True)
pixiv_keyword = on_command('搜图', priority=5, block=True)


@pixiv_rank.handle()
async def _(bot: Bot, event: MessageEvent, state: T_State):
    msg = get_message_text(event.json()).strip()
    if msg in ['帮助']:
        await pixiv_rank.finish(__plugin_usage__1)
    msg = msg.split(' ')
    msg = [m for m in msg if m]
    if not msg:
        msg = ['1']
    if msg[0] in ['6', '7', '8', '9']:
        if event.message_type == 'group':
            await pixiv_rank.finish('羞羞脸！私聊里自己看！', at_sender=True)
    # print(msg)
    if _ulmt.check(event.user_id):
        await pixiv_rank.finish("P站排行榜正在搜索噢，不要重复触发命令呀")
    _ulmt.set_True(event.user_id)
    if len(msg) == 0 or msg[0] == '':
        text_list, urls, code = await get_pixiv_urls(rank_dict.get('1'))
    elif len(msg) == 1:
        if msg[0] not in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
            await pixiv_rank.finish("要好好输入要看什么类型的排行榜呀！", at_sender=True)
        text_list, urls, code = await get_pixiv_urls(rank_dict.get(msg[0]))
    elif len(msg) == 2:
        text_list, urls, code = await get_pixiv_urls(rank_dict.get(msg[0]), int(msg[1]))
    elif len(msg) == 3:
        if not check_date(msg[2]):
            await pixiv_rank.finish('日期格式错误了', at_sender=True)
        text_list, urls, code = await get_pixiv_urls(rank_dict.get(msg[0]), int(msg[1]), msg[2])
    else:
        _ulmt.set_False(event.user_id)
        await pixiv_rank.finish('格式错了噢，看看帮助？', at_sender=True)
    if code != 200:
        await pixiv_keyword.finish(text_list[0])
    else:
        if not text_list or not urls:
            await pixiv_rank.finish('没有找到啊，等等再试试吧~V', at_sender=True)
        for i in range(len(text_list)):
            try:
                await pixiv_rank.send(text_list[i] + await download_pixiv_imgs(urls[i], event.user_id))
            except NetworkError:
                await pixiv_keyword.send('这张图网络炸了！', at_sender=True)
        logger.info(
            f"(USER {event.user_id}, GROUP {event.group_id if event.message_type != 'private' else 'private'})"
            f" 查看了P站排行榜 code：{msg[0]}")
    _ulmt.set_False(event.user_id)


@pixiv_keyword.handle()
async def _(bot: Bot, event: MessageEvent, state: T_State):
    msg = get_message_text(event.json()).strip()
    if msg in ['帮助'] or not msg:
        await pixiv_keyword.finish(__plugin_usage__2)
    if event.message_type == 'group':
        if msg.find('r18') != -1:
            await pixiv_keyword.finish('(脸红#) 你不会害羞的 八嘎！', at_sender=True)
    if msg.find('r18') == -1:
        r18 = 1
    else:
        r18 = 2
    msg = msg.replace('r18', '').strip()
    if _ulmt.check(event.user_id):
        await pixiv_rank.finish("P站关键词正在搜索噢，不要重复触发命令呀")
    _ulmt.set_True(event.user_id)
    msg = msg.split(' ')
    msg = [m for m in msg if m]
    if len(msg) == 1:
        keyword = msg[0].strip()
        num = 5
        order = 'popular'
    elif len(msg) == 2:
        keyword = msg[0].strip()
        if not is_number(msg[1].strip()):
            _ulmt.set_False(event.user_id)
            await pixiv_keyword.finish('图片数量必须是数字！', at_sender=True)
        num = int(msg[1].strip())
        order = 'popular'
    elif len(msg) == 3:
        keyword = msg[0].strip()
        if not is_number(msg[1].strip()):
            _ulmt.set_False(event.user_id)
            await pixiv_keyword.finish('图片数量必须是数字！', at_sender=True)
        num = int(msg[1].strip())
        if not is_number(msg[2].strip()):
            _ulmt.set_False(event.user_id)
            await pixiv_keyword.finish('排序方式必须是数字！', at_sender=True)
        if msg[2].strip() == '1':
            order = 'popular'
        else:
            order = 'xxx'
    else:
        _ulmt.set_False(event.user_id)
        await pixiv_keyword.finish('参数不正确，一定要好好看看帮助啊！', at_sender=True)
    text_list, urls, code = await search_pixiv_urls(keyword, num, order, r18)
    if code != 200:
        _ulmt.set_False(event.user_id)
        await pixiv_keyword.finish(text_list[0])
    else:
        for i in range(len(text_list)):
            try:
                await pixiv_keyword.send(text_list[i] + await download_pixiv_imgs(urls[i], event.user_id))
            except NetworkError:
                await pixiv_keyword.send('这张图网络炸了！', at_sender=True)
        logger.info(
            f"(USER {event.user_id}, GROUP {event.group_id if event.message_type != 'private' else 'private'})"
            f" 查看了搜索 {keyword} R18：{r18}")
    _ulmt.set_False(event.user_id)


def check_date(date):
    try:
        time.strptime(date, "%Y-%m-%d")
        return True
    except:
        return False
















