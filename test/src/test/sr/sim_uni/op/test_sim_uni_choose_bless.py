import unittest
from typing import List

import test
from basic.img import MatchResult
from sr.context import get_context
from sr.sim_uni.op.sim_uni_choose_bless import SimUniChooseBless, get_bless_pos, get_bless_by_priority, SimUniDropBless, \
    SimUniUpgradeBless
from sr.sim_uni.sim_uni_challenge_config import SimUniChallengeConfig
from sr.sim_uni.sim_uni_const import SimUniBless, SimUniBlessEnum


class TestSimUniBless(test.SrTestBase):

    def __init__(self, *args, **kwargs):
        test.SrTestBase.__init__(self, *args, **kwargs)

    def test_get_bless(self):
        """
        有3个祝福
        :return:
        """
        ctx = get_context()
        ctx.init_ocr_matcher()
        screen = self.get_test_image('can_reset_1')

        bless_list = get_bless_pos(screen, ctx.ocr, False)

        answer: List[SimUniBless] = [
            SimUniBlessEnum.BLESS_06_023.value,
            SimUniBlessEnum.BLESS_05_017.value,
            SimUniBlessEnum.BLESS_04_022.value
        ]

        self.assertEqual(len(answer), len(bless_list))
        for i in range(len(answer)):
            self.assertEqual(answer[i], bless_list[i].data)

    def test_get_bless_2(self):
        """
        只有2个祝福的情况
        :return:
        """
        ctx = get_context()
        ctx.init_ocr_matcher()
        screen = self.get_test_image('bless_2')

        bless_list = get_bless_pos(screen, ctx.ocr, False)

        answer: List[SimUniBless] = [
            SimUniBlessEnum.BLESS_07_024.value,
            SimUniBlessEnum.BLESS_04_019.value,
        ]

        self.assertEqual(len(answer), len(bless_list))
        for i in range(len(answer)):
            self.assertEqual(answer[i], bless_list[i].data)

    def test_get_bless_before_start(self):
        """
        楼层开始前的情况
        :return:
        """
        screen = self.get_test_image('before_level')

        ctx = get_context()
        ctx.init_ocr_matcher()

        bless_list = get_bless_pos(screen, ctx.ocr, True)

        answer: List[SimUniBless] = [
            SimUniBlessEnum.BLESS_00_001.value,
            SimUniBlessEnum.BLESS_00_002.value,
            SimUniBlessEnum.BLESS_00_003.value,
        ]

        self.assertEqual(len(answer), len(bless_list))
        for i in range(len(answer)):
            self.assertEqual(answer[i], bless_list[i].data)

    def test_can_reset(self):
        ctx = get_context()
        ctx.init_ocr_matcher()

        op = SimUniChooseBless(ctx)
        screen = self.get_test_image('can_reset_1')
        self.assertTrue(op._can_reset(screen))

        screen = self.get_test_image('cant_reset_1')
        self.assertFalse(op._can_reset(screen))

        screen = self.get_test_image('cant_reset_2')
        self.assertFalse(op._can_reset(screen))

    def test_get_bless_to_choose(self):
        """
        按优先级选择祝福
        :return:
        """
        screen = self.get_test_image('cant_reset_1')

        ctx = get_context()
        ctx.init_ocr_matcher()

        op = SimUniChooseBless(ctx, None, before_level_start=False)
        bless_list = get_bless_pos(screen, ctx.ocr, False)

        config = SimUniChallengeConfig(9, mock=True)
        op.config = config

        # 命中骨刃
        config.bless_priority = [SimUniBlessEnum.BLESS_08_017.name, SimUniBlessEnum.BLESS_05_000.name, SimUniBlessEnum.BLESS_01_000.name]
        mr = op._get_bless_to_choose(screen, bless_list)
        self.assertEqual(SimUniBlessEnum.BLESS_08_017.value, mr.data)

        # 命中巡猎
        config.bless_priority = [SimUniBlessEnum.BLESS_05_000.name, SimUniBlessEnum.BLESS_01_000.name]
        mr = op._get_bless_to_choose(screen, bless_list)
        self.assertEqual(SimUniBlessEnum.BLESS_05_015.value, mr.data)

        # 命中存护
        config.bless_priority = []
        config.bless_priority_2 = [SimUniBlessEnum.BLESS_01_000.name]
        mr = op._get_bless_to_choose(screen, bless_list)
        self.assertEqual(SimUniBlessEnum.BLESS_01_024.value, mr.data)

        # 都不命中 选最高级的
        config.bless_priority = []
        config.bless_priority_2 = []
        mr = op._get_bless_to_choose(screen, bless_list)
        self.assertEqual(SimUniBlessEnum.BLESS_05_015.value, mr.data)

        # 重置
        screen = self.get_test_image('can_reset_1')
        config.bless_priority = [SimUniBlessEnum.BLESS_01_000.name]
        config.bless_priority_2 = [SimUniBlessEnum.BLESS_01_000.name]
        bless_list = get_bless_pos(screen, ctx.ocr, False)
        mr = op._get_bless_to_choose(screen, bless_list)
        self.assertIsNone(mr)

    def test_drop_get_bless_2(self):
        ctx = get_context()
        ctx.init_ocr_matcher()

        screen = self.get_test_image('drop_bless_2')

        bless_pos_list: List[MatchResult] = get_bless_pos(screen, ctx.ocr, False)
        bless_list = [bless.data for bless in bless_pos_list]

        answer: List[SimUniBless] = [
            SimUniBlessEnum.BLESS_01_007.value,
            SimUniBlessEnum.BLESS_08_009.value,
        ]

        self.assertEqual(len(answer), len(bless_list))
        for i in range(len(answer)):
            self.assertEqual(answer[i], bless_list[i])

        priority = SimUniChallengeConfig([SimUniBlessEnum.BLESS_01_007.name, SimUniBlessEnum.BLESS_08_009.name], [])
        target_curio_pos: int = get_bless_by_priority(bless_list, priority, can_reset=False, asc=False)
        self.assertEqual(1, target_curio_pos)

    def test_upgrade_get_bless_pos(self):
        ctx = get_context()
        ctx.init_ocr_matcher()
        ctx.init_image_matcher()

        op = SimUniUpgradeBless(ctx)

        screen = self.get_test_image('upgrade')
        pos = op._get_bless_pos(screen)
        self.assertIsNotNone(pos)

    def test_op(self):
        ctx = get_context()
        ctx.start_running()

        op = SimUniChooseBless(ctx, None, before_level_start=False)
        op.execute()

    def test_drop_op(self):
        ctx = get_context()
        ctx.start_running()

        op = SimUniDropBless(ctx, None)
        op.execute()

    def test_upgrade_op(self):
        ctx = get_context()
        ctx.start_running()

        op = SimUniUpgradeBless(ctx)
        op.execute()
