#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
特征工程模块
包含特征提取、特征变换、特征选择等功能
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.feature_selection import SelectKBest, f_regression
import logging

logger = logging.getLogger(__name__)

class FeatureEngineer:
    """特征工程器"""
    
    def __init__(self):
        self.label_encoders = {}
        self.scaler = StandardScaler()
        self.feature_selector = None
        
    def create_time_features(self, data):
        """创建时间特征"""
        logger.info("创建时间特征...")
        
        # 注册日期特征
        if 'regDate' in data.columns:
            data['regDate_year'] = data['regDate'] // 10000
            data['regDate_month'] = (data['regDate'] % 10000) // 100
            data['regDate_day'] = data['regDate'] % 100
        
        # 创建日期特征
        if 'creatDate' in data.columns:
            data['creatDate_year'] = data['creatDate'] // 10000
            data['creatDate_month'] = (data['creatDate'] % 10000) // 100
            data['creatDate_day'] = data['creatDate'] % 100
        
        # 车龄特征
        if 'regDate_year' in data.columns and 'creatDate_year' in data.columns:
            data['car_age'] = data['creatDate_year'] - data['regDate_year']
            data['car_age'] = np.maximum(data['car_age'], 0)  # 确保车龄非负
        
        return data
    
    def create_interaction_features(self, data):
        """创建交互特征"""
        logger.info("创建交互特征...")
        
        # 功率相关特征
        data['power_per_year'] = data['power'] / (data['car_age'] + 1)
        data['kilometer_per_year'] = data['kilometer'] / (data['car_age'] + 1)
        
        # 品牌和型号组合
        data['brand_model'] = data['brand'].astype(str) + '_' + data['model'].astype(str)
        
        # 地区和品牌组合
        data['region_brand'] = data['regionCode'].astype(str) + '_' + data['brand'].astype(str)
        
        # 添加更多关键交互特征（激进优化）
        data['power_kilometer_ratio'] = data['power'] / (data['kilometer'] + 1)
        data['age_power_interaction'] = data['car_age'] / (data['power'] + 1)
        data['kilometer_age_ratio'] = data['kilometer'] / (data['car_age'] + 1)
        data['power_efficiency'] = data['power'] / (data['fuelType'] + 1)
        
        # 添加更多复合特征
        data['power_km_age'] = (data['power'] * data['kilometer']) / (data['car_age'] + 1)
        data['power_age_km'] = data['power'] * data['car_age'] / (data['kilometer'] + 1)
        data['km_per_power'] = data['kilometer'] / (data['power'] + 1)
        data['power_squared'] = data['power'] ** 2
        data['age_squared'] = data['car_age'] ** 2
        data['km_log'] = np.log1p(data['kilometer'])
        
        return data
    
    def create_statistical_features(self, data):
        """创建统计特征"""
        logger.info("创建统计特征...")
        
        # V特征统计
        v_cols = [col for col in data.columns if col.startswith('v_')]
        if v_cols:
            data['v_mean'] = data[v_cols].mean(axis=1)
            data['v_std'] = data[v_cols].std(axis=1)
            data['v_max'] = data[v_cols].max(axis=1)
            data['v_min'] = data[v_cols].min(axis=1)
            data['v_sum'] = data[v_cols].sum(axis=1)
        
        return data
    
    def encode_categorical_features(self, train_data, test_data):
        """编码类别特征"""
        logger.info("编码类别特征...")
        
        categorical_cols = ['brand', 'model', 'bodyType', 'fuelType', 'gearbox', 
                           'notRepairedDamage', 'regionCode', 'seller', 'offerType']
        
        # 添加新创建的类别特征
        if 'brand_model' in train_data.columns:
            categorical_cols.append('brand_model')
        if 'region_brand' in train_data.columns:
            categorical_cols.append('region_brand')
        
        for col in categorical_cols:
            if col in train_data.columns:
                # 合并训练和测试数据进行编码
                combined_data = pd.concat([train_data[col], test_data[col]], ignore_index=True)
                
                # 使用LabelEncoder
                le = LabelEncoder()
                le.fit(combined_data.astype(str))
                
                train_data[col + '_encoded'] = le.transform(train_data[col].astype(str))
                test_data[col + '_encoded'] = le.transform(test_data[col].astype(str))
                
                self.label_encoders[col] = le
        
        return train_data, test_data
    
    def create_target_encoding(self, train_data, test_data, target_col='price'):
        """目标编码"""
        logger.info("创建目标编码特征...")
        
        if target_col not in train_data.columns:
            logger.warning(f"目标列 {target_col} 不存在，跳过目标编码")
            return train_data, test_data
        
        categorical_cols = ['brand', 'model', 'regionCode']
        
        for col in categorical_cols:
            if col in train_data.columns:
                # 计算每个类别的平均目标值
                target_mean = train_data.groupby(col)[target_col].mean()
                
                # 应用到训练和测试数据
                train_data[col + '_target_enc'] = train_data[col].map(target_mean)
                test_data[col + '_target_enc'] = test_data[col].map(target_mean)
                
                # 填充缺失值（使用全局平均值）
                global_mean = train_data[target_col].mean()
                train_data[col + '_target_enc'].fillna(global_mean, inplace=True)
                test_data[col + '_target_enc'].fillna(global_mean, inplace=True)
        
        return train_data, test_data
    
    def select_features(self, X_train, y_train, X_test, k=100):
        """特征选择"""
        logger.info(f"选择前 {k} 个最重要的特征...")
        
        # 使用SelectKBest进行特征选择
        self.feature_selector = SelectKBest(score_func=f_regression, k=min(k, X_train.shape[1]))
        X_train_selected = self.feature_selector.fit_transform(X_train, y_train)
        X_test_selected = self.feature_selector.transform(X_test)
        
        # 获取选中的特征名
        selected_features = X_train.columns[self.feature_selector.get_support()]
        logger.info(f"选中的特征数量: {len(selected_features)}")
        
        return pd.DataFrame(X_train_selected, columns=selected_features), pd.DataFrame(X_test_selected, columns=selected_features)
    
    def engineer_features(self, train_data, test_data):
        """特征工程主函数"""
        logger.info("开始特征工程...")
        
        # 复制数据避免修改原始数据
        train_processed = train_data.copy()
        test_processed = test_data.copy()
        
        # 1. 创建时间特征
        train_processed = self.create_time_features(train_processed)
        test_processed = self.create_time_features(test_processed)
        
        # 2. 创建交互特征
        train_processed = self.create_interaction_features(train_processed)
        test_processed = self.create_interaction_features(test_processed)
        
        # 3. 创建统计特征
        train_processed = self.create_statistical_features(train_processed)
        test_processed = self.create_statistical_features(test_processed)
        
        # 4. 编码类别特征
        train_processed, test_processed = self.encode_categorical_features(train_processed, test_processed)
        
        # 5. 目标编码
        train_processed, test_processed = self.create_target_encoding(train_processed, test_processed)
        
        # 6. 准备特征矩阵
        # 排除不需要的列（包括原始类别特征，只保留编码后的特征）
        exclude_cols = ['SaleID', 'name', 'regDate', 'creatDate', 'price', 
                       'brand', 'model', 'bodyType', 'fuelType', 'gearbox', 
                       'notRepairedDamage', 'regionCode', 'seller', 'offerType',
                       'brand_model', 'region_brand']  # 排除字符串组合特征
        feature_cols = [col for col in train_processed.columns if col not in exclude_cols]
        
        X_train = train_processed[feature_cols]
        y_train = train_processed['price'] if 'price' in train_processed.columns else None
        X_test = test_processed[feature_cols]
        
        # 确保训练和测试数据有相同的特征
        common_features = list(set(X_train.columns) & set(X_test.columns))
        X_train = X_train[common_features]
        X_test = X_test[common_features]
        
        # 确保所有特征都是数值类型
        for col in X_train.columns:
            if X_train[col].dtype == 'object':
                logger.warning(f"发现非数值特征 {col}，尝试转换为数值类型")
                try:
                    X_train[col] = pd.to_numeric(X_train[col], errors='coerce')
                    X_test[col] = pd.to_numeric(X_test[col], errors='coerce')
                    # 填充转换失败的NaN值
                    X_train[col].fillna(X_train[col].median(), inplace=True)
                    X_test[col].fillna(X_train[col].median(), inplace=True)
                except:
                    logger.error(f"无法转换特征 {col}，将其删除")
                    X_train = X_train.drop(columns=[col])
                    X_test = X_test.drop(columns=[col])
        
        # 7. 特征选择（可选）
        if len(X_train.columns) > 150:  # 如果特征太多，进行特征选择
            X_train, X_test = self.select_features(X_train, y_train, X_test, k=150)
        
        logger.info(f"特征工程完成 - 特征数量: {X_train.shape[1]}")
        logger.info(f"训练数据形状: {X_train.shape}, 测试数据形状: {X_test.shape}")
        
        return X_train, y_train, X_test
