#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
二手车价格预测 - 主程序
使用 LightGBM + XGBoost + CatBoost 模型融合
"""

import os
import sys
import warnings
import pandas as pd
import numpy as np
from pathlib import Path

# 忽略警告
warnings.filterwarnings('ignore')

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT))

from src.data_processor import DataProcessor
from src.feature_engineer import FeatureEngineer
from src.model_trainer import ModelTrainer
from src.model_ensemble import ModelEnsemble
from src.utils import setup_logging, create_directories

def main():
    """主函数"""
    print("🚗 二手车价格预测系统")
    print("="*60)
    
    # 设置日志
    logger = setup_logging()
    logger.info("开始二手车价格预测任务")
    
    # 创建必要目录
    create_directories()
    
    try:
        # 1. 数据加载和预处理
        print("\n📊 步骤1: 数据加载和预处理")
        processor = DataProcessor()
        train_data, test_data = processor.load_and_preprocess()
        
        # 2. 特征工程
        print("\n🔧 步骤2: 特征工程")
        engineer = FeatureEngineer()
        X_train, y_train, X_test = engineer.engineer_features(train_data, test_data)
        
        # 3. 模型训练
        print("\n🤖 步骤3: 模型训练")
        trainer = ModelTrainer()
        models = trainer.train_models(X_train, y_train)
        
        # 4. 模型融合和预测
        print("\n🎯 步骤4: 模型融合和预测")
        ensemble = ModelEnsemble(models)
        predictions = ensemble.predict(X_test)
        
        # 5. 生成提交文件
        print("\n📝 步骤5: 生成提交文件")
        # 只保存testB的预测结果（后50000个）
        testB_predictions = predictions[50000:]  # testB从索引50000开始
        testB_sale_ids = test_data['SaleID'].iloc[50000:]  # testB的SaleID
        ensemble.save_submission(testB_predictions, testB_sale_ids)
        
        print("\n✅ 任务完成！提交文件已保存到 output/submission.csv")
        
    except Exception as e:
        logger.error(f"任务执行失败: {str(e)}", exc_info=True)
        print(f"\n❌ 错误: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
