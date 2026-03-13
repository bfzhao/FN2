""" dryrun test """
import asyncio
import pytest

from board import Board, TaskStatus, EscalationType, Acknowledge, Event
from dryrun import DryRun, VerificationInfo
from tests.test_scenarios import test_scenarios
from config import runtime
from main import dump_fn2_tree
from fn2_manager import FN2Manager

# Set up runtime configuration
runtime["dryrun"] = True
for component in runtime["trace"]:
    runtime["trace"][component] = False


class TestRunner:
    def __init__(self, fn2_manager: FN2Manager):
        self.fn2_manager = fn2_manager
        self.board = fn2_manager.get_board()
        self.dryrun = fn2_manager.get_dryrun()
        self.board.register_event(Event.TASK_ESCALATED, [self.handle_escalation])

    def _find_inquery_config(self, task_def, goal):
        """Recursively find task's inquery configuration"""
        if task_def.inquery and task_def.inquery.get("enable"):
            return task_def.inquery

        # Recursively check sub-steps
        for step in task_def.steps:
            if not step.get("atom", True) and "task_def" in step:
                result = self._find_inquery_config(step["task_def"], goal)
                if result:
                    return result
        return None

    async def handle_escalation(self, task):
        """Handle task escalation events, simulate user responses

        Note: Only handle user-initiated tasks (submitter != "system")
        System-initiated subtasks are handled automatically by the system (auto-confirm failure in execution_engine)
        """
        if task.submitter == "system":
            print(f"[Test] Skipping system-initiated task {task.task_id}, handled automatically by system")
            return

        if task.escalation_type == EscalationType.REQ_REFINE and hasattr(self, 'scenario'):
            # Recursively find inquery configuration
            inquery_config = self._find_inquery_config(self.scenario.task_def, task.goal)
            if inquery_config and inquery_config.get("enable"):
                prompt = inquery_config.get("prompt", [])
                if prompt and len(task.actions) > 0:
                    question = task.actions[0].inquery
                    # Find matching answer
                    for qa in prompt:
                        if qa.get("q") == question:
                            answer = qa.get("a", "")
                            ack = qa.get("ack", True)  # Default ack=True
                            print(f"[Test] Simulating user response: question='{question}', answer='{answer}', ack={ack}")
                            await self.board.ack_task(task.task_id, Acknowledge(ack=ack, issue=question, result=answer))
                            return

    async def run_scenario(self, scenario_name: str):
        if scenario_name not in test_scenarios:
            print(f"ERROR: unknown scenario '{scenario_name}'")
            print(f"Available scenarios: {', '.join(test_scenarios.keys())}")
            return False

        self.scenario = test_scenarios[scenario_name]
        self.dryrun.scenario = self.scenario

        print(f"\n{'='*60}")
        print(f"run scenario: {scenario_name}")

        self.dryrun.load_runtime_config()
        
        # Set dryrun for the manager
        if self.fn2_manager and hasattr(self.fn2_manager, 'dryrun'):
            self.fn2_manager.dryrun = self.dryrun
        
        # Spawn FN2 instance
        if self.fn2_manager:
            self.fn2 = await self.fn2_manager.spawn_fn2("test", self.scenario.name)

        max_wait = 30  # wait for 30 seconds
        wait_time = 0
        while wait_time < max_wait:
            await asyncio.sleep(0.1)
            wait_time += 0.1

            # Check if all tasks are completed
            all_done = True
            for t in self.board.list_tasks().values():
                if t.status not in [TaskStatus.VRFY, TaskStatus.ESCL, TaskStatus.ACK]:
                    all_done = False
                    break

            if all_done and len(self.board.list_tasks()) > 0:
                break

        self.dryrun.restore_runtime_config()
        return self.verify_result(scenario_name)

    def verify_result(self, scenario_name: str) -> bool:
        print(f"Verity test result: {scenario_name}")

        root_task = self.fn2.task if self.fn2 else None
        if not root_task:
            print("❌ ERROR: No root task found.")
            return False

        # 获取场景的验证信息
        scenario = test_scenarios.get(scenario_name)
        if not scenario or not scenario.verification:
            print(f"❌ ERROR: Scenario '{scenario_name}' has no verification info.")
            return False

        verification = scenario.verification
        return self._verify_generic_scenario(root_task, verification)

    def _get_children(self, fn2):
        """获取 FN2 节点的子节点"""
        children = []
        if self.fn2_manager and hasattr(self.fn2_manager, 'task_to_fn2'):
            for f in self.fn2_manager.task_to_fn2.values():
                if f.parent == fn2:
                    children.append(f)
        return children

    def _verify_generic_scenario(self, root_task, verification: VerificationInfo) -> bool:
        if verification.root_task_status:
            actual_status = root_task.status.value
            if actual_status != verification.root_task_status:
                print(f"❌ Failed: Root task status is not {verification.root_task_status}, but {actual_status}")
                return False

        if verification.decision:
            if not root_task.verify or verification.decision != root_task.verify.decision.value:
                print(f"❌ Failed: Root task verification decision is not {verification.decision}, but {root_task.verify.decision.value}")
                return False

        if verification.next_suggestion:
            if not root_task.verify or verification.next_suggestion not in root_task.verify.next_suggestion:
                print(f"❌ Failed: Root task verification next suggestion does not contain {verification.next_suggestion}")
                return False

        if verification.extra_count is not None:
            if root_task.extras and len(root_task.extras) != verification.extra_count:
                print(f"❌ Failed: Root task extra info count does not match expected, expected: {verification.extra_count}, actual: {len(root_task.extras)}")
                return False

        if verification.root_task_success is not None:
            if not root_task.result or root_task.result.success != verification.root_task_success:
                print(f"❌ Failed: Root task success status does not match expected, expected: {verification.root_task_success}, actual: {root_task.result.success if root_task.result else 'None'}")
                return False

        if verification.uncertainty_is_not_none and (not root_task.result or root_task.result.uncertainty is None):
            print("❌ Failed: Root task uncertainty value is None")
            return False

        if verification.uncertainty_value is not None:
            if not root_task.result or root_task.result.uncertainty != verification.uncertainty_value:
                print(f"❌ Failed: Root task uncertainty value does not match expected, expected: {verification.uncertainty_value}, actual: {root_task.result.uncertainty if root_task.result else 'None'}")
                return False

        if verification.try_count is not None:
            if root_task.try_count != verification.try_count:
                print(f"❌ Failed: Root task try count does not match expected, expected: {verification.try_count}, actual: {root_task.try_count}")
                return False

        if verification.depth is not None:
            if root_task.depth != verification.depth:
                print(f"❌ Failed: Root task depth does not match expected, expected: {verification.depth}, actual: {root_task.depth}")
                return False

        if verification.result_message_contains:
            if not root_task.result or not root_task.result.result or verification.result_message_contains not in root_task.result.result:
                print(f"❌ Failed: Result message does not contain expected content, actual result: {root_task.result.result if root_task.result else 'None'}")
                return False

        if verification.total_children is not None:
            children = self._get_children(self.fn2)
            if len(children) != verification.total_children:
                print(f"❌ Failed: Child task count does not match expected, expected: {verification.total_children}, actual: {len(children)}")
                return False

        ids = self.board.list_tasks()
        for child_info in verification.child_tasks:
            expected_goal = child_info.get("goal")
            expected_status = child_info.get("status")
            expected_result = child_info.get("result")
            expected_escalation_type = child_info.get("escalation_type")

            if expected_goal and expected_status:
                found = False
                for id in ids:
                    t = self.board.get_task(id)
                    if t.goal == expected_goal:
                        found = True
                        actual_status = t.status.value
                        if expected_status and not actual_status.startswith(expected_status):
                            print(f"❌ Failed: Child task '{expected_goal}' status does not match expected, expected: {expected_status}, actual: {actual_status}")
                            return False
                        if expected_result and not expected_result in t.result.result:
                            print(f"❌ Failed: Child task '{expected_goal}' result does not contain expected content, expected: {expected_result}, actual: {t.result.result.result}")
                            return False
                        if expected_escalation_type and t.escalation_type.value != expected_escalation_type:
                            print(f"❌ Failed: Child task '{expected_goal}' escalation type does not match expected, expected: {expected_escalation_type}, actual: {t.escalation_type.value}")
                            return False
                        break

                if not found:
                    print(f"❌ Failed: No child task found with goal '{expected_goal}'")
                    return False

        print("✅ Scenario test verification passed!")
        return True


