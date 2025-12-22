#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OpenBench NML Wizard - Command Line Interface

用于在服务器上无 GUI 环境下生成 NML 配置文件。

Usage:
    python cli.py --interactive           # 交互式配置
    python cli.py --config config.yaml    # 从配置文件生成
    python cli.py --template              # 生成配置模板
"""

import argparse
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.config_manager import ConfigManager


# 评估项目定义
EVALUATION_ITEMS = {
    "Carbon Cycle": [
        "Biomass", "Ecosystem_Respiration", "Gross_Primary_Productivity",
        "Leaf_Area_Index", "Methane", "Net_Ecosystem_Exchange",
        "Nitrogen_Fixation", "Soil_Carbon"
    ],
    "Water Cycle": [
        "Canopy_Interception", "Canopy_Transpiration", "Evapotranspiration",
        "Permafrost", "Root_Zone_Soil_Moisture", "Snow_Depth",
        "Snow_Water_Equivalent", "Soil_Evaporation",
        "Surface_Snow_Cover_In_Fraction", "Surface_Soil_Moisture",
        "Terrestrial_Water_Storage_Change", "Total_Runoff", "Water_Evaporation"
    ],
    "Energy Cycle": [
        "Surface_Albedo", "Ground_Heat", "Latent_Heat", "Net_Radiation",
        "Root_Zone_Soil_Temperature", "Sensible_Heat",
        "Surface_Net_LW_Radiation", "Surface_Net_SW_Radiation",
        "Surface_Soil_Temperature", "Surface_Upward_LW_Radiation",
        "Surface_Upward_SW_Radiation"
    ],
}

METRICS = [
    "RMSE", "Correlation", "Bias", "MSE", "NSE", "KGE",
    "Percent_Bias", "Index_Agreement", "Standard_Deviation"
]

SCORES = [
    "Overall_Score", "Bias_Score", "RMSE_Score",
    "Seasonality_Score", "Interannual_Score"
]


def print_header():
    """打印程序头部"""
    print("=" * 60)
    print("  OpenBench NML Wizard - Command Line Interface")
    print("=" * 60)
    print()


def print_section(title):
    """打印章节标题"""
    print()
    print(f"--- {title} ---")
    print()


def get_input(prompt, default=None, required=True):
    """获取用户输入"""
    if default is not None:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "

    while True:
        value = input(prompt).strip()
        if not value and default is not None:
            return default
        if value or not required:
            return value
        print("  此项为必填，请输入值。")


def get_number(prompt, default=None, min_val=None, max_val=None):
    """获取数字输入"""
    while True:
        value = get_input(prompt, default)
        try:
            num = float(value)
            if min_val is not None and num < min_val:
                print(f"  值必须 >= {min_val}")
                continue
            if max_val is not None and num > max_val:
                print(f"  值必须 <= {max_val}")
                continue
            return num
        except ValueError:
            print("  请输入有效数字。")


def get_yes_no(prompt, default=True):
    """获取是/否输入"""
    default_str = "Y/n" if default else "y/N"
    while True:
        value = input(f"{prompt} [{default_str}]: ").strip().lower()
        if not value:
            return default
        if value in ('y', 'yes', '是'):
            return True
        if value in ('n', 'no', '否'):
            return False
        print("  请输入 y 或 n")


def select_items(items, title):
    """交互式选择项目"""
    print(f"\n{title}")
    print("-" * 40)

    # 显示所有项目
    all_items = []
    for category, category_items in items.items():
        print(f"\n  [{category}]")
        for item in category_items:
            idx = len(all_items)
            print(f"    {idx:2d}. {item}")
            all_items.append(item)

    print("\n输入选项:")
    print("  - 输入数字（逗号分隔）选择项目，如: 0,1,5,10")
    print("  - 输入 'all' 选择全部")
    print("  - 输入 'none' 或直接回车跳过")

    while True:
        selection = input("\n请选择: ").strip().lower()

        if not selection or selection == 'none':
            return []

        if selection == 'all':
            return all_items

        try:
            indices = [int(x.strip()) for x in selection.split(',')]
            selected = []
            for idx in indices:
                if 0 <= idx < len(all_items):
                    selected.append(all_items[idx])
                else:
                    print(f"  无效索引: {idx}")
                    break
            else:
                return selected
        except ValueError:
            print("  请输入有效的数字，用逗号分隔。")


def select_from_list(items, title):
    """从列表中选择"""
    print(f"\n{title}")
    print("-" * 40)

    for i, item in enumerate(items):
        print(f"  {i:2d}. {item}")

    print("\n输入 'all' 选择全部，数字选择特定项，回车跳过")

    while True:
        selection = input("\n请选择: ").strip().lower()

        if not selection:
            return []

        if selection == 'all':
            return items

        try:
            indices = [int(x.strip()) for x in selection.split(',')]
            selected = []
            for idx in indices:
                if 0 <= idx < len(items):
                    selected.append(items[idx])
            return selected
        except ValueError:
            print("  请输入有效的数字。")


def configure_data_source(source_type):
    """配置数据源"""
    print(f"\n配置 {source_type} 数据源")
    print("-" * 40)

    sources = {}

    while True:
        name = get_input("数据源名称 (输入空值结束)", required=False)
        if not name:
            break

        print(f"\n  配置 '{name}':")
        source = {
            "dir": get_input("    数据目录"),
            "suffix": get_input("    文件后缀", ".nc"),
            "varname": get_input("    变量名"),
            "syear": int(get_number("    起始年份", 2000)),
            "eyear": int(get_number("    结束年份", 2020)),
            "tim_res": get_input("    时间分辨率", "monthly"),
            "nlon": int(get_number("    经度格点数", 720)),
            "nlat": int(get_number("    纬度格点数", 360)),
            "geo_res": get_number("    空间分辨率(度)", 0.5),
            "data_type": get_input("    数据类型", "flux"),
        }
        sources[name] = source
        print(f"  ✓ 已添加数据源: {name}")

    return sources


def interactive_mode():
    """交互式配置模式"""
    print_header()

    config = ConfigManager()

    # === 通用设置 ===
    print_section("1. 通用设置")

    general = {
        "casename": get_input("案例名称", "my_evaluation"),
        "basedir": get_input("输出基础目录", os.path.expanduser("~/openbench_output")),
        "start_year": int(get_number("起始年份", 2000)),
        "end_year": int(get_number("结束年份", 2020)),
        "min_lat": get_number("最小纬度", -90, -90, 90),
        "max_lat": get_number("最大纬度", 90, -90, 90),
        "min_lon": get_number("最小经度", -180, -180, 180),
        "max_lon": get_number("最大经度", 180, -180, 180),
        "comparison": get_yes_no("启用比较功能?", False),
        "statistics": get_yes_no("启用统计功能?", False),
    }
    config.update_section("general", general)

    # === 评估项目 ===
    print_section("2. 选择评估项目")

    selected_items = select_items(EVALUATION_ITEMS, "可用评估项目:")
    eval_items = {item: True for item in selected_items}
    config.update_section("evaluation_items", eval_items)
    print(f"\n✓ 已选择 {len(selected_items)} 个评估项目")

    # === 指标 ===
    print_section("3. 选择评估指标")

    selected_metrics = select_from_list(METRICS, "可用指标:")
    metrics = {m: True for m in selected_metrics}
    config.update_section("metrics", metrics)
    print(f"\n✓ 已选择 {len(selected_metrics)} 个指标")

    # === 评分 ===
    print_section("4. 选择评分项")

    selected_scores = select_from_list(SCORES, "可用评分:")
    scores = {s: True for s in selected_scores}
    config.update_section("scores", scores)
    print(f"\n✓ 已选择 {len(selected_scores)} 个评分项")

    # === 参考数据 ===
    print_section("5. 配置参考数据")

    if get_yes_no("是否配置参考数据?", True):
        ref_data = configure_data_source("参考")
        config.update_section("ref_data", ref_data)

    # === 模拟数据 ===
    print_section("6. 配置模拟数据")

    if get_yes_no("是否配置模拟数据?", True):
        sim_data = configure_data_source("模拟")
        config.update_section("sim_data", sim_data)

    # === 生成配置文件 ===
    print_section("7. 生成配置文件")

    output_dir = get_input("配置文件输出目录", general["basedir"])
    os.makedirs(output_dir, exist_ok=True)

    # 生成并保存
    main_nml = config.generate_main_nml()
    ref_nml = config.generate_ref_nml()
    sim_nml = config.generate_sim_nml()

    main_path = Path(output_dir) / "main_nml.yaml"
    ref_path = Path(output_dir) / "ref_nml.yaml"
    sim_path = Path(output_dir) / "sim_nml.yaml"

    with open(main_path, 'w', encoding='utf-8') as f:
        f.write(main_nml)
    with open(ref_path, 'w', encoding='utf-8') as f:
        f.write(ref_nml)
    with open(sim_path, 'w', encoding='utf-8') as f:
        f.write(sim_nml)

    print()
    print("=" * 60)
    print("  配置文件生成完成!")
    print("=" * 60)
    print()
    print(f"  主配置文件: {main_path}")
    print(f"  参考数据配置: {ref_path}")
    print(f"  模拟数据配置: {sim_path}")
    print()

    # 预览
    if get_yes_no("是否预览主配置文件?", True):
        print("\n--- main_nml.yaml ---")
        print(main_nml)

    return str(main_path)


def generate_template(output_path):
    """生成配置模板文件"""
    template = """# OpenBench NML Wizard 配置模板
