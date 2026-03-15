"""Test scenarios for FN2 dryrun"""

from fn2.dryrun import Scenario, TaskDef, VerificationInfo, RuntimeConfig

def get_success_scenario():
    """Normal success test scenario"""
    return Scenario(
        name="success_test",
        task_def=TaskDef(
            inquery=None,
            steps=[
                dict(
                    atom=True,
                    operation="step1",
                    success=True
                ),
                dict(
                    atom=True,
                    operation="step2",
                    success=True
                ),
                dict(
                    atom=True,
                    operation="step3",
                    success=True
                ),
            ]
        ),
        verification=VerificationInfo(
            root_task_status="verified",
            root_task_success=True
        )
    )

def get_failure_scenario():
    """Step failure test scenario"""
    return Scenario(
        name="failure_test",
        task_def=TaskDef(
            inquery=None,
            steps=[
                dict(
                    atom=True,
                    operation="step1",
                    success=True
                ),
                dict(
                    atom=True,
                    operation="step2",
                    success=False,
                    error="Step 2 failed"
                ),
                dict(
                    atom=True,
                    operation="step3",
                    success=True
                ),
            ]
        ),
        verification=VerificationInfo(
            root_task_status="escalated",
            root_task_success=False
        )
    )

def get_nested_scenario():
    """Nested subtask test scenario"""
    return Scenario(
        name="nested_test",
        task_def=TaskDef(
            inquery=None,
            steps=[
                dict(
                    atom=False,
                    operation="parent_step",
                    task_def=TaskDef(
                        inquery=None,
                        steps=[
                            dict(
                                atom=False,
                                operation="child_step",
                                task_def=TaskDef(
                                    inquery=None,
                                    steps=[
                                        dict(
                                            atom=True,
                                            operation="grandchild_step1",
                                            success=True
                                        ),
                                        dict(
                                            atom=True,
                                            operation="grandchild_step2",
                                            success=True
                                        ),
                                    ]
                                )
                            ),
                            dict(
                                atom=True,
                                operation="child_step2",
                                success=True
                            ),
                        ]
                    )
                ),
                dict(
                    atom=True,
                    operation="final_step",
                    success=True
                ),
            ]
        ),
        verification=VerificationInfo(
            root_task_status="verified",
            root_task_success=True,
            child_tasks=[
                {"goal": "parent_step", "status": "acknowledged"},
                {"goal": "child_step", "status": "acknowledged"}
            ]
        )
    )

def get_retry_scenario():
    """Retry mechanism test scenario"""
    return Scenario(
        name="retry_test",
        runtime_config=RuntimeConfig(
            config={"auto_retry_tasks": False}  # Disable auto retry
        ),
        task_def=TaskDef(
            inquery=None,
            steps=[
                dict(
                    atom=True,
                    operation="flaky_step",
                    success=False,
                    error="Flaky step failed"
                ),
            ]
        ),
        verification=VerificationInfo(
            root_task_status="escalated",
            root_task_success=False,
            decision="ESCALATE",
            next_suggestion="manual retry"
        )
    )

def get_inquery_scenario():
    """User input required test scenario"""
    return Scenario(
        name="inquery_test",
        task_def=TaskDef(
            inquery=dict(
                enable=True,
                prompt=[
                    {"q": "What's your name?", "a": "Test User", "ack": True},
                    {"q": "How old are you?", "a": "30", "ack": True},
                ],
            ),
            steps=[
                dict(
                    atom=True,
                    operation="step1",
                    success=True
                ),
            ]
        ),
        verification=VerificationInfo(
            root_task_status="verified",
            root_task_success=True,
            extra_count=2
        )
    )

def get_cancel_scenario():
    """User cancel task test scenario"""
    return Scenario(
        name="cancel_test",
        task_def=TaskDef(
            inquery=dict(
                enable=True,
                prompt=[
                    {"q": "Do you want to proceed?", "a": "No", "ack": False},  # ack=False means cancel
                ],
            ),
            steps=[
                dict(
                    atom=True,
                    operation="step1",
                    success=True
                ),
            ]
        ),
        verification=VerificationInfo(
            root_task_status="acknowledged",
            root_task_success=False
        )
    )

