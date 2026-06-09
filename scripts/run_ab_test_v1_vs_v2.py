"""运行AB测试：对比v1和v2版本的prompt/skill。"""

import json
import sys
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(PROJECT_ROOT))

from llm_werewolf.evaluation.evolution.runner import run_evolution_cycle


def run_ab_test(
    experiment_dir: str | Path,
    games_per_group: int = 30,
    seed: int = 42,
):
    """运行AB测试。
    
    Args:
        experiment_dir: 实验目录路径
        games_per_group: 每组游戏数量
        seed: 随机种子
    """
    exp_dir = Path(experiment_dir)
    exp_dir.mkdir(parents=True, exist_ok=True)
    
    # 运行control组 (v1)
    control_dir = exp_dir / "control-v1"
    print("=" * 80)
    print("运行Control组 (v1基础prompt/skill)")
    print("=" * 80)
    
    run_evolution_cycle(
        output_root=control_dir,
        scenario="smoke_6p_basic",
        rounds=1,
        games_per_round=games_per_group,
        timeout_seconds=30.0,
        seed=seed,
        model="doubao",
        prompt_version="v1",
        initial_skill_version="v1",
    )
    
    # 运行treatment组 (v2)
    treatment_dir = exp_dir / "treatment-v2"
    print("\n" + "=" * 80)
    print("运行Treatment组 (v2进化后prompt/skill)")
    print("=" * 80)
    
    run_evolution_cycle(
        output_root=treatment_dir,
        scenario="smoke_6p_basic",
        rounds=1,
        games_per_round=games_per_group,
        timeout_seconds=30.0,
        seed=seed + 1000,
        model="doubao",
        prompt_version="v2",
        initial_skill_version="v2",
    )
    
    print("\n" + "=" * 80)
    print("AB测试完成！")
    print("=" * 80)
    print(f"Control组结果: {control_dir / 'evolution_summary.json'}")
    print(f"Treatment组结果: {treatment_dir / 'evolution_summary.json'}")


if __name__ == "__main__":
    experiment_dir = Path(__file__).resolve().parent.parent.parent / "memory-evolution-ab-test" / "ab-test-v1-vs-v2"
    run_ab_test(experiment_dir, games_per_group=30, seed=42)
