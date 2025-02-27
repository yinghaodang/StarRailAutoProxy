import time
from typing import Optional, List

from cv2.typing import MatLike

from basic import str_utils, Point
from basic.i18_utils import gt
from basic.img import cv2_utils, MatchResult
from basic.log_utils import log
from sr.const.map_const import Planet, Region, PLANET_2_REGION, best_match_region_by_name
from sr.context import Context
from sr.image.sceenshot import large_map
from sr.operation import Operation, StateOperation, OperationOneRoundResult
from sr.screen_area.screen_large_map import ScreenLargeMap


class ChooseRegion(Operation):

    def __init__(self, ctx: Context, region: Region):
        """
        默认已经打开了大地图 且选择了正确的星球。
        选择目标区域
        :param region: 区域
        """
        super().__init__(ctx, try_times=20,
                         op_name=gt('选择区域 %s') % region.display_name,
                         )
        self.planet: Planet = region.planet
        self.region: Region = region

    def _execute_one_round(self) -> OperationOneRoundResult:
        screen = self.screenshot()

        planet = large_map.get_planet(screen, self.ctx.ocr)
        if planet is None or planet != self.planet:
            return Operation.round_fail()  # 目前不在目标星球的大地图了

        if self.check_tp_and_cancel(screen):
            return Operation.round_retry(wait=1)

        # 判断当前选择区域是否目标区域
        current_region_name = large_map.get_active_region_name(screen, self.ctx.ocr)
        current_region = best_match_region_by_name(current_region_name, planet=self.planet)
        log.info('当前区域文本 %s 匹配区域名称 %s', current_region_name, current_region.cn if current_region is not None else '')

        is_current: bool = (current_region is not None and current_region.pr_id == self.region.pr_id)

        # 还没有选好区域
        if not is_current:
            region_pos_list = self.get_region_pos_list(screen)
            pr_id_set: set[str] = set()
            for region_pos in region_pos_list:
                pr_id_set.add(region_pos.data.pr_id)
                if region_pos.data.pr_id == self.region.pr_id:
                    self.ctx.controller.click(region_pos.center)
                    return Operation.round_retry(wait=1)

            # 没有发现目标区域 需要滚动
            with_before_region: bool = False  # 当前区域列表在目标区域之前
            region_list = PLANET_2_REGION.get(self.region.planet.np_id)
            for r in region_list:
                if r.pr_id in pr_id_set:
                    with_before_region = True
                if r.pr_id == self.region.pr_id:
                    break

            self.scroll_region_area(1 if with_before_region else -1)
            return Operation.round_retry(wait=1)

        # 已经选好了区域 还需要选择层数
        if self.region.floor != 0:
            current_floor_str = large_map.get_active_floor(screen, self.ctx.ocr)
            log.info('当前层数 %s', current_floor_str)
            if current_floor_str is None:
                log.error('未找到当前选择的层数')
            target_floor_str = gt('%d层' % self.region.floor, 'ocr')
            log.info('目标层数 %s', target_floor_str)
            if target_floor_str != current_floor_str:
                cl = self.click_target_floor(screen, target_floor_str)
                if not cl:
                    log.error('未成功点击层数')
                    return Operation.round_retry(wait=0.5)
                else:
                    return Operation.round_success(wait=0.5)
            else:  # 已经是目标楼层
                return Operation.round_success(wait=0.5)

        return Operation.round_success()

    def click_target_region(self, screen) -> bool:
        """
        在右侧找到点击区域并点击
        :param screen:
        :return:
        """
        return self.ctx.controller.click_ocr(screen, self.region.cn, rect=large_map.REGION_LIST_RECT,
                                             lcs_percent=self.gc.region_lcs_percent, merge_line_distance=40)

    def get_region_pos_list(self, screen: MatLike) -> List[MatchResult]:
        """
        获取当前屏幕显示的区域
        MatchResult.data = Region
        :param screen:
        :return:
        """
        area = ScreenLargeMap.REGION_LIST.value
        part = cv2_utils.crop_image_only(screen, area.rect)
        ocr_map = self.ctx.ocr.run_ocr(part, merge_line_distance=40)

        result_list: List[MatchResult] = []

        for word, mrl in ocr_map.items():
            if mrl.max is None:
                continue
            result = mrl.max
            region = best_match_region_by_name(word, planet=self.planet)
            if region is not None:
                result.data = region
                result.x += area.rect.left_top.x
                result.y += area.rect.left_top.y
                result_list.append(result)

        return result_list

    def scroll_region_area(self, d: int = 1):
        """
        在选择区域的地方滚动鼠标
        :param d: 滚动距离 正向下 负向上
        :return:
        """
        drag_to = large_map.REGION_LIST_RECT.center
        drag_from = Point(0, d * 200) + drag_to
        self.ctx.controller.drag_to(start=drag_from, end=drag_to, duration=0.5)

    def click_target_floor(self, screen, target_floor_str: str) -> bool:
        """
        点击目标层数
        :param screen: 大地图界面截图
        :param target_floor_str: 层数
        :return:
        """
        return self.ctx.controller.click_ocr(screen, target_floor_str, rect=large_map.FLOOR_LIST_PART,
                                             same_word=True)

    def check_tp_and_cancel(self, screen: MatLike) -> bool:
        """
        检测右边是否出现传送 有的话 点一下空白位置取消
        :param screen:
        :return:
        """
        area = ScreenLargeMap.TP_BTN.value
        if self.find_area(area, screen):
            return self.ctx.controller.click(large_map.EMPTY_MAP_POS)
        return False