def get_depth_limit_scenario():
    """Depth limit test scenario - should escalate as capability limit when exceeding max depth"""
    return Scenario(
        name="depth_limit_test",
        task_def=TaskDef(
            inquery=None,
            steps=[
                dict(
                    atom=False,
                    operation="level1",
                    task_def=TaskDef(
                        inquery=None,
                        steps=[
                            dict(
                                atom=False,
                                operation="level2",
                                task_def=TaskDef(
                                    inquery=None,
                                    steps=[
                                        dict(
                                            atom=False,
                                            operation="level3",
                                            task_def=TaskDef(
                                                inquery=None,
                                                steps=[
                                                    dict(
                                                        atom=False,
                                                        operation="level4",
                                                        task_def=TaskDef(
                                                            inquery=None,
                                                            steps=[
                                                                dict(
                                                                    atom=False,
                                                                    operation="level5",
                                                                    task_def=TaskDef(
                                                                        inquery=None,
                                                                        steps=[
                                                                            dict(
                                                                                atom=False,
                                                                                operation="level6",
                                                                                task_def=TaskDef(
                                                                                    inquery=None,
                                                                                    steps=[
                                                                                        dict(
                                                                                            atom=True,
                                                                                            operation="level7_step",
                                                                                            success=True
                                                                                        ),
                                                                                    ]
                                                                                )
                                                                            ),
                                                                        ]
                                                                    )
                                                                ),
                                                            ]
                                                        )
                                                    ),
                                                ]
                                            )
                                        ),
                                    ]
                                )
                            ),
                        ]
                    )
                ),
            ]
        ),
        verification=VerificationInfo(
            root_task_status="verified",
            root_task_success=True
        )
    )

def get_subtask_fail_scenario():
    return Scenario(
        name="subtask_fail_test",
        task_def=TaskDef(
            inquery=None,
            steps=[
                dict(
                    atom=True,
                    operation="prepare_data",
                    success=True
                ),
                dict(
                    atom=False,
                    operation="process_data",
                    task_def=TaskDef(
                        inquery=dict(
                            enable=True,  # 子任务生成 inquery
                            prompt=[
                                {"q": "Please provide the data format", "a": "", "ack": True},
                            ],
                        ),
                        steps=[
                            dict(
                                atom=True,
                                operation="process_step1",
                                success=True
                            ),
                        ]
                    )
                ),
                dict(
                    atom=True,
                    operation="finalize",
                    success=True
                ),
            ]
        ),
        verification=VerificationInfo(
            root_task_status="escalated",
            root_task_success=False,
            child_tasks=[
                {"goal": "process_data", "status": "acknowledged", "result": "auto abort"}
            ]
        )
    )

def get_synthesize_scenario():
    return Scenario(
        name="synthesize_test",
        task_def=TaskDef(
            inquery=None,
            steps=[
                dict(
                    atom=True,
                    operation="step1",
                    success=False,  # 步骤失败
                    error="Step 1 failed"
                ),
                dict(
                    atom=True,
                    operation="step2",
                    success=True
                ),
            ],
            synthesize=dict(
                success=True,  # 显式指定合成结果为成功
                uncertainty=0.0,
                result="Synthesis test completed successfully"
            ),
        ),
        verification=VerificationInfo(
            root_task_status="verified",
            root_task_success=True,
            result_message_contains="Synthesis test completed successfully"
        )
    )

def get_multiple_children_scenario():
    return Scenario(
        name="multiple_children_test",
        task_def=TaskDef(
            inquery=None,
            steps=[
                dict(
                    atom=False,
                    operation="child1",
                    task_def=TaskDef(
                        inquery=None,
                        steps=[
                            dict(atom=True, operation="child1_step1", success=True),
                        ]
                    )
                ),
                dict(
                    atom=False,
                    operation="child2",
                    task_def=TaskDef(
                        inquery=None,
                        steps=[
                            dict(atom=True, operation="child2_step1", success=True),
                        ]
                    )
                ),
                dict(
                    atom=False,
                    operation="child3",
                    task_def=TaskDef(
                        inquery=None,
                        steps=[
                            dict(atom=True, operation="child3_step1", success=True),
                        ]
                    )
                ),
            ]
        ),
        verification=VerificationInfo(
            root_task_status="verified",
            root_task_success=True,
            total_children=3,
            child_tasks=[
                {"goal": "child1", "status": "acknowledged"},
                {"goal": "child2", "status": "acknowledged"},
                {"goal": "child3", "status": "acknowledged"},
            ]
        )
    )

def get_mixed_children_scenario():
    return Scenario(
        name="mixed_children_test",
        task_def=TaskDef(
            inquery=None,
            steps=[
                dict(
                    atom=False,
                    operation="success_child",
                    task_def=TaskDef(
                        inquery=None,
                        steps=[
                            dict(atom=True, operation="success_step", success=True),
                        ]
                    )
                ),
                dict(
                    atom=False,
                    operation="fail_child",
                    task_def=TaskDef(
                        inquery=None,
                        steps=[
                            dict(atom=True, operation="fail_step", success=False, error="Child failed"),
                        ]
                    )
                ),
            ]
        ),
        verification=VerificationInfo(
            root_task_status="escalated",
            root_task_success=False,
            child_tasks=[
                {"goal": "success_child", "status": "acknowledged"},
                {"goal": "fail_child", "status": "acknowledged"},
            ]
        )
    )

