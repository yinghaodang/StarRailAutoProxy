import os
from typing import Optional, List

from basic import os_utils
from basic.config import ConfigHolder
from basic.i18_utils import gt
from basic.log_utils import log
from sr.app.world_patrol.world_patrol_whitelist_config import WorldPatrolWhitelist
from sr.const import map_const, operation_const
from sr.const.map_const import Planet, Region, TransportPoint, PLANET_2_REGION, REGION_2_SP, PLANET_LIST


class WorldPatrolRouteId:

    def __init__(self, planet: Planet, raw_id: str):
        """
        :param planet: 星球
        :param raw_id: config\world_patrol\{planet}\{raw_id}.yml
        """
        idx = -1
        idx_cnt = 0
        # 统计字符串中含有多少个'_'字符,
        # idx = {字符数} - 1
        # 不需要分层的路线, idx_cnt = 2, 反之 idx_cnt=3
        while True:
            idx = raw_id.find('_', idx + 1)
            if idx == -1:
                break
            idx_cnt += 1
        idx = raw_id.rfind('_')

        self.route_num: int = 0 if idx_cnt == 3 else int(raw_id[idx+1:])

        self.planet: Planet = planet
        self.region: Optional[Region] = None
        self.tp: Optional[TransportPoint] = None

        for region in PLANET_2_REGION.get(planet.np_id):
            if raw_id.startswith(region.r_id):
                self.region: Region = region
                break

        for sp in REGION_2_SP.get(self.region.pr_id):
            if self.route_num == 0:
                if raw_id.endswith(sp.id):
                    self.tp = sp
                    break
            else:
                if raw_id[:raw_id.rfind('_')].endswith(sp.id):
                    self.tp = sp
                    break

        assert self.tp is not None

        self.raw_id = raw_id

    @property
    def display_name(self):
        """
        用于前端显示路线名称
        :return:
        """
        return '%s_%s_%s' % (gt(self.planet.cn, 'ui'), gt(self.region.cn, 'ui'), gt(self.tp.cn, 'ui')) + ('' if self.route_num == 0 else '_%02d' % self.route_num)

    @property
    def unique_id(self):
        """
        唯一标识 用于各种配置中保存
        :return:
        """
        return '%s_%s_%s' % (self.planet.np_id, self.region.r_id, self.tp.id) + ('' if self.route_num == 0 else '_%02d' % self.route_num)

    def equals(self, another_route_id):
        return another_route_id is not None and self.planet == another_route_id.planet and self.raw_id == another_route_id.raw_id

    @property
    def file_path(self):
        """
        对应的文件路径
        :return:
        """
        dir_path = os_utils.get_path_under_work_dir('config', 'world_patrol', self.planet.np_id)
        return os.path.join(dir_path, '%s.yml' % self.raw_id)


class WorldPatrolRoute(ConfigHolder):

    def __init__(self, route_id: WorldPatrolRouteId):
        self.author_list: Optional[List[str]] = None
        self.tp: Optional[TransportPoint] = None
        self.route_list: Optional[List] = None
        self.route_id: WorldPatrolRouteId = route_id
        super().__init__(route_id.raw_id, sample=False, sub_dir=['world_patrol', route_id.planet.np_id])

    def _init_after_read_file(self):
        self.init_from_data(**self.data)

    def init_from_data(self, author: List[str], planet: str, region: str, tp: str, floor: int, route: List):
        self.author_list = author
        self.tp: TransportPoint = map_const.get_sp_by_cn(planet, region, floor, tp)
        self.route_list = route

    @property
    def display_name(self):
        return self.route_id.display_name

    def add_author(self, new_author: str, save: bool = True):
        """
        增加一个作者
        :param new_author:
        :return:
        """
        if self.author_list is None:
            self.author_list = []
        if new_author not in self.author_list:
            self.author_list.append(new_author)
        if save:
            self.save()

    @property
    def route_config_str(self) -> str:
        cfg: str = ''
        if self.tp is None:
            return cfg
        last_floor = self.tp.region.floor
        cfg += "author: %s\n" % self.author_list
        cfg += "planet: '%s'\n" % self.tp.planet.cn
        cfg += "region: '%s'\n" % self.tp.region.cn
        cfg += "floor: %d\n" % last_floor
        cfg += "tp: '%s'\n" % self.tp.cn
        cfg += "route:\n"
        for route_item in self.route_list:
            if route_item['op'] in [operation_const.OP_MOVE, operation_const.OP_SLOW_MOVE,
                                    operation_const.OP_UPDATE_POS]:
                cfg += "  - op: '%s'\n" % route_item['op']
                pos = route_item['data']
                if len(pos) > 2 and pos[2] != last_floor:
                    cfg += "    data: [%d, %d, %d]\n" % (pos[0], pos[1], pos[2])
                    last_floor = pos[2]
                else:
                    cfg += "    data: [%d, %d]\n" % (pos[0], pos[1])
            elif route_item['op'] == operation_const.OP_PATROL:
                cfg += "  - op: '%s'\n" % route_item['op']
            elif route_item['op'] == operation_const.OP_INTERACT:
                cfg += "  - op: '%s'\n" % route_item['op']
                cfg += "    data: '%s'\n" % route_item['data']
            elif route_item['op'] == operation_const.OP_WAIT:
                cfg += "  - op: '%s'\n" % route_item['op']
                cfg += "    data: ['%s', '%s']\n" % (route_item['data'][0], route_item['data'][1])
        return cfg

    def save(self):
        self.save_diy(self.route_config_str)


def load_all_route_id(whitelist: WorldPatrolWhitelist = None, finished: List[str] = None) -> List[WorldPatrolRouteId]:
    """
    加载所有路线
    :param whitelist: 白名单
    :param finished: 已完成的列表
    :return:
    """
    route_id_arr: List[WorldPatrolRouteId] = []
    dir_path = os_utils.get_path_under_work_dir('config', 'world_patrol')

    finished_unique_id = [] if finished is None else finished

    for planet in PLANET_LIST:
        planet_dir_path = os.path.join(dir_path, planet.np_id)
        if not os.path.exists(planet_dir_path):
            continue
        for filename in os.listdir(planet_dir_path):
            idx = filename.find('.yml')
            if idx == -1:
                continue
            route_id: WorldPatrolRouteId = WorldPatrolRouteId(planet, filename[0:idx])
            if route_id.unique_id in finished_unique_id:
                continue

            if whitelist is not None:
                if whitelist.type == 'white' and route_id.unique_id not in whitelist.list:
                    continue
                if whitelist.type == 'black' and route_id.unique_id in whitelist.list:
                    continue

            route_id_arr.append(route_id)
    log.info('最终加载 %d 条线路 过滤已完成 %d 条 使用名单 %s',
             len(route_id_arr), len(finished_unique_id), 'None' if whitelist is None else whitelist.name)

    return route_id_arr
