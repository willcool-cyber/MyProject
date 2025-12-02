#ifndef __PAGELIBPREPROCESSOR_H__
#define __PAGELIBPREPROCESSOR_H__

#include "pageLib.h"
#include <unordered_map>

using std::vector;
using std::unordered_map;

// 页面库预处理类：负责对原始页面库进行去重、构建倒排索引等预处理操作
class PageLibPreprocessor{
public:
    PageLibPreprocessor(PageLib &pagelib);  // 接收页面库实例引用，初始化预处理对象

    void cutRedundantPages();  // 去重操作：去除页面库中内容重复的页面（如相似文档）

    void buildInvertIndexMap();  // 构建倒排索引：生成关键词到<文档ID, 词频/权重>的映射表

private:
    // 倒排索引表：键为关键词（string），值为该词出现的文档列表（vector<pair<文档ID, 权重>>）
    unordered_map<string,vector<pair<int,double>>> InvertIndexTable;

    PageLib &m_pagelib;  // 关联的原始页面库实例引用（提供预处理所需的原始页面数据）
};


#endif