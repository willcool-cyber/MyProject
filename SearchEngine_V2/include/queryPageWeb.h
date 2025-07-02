#ifndef __QUERYPAGEWEB_H__
#define __QUERYPAGEWEB_H__

#include "pageLib.h"
#include "PageLibPreprocessor.h"
#include "queryPage.h"

// 网页查询服务主类：整合页面存储、预处理和查询功能，提供完整查询接口
class querypageWeb
{
public:
    querypageWeb(string pwd);  // 构造函数：接收工作目录路径（如页面库存储路径）初始化组件

    void start();  // 启动服务：触发预处理（加载页面、构建索引）等初始化流程

    // 执行用户查询
    // 参数：s-用户输入的查询字符串（如"人工智能"），qr-输出查询结果（存储匹配的网页列表）
    void query(string &s, vector<queryResult> &query);

private:
    PageLib m_pagelib;  // 页面库实例：存储原始网页数据（如从文件/数据库加载的网页内容）

    PageLibPreprocessor m_pagelibpreprocessor;  // 预处理实例：对原始页面去重、构建倒排索引（供查询使用）

    queryPage m_querypage;  // 查询处理实例：基于预处理后的索引，执行关键词匹配和结果排序
};

#endif