# 使用方法: python cli.py --config this_file.yaml

general:
  casename: my_evaluation
  basedir: /path/to/output
  start_year: 2000
  end_year: 2020
  min_lat: -90
  max_lat: 90
  min_lon: -180
  max_lon: 180
  comparison: false
  statistics: false

evaluation_items:
  Gross_Primary_Productivity: true
  Evapotranspiration: true
  Latent_Heat: true
  # 添加更多评估项...

metrics:
  RMSE: true
  Correlation: true
  Bias: true
  # 添加更多指标...

scores:
  Overall_Score: true
  Bias_Score: true
  # 添加更多评分项...

ref_data:
  FLUXNET:
    dir: /data/reference/gpp
    suffix: .nc
    varname: GPP
    syear: 2000
    eyear: 2020
    tim_res: monthly
    nlon: 720
    nlat: 360
    geo_res: 0.5
    data_type: flux

sim_data:
  CLM5:
    dir: /data/simulation/clm5
    suffix: .nc
    varname: GPP
    syear: 2000
    eyear: 2020
    tim_res: monthly
    nlon: 720
    nlat: 360
    geo_res: 0.5
    data_type: flux
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(template)

    print(f"✓ 配置模板已生成: {output_path}")
    print("\n编辑此文件后，使用以下命令生成 NML 配置:")
    print(f"  python cli.py --config {output_path}")


