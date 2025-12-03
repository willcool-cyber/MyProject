#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模型融合模块
实现多模型预测结果的融合和最终预测
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ModelEnsemble:
    """模型融合器"""
    
    def __init__(self, models):
        self.models = models
        
    def predict_single_model(self, model_name, X_test):
        """单个模型预测"""
        if model_name not in self.models:
            logger.warning(f"模型 {model_name} 不存在")
            return None
        
        model_info = self.models[model_name]
        fold_models = model_info['models']
        
        # 所有fold模型的预测结果
        predictions = []
        
        for fold_model in fold_models:
            if model_name == 'lightgbm':
                pred = fold_model.predict(X_test)
            elif model_name == 'xgboost':
                pred = fold_model.predict(X_test)
            elif model_name == 'catboost':
                pred = fold_model.predict(X_test)
            else:
                continue
            
            predictions.append(pred)
        
        # 取平均值作为最终预测
        if predictions:
            return np.mean(predictions, axis=0)
        else:
            return None
    
    def predict(self, X_test):
        """融合预测"""
        logger.info("开始模型融合预测...")
        
        all_predictions = {}
        weights = {}
        
        # 获取每个模型的预测结果
        for model_name in self.models:
            pred = self.predict_single_model(model_name, X_test)
            if pred is not None:
                all_predictions[model_name] = pred
                weights[model_name] = self.models[model_name]['weight']
                logger.info(f"{model_name} 预测完成，权重: {weights[model_name]:.3f}")
        
        if not all_predictions:
            raise ValueError("没有可用的模型进行预测")
        
        # 加权融合
        final_predictions = np.zeros(len(X_test))
        total_weight = sum(weights.values())
        
        for model_name, pred in all_predictions.items():
            weight = weights[model_name] / total_weight
            final_predictions += weight * pred
            logger.info(f"{model_name} 融合权重: {weight:.3f}")
        
        logger.info("模型融合预测完成")
        return final_predictions
    
    def predict_with_methods(self, X_test):
        """使用多种融合方法预测"""
        logger.info("使用多种融合方法预测...")
        
        all_predictions = {}
        
        # 获取每个模型的预测结果
        for model_name in self.models:
            pred = self.predict_single_model(model_name, X_test)
            if pred is not None:
                all_predictions[model_name] = pred
        
        if not all_predictions:
            raise ValueError("没有可用的模型进行预测")
        
        predictions_array = np.array(list(all_predictions.values()))
        
        # 方法1: 简单平均
        simple_avg = np.mean(predictions_array, axis=0)
        
        # 方法2: 加权平均（基于验证性能）
        weights = np.array([self.models[name]['weight'] for name in all_predictions.keys()])
        weighted_avg = np.average(predictions_array, axis=0, weights=weights)
        
        # 方法3: 中位数
        median_pred = np.median(predictions_array, axis=0)
        
        # 返回加权平均作为主要结果
        return weighted_avg, {
            'simple_avg': simple_avg,
            'weighted_avg': weighted_avg,
            'median': median_pred
        }
    
    def save_submission(self, predictions, test_ids, filename='submission.csv'):
        """保存提交文件"""
        logger.info("保存提交文件...")
        
        # 确保输出目录存在
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        # 使用实际的测试数据SaleID，不要强制修改
        # testA: 150000-199999, testB: 200000-249999
        sale_ids = test_ids
        
        # 创建提交数据框
        submission = pd.DataFrame({
            'SaleID': sale_ids,
            'price': predictions
        })
        
        # 保存文件
        output_path = output_dir / filename
        submission.to_csv(output_path, index=False)
        
        logger.info(f"提交文件已保存到: {output_path}")
        logger.info(f"预测价格统计:")
        logger.info(f"  最小值: {predictions.min():.2f}")
        logger.info(f"  最大值: {predictions.max():.2f}")
        logger.info(f"  平均值: {predictions.mean():.2f}")
        logger.info(f"  中位数: {np.median(predictions):.2f}")
        
        return output_path
    
    def save_detailed_submission(self, X_test, test_ids):
        """保存详细的提交文件（包含多种融合方法）"""
        logger.info("生成详细提交文件...")
        
        # 获取多种预测结果
        main_pred, all_methods = self.predict_with_methods(X_test)
        
        # 创建详细提交数据框
        detailed_submission = pd.DataFrame({
            'SaleID': test_ids,
            'price_main': main_pred,
            'price_simple_avg': all_methods['simple_avg'],
            'price_weighted_avg': all_methods['weighted_avg'],
            'price_median': all_methods['median']
        })
        
        # 保存详细文件
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        detailed_path = output_dir / "detailed_submission.csv"
        detailed_submission.to_csv(detailed_path, index=False)
        
        # 保存主要提交文件
        main_submission_path = self.save_submission(main_pred, test_ids)
        
        logger.info(f"详细提交文件已保存到: {detailed_path}")
        
        return main_submission_path, detailed_path