def get_empty_steps_scenario():
    return Scenario(
        name="empty_steps_test",
        task_def=TaskDef(
            inquery=None,
            steps=[]
        ),
        verification=VerificationInfo(
            root_task_status="verified",
            root_task_success=True
        )
    )

def get_single_step_scenario():
    return Scenario(
        name="single_step_test",
        task_def=TaskDef(
            inquery=None,
            steps=[
                dict(atom=True, operation="only_step", success=True)
            ]
        ),
        verification=VerificationInfo(
            root_task_status="verified",
            root_task_success=True
        )
    )

def get_auto_retry_disabled_scenario():
    return Scenario(
        name="auto_retry_disabled_test",
        task_def=TaskDef(
            inquery=None,
            steps=[
                dict(
                    atom=True,
                    operation="failing_step",
                    success=False,
                    error="Step failed"
                ),
            ],
            synthesize=dict(
                success=False,
                result="Step failed"
            )
        ),
        verification=VerificationInfo(
            root_task_status="escalated",
            root_task_success=False,
            # next_suggestion="manual retry",
            try_count=1  # Only try once, no retry
        ),
        runtime_config=RuntimeConfig(
            config={"auto_retry_tasks": False}  # Disable auto retry
        )
    )

def get_auto_retry_enabled_scenario():
    return Scenario(
        name="auto_retry_enabled_test",
        task_def=TaskDef(
            inquery=None,
            steps=[
                dict(
                    atom=True,
                    operation="failing_step 1",
                    success=False,
                    error="Step failed"
                ),
            ],
            synthesize=dict(
                success=False,
                result="Step failed"
            )
        ),
        verification=VerificationInfo(
            root_task_status="escalated",
            root_task_success=False,
            try_count=3,  # Initial attempt + 2 retries (max_iterations=3)
            # next_suggestion="eleberate the request",
        ),
        runtime_config=RuntimeConfig(
            config={"auto_retry_tasks": True}  # Enable auto retry
        )
    )

def get_auto_fail_disabled_scenario():
    return Scenario(
        name="auto_fail_disabled_test",
        task_def=TaskDef(
            inquery=None,
            steps=[
                dict(
                    atom=False,
                    operation="system_task",
                    task_def=TaskDef(
                        inquery=dict(
                            enable=True,
                            prompt=[
                                {"q": "System query", "a": "", "ack": False},
                            ],
                        ),
                        steps=[
                            dict(atom=True, operation="step1", success=True),
                        ]
                    )
                ),
            ]
        ),
        verification=VerificationInfo(
            root_task_status="analyzed",
            root_task_success=None,
            child_tasks=[
                {"goal": "system_task", "status": "escalated", "escalation_type": "REFINE" }  # Won't auto fail
            ]
        ),
        runtime_config=RuntimeConfig(
            config={"auto_fail_system_escalation": False}  # Disable system auto failure
        )
    )

def get_auto_fail_enabled_scenario():
    return Scenario(
        name="auto_fail_enabled_test",
        task_def=TaskDef(
            inquery=None,
            steps=[
                dict(
                    atom=False,
                    operation="system_task",
                    task_def=TaskDef(
                        inquery=dict(
                            enable=True,
                            prompt=[
                                {"q": "System query", "a": "", "ack": False},
                            ],
                        ),
                        steps=[
                            dict(atom=True, operation="step1", success=True),
                        ]
                    )
                ),
            ]
        ),
        verification=VerificationInfo(
            root_task_status="escalated",
            root_task_success=False,
            child_tasks=[
                {"goal": "system_task", "status": "acknowledged"}  # Auto fail
            ]
        ),
        runtime_config=RuntimeConfig(
            config={"auto_fail_system_escalation": True}  # Enable system auto failure
        )
    )


test_scenarios = {
    "success": get_success_scenario(),
    "failure": get_failure_scenario(),
    "nested": get_nested_scenario(),
    "retry": get_retry_scenario(),
    "inquery": get_inquery_scenario(),
    "cancel": get_cancel_scenario(),
    "depth_limit": get_depth_limit_scenario(),
    "subtask_fail": get_subtask_fail_scenario(),
    "synthesize": get_synthesize_scenario(),
    "multiple_children": get_multiple_children_scenario(),
    "mixed_children": get_mixed_children_scenario(),
    "empty_steps": get_empty_steps_scenario(),
    "single_step": get_single_step_scenario(),
    "auto_retry_disabled": get_auto_retry_disabled_scenario(),
    "auto_retry_enabled": get_auto_retry_enabled_scenario(),
    "auto_fail_disabled": get_auto_fail_disabled_scenario(),
    "auto_fail_enabled": get_auto_fail_enabled_scenario(),
}