def from_config_file(config_path, output_dir=None):
    """从配置文件生成 NML"""
    import yaml

    print(f"读取配置文件: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        user_config = yaml.safe_load(f)

    config = ConfigManager()

    # 加载各节配置
    for section in ['general', 'evaluation_items', 'metrics', 'scores',
                    'comparisons', 'statistics', 'ref_data', 'sim_data']:
        if section in user_config:
            config.update_section(section, user_config[section])

    # 确定输出目录
    if output_dir is None:
        output_dir = user_config.get('general', {}).get('basedir', '.')

    os.makedirs(output_dir, exist_ok=True)

    # 生成并保存
    main_nml = config.generate_main_nml()
    ref_nml = config.generate_ref_nml()
    sim_nml = config.generate_sim_nml()

    main_path = Path(output_dir) / "main_nml.yaml"
    ref_path = Path(output_dir) / "ref_nml.yaml"
    sim_path = Path(output_dir) / "sim_nml.yaml"

    with open(main_path, 'w', encoding='utf-8') as f:
        f.write(main_nml)
    with open(ref_path, 'w', encoding='utf-8') as f:
        f.write(ref_nml)
    with open(sim_path, 'w', encoding='utf-8') as f:
        f.write(sim_nml)

    print()
    print("✓ 配置文件生成完成!")
    print(f"  主配置文件: {main_path}")
    print(f"  参考数据配置: {ref_path}")
    print(f"  模拟数据配置: {sim_path}")

    return str(main_path)


def main():
    parser = argparse.ArgumentParser(
        description="OpenBench NML Wizard - 命令行界面",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python cli.py --interactive              # 交互式配置
  python cli.py --template                 # 生成配置模板
  python cli.py --config my_config.yaml    # 从配置文件生成
  python cli.py --config my_config.yaml --output /path/to/output
        """
    )

    parser.add_argument(
        '-i', '--interactive',
        action='store_true',
        help='交互式配置模式'
    )

    parser.add_argument(
        '-c', '--config',
        type=str,
        help='从指定配置文件生成 NML'
    )

    parser.add_argument(
        '-t', '--template',
        type=str,
        nargs='?',
        const='wizard_config_template.yaml',
        help='生成配置模板文件'
    )

    parser.add_argument(
        '-o', '--output',
        type=str,
        help='输出目录'
    )

    args = parser.parse_args()

    # 没有参数时显示帮助
    if len(sys.argv) == 1:
        parser.print_help()
        print("\n提示: 使用 --interactive 进入交互式配置模式")
        return

    if args.template:
        generate_template(args.template)
    elif args.config:
        from_config_file(args.config, args.output)
    elif args.interactive:
        interactive_mode()


if __name__ == "__main__":
    main()
