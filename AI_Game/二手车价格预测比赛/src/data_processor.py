#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据预处理模块
处理训练数据和测试数据的加载、清洗、基础预处理
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class DataProcessor:
    """数据预处理器"""
    
    def __init__(self):
        self.data_dir = Path("data")
        
    def load_data(self):
        """加载数据"""
        logger.info("开始加载数据...")
        
        try:
            # 加载训练数据
            train_path = self.data_dir / "used_car_train_20200313.csv"
            if train_path.exists():
                train_data = pd.read_csv(train_path, sep=' ')
                logger.info(f"训练数据加载成功: {train_data.shape}")
            else:
                # 如果文件不存在，创建示例数据
                train_data = self._create_sample_data(150000, with_price=True)
                logger.warning("训练数据文件不存在，使用示例数据")
            
            # 加载测试数据A
            testA_path = self.data_dir / "used_car_testA_20200313.csv"
            if testA_path.exists():
                testA_data = pd.read_csv(testA_path, sep=' ')
                logger.info(f"测试数据A加载成功: {testA_data.shape}")
            else:
                testA_data = self._create_sample_data(50000, with_price=False)
                logger.warning("测试数据A文件不存在，使用示例数据")
            
            # 加载测试数据B - 尝试多个可能的文件名
            testB_paths = [
                self.data_dir / "used_car_testB_20200421.csv",  # 新的文件名
                self.data_dir / "used_car_testB_20200313.csv"   # 原始文件名
            ]
            
            testB_data = None
            for testB_path in testB_paths:
                if testB_path.exists():
                    testB_data = pd.read_csv(testB_path, sep=' ')
                    logger.info(f"测试数据B加载成功: {testB_data.shape} (文件: {testB_path.name})")
                    break
            
            if testB_data is None:
                testB_data = self._create_sample_data(50000, with_price=False)
                logger.warning("测试数据B文件不存在，使用示例数据")
            
            # 合并测试数据，但最终只提交testB的预测
            test_data_combined = pd.concat([testA_data, testB_data], ignore_index=True)
            logger.info(f"合并后测试数据: {test_data_combined.shape}")
            
            # 保存testB的索引范围用于最终提交
            testB_start_idx = len(testA_data)
            test_data = test_data_combined
            
            return train_data, test_data
            
        except Exception as e:
            logger.error(f"数据加载失败: {str(e)}")
            raise
    
    def _create_sample_data(self, n_samples, with_price=True):
        """创建示例数据"""
        np.random.seed(42)
        
        data = {
            'SaleID': range(n_samples),
            'name': np.random.randint(0, 40000, n_samples),
            'regDate': np.random.randint(19910101, 20160101, n_samples),
            'model': np.random.randint(0, 250, n_samples),
            'brand': np.random.randint(0, 40, n_samples),
            'bodyType': np.random.randint(0, 8, n_samples),
            'fuelType': np.random.randint(0, 7, n_samples),
            'gearbox': np.random.randint(0, 2, n_samples),
            'power': np.random.randint(0, 600, n_samples),
            'kilometer': np.random.randint(0, 600000, n_samples),
            'notRepairedDamage': np.random.choice([0, 1, -1], n_samples, p=[0.7, 0.2, 0.1]),
            'regionCode': np.random.randint(1, 8000, n_samples),
            'seller': np.random.randint(0, 2, n_samples),
            'offerType': np.random.randint(0, 2, n_samples),
            'creatDate': np.random.randint(20160101, 20160501, n_samples),
            'v_0': np.random.normal(0, 1, n_samples),
            'v_1': np.random.normal(0, 1, n_samples),
            'v_2': np.random.normal(0, 1, n_samples),
            'v_3': np.random.normal(0, 1, n_samples),
            'v_4': np.random.normal(0, 1, n_samples),
            'v_5': np.random.normal(0, 1, n_samples),
            'v_6': np.random.normal(0, 1, n_samples),
            'v_7': np.random.normal(0, 1, n_samples),
            'v_8': np.random.normal(0, 1, n_samples),
            'v_9': np.random.normal(0, 1, n_samples),
            'v_10': np.random.normal(0, 1, n_samples),
            'v_11': np.random.normal(0, 1, n_samples),
            'v_12': np.random.normal(0, 1, n_samples),
            'v_13': np.random.normal(0, 1, n_samples),
            'v_14': np.random.normal(0, 1, n_samples),
        }
        
        if with_price:
            # 生成价格（基于其他特征的简单线性组合 + 噪声）
            price = (data['power'] * 50 + 
                    (2020 - data['regDate'] // 10000) * 1000 + 
                    data['kilometer'] * -0.1 + 
                    np.random.normal(0, 5000, n_samples))
            price = np.maximum(price, 500)  # 最低价格500
            data['price'] = price
        
        return pd.DataFrame(data)
    
    def clean_data(self, data):
        """数据清洗 - 优化版本"""
        logger.info("开始数据清洗...")
        
        # 处理异常值 - 517版本的方式
        # 功率异常值处理
        data.loc[data['power'] > 600, 'power'] = data['power'].median()
        data.loc[data['power'] < 1, 'power'] = data['power'].median()
        
        # 里程异常值处理
        data.loc[data['kilometer'] > 600000, 'kilometer'] = data['kilometer'].median()
        
        # 处理缺失值
        for col in data.columns:
            if data[col].dtype == 'object':
                # 类别特征用众数填充
                mode_val = data[col].mode()
                if len(mode_val) > 0:
                    data[col].fillna(mode_val[0], inplace=True)
                else:
                    data[col].fillna('unknown', inplace=True)
            else:
                # 数值特征用中位数填充
                median_val = data[col].median()
                data[col].fillna(median_val, inplace=True)
        
        logger.info("数据清洗完成")
        return data
    
    def load_and_preprocess(self):
        """加载并预处理数据"""
        # 加载数据
        train_data, test_data = self.load_data()
        
        # 清洗数据
        train_data = self.clean_data(train_data)
        test_data = self.clean_data(test_data)
        
        logger.info(f"预处理完成 - 训练数据: {train_data.shape}, 测试数据: {test_data.shape}")
        
        return train_data, test_data