async def run_case(scenario: str):
    dryrun = DryRun()
    board = Board()

    async with board:
        fn2_manager = FN2Manager(board=board, dryrun=dryrun)
        runner = TestRunner(fn2_manager)
        success = await runner.run_scenario(scenario)
        print("\nTask Tree:")
        dump_fn2_tree(fn2_manager)
        return success


@pytest.mark.asyncio
async def test_success_scenario():
    """Test success scenario"""
    result = await run_case("success")
    assert result, "Success scenario test failed"


@pytest.mark.asyncio
async def test_failure_scenario():
    """Test failure scenario"""
    result = await run_case("failure")
    assert result, "Failure scenario test failed"


@pytest.mark.asyncio
async def test_nested_scenario():
    """Test nested scenario"""
    result = await run_case("nested")
    assert result, "Nested scenario test failed"


@pytest.mark.asyncio
async def test_retry_scenario():
    """Test retry scenario"""
    result = await run_case("retry")
    assert result, "Retry scenario test failed"


@pytest.mark.asyncio
async def test_inquery_scenario():
    """Test inquery scenario"""
    result = await run_case("inquery")
    assert result, "Inquery scenario test failed"


@pytest.mark.asyncio
async def test_cancel_scenario():
    """Test cancel scenario"""
    result = await run_case("cancel")
    assert result, "Cancel scenario test failed"


