// 全局变量
let tasks = [];
let allTasks = []; // 保存所有任务，包括派生任务
let escalatedTasks = [];
let notifications = [];
let lastNotificationCheck = 0;
let wsConnection = null;
let wsReconnectAttempts = 0;
const MAX_WS_RECONNECT_ATTEMPTS = 5;
let refreshTimeout = null;
const REFRESH_DELAY = 1000; // 防抖延迟，避免短时间内多次刷新

// API基础URL
const API_BASE = `${window.location.protocol}//${window.location.host}/api`;
// WebSocket URL
const WS_BASE = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/ws/notifications`;

// 初始化
async function init() {
    // 加载初始数据
    await loadInitialData();

    // 连接WebSocket
    connectWebSocket();

    // 绑定事件
    bindEvents();
}

// 加载初始数据
async function loadInitialData() {
    await loadTasks();
    await loadEscalatedTasks();
    await loadNotifications();
}

// 刷新所有数据（用户手动触发或WebSocket连接失败时）
async function refreshAllData() {
    console.log('手动刷新数据');
    await loadTasks();
    await loadEscalatedTasks();
    await loadNotifications();
}

// 防抖刷新函数
function debouncedRefresh() {
    if (refreshTimeout) {
        clearTimeout(refreshTimeout);
    }
    refreshTimeout = setTimeout(async () => {
        console.log('WebSocket消息触发刷新');
        await loadEscalatedTasks();
        await loadTasks();
    }, REFRESH_DELAY);
}

// 连接WebSocket
function connectWebSocket() {
    try {
        wsConnection = new WebSocket(WS_BASE);

        wsConnection.onopen = function (event) {
            console.log('WebSocket连接已建立');
            wsReconnectAttempts = 0;
        };

        wsConnection.onmessage = function (event) {
            try {
                const data = JSON.parse(event.data);
                console.log('WebSocket收到消息:', data);

                // 添加通知到列表
                notifications.push(data);
                updateNotificationBadge();

                // 使用防抖机制刷新数据，避免短时间内多次刷新
                debouncedRefresh();
            } catch (error) {
                console.error('处理WebSocket消息失败:', error);
            }
        };

        wsConnection.onclose = function (event) {
            console.log('WebSocket连接已关闭');
            wsConnection = null;

            // 尝试重连
            if (wsReconnectAttempts < MAX_WS_RECONNECT_ATTEMPTS) {
                wsReconnectAttempts++;
                console.log(`WebSocket将在3秒后重连 (尝试 ${wsReconnectAttempts}/${MAX_WS_RECONNECT_ATTEMPTS})`);
                setTimeout(connectWebSocket, 3000);
            } else {
                console.log('WebSocket重连次数已达上限，将使用手动刷新');
            }
        };

        wsConnection.onerror = function (error) {
            console.error('WebSocket错误:', error);
        };
    } catch (error) {
        console.error('创建WebSocket连接失败:', error);
    }
}

// 绑定事件
function bindEvents() {
    // 创建任务
    try {
        const createTaskBtn = document.getElementById('create-task-btn');
        if (createTaskBtn) {
            createTaskBtn.addEventListener('click', showCreateTaskModal);
        } else {
            console.error('create-task-btn元素不存在');
        }

        const closeCreateTaskModal = document.getElementById('close-create-task-modal');
        if (closeCreateTaskModal) {
            closeCreateTaskModal.addEventListener('click', hideCreateTaskModal);
        }

        const cancelCreateTask = document.getElementById('cancel-create-task');
        if (cancelCreateTask) {
            cancelCreateTask.addEventListener('click', hideCreateTaskModal);
        }

        const submitCreateTask = document.getElementById('submit-create-task');
        if (submitCreateTask) {
            submitCreateTask.addEventListener('click', createTask);
        }

        const taskInput = document.getElementById('task-input');
        if (taskInput) {
            taskInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') createTask();
            });
        }
    } catch (error) {
        console.error('绑定创建任务事件失败:', error);
    }

    // 刷新按钮
    try {
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', refreshAllData);
        }
    } catch (error) {
        console.error('绑定刷新按钮事件失败:', error);
    }

    // 通知按钮
    try {
        const notificationsBtn = document.getElementById('notifications-btn');
        if (notificationsBtn) {
            notificationsBtn.addEventListener('click', showNotifications);
        }

        const closeNotificationModal = document.getElementById('close-notification-modal');
        if (closeNotificationModal) {
            closeNotificationModal.addEventListener('click', hideNotifications);
        }

        const markAllRead = document.getElementById('mark-all-read');
        if (markAllRead) {
            markAllRead.addEventListener('click', markAllNotificationsRead);
        }
    } catch (error) {
        console.error('绑定通知按钮事件失败:', error);
    }

    // 任务详情模态框
    try {
        const closeTaskModal = document.getElementById('close-task-modal');
        if (closeTaskModal) {
            closeTaskModal.addEventListener('click', hideTaskModal);
        }
    } catch (error) {
        console.error('绑定任务详情模态框事件失败:', error);
    }

    // 升级任务模态框
    try {
        const closeEscalationModal = document.getElementById('close-escalation-modal');
        if (closeEscalationModal) {
            closeEscalationModal.addEventListener('click', hideEscalationModal);
        }
    } catch (error) {
        console.error('绑定升级任务模态框事件失败:', error);
    }

    // 任务过滤器
    try {
        const taskFilterBtns = document.querySelectorAll('.task-filter-btn');
        if (taskFilterBtns.length > 0) {
            taskFilterBtns.forEach(btn => {
                btn.addEventListener('click', (e) => {
                    document.querySelectorAll('.task-filter-btn').forEach(b => b.classList.remove('bg-primary', 'text-white'));
                    document.querySelectorAll('.task-filter-btn').forEach(b => b.classList.add('bg-gray-200'));
                    e.target.classList.remove('bg-gray-200');
                    e.target.classList.add('bg-primary', 'text-white');
                    filterTasks(e.target.dataset.filter);
                });
            });
        }
    } catch (error) {
        console.error('绑定任务过滤器事件失败:', error);
    }
}

// 显示创建任务模态框
function showCreateTaskModal() {
    try {
        const createTaskModal = document.getElementById('create-task-modal');
        if (createTaskModal) {
            createTaskModal.classList.remove('hidden');
        }

        const taskInput = document.getElementById('task-input');
        if (taskInput) {
            taskInput.focus();
        }
    } catch (error) {
        console.error('显示创建任务模态框失败:', error);
    }
}

// 隐藏创建任务模态框
function hideCreateTaskModal() {
    try {
        const createTaskModal = document.getElementById('create-task-modal');
        if (createTaskModal) {
            createTaskModal.classList.add('hidden');
        }

        const taskInput = document.getElementById('task-input');
        if (taskInput) {
            taskInput.value = '';
        }
    } catch (error) {
        console.error('隐藏创建任务模态框失败:', error);
    }
}

// 加载任务
async function loadTasks() {
    try {
        const response = await fetch(`${API_BASE}/tasks`);
        const data = await response.json();

        // 保存所有任务（包括派生任务）
        allTasks = data.tasks || [];

        // 只显示用户任务（submitter为"user"的任务）在任务列表中
        tasks = (data.tasks || []).filter(task => task.submitter === 'user');

        renderTaskList();
        updateTaskStats();
        renderTaskTree();
    } catch (error) {
        console.error('加载任务失败:', error);
    }
}

// 加载升级任务
async function loadEscalatedTasks() {
    try {
        const response = await fetch(`${API_BASE}/escalated-tasks`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        escalatedTasks = data.tasks || [];
        renderEscalatedTasks();
        updateTaskStats();
    } catch (error) {
        console.error('加载升级任务失败:', error);
        // 即使失败也继续执行，避免页面卡住
        escalatedTasks = [];
        renderEscalatedTasks();
        updateTaskStats();
    }
}

// 加载通知（备用）
async function loadNotifications() {
    try {
        const response = await fetch(`${API_BASE}/notifications?since=${lastNotificationCheck}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();

        if (data.events && data.events.length > 0) {
            notifications = [...notifications, ...data.events];
            lastNotificationCheck = Date.now() / 1000;
            updateNotificationBadge();
        }
    } catch (error) {
        console.error('加载通知失败:', error);
        // 即使失败也继续执行，避免页面卡住
    }
}

