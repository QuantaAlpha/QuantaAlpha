"""
Factor workflow with session control and evolution support.

Supports three round phases:
- Original: Initial exploration in each direction
- Mutation: Orthogonal exploration from parent trajectories
- Crossover: Hybrid strategies from multiple parents

Supports parallel execution within each phase when enabled.
"""

from typing import Any
from pathlib import Path
import fire
import signal
import sys
import threading
from multiprocessing import Process, Queue
from functools import wraps
import time
import ctypes
import os
import pickle
from quantaalpha.pipeline.settings import ALPHA_AGENT_FACTOR_PROP_SETTING
from quantaalpha.pipeline.planning import generate_parallel_directions
from quantaalpha.pipeline.planning import load_run_config
from quantaalpha.pipeline.loop import AlphaAgentLoop
from quantaalpha.pipeline.evolution import (
    EvolutionController, 
    EvolutionConfig,
    StrategyTrajectory,
    RoundPhase,
)
from quantaalpha.core.exception import FactorEmptyError
from quantaalpha.log import logger
from quantaalpha.log.time import measure_time
from quantaalpha.llm.config import LLM_SETTINGS




def force_timeout():
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 优先选择timeout参数
            seconds = LLM_SETTINGS.factor_mining_timeout
            def handle_timeout(signum, frame):
                logger.error(f"强制终止程序执行，已超过{seconds}秒")
                sys.exit(1)

            # 设置信号处理器
            signal.signal(signal.SIGALRM, handle_timeout)
            # 设置闹钟
            signal.alarm(seconds)

            try:
                result = func(*args, **kwargs)
            finally:
                # 取消闹钟
                signal.alarm(0)
            return result
        return wrapper
    return decorator


def _run_branch(
    direction: str | None,
    step_n: int,
    use_local: bool,
    idx: int,
    log_root: str,
    log_prefix: str,
    quality_gate_cfg: dict = None,
):
    if log_root:
        branch_name = f"{log_prefix}_{idx:02d}"
        branch_log = Path(log_root) / branch_name
        branch_log.mkdir(parents=True, exist_ok=True)
        logger.set_trace_path(branch_log)
    model_loop = AlphaAgentLoop(
        ALPHA_AGENT_FACTOR_PROP_SETTING,
        potential_direction=direction,
        stop_event=None,
        use_local=use_local,
        quality_gate_config=quality_gate_cfg or {},
    )
    model_loop.user_initial_direction = direction
    model_loop.run(step_n=step_n, stop_event=None)


