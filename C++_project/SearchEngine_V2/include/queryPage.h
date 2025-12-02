#ifndef __QUERYPAGE_H__
#define __QUERYPAGE_H__
#include "pageLib.h"

/**
 * 查询结果结构体
 * 存储单个查询结果的相关信息
 */
struct queryResult
{
    string title;       // 网页标题
    string link;        // 网页链接
    string description; // 网页摘要
    string content;     // 网页内容
};

/**
 * 用于处理用户查询请求，检索相关网页并返回结果
 */
class queryPage{
public:
    // pagelib 引用已构建的网页库对象
    queryPage(PageLib &pagelib);
    
    /**
     * 执行关键词查询，返回相似网页
     *  m_words 用户输入的查询关键词
     *  qrs 存储查询结果的向量引用
     */
    void wordsSim(string m_words, vector<queryResult> &qrs);
    
    /**
     * 计算查询关键词与网页的交集(intersect)，并获取相关权重
     *  keywords 查询关键词向量
     *  docIds 存储匹配文档ID的向量
     *  weights 存储对应文档的关键词权重矩阵
     */
    void intersect(const vector<string> &keywords, vector<string> &docIds, vector<vector<double>> &weights);
    
    /**
     * 从网页库中提取指定索引的网页信息到查询结果结构
     *  qr 存储提取结果的查询结果结构体引用
     *  idx 网页在网页库中的索引
     */
    void xmlToStr(queryResult &query, int idx);

private:
    PageLib &m_pageLib;  // 引用网页库对象，用于查询操作
};

#endif