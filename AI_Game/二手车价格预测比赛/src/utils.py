#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工具函数模块
包含日志设置、目录创建等通用功能
"""

import os
import logging
from pathlib import Path
from datetime import datetime

def setup_logging(log_level=logging.INFO):
    """设置日志"""
    # 创建logs目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 日志文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"car_price_prediction_{timestamp}.log"
    
    # 配置日志
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"日志系统初始化完成，日志文件: {log_file}")
    
    return logger

def create_directories():
    """创建必要的目录"""
    directories = [
        "data",
        "output", 
        "logs",
        "models",
        "cache"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print("📁 目录结构创建完成")

def format_number(num):
    """格式化数字显示"""
    if num >= 1e6:
        return f"{num/1e6:.1f}M"
    elif num >= 1e3:
        return f"{num/1e3:.1f}K"
    else:
        return f"{num:.1f}"

def print_data_info(data, name="数据"):
    """打印数据信息"""
    print(f"\n📊 {name}信息:")
    print(f"  形状: {data.shape}")
    print(f"  内存使用: {data.memory_usage(deep=True).sum() / 1024**2:.1f} MB")
    
    if hasattr(data, 'dtypes'):
        print(f"  数据类型分布:")
        dtype_counts = data.dtypes.value_counts()
        for dtype, count in dtype_counts.items():
            print(f"    {dtype}: {count}")
    
    # 缺失值统计
    if hasattr(data, 'isnull'):
        missing_count = data.isnull().sum().sum()
        if missing_count > 0:
            print(f"  缺失值: {missing_count}")

def save_model_info(models, filepath="output/model_info.txt"):
    """保存模型信息"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("二手车价格预测模型信息\n")
        f.write("="*50 + "\n\n")
        
        for model_name, model_info in models.items():
            f.write(f"模型: {model_name}\n")
            f.write(f"MAE: {model_info['mae']:.4f}\n")
            f.write(f"权重: {model_info['weight']:.3f}\n")
            f.write(f"Fold数量: {len(model_info['models'])}\n")
            f.write("-" * 30 + "\n")
    
    print(f"📝 模型信息已保存到: {filepath}")

class Timer:
    """计时器"""
    
    def __init__(self):
        self.start_time = None
        
    def start(self):
        """开始计时"""
        self.start_time = datetime.now()
        
    def elapsed(self):
        """获取经过时间"""
        if self.start_time is None:
            return 0
        return (datetime.now() - self.start_time).total_seconds()
    
    def elapsed_str(self):
        """获取格式化的经过时间"""
        elapsed = self.elapsed()
        if elapsed < 60:
            return f"{elapsed:.1f}秒"
        elif elapsed < 3600:
            return f"{elapsed/60:.1f}分钟"
        else:
            return f"{elapsed/3600:.1f}小时"