def _run_evolution_task(
    task: dict[str, Any],
    directions: list[str],
    step_n: int,
    use_local: bool,
    user_direction: str | None,
    log_root: str,
    stop_event: threading.Event | None,
    quality_gate_cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    运行单个进化任务（一轮小流程）。
    
    Args:
        task: 进化任务描述
        directions: 原始方向列表
        step_n: 每轮步数
        use_local: 是否使用本地回测
        user_direction: 用户初始方向
        log_root: 日志根目录
        stop_event: 停止事件
        quality_gate_cfg: 质量门控配置
        
    Returns:
        包含轨迹数据的字典
    """
    phase = task["phase"]
    direction_id = task["direction_id"]
    strategy_suffix = task.get("strategy_suffix", "")
    round_idx = task["round_idx"]
    parent_trajectories = task.get("parent_trajectories", [])
    
    # 根据阶段确定方向
    if phase == RoundPhase.ORIGINAL:
        direction = directions[direction_id] if direction_id < len(directions) else None
    elif phase == RoundPhase.MUTATION:
        # 变异轮使用原始方向，但附加策略后缀
        direction = directions[direction_id] if direction_id < len(directions) else None
    else:  # CROSSOVER
        # 交叉轮使用混合方向
        direction = None
    
    # 生成轨迹ID
    trajectory_id = StrategyTrajectory.generate_id(direction_id, round_idx, phase)
    parent_ids = [p.trajectory_id for p in parent_trajectories]
    
    # 设置日志目录
    if log_root:
        branch_name = f"{phase.value}_{round_idx:02d}_{direction_id:02d}"
        branch_log = Path(log_root) / branch_name
        branch_log.mkdir(parents=True, exist_ok=True)
        logger.set_trace_path(branch_log)
    
    logger.info(f"开始进化任务: phase={phase.value}, round={round_idx}, direction={direction_id}")
    
    # 创建并运行循环
    model_loop = AlphaAgentLoop(
        ALPHA_AGENT_FACTOR_PROP_SETTING,
        potential_direction=direction,
        stop_event=stop_event,
        use_local=use_local,
        strategy_suffix=strategy_suffix,
        evolution_phase=phase.value,
        trajectory_id=trajectory_id,
        parent_trajectory_ids=parent_ids,
        direction_id=direction_id,
        round_idx=round_idx,
        quality_gate_config=quality_gate_cfg or {},
    )
    model_loop.user_initial_direction = user_direction
    
    # 运行一轮小流程（5步）
    model_loop.run(step_n=step_n, stop_event=stop_event)
    
    # 获取轨迹数据
    traj_data = model_loop._get_trajectory_data()
    traj_data["task"] = task
    
    return traj_data


def _parallel_task_worker(
    task: dict[str, Any],
    directions: list[str],
    step_n: int,
    use_local: bool,
    user_direction: str | None,
    log_root: str,
    result_queue: Queue,
    task_idx: int,
):
    """
    并行任务工作进程。
    
    在独立进程中运行进化任务，将结果放入队列。
    
    Args:
        task: 进化任务描述
        directions: 原始方向列表
        step_n: 每轮步数
        use_local: 是否使用本地回测
        user_direction: 用户初始方向
        log_root: 日志根目录
        result_queue: 结果队列
        task_idx: 任务索引
    """
    try:
        # 在子进程中禁用文件锁，避免并行执行时的死锁问题
        from quantaalpha.core.conf import RD_AGENT_SETTINGS
        RD_AGENT_SETTINGS.use_file_lock = False
        # 每个子进程使用独立的缓存目录
        RD_AGENT_SETTINGS.pickle_cache_folder_path_str = str(
            Path(log_root) / f"pickle_cache_{task_idx}"
        )
        
        # 注意：task 中的 parent_trajectories 需要序列化，这里用简化版本
        traj_data = _run_evolution_task(
            task=task,
            directions=directions,
            step_n=step_n,
            use_local=use_local,
            user_direction=user_direction,
            log_root=log_root,
            stop_event=None,  # 子进程不使用 stop_event
        )
        result_queue.put({
            "success": True,
            "task_idx": task_idx,
            "task": task,
            "traj_data": traj_data,
        })
    except Exception as e:
        import traceback
        result_queue.put({
            "success": False,
            "task_idx": task_idx,
            "task": task,
            "error": str(e),
            "traceback": traceback.format_exc(),
        })


def _serialize_task_for_parallel(task: dict[str, Any]) -> dict[str, Any]:
    """
    序列化任务以便在子进程中使用。
    
    parent_trajectories 包含复杂对象，需要转换为可序列化格式。
    """
    serialized = task.copy()
    
    # 将 RoundPhase 转换为字符串
    if "phase" in serialized and isinstance(serialized["phase"], RoundPhase):
        serialized["phase"] = serialized["phase"]
    
    # 将 parent_trajectories 中的对象转换为必要信息
    if "parent_trajectories" in serialized:
        serialized["parent_trajectory_ids"] = [
            p.trajectory_id for p in serialized.get("parent_trajectories", [])
        ]
        # 子进程不需要完整的 trajectory 对象，使用空列表
        # strategy_suffix 已经包含了所需信息
        serialized["parent_trajectories"] = []
    
    return serialized


def _run_tasks_parallel(
    tasks: list[dict[str, Any]],
    directions: list[str],
    step_n: int,
    use_local: bool,
    user_direction: str | None,
    log_root: str,
) -> list[dict[str, Any]]:
    """
    并行运行多个进化任务。
    
    Args:
        tasks: 任务列表
        directions: 方向列表
        step_n: 每轮步数
        use_local: 是否使用本地回测
        user_direction: 用户初始方向
        log_root: 日志根目录
        
    Returns:
        结果列表，每个元素包含 task 和 traj_data
    """
    if not tasks:
        return []
    
    result_queue = Queue()
    processes = []
    
    logger.info(f"启动 {len(tasks)} 个并行进化任务")
    
    for idx, task in enumerate(tasks):
        # 序列化任务
        serialized_task = _serialize_task_for_parallel(task)
        
        p = Process(
            target=_parallel_task_worker,
            args=(
                serialized_task,
                directions,
                step_n,
                use_local,
                user_direction,
                log_root,
                result_queue,
                idx,
            ),
        )
        p.start()
        processes.append(p)
        logger.info(f"启动任务 {idx}: phase={task['phase'].value}, direction={task['direction_id']}")
    
    # 收集结果
    results = []
    for _ in range(len(tasks)):
        result = result_queue.get()
        if result["success"]:
            # 恢复原始 task（包含完整的 parent_trajectories）
            original_task = tasks[result["task_idx"]]
            result["task"] = original_task
            result["traj_data"]["task"] = original_task
            results.append(result)
            logger.info(f"任务 {result['task_idx']} 完成")
        else:
            logger.error(f"任务 {result['task_idx']} 失败: {result['error']}")
            logger.error(result.get('traceback', ''))
    
    # 等待所有进程结束
    for p in processes:
        p.join()
    
    logger.info(f"并行任务完成: {len(results)}/{len(tasks)} 成功")
    
    return results


def run_evolution_loop(
    initial_direction: str | None,
    evolution_cfg: dict[str, Any],
    exec_cfg: dict[str, Any],
    planning_cfg: dict[str, Any],
    stop_event: threading.Event | None = None,
    quality_gate_cfg: dict[str, Any] | None = None,
):
    """
    运行进化循环：原始轮 → 变异轮 → 交叉轮 → 变异轮 → ...
    
    支持并行执行：
    - 原始轮：n个方向可以并行
    - 变异轮：各条线可以并行
    - 交叉轮：选完父代后，不同组合可以并行
    
    Args:
        initial_direction: 用户初始方向
        evolution_cfg: 进化配置
        exec_cfg: 执行配置
        planning_cfg: 规划配置
        stop_event: 停止事件
        quality_gate_cfg: 质量门控配置
    """
    quality_gate_cfg = quality_gate_cfg or {}
    # 在进化模式下禁用文件锁，避免并行/递归调用时的死锁问题
    from quantaalpha.core.conf import RD_AGENT_SETTINGS
    RD_AGENT_SETTINGS.use_file_lock = False
    logger.info("进化模式：已禁用文件锁以避免死锁")
    
    # 解析配置
    num_directions = int(planning_cfg.get("num_directions", 2))
    max_rounds = int(evolution_cfg.get("max_rounds", 10))
    crossover_size = int(evolution_cfg.get("crossover_size", 2))
    crossover_n = int(evolution_cfg.get("crossover_n", 3))
    steps_per_loop = int(exec_cfg.get("steps_per_loop", 5))
    use_local = bool(exec_cfg.get("use_local", True))
    
    # 进化阶段启用配置
    mutation_enabled = bool(evolution_cfg.get("mutation_enabled", True))
    crossover_enabled = bool(evolution_cfg.get("crossover_enabled", True))
    
    # 父代选择策略配置
    parent_selection_strategy = str(evolution_cfg.get("parent_selection_strategy", "best"))
    top_percent_threshold = float(evolution_cfg.get("top_percent_threshold", 0.3))
    
    # 使用当前实验的日志目录作为轨迹池根目录，确保多实验隔离
    # logger.log_trace_path 是每个实验的专属目录（如 log/2026-01-16_10-01-59-778290/）
    log_root = str(logger.log_trace_path)
    
    # 并行配置
    parallel_enabled = bool(evolution_cfg.get("parallel_enabled", False))
    
    # 轨迹池配置：是否每次从空池开始
    fresh_start = bool(evolution_cfg.get("fresh_start", True))
    # 实验结束后是否清理轨迹池文件
    cleanup_on_finish = bool(evolution_cfg.get("cleanup_on_finish", False))
    
    # 生成初始方向
    # 检查 planning.enabled 配置
    planning_enabled = bool(planning_cfg.get("enabled", False))
    prompt_file = planning_cfg.get("prompt_file") or "planning_prompts.yaml"
    prompt_path = Path(__file__).parent / "prompts" / str(prompt_file)
    
    if planning_enabled and initial_direction:
        # planning 启用时：使用 LLM 生成多个方向
        directions = generate_parallel_directions(
            initial_direction=initial_direction,
            n=num_directions,
            prompt_file=prompt_path,
            max_attempts=int(planning_cfg.get("max_attempts", 5)),
            use_llm=bool(planning_cfg.get("use_llm", True)),
            allow_fallback=bool(planning_cfg.get("allow_fallback", True)),
        )
    elif planning_enabled:
        # planning 启用但无初始方向：使用默认方向列表
        directions = [None] * num_directions
    else:
        # planning 禁用：只使用单一方向
        directions = [initial_direction] if initial_direction else [None]
    
    logger.info(f"生成了 {len(directions)} 个探索方向")
    for i, d in enumerate(directions):
        logger.info(f"  方向 {i}: {d}")
    
    # 创建进化控制器
    # 轨迹池文件保存在实验专属目录下，确保多实验隔离
    pool_save_path = Path(log_root) / "trajectory_pool.json"
    mutation_prompt_path = Path(__file__).parent / "prompts" / "evolution_prompts.yaml"
    
    logger.info(f"轨迹池路径: {pool_save_path} (fresh_start={fresh_start})")
    
    config = EvolutionConfig(
        num_directions=len(directions),
        steps_per_loop=steps_per_loop,
        max_rounds=max_rounds,
        mutation_enabled=mutation_enabled,
        crossover_enabled=crossover_enabled,
        crossover_size=crossover_size,
        crossover_n=crossover_n,
        prefer_diverse_crossover=True,
        parent_selection_strategy=parent_selection_strategy,
        top_percent_threshold=top_percent_threshold,
        parallel_enabled=parallel_enabled,
        pool_save_path=str(pool_save_path),
        mutation_prompt_path=str(mutation_prompt_path) if mutation_prompt_path.exists() else None,
        crossover_prompt_path=str(mutation_prompt_path) if mutation_prompt_path.exists() else None,
        fresh_start=fresh_start,  # 传递 fresh_start 参数
    )
    
    controller = EvolutionController(config)
    
    # 进化主循环
    logger.info("="*60)
    logger.info("开始进化循环")
    logger.info(f"配置: directions={len(directions)}, max_rounds={max_rounds}, "
               f"crossover_size={crossover_size}, crossover_n={crossover_n}")
    logger.info(f"进化阶段: mutation={'启用' if mutation_enabled else '禁用'}, "
               f"crossover={'启用' if crossover_enabled else '禁用'}")
    if mutation_enabled and not crossover_enabled:
        logger.info("模式: 仅变异 (Original → Mutation → Mutation → ...)")
    elif crossover_enabled and not mutation_enabled:
        logger.info("模式: 仅交叉 (Original → Crossover → Crossover → ...)")
    elif mutation_enabled and crossover_enabled:
        logger.info("模式: 完整进化 (Original → Mutation → Crossover → Mutation → ...)")
    else:
        logger.info("模式: 仅原始轮 (无进化)")
    logger.info(f"父代选择策略: {parent_selection_strategy}" + 
               (f" (top_percent={top_percent_threshold})" if parent_selection_strategy == "top_percent_plus_random" else ""))
    logger.info(f"并行执行: {'启用' if parallel_enabled else '禁用'}")
    logger.info("="*60)
    
    # === 并行执行模式 ===
    if parallel_enabled:
        while not controller.is_complete():
            if stop_event and stop_event.is_set():
                logger.info("收到停止信号，终止进化循环")
                break
            
            # 获取当前阶段的所有任务
            tasks = controller.get_all_tasks_for_current_phase()
            if not tasks:
                logger.info("进化完成：没有更多任务")
                break
            
            current_phase = tasks[0]["phase"]
            current_round = tasks[0]["round_idx"]
            
            logger.info(f"并行执行阶段: phase={current_phase.value}, round={current_round}, "
                       f"任务数={len(tasks)}")
            
            # 并行运行所有任务
            results = _run_tasks_parallel(
                tasks=tasks,
                directions=directions,
                step_n=steps_per_loop,
                use_local=use_local,
                user_direction=initial_direction,
                log_root=log_root,
            )
            
            # 处理结果
            completed_tasks = []
            for result in results:
                if result["success"]:
                    task = result["task"]
                    traj_data = result["traj_data"]
                    
                    # 创建轨迹并报告完成
                    trajectory = controller.create_trajectory_from_loop_result(
                        task=task,
                        hypothesis=traj_data.get("hypothesis"),
                        experiment=traj_data.get("experiment"),
                        feedback=traj_data.get("feedback"),
                    )
                    
                    controller.report_task_complete(task, trajectory)
                    completed_tasks.append(task)
                    
                    logger.info(f"轨迹完成: {trajectory.trajectory_id}, "
                               f"RankIC={trajectory.get_primary_metric()}")
            
            # 更新控制器状态（推进到下一阶段）
            controller.advance_phase_after_parallel_completion(completed_tasks)
    
    # === 串行执行模式 ===
    else:
        while not controller.is_complete():
            if stop_event and stop_event.is_set():
                logger.info("收到停止信号，终止进化循环")
                break
            
            # 获取下一个任务
            task = controller.get_next_task()
            if task is None:
                logger.info("进化完成：没有更多任务")
                break
            
            logger.info(f"执行任务: phase={task['phase'].value}, round={task['round_idx']}, "
                       f"direction={task['direction_id']}")
            
            try:
                # 运行任务
                traj_data = _run_evolution_task(
                    task=task,
                    directions=directions,
                    step_n=steps_per_loop,
                    use_local=use_local,
                    user_direction=initial_direction,
                    log_root=log_root,
                    stop_event=stop_event,
                    quality_gate_cfg=quality_gate_cfg,
                )
                
                # 创建轨迹并报告完成
                trajectory = controller.create_trajectory_from_loop_result(
                    task=task,
                    hypothesis=traj_data.get("hypothesis"),
                    experiment=traj_data.get("experiment"),
                    feedback=traj_data.get("feedback"),
                )
                
                controller.report_task_complete(task, trajectory)
                
                logger.info(f"任务完成: trajectory_id={trajectory.trajectory_id}, "
                           f"RankIC={trajectory.get_primary_metric()}")
                
            except Exception as e:
                logger.error(f"任务执行失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # 继续下一个任务
                continue
    
    # 保存最终状态
    state_path = Path(log_root) / "evolution_state.json"
    controller.save_state(state_path)
    
    # 输出最佳结果
    best_trajs = controller.get_best_trajectories(top_n=5)
    logger.info("="*60)
    logger.info(f"进化完成！最佳轨迹 (Top {len(best_trajs)}):")
    for i, t in enumerate(best_trajs):
        metric = t.get_primary_metric()
        metric_str = f"{metric:.4f}" if metric is not None else "N/A"
        logger.info(f"  {i+1}. {t.trajectory_id}: phase={t.phase.value}, RankIC={metric_str}")
    logger.info(f"轨迹池统计: {controller.pool.get_statistics()}")
    logger.info("="*60)
    
    # 实验结束后清理轨迹池文件（如果配置了 cleanup_on_finish）
    if cleanup_on_finish:
        logger.info("清理轨迹池文件...")
        controller.pool.cleanup_file()


@force_timeout()
def main(path=None, step_n=100, direction=None, stop_event=None, config_path=None, evolution_mode=None):
    """
    Autonomous alpha factor mining with optional evolution support.

    Args:
        path: 会话路径（用于恢复）
        step_n: 步骤数，默认100（20个循环 * 5个步骤/循环）
        direction: 初始方向
        stop_event: 停止事件
        config_path: 运行配置文件路径
        evolution_mode: 是否启用进化模式（None=使用配置，True/False=覆盖配置）

    进化模式流程：
        原始轮 → 变异轮 → 交叉轮 → 变异轮 → 交叉轮 → ...

    You can continue running session by

    .. code-block:: python

        quantaalpha mine --direction "[Initial Direction]" --config_path configs/experiment.yaml

    """
    try:
        # 显示当前实验的缓存和工作空间配置
        from quantaalpha.core.conf import RD_AGENT_SETTINGS
        logger.info("="*60)
        logger.info("实验配置")
        logger.info(f"  工作空间: {RD_AGENT_SETTINGS.workspace_path}")
        logger.info(f"  缓存目录: {RD_AGENT_SETTINGS.pickle_cache_folder_path_str}")
        logger.info(f"  启用缓存: {RD_AGENT_SETTINGS.cache_with_pickle}")
        logger.info("="*60)
        
        # 配置文件默认在项目根目录的 configs/ 下
        _project_root = Path(__file__).resolve().parents[2]
        config_default = _project_root / "configs" / "experiment.yaml"
        config_file = Path(config_path) if config_path else config_default
        run_cfg = load_run_config(config_file)
        planning_cfg = (run_cfg.get("planning") or {}) if isinstance(run_cfg, dict) else {}
        exec_cfg = (run_cfg.get("execution") or {}) if isinstance(run_cfg, dict) else {}
        evolution_cfg = (run_cfg.get("evolution") or {}) if isinstance(run_cfg, dict) else {}
        quality_gate_cfg = (run_cfg.get("quality_gate") or {}) if isinstance(run_cfg, dict) else {}

        # 确定是否使用进化模式
        if evolution_mode is not None:
            use_evolution = evolution_mode
        else:
            use_evolution = bool(evolution_cfg.get("enabled", False))

        if step_n is None or step_n == 100:
            if exec_cfg.get("step_n") is not None:
                step_n = exec_cfg.get("step_n")
            else:
                max_loops = int(exec_cfg.get("max_loops", 10))
                steps_per_loop = int(exec_cfg.get("steps_per_loop", 5))
                step_n = max_loops * steps_per_loop

        use_local = os.getenv("USE_LOCAL", "True").lower()
        use_local = True if use_local in ["true", "1"] else False
        if exec_cfg.get("use_local") is not None:
            use_local = bool(exec_cfg.get("use_local"))
        exec_cfg["use_local"] = use_local
        
        logger.info(f"Use {'Local' if use_local else 'Docker container'} to execute factor backtest")
        
        # 进化模式
        if use_evolution and path is None:
            logger.info("="*60)
            logger.info("启用进化模式: 原始轮 → 变异轮 → 交叉轮 循环")
            logger.info("="*60)
            
            run_evolution_loop(
                initial_direction=direction,
                evolution_cfg=evolution_cfg,
                exec_cfg=exec_cfg,
                planning_cfg=planning_cfg,
                stop_event=stop_event,
                quality_gate_cfg=quality_gate_cfg,
            )
        
        # 传统模式（无进化）
        elif path is None:
            planning_enabled = bool(planning_cfg.get("enabled", False))
            n_dirs = int(planning_cfg.get("num_directions", 1))
            max_attempts = int(planning_cfg.get("max_attempts", 5))
            use_llm = bool(planning_cfg.get("use_llm", True))
            allow_fallback = bool(planning_cfg.get("allow_fallback", True))
            prompt_file = planning_cfg.get("prompt_file") or "planning_prompts.yaml"
            prompt_path = Path(__file__).parent / "prompts" / str(prompt_file)
            if planning_enabled and direction:
                directions = generate_parallel_directions(
                    initial_direction=direction,
                    n=n_dirs,
                    prompt_file=prompt_path,
                    max_attempts=max_attempts,
                    use_llm=use_llm,
                    allow_fallback=allow_fallback,
                )
            else:
                directions = [direction] if direction else [None]

            log_root = exec_cfg.get("branch_log_root") or "log"
            log_prefix = exec_cfg.get("branch_log_prefix") or "branch"
            use_branch_logs = planning_enabled and len(directions) > 1
            parallel_execution = bool(exec_cfg.get("parallel_execution", False))

            if parallel_execution and len(directions) > 1:
                procs: list[Process] = []
                for idx, dir_text in enumerate(directions, start=1):
                    if dir_text:
                        logger.info(f"[Planning] Branch {idx}/{len(directions)} direction: {dir_text}")
                    p = Process(
                        target=_run_branch,
                        args=(dir_text, step_n, use_local, idx, log_root if use_branch_logs else "", log_prefix),
                    )
                    p.start()
                    procs.append(p)
                for p in procs:
                    p.join()
            else:
                for idx, dir_text in enumerate(directions, start=1):
                    if dir_text:
                        logger.info(f"[Planning] Branch {idx}/{len(directions)} direction: {dir_text}")
                    if use_branch_logs:
                        branch_name = f"{log_prefix}_{idx:02d}"
                        branch_log = Path(log_root) / branch_name
                        branch_log.mkdir(parents=True, exist_ok=True)
                        logger.set_trace_path(branch_log)
                    model_loop = AlphaAgentLoop(
                        ALPHA_AGENT_FACTOR_PROP_SETTING,
                        potential_direction=dir_text,
                        stop_event=stop_event,
                        use_local=use_local,
                        quality_gate_config=quality_gate_cfg,
                    )
                    model_loop.user_initial_direction = direction
                    model_loop.run(step_n=step_n, stop_event=stop_event)
        else:
            model_loop = AlphaAgentLoop.load(path, use_local=use_local)
            model_loop.run(step_n=step_n, stop_event=stop_event)
    except Exception as e:
        logger.error(f"执行过程中发生错误: {str(e)}")
        raise
    finally:
        logger.info("程序执行完成或被终止")

if __name__ == "__main__":
    fire.Fire(main)
