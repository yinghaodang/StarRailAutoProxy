from typing import Optional, List

from basic.log_utils import log
from sr.app.app_run_record import AppRunRecord
from sr.context import Context
from sr.operation import Operation, OperationResult, StateOperation, StateOperationNode, StateOperationEdge
from sr.operation.unit.enter_game import EnterGame


class Application(Operation):

    def __init__(self, ctx: Context, op_name: str = None,
                 init_context_before_start: bool = True,
                 stop_context_after_stop: bool = True,
                 run_record: Optional[AppRunRecord] = None):
        super().__init__(ctx, try_times=1,  # 应用只是组装指令 不应该有重试
                         op_name=op_name,
                         )

        self.run_record: Optional[AppRunRecord] = run_record
        """运行记录"""

        self.init_context_before_start: bool = init_context_before_start
        """运行前是否初始化上下文 一条龙只有第一个应用需要"""

        self.stop_context_after_stop: bool = stop_context_after_stop
        """运行后是否停止上下文 一条龙只有最后一个应用需要"""

    def _init_context(self) -> bool:
        """
        上下文的初始化
        :return: 是否初始化成功
        """
        if not self.init_context_before_start:
            return True

        if not self.ctx.start_running():
            return False

        if self.ctx.open_game_by_script:
            op = EnterGame(self.ctx)
            result = op.execute()
            if not result.success:
                log.error('进入游戏失败')
                self.ctx.stop_running()
                return False

        return True

    def execute(self) -> OperationResult:
        if not self._init_context():
            return Operation.op_fail('初始化失败')
        result: OperationResult = super().execute()
        self._stop_context()
        return result

    def on_resume(self):
        super().on_resume()
        self.ctx.controller.init()

    def _stop_context(self):
        if self.stop_context_after_stop:
            self.ctx.stop_running()

    def _after_operation_done(self, result: OperationResult):
        """
        停止后的处理
        :return:
        """
        Operation._after_operation_done(self, result)
        if self.run_record is not None:
            if result.success:
                self.run_record.update_status(AppRunRecord.STATUS_SUCCESS)
            else:
                self.run_record.update_status(AppRunRecord.STATUS_FAIL)

    @property
    def current_execution_desc(self) -> str:
        """
        当前运行的描述 用于UI展示
        :return:
        """
        return ''

    @property
    def next_execution_desc(self) -> str:
        """
        下一步运行的描述 用于UI展示
        :return:
        """
        return ''


class Application2(StateOperation):

    def __init__(self, ctx: Context, try_times: int = 2, op_name: str = None,
                 nodes: Optional[List[StateOperationNode]] = None,
                 edges: Optional[List[StateOperationEdge]] = None,
                 specified_start_node: Optional[StateOperationNode] = None,
                 init_context_before_start: bool = True,
                 stop_context_after_stop: bool = True,
                 run_record: Optional[AppRunRecord] = None):
        super().__init__(ctx, try_times=try_times, op_name=op_name,
                         nodes=nodes, edges=edges, specified_start_node=specified_start_node)

        self.run_record: Optional[AppRunRecord] = run_record
        """运行记录"""

        self.init_context_before_start: bool = init_context_before_start
        """运行前是否初始化上下文 一条龙只有第一个应用需要"""

        self.stop_context_after_stop: bool = stop_context_after_stop
        """运行后是否停止上下文 一条龙只有最后一个应用需要"""

    def _init_context(self) -> bool:
        """
        上下文的初始化
        :return: 是否初始化成功
        """
        if not self.init_context_before_start:
            return True

        if not self.ctx.start_running():
            return False

        if self.ctx.open_game_by_script:
            op = EnterGame(self.ctx)
            result = op.execute()
            if not result.success:
                log.error('进入游戏失败')
                self.ctx.stop_running()
                return False

        return True

    def _init_before_execute(self):
        super()._init_before_execute()
        if self.run_record is not None:
            self.run_record.update_status(AppRunRecord.STATUS_RUNNING)

    def execute(self) -> OperationResult:
        if not self._init_context():
            return Operation.op_fail('初始化失败')
        result: OperationResult = super().execute()
        return result

    def on_resume(self):
        super().on_resume()
        self.ctx.controller.init()

    def _stop_context(self):
        if self.stop_context_after_stop:
            self.ctx.stop_running()

    def _after_operation_done(self, result: OperationResult):
        """
        停止后的处理
        :return:
        """
        super()._after_operation_done(result)
        self._update_record_after_stop(result)
        self._stop_context()

    def _update_record_after_stop(self, result: OperationResult):
        """
        应用停止后的对运行记录的更新
        :param result: 运行结果
        :return:
        """
        if self.run_record is not None:
            if result.success:
                self.run_record.update_status(AppRunRecord.STATUS_SUCCESS)
            else:
                self.run_record.update_status(AppRunRecord.STATUS_FAIL)

    @property
    def current_execution_desc(self) -> str:
        """
        当前运行的描述 用于UI展示
        :return:
        """
        return ''

    @property
    def next_execution_desc(self) -> str:
        """
        下一步运行的描述 用于UI展示
        :return:
        """
        return ''
