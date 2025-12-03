#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模型训练模块
包含 LightGBM、XGBoost、CatBoost 模型的训练和调优
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import KFold, cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error
import lightgbm as lgb
import xgboost as xgb
import catboost as cb
import logging

logger = logging.getLogger(__name__)

class ModelTrainer:
    """模型训练器"""
    
    def __init__(self, n_folds=5, random_state=42):
        self.n_folds = n_folds
        self.random_state = random_state
        self.models = {}
        
    def train_lightgbm(self, X_train, y_train):
        """训练 LightGBM 模型"""
        logger.info("开始训练 LightGBM 模型...")
        
        # LightGBM 参数 - 超级激进优化（目标500以内）
        lgb_params = {
            'objective': 'regression',
            'metric': 'mae',
            'boosting_type': 'gbdt',
            'num_leaves': 50,  # 显著增加复杂度
            'learning_rate': 0.025,  # 更低的学习率
            'feature_fraction': 0.95,  # 更高的特征采样
            'bagging_fraction': 0.95,  # 更高的样本采样
            'bagging_freq': 1,
            'min_child_samples': 5,  # 极低约束
            'min_child_weight': 0.0001,
            'reg_alpha': 0.01,  # 极低正则化
            'reg_lambda': 0.01,
            'lambda_l1': 0.001,
            'lambda_l2': 0.001,
            'min_gain_to_split': 0.001,
            'verbose': -1,
            'random_state': self.random_state,
            'n_estimators': 3000,  # 大幅增加迭代
            'early_stopping_rounds': 500
        }
        
        # 交叉验证训练
        kf = KFold(n_splits=self.n_folds, shuffle=True, random_state=self.random_state)
        lgb_models = []
        cv_scores = []
        
        for fold, (train_idx, val_idx) in enumerate(kf.split(X_train)):
            X_fold_train, X_fold_val = X_train.iloc[train_idx], X_train.iloc[val_idx]
            y_fold_train, y_fold_val = y_train.iloc[train_idx], y_train.iloc[val_idx]
            
            # 创建数据集
            train_data = lgb.Dataset(X_fold_train, label=y_fold_train)
            val_data = lgb.Dataset(X_fold_val, label=y_fold_val, reference=train_data)
            
            # 训练模型
            model = lgb.train(
                lgb_params,
                train_data,
                valid_sets=[val_data],
                callbacks=[lgb.log_evaluation(0)]
            )
            
            # 预测验证集
            val_pred = model.predict(X_fold_val)
            mae = mean_absolute_error(y_fold_val, val_pred)
            cv_scores.append(mae)
            lgb_models.append(model)
            
            logger.info(f"LightGBM Fold {fold+1} MAE: {mae:.4f}")
        
        avg_mae = np.mean(cv_scores)
        logger.info(f"LightGBM 平均 MAE: {avg_mae:.4f} (+/- {np.std(cv_scores)*2:.4f})")
        
        return lgb_models, avg_mae
    
    def train_xgboost(self, X_train, y_train):
        """训练 XGBoost 模型"""
        logger.info("开始训练 XGBoost 模型...")
        
        # XGBoost 参数 - 超级激进优化（目标500以内）
        xgb_params = {
            'objective': 'reg:squarederror',
            'eval_metric': 'mae',
            'max_depth': 7,  # 增加深度以捕捉更复杂的模式
            'learning_rate': 0.03,  # 更低的学习率
            'subsample': 0.92,  # 更高的采样
            'colsample_bytree': 0.92,
            'colsample_bylevel': 0.92,
            'colsample_bynode': 0.92,
            'min_child_weight': 0.5,  # 降低约束
            'reg_alpha': 0.001,  # 极低L1正则化
            'reg_lambda': 0.001,  # 极低L2正则化
            'gamma': 0.001,  # 极低损失减少阈值
            'scale_pos_weight': 1,
            'random_state': self.random_state,
            'n_estimators': 3000,  # 大幅增加迭代
            'early_stopping_rounds': 500,
            'verbose': False,
            'enable_categorical': False
        }
        
        # 交叉验证训练
        kf = KFold(n_splits=self.n_folds, shuffle=True, random_state=self.random_state)
        xgb_models = []
        cv_scores = []
        
        for fold, (train_idx, val_idx) in enumerate(kf.split(X_train)):
            X_fold_train, X_fold_val = X_train.iloc[train_idx], X_train.iloc[val_idx]
            y_fold_train, y_fold_val = y_train.iloc[train_idx], y_train.iloc[val_idx]
            
            # 训练模型
            model = xgb.XGBRegressor(**xgb_params)
            model.fit(
                X_fold_train, y_fold_train,
                eval_set=[(X_fold_val, y_fold_val)],
                verbose=False
            )
            
            # 预测验证集
            val_pred = model.predict(X_fold_val)
            mae = mean_absolute_error(y_fold_val, val_pred)
            cv_scores.append(mae)
            xgb_models.append(model)
            
            logger.info(f"XGBoost Fold {fold+1} MAE: {mae:.4f}")
        
        avg_mae = np.mean(cv_scores)
        logger.info(f"XGBoost 平均 MAE: {avg_mae:.4f} (+/- {np.std(cv_scores)*2:.4f})")
        
        return xgb_models, avg_mae
    
    def train_catboost(self, X_train, y_train):
        """训练 CatBoost 模型"""
        logger.info("开始训练 CatBoost 模型...")
        
        # CatBoost 参数 - 回到原始配置
        cb_params = {
            'loss_function': 'MAE',
            'eval_metric': 'MAE',
            'depth': 6,
            'learning_rate': 0.05,
            'iterations': 1000,
            'random_seed': self.random_state,
            'verbose': False,
            'early_stopping_rounds': 100
        }
        
        # 交叉验证训练
        kf = KFold(n_splits=self.n_folds, shuffle=True, random_state=self.random_state)
        cb_models = []
        cv_scores = []
        
        for fold, (train_idx, val_idx) in enumerate(kf.split(X_train)):
            X_fold_train, X_fold_val = X_train.iloc[train_idx], X_train.iloc[val_idx]
            y_fold_train, y_fold_val = y_train.iloc[train_idx], y_train.iloc[val_idx]
            
            # 训练模型
            model = cb.CatBoostRegressor(**cb_params)
            model.fit(
                X_fold_train, y_fold_train,
                eval_set=(X_fold_val, y_fold_val),
                verbose=False
            )
            
            # 预测验证集
            val_pred = model.predict(X_fold_val)
            mae = mean_absolute_error(y_fold_val, val_pred)
            cv_scores.append(mae)
            cb_models.append(model)
            
            logger.info(f"CatBoost Fold {fold+1} MAE: {mae:.4f}")
        
        avg_mae = np.mean(cv_scores)
        logger.info(f"CatBoost 平均 MAE: {avg_mae:.4f} (+/- {np.std(cv_scores)*2:.4f})")
        
        return cb_models, avg_mae
    
    def train_models(self, X_train, y_train):
        """训练所有模型"""
        logger.info("开始训练所有模型...")
        
        models = {}
        
        try:
            # 训练 LightGBM
            lgb_models, lgb_mae = self.train_lightgbm(X_train, y_train)
            models['lightgbm'] = {
                'models': lgb_models,
                'mae': lgb_mae,
                'weight': 1.0
            }
        except Exception as e:
            logger.error(f"LightGBM 训练失败: {str(e)}")
        
        try:
            # 训练 XGBoost
            xgb_models, xgb_mae = self.train_xgboost(X_train, y_train)
            models['xgboost'] = {
                'models': xgb_models,
                'mae': xgb_mae,
                'weight': 1.0
            }
        except Exception as e:
            logger.error(f"XGBoost 训练失败: {str(e)}")
        
        # 注释掉CatBoost，只使用XGBoost和LightGBM进行双模型融合
        # try:
        #     # 训练 CatBoost
        #     cb_models, cb_mae = self.train_catboost(X_train, y_train)
        #     models['catboost'] = {
        #         'models': cb_models,
        #         'mae': cb_mae,
        #         'weight': 1.0
        #     }
        # except Exception as e:
        #     logger.error(f"CatBoost 训练失败: {str(e)}")
        
        # 检查是否有成功训练的模型
        if not models:
            logger.error("没有模型训练成功！")
            raise ValueError("所有模型训练都失败了")
        
        # 计算权重（基于性能的倒数）
        if len(models) > 1:
            total_inv_mae = sum(1/model_info['mae'] for model_info in models.values())
            for model_name in models:
                models[model_name]['weight'] = (1/models[model_name]['mae']) / total_inv_mae
        else:
            # 只有一个模型时，权重设为1
            for model_name in models:
                models[model_name]['weight'] = 1.0
        
        logger.info("所有模型训练完成")
        for model_name, model_info in models.items():
            logger.info(f"{model_name}: MAE={model_info['mae']:.4f}, Weight={model_info['weight']:.3f}")
        
        self.models = models
        return models