@pytest.mark.asyncio
async def test_depth_limit_scenario():
    """Test depth limit scenario"""
    result = await run_case("depth_limit")
    assert result, "Depth limit scenario test failed"


@pytest.mark.asyncio
async def test_subtask_fail_scenario():
    """Test subtask fail scenario"""
    result = await run_case("subtask_fail")
    assert result, "Subtask fail scenario test failed"


@pytest.mark.asyncio
async def test_synthesize_scenario():
    """Test synthesize scenario"""
    result = await run_case("synthesize")
    assert result, "Synthesize scenario test failed"


@pytest.mark.asyncio
async def test_multiple_children_scenario():
    """Test multiple children scenario"""
    result = await run_case("multiple_children")
    assert result, "Multiple children scenario test failed"


@pytest.mark.asyncio
async def test_mixed_children_scenario():
    """Test mixed children scenario"""
    result = await run_case("mixed_children")
    assert result, "Mixed children scenario test failed"


@pytest.mark.asyncio
async def test_empty_steps_scenario():
    """Test empty steps scenario"""
    result = await run_case("empty_steps")
    assert result, "Empty steps scenario test failed"


@pytest.mark.asyncio
async def test_single_step_scenario():
    """Test single step scenario"""
    result = await run_case("single_step")
    assert result, "Single step scenario test failed"


@pytest.mark.asyncio
async def test_auto_retry_disabled_scenario():
    """Test auto retry disabled scenario"""
    result = await run_case("auto_retry_disabled")
    assert result, "Auto retry disabled scenario test failed"


@pytest.mark.asyncio
async def test_auto_retry_enabled_scenario():
    """Test auto retry enabled scenario"""
    result = await run_case("auto_retry_enabled")
    assert result, "Auto retry enabled scenario test failed"


@pytest.mark.asyncio
async def test_auto_fail_disabled_scenario():
    """Test auto fail disabled scenario"""
    result = await run_case("auto_fail_disabled")
    assert result, "Auto fail disabled scenario test failed"


@pytest.mark.asyncio
async def test_auto_fail_enabled_scenario():
    """Test auto fail enabled scenario"""
    result = await run_case("auto_fail_enabled")
    assert result, "Auto fail enabled scenario test failed"