// 创建任务
async function createTask() {
    try {
        const taskInput = document.getElementById('task-input');
        if (!taskInput) {
            console.error('task-input元素不存在');
            return;
        }

        const goal = taskInput.value.trim();

        if (!goal) {
            alert('请输入任务目标');
            return;
        }

        const response = await fetch(`${API_BASE}/task`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ goal })
        });

        if (response.ok) {
            // 任务成功后不提示，直接关闭模态框并刷新任务列表
            hideCreateTaskModal();
            await loadTasks();
        } else {
            alert('任务创建失败');
        }
    } catch (error) {
        console.error('创建任务失败:', error);
        alert('任务创建失败');
    }
}

// 判断任务是否为进行中
function isTaskRunning(status) {
    const runningStatuses = ['initalized', 'accepted', 'ambiguous', 'analyzed', 'execution done', 'synthesized', 'verified'];
    return runningStatuses.includes(status);
}

// 判断任务是否已完成
function isTaskCompleted(status) {
    return status === 'acknowledged';
}

// 判断任务是否需要处理
function isTaskPending(status) {
    return status === 'escalated';
}

// 获取任务状态显示文本
function getTaskStatusText(status) {
    if (isTaskRunning(status)) return '进行中';
    if (isTaskCompleted(status)) return '已完成';
    if (isTaskPending(status)) return '需处理';
    return status;
}

