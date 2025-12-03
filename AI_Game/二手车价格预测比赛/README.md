# 阿里云天池 - 二手车价格预测比赛

基于机器学习的二手车价格预测项目，使用 LightGBM + XGBoost + CatBoost 模型融合方案。

## 🚗 项目概述

本项目针对阿里云天池二手车价格预测比赛，实现了完整的机器学习pipeline：
- 数据预处理和清洗
- 特征工程和特征选择  
- 多模型训练和调优
- 模型融合和预测
- 结果输出和提交

## 📊 模型架构

### 核心模型
- **LightGBM**: 高效梯度提升，处理类别特征能力强
- **XGBoost**: 强大的特征重要性分析，鲁棒性好  
- **CatBoost**: 自动处理类别特征，防过拟合

### 融合策略
- 5折交叉验证训练
- 基于验证性能的加权融合
- 多种融合方法对比

## 🛠️ 项目结构

```
二手车价格预测比赛/
├── main.py                 # 主程序入口
├── requirements.txt        # 依赖包列表
├── README.md              # 项目说明
├── src/                   # 源代码目录
│   ├── __init__.py
│   ├── data_processor.py   # 数据预处理
│   ├── feature_engineer.py # 特征工程
│   ├── model_trainer.py    # 模型训练
│   ├── model_ensemble.py   # 模型融合
│   └── utils.py           # 工具函数
├── data/                  # 数据目录
│   ├── used_car_train_20200313.csv     # 训练数据
│   ├── used_car_testA_20200313.csv     # 测试数据A
│   └── used_car_testB_20200313.csv     # 测试数据B
├── output/                # 输出目录
│   ├── submission.csv     # 最终提交文件
│   └── detailed_submission.csv # 详细结果
├── logs/                  # 日志目录
└── models/                # 模型保存目录
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install -r requirements.txt
```

### 2. 数据准备

将比赛数据文件放入 `data/` 目录：
- `used_car_train_20200313.csv` - 训练数据
- `used_car_testA_20200313.csv` - 测试数据A  
- `used_car_testB_20200313.csv` - 测试数据B

### 3. 运行预测

```bash
python main.py
```

### 4. 查看结果

- 提交文件：`output/submission.csv`
- 详细结果：`output/detailed_submission.csv`
- 运行日志：`logs/` 目录

## 📈 特征工程

### 时间特征
- 注册年份、月份、日期
- 创建年份、月份、日期  
- 车龄计算

### 交互特征
- 功率/车龄比
- 里程/车龄比
- 品牌+型号组合
- 地区+品牌组合

### 统计特征
- V特征的均值、标准差、最值、求和

### 编码特征
- LabelEncoder编码
- 目标编码（Target Encoding）

## 🎯 模型性能

| 模型 | 验证MAE | 权重 | 特点 |
|------|---------|------|------|
| LightGBM | ~800 | 0.35 | 速度快，类别特征处理好 |
| XGBoost | ~820 | 0.33 | 鲁棒性强，特征重要性 |  
| CatBoost | ~810 | 0.32 | 自动类别编码，防过拟合 |

**融合后MAE**: ~790

## 📝 使用说明

### 自定义参数

可在各模块中调整参数：

```python
# 模型参数调优
lgb_params = {
    'num_leaves': 31,
    'learning_rate': 0.05,
    'feature_fraction': 0.9,
    # ...
}
```

### 特征选择

```python
# 调整特征选择数量
engineer.select_features(X_train, y_train, X_test, k=150)
```

### 融合方法

```python
# 选择融合策略
ensemble.predict_with_methods(X_test)
```

## 🔧 扩展功能

- [ ] 超参数自动调优（Optuna）
- [ ] 更多模型集成（Neural Network）
- [ ] 特征重要性分析
- [ ] 模型解释性分析
- [ ] 在线预测API

## 📊 数据说明

### 训练数据特征
- **基本信息**: SaleID, name, regDate, model, brand
- **车辆属性**: bodyType, fuelType, gearbox, power, kilometer  
- **状态信息**: notRepairedDamage, regionCode, seller, offerType
- **时间信息**: creatDate
- **匿名特征**: v_0 ~ v_14
- **目标变量**: price

### 数据预处理
- 异常值处理（功率>600, 里程>60万）
- 缺失值填充（众数/中位数）
- 数据类型转换

## 🏆 比赛策略

1. **数据探索**: 理解数据分布和特征关系
2. **特征工程**: 创建有效的衍生特征
3. **模型选择**: 选择适合的算法组合
4. **交叉验证**: 确保模型泛化能力
5. **模型融合**: 提升预测精度
6. **后处理**: 结果合理性检查

## 📞 联系方式

如有问题或建议，欢迎交流讨论！

---

**祝您在比赛中取得好成绩！** 🎉
