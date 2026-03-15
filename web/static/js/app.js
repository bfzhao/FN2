// 全局变量
let tasks = [];
let escalatedTasks = [];
let notifications = [];
let lastNotificationCheck = 0;

// API基础URL
const API_BASE = `${window.location.protocol}//${window.location.host}/api`;

// 初始化
async function init() {
    // 加载数据
    await loadTasks();
    await loadEscalatedTasks();
    await loadNotifications();

    // 设置定时刷新
    setInterval(async () => {
        await loadTasks();
        await loadEscalatedTasks();
        await loadNotifications();
    }, 5000); // 每5秒刷新一次

    // 绑定事件
    bindEvents();
}

// 绑定事件
function bindEvents() {
    // 创建任务
    document.getElementById('create-task-btn').addEventListener('click', showCreateTaskModal);
    document.getElementById('close-create-task-modal').addEventListener('click', hideCreateTaskModal);
    document.getElementById('cancel-create-task').addEventListener('click', hideCreateTaskModal);
    document.getElementById('submit-create-task').addEventListener('click', createTask);
    document.getElementById('task-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') createTask();
    });

    // 刷新按钮
    document.getElementById('refresh-btn').addEventListener('click', async () => {
        await loadTasks();
        await loadEscalatedTasks();
        await loadNotifications();
    });

    // 通知按钮
    document.getElementById('notifications-btn').addEventListener('click', showNotifications);
    document.getElementById('close-notification-modal').addEventListener('click', hideNotifications);
    document.getElementById('mark-all-read').addEventListener('click', markAllNotificationsRead);

    // 任务详情模态框
    document.getElementById('close-task-modal').addEventListener('click', hideTaskModal);

    // 升级任务模态框
    document.getElementById('close-escalation-modal').addEventListener('click', hideEscalationModal);

    // 任务过滤器
    document.querySelectorAll('.task-filter-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.task-filter-btn').forEach(b => b.classList.remove('bg-primary', 'text-white'));
            document.querySelectorAll('.task-filter-btn').forEach(b => b.classList.add('bg-gray-200'));
            e.target.classList.remove('bg-gray-200');
            e.target.classList.add('bg-primary', 'text-white');
            filterTasks(e.target.dataset.filter);
        });
    });
}

// 显示创建任务模态框
function showCreateTaskModal() {
    document.getElementById('create-task-modal').classList.remove('hidden');
    document.getElementById('task-input').focus();
}

// 隐藏创建任务模态框
function hideCreateTaskModal() {
    document.getElementById('create-task-modal').classList.add('hidden');
    document.getElementById('task-input').value = '';
}