// 渲染任务列表
function renderTaskList(filter = 'all') {
    try {
        const taskList = document.getElementById('task-list');
        if (!taskList) {
            console.error('task-list元素不存在');
            return;
        }

        let filteredTasks = tasks;
        if (filter === 'running') {
            filteredTasks = tasks.filter(task => isTaskRunning(task.status));
        } else if (filter === 'completed') {
            filteredTasks = tasks.filter(task => isTaskCompleted(task.status));
        }

        if (filteredTasks.length === 0) {
            taskList.innerHTML = `
                <div class="text-center text-gray-500 py-8">
                    <i class="fa fa-tasks text-3xl mb-2"></i>
                    <p>暂无任务</p>
                </div>
            `;
            return;
        }

        taskList.innerHTML = filteredTasks.map(task => {
            const statusClass = isTaskRunning(task.status) ? 'bg-warning bg-opacity-20 text-warning' :
                isTaskCompleted(task.status) ? 'bg-success bg-opacity-20 text-success' :
                    'bg-danger bg-opacity-20 text-danger';
            return `
            <div class="border-b border-gray-200 py-3 last:border-0 cursor-pointer hover:bg-gray-50 transition-colors" onclick="showTaskInTree('${task.task_id}')">
                <div class="flex justify-between items-center">
                    <h4 class="font-medium">${task.goal}</h4>
                    <span class="px-2 py-1 rounded-full text-xs font-medium ${statusClass}">
                        ${getTaskStatusText(task.status)}
                    </span>
                </div>
            </div>
            `;
        }).join('');
    } catch (error) {
        console.error('渲染任务列表失败:', error);
    }
}

