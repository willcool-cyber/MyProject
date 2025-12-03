#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速运行脚本 - 一键完成二手车价格预测
"""

import subprocess
import sys
from pathlib import Path

def install_requirements():
    """安装依赖包"""
    print("📦 检查并安装依赖包...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ 依赖包安装完成")
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖包安装失败: {e}")
        return False
    return True

def check_data_files():
    """检查数据文件"""
    print("📊 检查数据文件...")
    data_dir = Path("data")
    
    required_files = [
        "used_car_train_20200313.csv",
        "used_car_testA_20200313.csv", 
        "used_car_testB_20200313.csv"
    ]
    
    missing_files = []
    for file in required_files:
        if not (data_dir / file).exists():
            missing_files.append(file)
    
    if missing_files:
        print("⚠️  以下数据文件缺失，将使用示例数据:")
        for file in missing_files:
            print(f"   - {file}")
        print("💡 请将真实数据文件放入 data/ 目录以获得最佳效果")
    else:
        print("✅ 所有数据文件就绪")
    
    return True

def run_main():
    """运行主程序"""
    print("🚀 开始运行二手车价格预测...")
    try:
        subprocess.check_call([sys.executable, "main.py"])
        print("✅ 预测完成！")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 预测失败: {e}")
        return False

def main():
    """主函数"""
    print("🚗 阿里云天池 - 二手车价格预测比赛")
    print("="*50)
    
    # 1. 安装依赖
    if not install_requirements():
        return
    
    # 2. 检查数据
    if not check_data_files():
        return
    
    # 3. 运行预测
    if run_main():
        print("\n🎉 任务完成！")
        print("📁 查看结果:")
        print("   - 提交文件: output/submission.csv")
        print("   - 详细结果: output/detailed_submission.csv")
        print("   - 运行日志: logs/")
    else:
        print("\n❌ 任务失败，请查看错误信息")

if __name__ == "__main__":
    main()