// 加载任务
async function loadTasks() {
    try {
        const response = await fetch(`${API_BASE}/tasks`);
        const data = await response.json();

        // 使用API返回的真实任务数据
        tasks = data.tasks || [];

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

// 加载通知
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
    const taskInput = document.getElementById('task-input');
    const goal = taskInput.value.trim();

    if (!goal) {
        alert('请输入任务目标');
        return;
    }

    try {
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

// 渲染任务列表
function renderTaskList(filter = 'all') {
    const taskList = document.getElementById('task-list');

    let filteredTasks = tasks;
    if (filter === 'running') {
        filteredTasks = tasks.filter(task => task.status === 'running');
    } else if (filter === 'completed') {
        filteredTasks = tasks.filter(task => task.status === 'completed');
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

    taskList.innerHTML = filteredTasks.map(task => `
        <div class="border-b border-gray-200 py-3 last:border-0 cursor-pointer hover:bg-gray-50 transition-colors" onclick="showTaskInTree('${task.task_id}')">
            <div class="flex justify-between items-center">
                <h4 class="font-medium">${task.goal}</h4>
                <span class="px-2 py-1 rounded-full text-xs font-medium ${task.status === 'running' ? 'bg-warning bg-opacity-20 text-warning' : 'bg-success bg-opacity-20 text-success'}">
                    ${task.status === 'running' ? '进行中' : '已完成'}
                </span>
            </div>
        </div>
    `).join('');
}

// 渲染升级任务
function renderEscalatedTasks() {
    const escalatedTasksEl = document.getElementById('escalated-tasks');

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
    const taskTree = document.getElementById('task-tree');

    if (tasks.length === 0) {
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
        const selectedTask = tasks.find(t => t.task_id === selectedTaskId);
        if (selectedTask) {
            taskTree.innerHTML = `
                <div class="p-4">
                    <div class="mb-4">
                        <div class="flex items-center mb-2">
                            <div class="w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center mr-3 flex-shrink-0">
                                <i class="fa fa-tasks"></i>
                            </div>
                            <h3 class="font-medium text-lg">${selectedTask.goal}</h3>
                        </div>
                        <div class="ml-11 space-y-2">
                            <p class="text-sm text-gray-500">任务ID: ${selectedTask.task_id}</p>
                            <p class="text-sm text-gray-500">状态: ${selectedTask.status === 'running' ? '进行中' : '已完成'}</p>
                            <p class="text-sm text-gray-500">创建时间: ${new Date(selectedTask.created_at).toLocaleString()}</p>
                        </div>
                    </div>
                    
                    <div class="ml-11 mt-4">
                        <h4 class="font-medium mb-2">任务步骤</h4>
                        <div class="border-l-2 border-gray-200 pl-4 space-y-4">
                            <!-- 这里显示任务的步骤 -->
                            <div class="step-item">
                                <div class="flex items-center mb-1">
                                    <div class="w-6 h-6 rounded-full bg-gray-300 text-white flex items-center justify-center mr-2 flex-shrink-0">
                                        1
                                    </div>
                                    <h5 class="font-medium">初始化任务</h5>
                                </div>
                                <div class="ml-8 text-sm text-gray-600">
                                    <p>任务已创建并准备执行</p>
                                </div>
                            </div>
                            <div class="step-item">
                                <div class="flex items-center mb-1">
                                    <div class="w-6 h-6 rounded-full bg-gray-300 text-white flex items-center justify-center mr-2 flex-shrink-0">
                                        2
                                    </div>
                                    <h5 class="font-medium">执行任务</h5>
                                </div>
                                <div class="ml-8 text-sm text-gray-600">
                                    <p>正在执行任务目标</p>
                                </div>
                            </div>
                            <div class="step-item">
                                <div class="flex items-center mb-1">
                                    <div class="w-6 h-6 rounded-full bg-gray-300 text-white flex items-center justify-center mr-2 flex-shrink-0">
                                        3
                                    </div>
                                    <h5 class="font-medium">完成任务</h5>
                                </div>
                                <div class="ml-8 text-sm text-gray-600">
                                    <p>任务执行完成</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            return;
        }
    }

    // 如果没有选中的任务，显示任务列表
    taskTree.innerHTML = `
        <div class="p-4">
            <p class="text-gray-500 mb-4">点击左侧任务列表中的任务查看详细信息</p>
            <ul class="space-y-4">
                ${tasks.map(task => `
                    <li class="flex items-start cursor-pointer hover:bg-gray-50 p-2 rounded" onclick="showTaskInTree('${task.task_id}')">
                        <div class="w-6 h-6 rounded-full bg-primary text-white flex items-center justify-center mr-3 flex-shrink-0">
                            <i class="fa fa-tasks"></i>
                        </div>
                        <div>
                            <h4 class="font-medium">${task.goal}</h4>
                        </div>
                    </li>
                `).join('')}
            </ul>
        </div>
    `;
}

// 显示任务详情
function showTaskDetails(taskId) {
    const task = tasks.find(t => t.task_id === taskId);
    if (!task) return;

    const modalTitle = document.getElementById('modal-task-title');
    const modalContent = document.getElementById('modal-task-content');

    modalTitle.textContent = `任务详情 - ${task.goal}`;
    modalContent.innerHTML = `
        <div class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-gray-700">任务目标</label>
                <p class="mt-1 p-2 bg-gray-50 rounded">${task.goal}</p>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700">任务ID</label>
                <p class="mt-1 p-2 bg-gray-50 rounded">${task.task_id}</p>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700">状态</label>
                <p class="mt-1 p-2 bg-gray-50 rounded ${task.status === 'running' ? 'text-warning' : 'text-success'}">
                    ${task.status === 'running' ? '进行中' : '已完成'}
                </p>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700">创建时间</label>
                <p class="mt-1 p-2 bg-gray-50 rounded">${new Date(task.created_at).toLocaleString()}</p>
            </div>
        </div>
    `;

    document.getElementById('task-modal').classList.remove('hidden');
}

// 显示升级任务表单
function showEscalationForm(taskId) {
    const task = escalatedTasks.find(t => t.task_id === taskId);
    if (!task) return;

    const escalationForm = document.getElementById('escalation-form');

    escalationForm.innerHTML = `
        <div class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-gray-700">任务目标</label>
                <p class="mt-1 p-2 bg-gray-50 rounded">${task.goal}</p>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700">任务ID</label>
                <p class="mt-1 p-2 bg-gray-50 rounded">${task.task_id}</p>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700">需要回答的问题</label>
                ${task.inquiries.map((inquiry, index) => `
                    <div class="mt-2">
                        <p class="text-sm font-medium">问题 ${index + 1}:</p>
                        <p class="text-sm mb-2">${inquiry.inquery}</p>
                        <input type="text" id="answer-${index}" placeholder="输入答案..." class="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent">
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

    document.getElementById('escalation-modal').classList.remove('hidden');
}

// 提交升级任务回答
async function submitEscalation(taskId) {
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

    try {
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

        alert('任务处理成功！');
        hideEscalationModal();
        await loadEscalatedTasks();
    } catch (error) {
        console.error('提交回答失败:', error);
        alert('提交回答失败');
    }
}

// 显示通知
function showNotifications() {
    const notificationList = document.getElementById('notification-list');

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
                    <div class="w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center mr-3 flex-shrink-0">
                        <i class="fa fa-bell"></i>
                    </div>
                    <div>
                        <p class="text-sm font-medium">${notification.message}</p>
                        <p class="text-xs text-gray-500">${new Date(notification.timestamp * 1000).toLocaleString()}</p>
                    </div>
                </div>
            </div>
        `).join('');
    }

    document.getElementById('notification-modal').classList.remove('hidden');
}

// 隐藏通知
function hideNotifications() {
    document.getElementById('notification-modal').classList.add('hidden');
}

// 隐藏任务详情
function hideTaskModal() {
    document.getElementById('task-modal').classList.add('hidden');
}

// 隐藏升级任务表单
function hideEscalationModal() {
    document.getElementById('escalation-modal').classList.add('hidden');
}

// 标记所有通知为已读
function markAllNotificationsRead() {
    notifications = [];
    updateNotificationBadge();
    showNotifications();
}

// 更新通知徽章
function updateNotificationBadge() {
    const badge = document.getElementById('notification-badge');
    badge.textContent = notifications.length;
    if (notifications.length > 0) {
        badge.classList.remove('hidden');
    } else {
        badge.classList.add('hidden');
    }
}

// 更新任务统计
function updateTaskStats() {
    document.getElementById('total-tasks').textContent = tasks.length;
    document.getElementById('running-tasks').textContent = tasks.filter(t => t.status === 'running').length;
    document.getElementById('pending-tasks').textContent = escalatedTasks.length;
}

// 过滤任务
function filterTasks(filter) {
    renderTaskList(filter);
}

// 页面加载完成后初始化
window.addEventListener('DOMContentLoaded', init);