// 渲染升级任务
function renderEscalatedTasks() {
    try {
        const escalatedTasksEl = document.getElementById('escalated-tasks');
        if (!escalatedTasksEl) {
            console.error('escalated-tasks元素不存在');
            return;
        }

        if (escalatedTasks.length === 0) {
            escalatedTasksEl.innerHTML = `
                <div class="text-center text-gray-500 py-8">
                    <i class="fa fa-exclamation-triangle text-3xl mb-2 text-warning"></i>
                    <p>暂无需要处理的任务</p>
                </div>
            `;
            return;
        }

        escalatedTasksEl.innerHTML = escalatedTasks.map(task => `
            <div class="border-b border-gray-200 py-3 last:border-0">
                <div class="flex justify-between items-start">
                    <div>
                        <h4 class="font-medium">${task.goal}</h4>
                        <p class="text-sm text-gray-500">任务ID: ${task.task_id}</p>
                        <p class="text-sm text-gray-500">类型: ${task.escalation_type}</p>
                    </div>
                    <span class="px-2 py-1 rounded-full text-xs font-medium bg-danger bg-opacity-20 text-danger">
                        需要处理
                    </span>
                </div>
                <div class="mt-2">
                    ${task.inquiries.map((inquiry, index) => `
                        <div class="bg-gray-50 p-2 rounded mb-2">
                            <p class="text-sm font-medium">问题 ${index + 1}:</p>
                            <p class="text-sm">${inquiry.inquery}</p>
                        </div>
                    `).join('')}
                </div>
                <div class="mt-2">
                    <button class="text-xs px-2 py-1 bg-primary text-white rounded hover:bg-blue-600 transition-all-300" onclick="showEscalationForm('${task.task_id}')">
                        处理任务
                    </button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('渲染升级任务失败:', error);
    }
}

// 全局变量：当前选中的任务ID
let selectedTaskId = null;

// 显示任务在任务树中
function showTaskInTree(taskId) {
    selectedTaskId = taskId;
    renderTaskTree();
}

// 渲染任务树
function renderTaskTree() {
    try {
        const taskTree = document.getElementById('task-tree');
        if (!taskTree) {
            console.error('task-tree元素不存在');
            return;
        }

        if (allTasks.length === 0) {
            taskTree.innerHTML = `
                <div class="text-center text-gray-500 py-8">
                    <i class="fa fa-sitemap text-3xl mb-2"></i>
                    <p>暂无任务树数据</p>
                </div>
            `;
            return;
        }

        // 如果有选中的任务，显示该任务的详细信息
        if (selectedTaskId) {
            const task = allTasks.find(t => t.task_id === selectedTaskId);
            if (task) {
                renderTaskDetails(task);
                return;
            }
        }

        // 否则显示所有用户任务及其派生任务的树状结构
        // 首先找到所有用户任务（根任务）
        const rootTasks = allTasks.filter(task => task.submitter === 'user');

        taskTree.innerHTML = `
            <div class="space-y-4">
                ${rootTasks.map(task => renderTaskNode(task)).join('')}
            </div>
        `;
    } catch (error) {
        console.error('渲染任务树失败:', error);
    }
}

// 获取任务的派生任务
function getDerivedTasks(taskId) {
    return allTasks.filter(task => task.parent_id === taskId);
}

// 获取与步骤关联的派生任务
function getStepDerivedTasks(stepTrackId) {
    return allTasks.find(task => task.task_id === stepTrackId);
}

// 渲染单个任务节点
function renderTaskNode(task, level = 0) {
    const indent = level * 20;
    const statusClass = isTaskRunning(task.status) ? 'bg-warning bg-opacity-20 text-warning' :
        isTaskCompleted(task.status) ? 'bg-success bg-opacity-20 text-success' :
            'bg-danger bg-opacity-20 text-danger';

    // 获取派生任务
    const derivedTasks = getDerivedTasks(task.task_id);

    return `
        <div class="border-l-2 border-gray-200 pl-4" style="margin-left: ${indent}px">
            <div class="bg-white p-3 rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow cursor-pointer ${selectedTaskId === task.task_id ? 'ring-2 ring-primary' : ''}"
                 onclick="showTaskInTree('${task.task_id}')">
                <div class="flex justify-between items-start">
                    <div class="flex-1">
                        <h4 class="font-medium text-gray-900">${task.goal}</h4>
                        <div class="flex items-center gap-2 mt-1">
                            <span class="text-xs text-gray-500">ID: ${task.task_id.substring(0, 8)}...</span>
                            <span class="px-2 py-0.5 rounded-full text-xs font-medium ${statusClass}">
                                ${getTaskStatusText(task.status)}
                            </span>
                            ${task.submitter !== 'user' ? `<span class="text-xs text-gray-500">派生任务</span>` : ''}
                        </div>
                    </div>
                </div>
                ${task.actions && task.actions.length > 0 ? `
                    <div class="mt-3 space-y-3">
                        ${task.actions.map((action, index) => {
        // 检查是否有与该步骤关联的派生任务
        const derivedTask = action.result && action.result.track_id ? getStepDerivedTasks(action.result.track_id) : null;

        return `
                                <div class="bg-gray-50 p-3 rounded text-sm">
                                    <div class="flex items-center gap-2">
                                        <span class="text-xs font-medium text-gray-500">步骤 ${index + 1}:</span>
                                        <span class="text-xs text-gray-400">${action.type}</span>
                                    </div>
                                    ${action.request ? `<p class="mt-1 text-gray-700">请求: ${action.request}</p>` : ''}
                                    ${action.operation ? `<p class="mt-1 text-gray-700">操作: ${action.operation}</p>` : ''}
                                    ${action.inquery ? `<p class="mt-1 text-gray-700">询问: ${action.inquery}</p>` : ''}
                                    ${action.result ? `
                                        <div class="mt-2 p-2 bg-white rounded border border-gray-200">
                                            <p class="text-xs text-gray-500">结果:</p>
                                            <p class="text-sm ${action.result.success ? 'text-success' : 'text-danger'}">
                                                ${action.result.success ? '✓' : '✗'} ${action.result.result || ''}
                                            </p>
                                            ${action.result.observation ? `<p class="text-xs text-gray-600 mt-1">${action.result.observation}</p>` : ''}
                                        </div>
                                    ` : ''}
                                    ${derivedTask ? `
                                        <div class="mt-3 pl-4 border-l-2 border-blue-200">
                                            <div class="bg-blue-50 p-2 rounded text-sm cursor-pointer hover:bg-blue-100 transition-colors"
                                                 onclick="event.stopPropagation(); showTaskInTree('${derivedTask.task_id}')">
                                                <div class="flex items-center gap-2">
                                                    <span class="text-xs font-medium text-blue-600">派生任务:</span>
                                                    <span class="text-xs text-blue-500">${derivedTask.goal}</span>
                                                </div>
                                                <div class="flex items-center gap-2 mt-1">
                                                    <span class="text-xs text-gray-500">ID: ${derivedTask.task_id.substring(0, 8)}...</span>
                                                    <span class="px-2 py-0.5 rounded-full text-xs font-medium ${isTaskRunning(derivedTask.status) ? 'bg-warning bg-opacity-20 text-warning' : isTaskCompleted(derivedTask.status) ? 'bg-success bg-opacity-20 text-success' : 'bg-danger bg-opacity-20 text-danger'}">
                                                        ${getTaskStatusText(derivedTask.status)}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                    ` : ''}
                                </div>
                            `;
    }).join('')}
                    </div>
                ` : ''}
                ${task.result ? `
                    <div class="mt-3 p-3 bg-gray-50 rounded-lg">
                        <p class="text-xs text-gray-500 mb-1">最终结果:</p>
                        <p class="text-sm ${task.result.success ? 'text-success' : 'text-danger'}">
                            ${task.result.success ? '✓ 成功' : '✗ 失败'} - ${task.result.result || ''}
                        </p>
                        ${task.result.uncertainty ? `<p class="text-xs text-gray-500 mt-1">置信度: ${(task.result.uncertainty * 100).toFixed(1)}%</p>` : ''}
                    </div>
                ` : ''}
            </div>
        </div>
    `;
}

// 渲染任务详情
function renderTaskDetails(task) {
    try {
        const taskTree = document.getElementById('task-tree');
        if (!taskTree) {
            console.error('task-tree元素不存在');
            return;
        }

        const statusClass = isTaskRunning(task.status) ? 'bg-warning bg-opacity-20 text-warning' :
            isTaskCompleted(task.status) ? 'bg-success bg-opacity-20 text-success' :
                'bg-danger bg-opacity-20 text-danger';

        taskTree.innerHTML = `
            <div class="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
                <div class="flex justify-between items-start mb-4">
                    <div>
                        <h3 class="text-lg font-semibold text-gray-900">${task.goal}</h3>
                        <div class="flex items-center gap-2 mt-2">
                            <span class="text-sm text-gray-500">任务ID: ${task.task_id}</span>
                            <span class="px-2 py-1 rounded-full text-xs font-medium ${statusClass}">
                                ${getTaskStatusText(task.status)}
                            </span>
                            <span class="text-xs text-gray-500">提交者: ${task.submitter}</span>
                            ${task.parent_id ? `<span class="text-xs text-gray-500">父任务: ${task.parent_id.substring(0, 8)}...</span>` : ''}
                        </div>
                    </div>
                    <button onclick="selectedTaskId = null; renderTaskTree();" class="text-gray-400 hover:text-gray-600">
                        <i class="fa fa-times"></i> 返回列表
                    </button>
                </div>

                ${task.actions && task.actions.length > 0 ? `
                    <div class="mt-6">
                        <h4 class="font-medium text-gray-900 mb-3">执行步骤</h4>
                        <div class="space-y-4">
                            ${task.actions.map((action, index) => {
            // 检查是否有与该步骤关联的派生任务
            const derivedTask = action.result && action.result.track_id ? getStepDerivedTasks(action.result.track_id) : null;

            return `
                                    <div class="border-l-4 ${action.result && action.result.success ? 'border-success' : action.result ? 'border-danger' : 'border-gray-300'} pl-4 py-3">
                                        <div class="flex items-center gap-2 mb-2">
                                            <span class="text-sm font-medium text-gray-700">步骤 ${index + 1}</span>
                                            <span class="text-xs text-gray-500">[${action.type}]</span>
                                            ${action.result ? `
                                                <span class="text-xs ${action.result.success ? 'text-success' : 'text-danger'}">
                                                    ${action.result.success ? '✓ 成功' : '✗ 失败'}
                                                </span>
                                            ` : ''}
                                        </div>
                                        ${action.request ? `<p class="text-sm text-gray-600 mb-1"><span class="font-medium">请求:</span> ${action.request}</p>` : ''}
                                        ${action.operation ? `<p class="text-sm text-gray-600 mb-1"><span class="font-medium">操作:</span> ${action.operation}</p>` : ''}
                                        ${action.inquery ? `<p class="text-sm text-gray-600 mb-1"><span class="font-medium">询问:</span> ${action.inquery}</p>` : ''}
                                        ${action.result ? `
                                            <div class="mt-2 bg-gray-50 p-3 rounded">
                                                <p class="text-xs text-gray-500 mb-1">执行结果:</p>
                                                <p class="text-sm text-gray-700">${action.result.result || ''}</p>
                                                ${action.result.observation ? `<p class="text-xs text-gray-500 mt-1">观察: ${action.result.observation}</p>` : ''}
                                            </div>
                                        ` : ''}
                                        ${derivedTask ? `
                                            <div class="mt-3 pl-4 border-l-2 border-blue-200">
                                                <div class="bg-blue-50 p-2 rounded text-sm cursor-pointer hover:bg-blue-100 transition-colors"
                                                     onclick="event.stopPropagation(); showTaskInTree('${derivedTask.task_id}')">
                                                    <h5 class="font-medium text-blue-700">派生任务</h5>
                                                    <p class="text-sm text-blue-600 mt-1">${derivedTask.goal}</p>
                                                    <div class="flex items-center gap-2 mt-1">
                                                        <span class="text-xs text-gray-500">ID: ${derivedTask.task_id.substring(0, 8)}...</span>
                                                        <span class="px-2 py-0.5 rounded-full text-xs font-medium ${isTaskRunning(derivedTask.status) ? 'bg-warning bg-opacity-20 text-warning' : isTaskCompleted(derivedTask.status) ? 'bg-success bg-opacity-20 text-success' : 'bg-danger bg-opacity-20 text-danger'}">
                                                            ${getTaskStatusText(derivedTask.status)}
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>
                                        ` : ''}
                                    </div>
                                `;
        }).join('')}
                        </div>
                    </div>
                ` : '<p class="text-gray-500 text-center py-4">暂无执行步骤信息</p>'}

                ${task.result ? `
                    <div class="mt-6 p-4 bg-gray-50 rounded-lg">
                        <h4 class="font-medium text-gray-900 mb-2">最终结果</h4>
                        <p class="text-sm ${task.result.success ? 'text-success' : 'text-danger'}">
                            ${task.result.success ? '✓ 任务成功完成' : '✗ 任务执行失败'}
                        </p>
                        <p class="text-gray-700 mt-1">${task.result.result || ''}</p>
                        ${task.result.uncertainty ? `<p class="text-xs text-gray-500 mt-2">置信度: ${(task.result.uncertainty * 100).toFixed(1)}%</p>` : ''}
                    </div>
                ` : ''}
            </div>
        `;
    } catch (error) {
        console.error('渲染任务详情失败:', error);
    }
}

// 过滤任务
function filterTasks(filter) {
    renderTaskList(filter);
}

// 更新任务统计
function updateTaskStats() {
    try {
        const runningCount = tasks.filter(task => isTaskRunning(task.status)).length;
        const completedCount = tasks.filter(task => isTaskCompleted(task.status)).length;
        const pendingCount = escalatedTasks.length;

        const totalTasksEl = document.getElementById('total-tasks');
        if (totalTasksEl) {
            totalTasksEl.textContent = tasks.length;
        }

        const runningTasksEl = document.getElementById('running-tasks');
        if (runningTasksEl) {
            runningTasksEl.textContent = runningCount;
        }

        const completedTasksEl = document.getElementById('completed-tasks');
        if (completedTasksEl) {
            completedTasksEl.textContent = completedCount;
        }

        const pendingTasksEl = document.getElementById('pending-tasks');
        if (pendingTasksEl) {
            pendingTasksEl.textContent = pendingCount;
        }
    } catch (error) {
        console.error('更新任务统计失败:', error);
    }
}

// 更新通知徽章
function updateNotificationBadge() {
    try {
        const badge = document.getElementById('notification-badge');
        if (badge) {
            if (notifications.length > 0) {
                badge.textContent = notifications.length;
                badge.classList.remove('hidden');
            } else {
                badge.classList.add('hidden');
            }
        }
    } catch (error) {
        console.error('更新通知徽章失败:', error);
    }
}

// 显示通知
function showNotifications() {
    try {
        const notificationList = document.getElementById('notification-list');
        if (!notificationList) {
            console.error('notification-list元素不存在');
            return;
        }

        if (notifications.length === 0) {
            notificationList.innerHTML = `
                <div class="text-center text-gray-500 py-4">
                    <i class="fa fa-bell-o text-2xl mb-2"></i>
                    <p>暂无通知</p>
                </div>
            `;
        } else {
            notificationList.innerHTML = notifications.map(notification => `
                <div class="border-b border-gray-200 py-3 last:border-0">
                    <div class="flex items-start">
                        <div class="flex-1">
                            <p class="text-sm font-medium text-gray-900">${notification.message || '新通知'}</p>
                            <p class="text-xs text-gray-500 mt-1">任务ID: ${notification.task_id?.substring(0, 8)}...</p>
                            <p class="text-xs text-gray-400 mt-1">${new Date(notification.timestamp * 1000).toLocaleString()}</p>
                        </div>
                    </div>
                </div>
            `).join('');
        }

        const notificationModal = document.getElementById('notification-modal');
        if (notificationModal) {
            notificationModal.classList.remove('hidden');
        }
    } catch (error) {
        console.error('显示通知失败:', error);
    }
}

// 隐藏通知
function hideNotifications() {
    try {
        const notificationModal = document.getElementById('notification-modal');
        if (notificationModal) {
            notificationModal.classList.add('hidden');
        }
    } catch (error) {
        console.error('隐藏通知失败:', error);
    }
}

// 标记所有通知为已读
function markAllNotificationsRead() {
    notifications = [];
    updateNotificationBadge();
    hideNotifications();
}

// 隐藏任务详情模态框
function hideTaskModal() {
    try {
        const taskModal = document.getElementById('task-modal');
        if (taskModal) {
            taskModal.classList.add('hidden');
        }
    } catch (error) {
        console.error('隐藏任务详情模态框失败:', error);
    }
}

// 显示升级任务表单
function showEscalationForm(taskId) {
    try {
        const task = escalatedTasks.find(t => t.task_id === taskId);
        if (!task) return;

        const content = document.getElementById('escalation-form');
        if (!content) {
            console.error('escalation-form元素不存在');
            return;
        }

        content.innerHTML = `
            <div class="space-y-4">
                <div class="bg-gray-50 p-3 rounded">
                    <h4 class="font-medium text-gray-900">${task.goal}</h4>
                    <p class="text-sm text-gray-500">任务ID: ${task.task_id}</p>
                </div>
                <div class="space-y-3">
                    ${task.inquiries.map((inquiry, index) => `
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">问题 ${index + 1}: ${inquiry.inquery}</label>
                            <textarea id="answer-${index}" class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary" rows="3" placeholder="请输入您的回答..."></textarea>
                        </div>
                    `).join('')}
                </div>
                <div class="mt-4 flex justify-end">
                    <button class="px-4 py-2 bg-primary text-white rounded-md hover:bg-blue-600 transition-all-300" onclick="submitEscalation('${task.task_id}')">
                        提交回答
                    </button>
                </div>
            </div>
        `;

        const escalationModal = document.getElementById('escalation-modal');
        if (escalationModal) {
            escalationModal.classList.remove('hidden');
        }
    } catch (error) {
        console.error('显示升级任务表单失败:', error);
    }
}

// 隐藏升级任务模态框
function hideEscalationModal() {
    try {
        const escalationModal = document.getElementById('escalation-modal');
        if (escalationModal) {
            escalationModal.classList.add('hidden');
        }
    } catch (error) {
        console.error('隐藏升级任务模态框失败:', error);
    }
}

// 提交升级任务回答
async function submitEscalation(taskId) {
    try {
        const task = escalatedTasks.find(t => t.task_id === taskId);
        if (!task) return;

        const answers = [];
        task.inquiries.forEach((_, index) => {
            const answer = document.getElementById(`answer-${index}`).value.trim();
            if (answer) {
                answers.push({
                    issue: task.inquiries[index].inquery,
                    result: answer
                });
            }
        });

        if (answers.length === 0) {
            alert('请至少回答一个问题');
            return;
        }

        // 为每个问题提交一个回答
        for (const answer of answers) {
            const response = await fetch(`${API_BASE}/task/${taskId}/acknowledge`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(answer)
            });

            if (!response.ok) {
                throw new Error('提交失败');
            }
        }

        hideEscalationModal();
        await loadEscalatedTasks();
        await loadTasks();
    } catch (error) {
        console.error('提交回答失败:', error);
        alert('提交回答失败');
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', init);
