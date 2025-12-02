#include "../include/queryPage.h"
#include "../include/simhash/Simhasher.hpp"
#include <sw/redis++/redis++.h>
#include <string>
#include <vector>
#include <set>
#include <algorithm>
#include <cmath>
#include <cstdlib>

using namespace simhash;
using namespace sw::redis;
using std::pair;
using std::string;
using std::vector;
using std::set;

/**
 * 
 *  负责处理用户查询请求，实现关键词检索、相似度计算和结果生成
 *  依赖PageLib网页库和Redis存储的倒排索引数据，通过Simhash算法提取关键词
 *  使用余弦相似度进行文档排序
 */
queryPage::queryPage(PageLib &pagelib)
: m_pageLib(pagelib) // 初始化成员变量，关联网页库对象
{}

/**
 *  从字符串中提取指定标签对之间的内容
 *  content 包含标签的完整文档内容字符串
 *  startTag 起始标签（如"<url>"，包含尖括号）
 *  endTag 结束标签（如"</url>"，包含尖括号）
 *  标签对之间的内容，若标签不存在则返回空字符串
 *  示例：输入"<url>http://example.com</url>"，提取结果为"http://example.com"
 */
string extractTagContent(const string &content, const string &startTag, const string &endTag) {
    // 查找起始标签位置
    size_t startPos = content.find(startTag);
    if (startPos == string::npos) return ""; // 起始标签不存在时返回空

    // 定位到标签内容的起始位置（跳过标签本身）
    startPos += startTag.length();
    // 查找结束标签位置（从startPos之后开始查找）
    size_t endPos = content.find(endTag, startPos);
    if (endPos == string::npos) return ""; // 结束标签不存在时返回空

    // 提取标签之间的内容并返回
    return content.substr(startPos, endPos - startPos);
}

/**
 *  执行关键词相似度查询，返回相关网页结果
 *  m_words 用户输入的查询关键词字符串（如"人工智能 大数据"）
 *  qrs 输出参数，存储查询结果的向量（每个元素包含网页标题、链接、摘要和内容）
 *  流程：
 * 1. 使用Simhash提取查询关键词及其TF-IDF权重
 * 2. 在Redis倒排索引中查询包含所有关键词的文档（交集）
 * 3. 计算文档与查询的余弦相似度并按降序排序
 * 4. 提取前10条结果，生成包含关键词的摘要
 */
void queryPage::wordsSim(string m_words, vector<queryResult> &qrs) {
    set<string> dc; // 存储查询关键词集合（自动去重）

    // 初始化Simhash分词器，加载中文分词所需词典和模型
    Simhasher simhasher(
        "../include/simhash/dict/jieba.dict.utf8",
        "../include/simhash/dict/hmm_model.utf8",
        "../include/simhash/dict/idf.utf8",
        "../include/simhash/dict/stop_words.utf8" 
    );

    size_t topN = 3; // 提取最重要的3个关键词（根据TF-IDF值）
    vector<pair<string, double>> res; // 存储关键词及其权重（词-权重对）
    
    // 从查询语句中提取关键词和权重
    simhasher.extract(m_words, res, topN);

    vector<string> keys;        // 关键词列表（如{"人工智能", "大数据"}）
    vector<double> keyWeigth;   // 关键词权重列表（TF-IDF值）
    for (auto &elem : res) {
        keys.push_back(elem.first);
        keyWeigth.push_back(elem.second);
        dc.insert(elem.first); // 将关键词加入集合去重
    }

    vector<string> result;       // 存储匹配的文档ID（字符串形式，如"123"）
    vector<vector<double>> weight; // 存储文档-关键词权重矩阵（每行对应一个文档的各关键词权重）

    // 查询倒排索引，获取包含所有关键词的文档及对应权重
    intersect(keys, result, weight);

    vector<pair<string, double>> resPage; // 存储文档ID与相似度分数

    // 计算每个文档与查询的余弦相似度
    for (int i = 0; i < weight.size(); ++i) {
        double xy = 0, x = 0, y = 0; // 分子（点积）、分母（向量模长乘积）

        // 计算向量点积和模长
        for (int j = 0; j < keyWeigth.size(); ++j) {
            xy += weight[i][j] * keyWeigth[j];    // 点积项
            x += weight[i][j] * weight[i][j];      // 文档向量模长平方
            y += keyWeigth[j] * keyWeigth[j];      // 查询向量模长平方
        }
        // 避免除零错误，处理模长为0的极端情况（通常不会发生）
        double tmp = (x == 0 || y == 0) ? 0.0 : xy / (sqrt(x) * sqrt(y));
        resPage.push_back(std::make_pair(result[i], tmp));
    }

    // 按相似度降序排序（Lambda表达式：a的相似度大于b则排在前面）
    sort(resPage.begin(), resPage.end(),
         [](const pair<string, double> &a, const pair<string, double> &b) {
             return a.second > b.second;
         });

    int numToAdd = 0; // 限制最多返回10条结果
    for (auto &elem : resPage) {
        set<string> dcp = dc; // 复制查询关键词集合，用于生成摘要
        queryResult qr;       // 单条查询结果

        // 从Redis中提取文档详细信息（文档ID转换为整数索引）
        xmlToStr(qr, atoi(elem.first.c_str()));

        size_t topN2 = 5; // 从文档内容中提取前5个关键词补充到摘要
        vector<pair<string, double>> res2;
        simhasher.extract(qr.content, res2, topN2); // 提取文档内容关键词
        // 提取文档内容关键词
        simhasher.extract(qr.content, res2, topN2);

        // 将文档内容关键词加入摘要集合（去重）
        for (auto &resElem : res2) {
            dcp.insert(resElem.first);
        }

        // 构建摘要：拼接所有关键词（查询词+文档词），用空格分隔
        for (auto &setElem : dcp) {
            qr.description += setElem + "  "; // 每个关键词后加两个空格
        }
        qrs.push_back(qr); // 添加结果到返回向量

        if (++numToAdd >= 10) break; // 限制结果数量为10条
    }
}

/**
 *  在Redis倒排索引中查询多个关键词的共同文档，并获取对应权重
 *  keys 查询关键词列表（如{"云计算", "机器学习"}）
 *  result 输出：匹配的文档ID列表（按相似度降序排列，字符串形式）
 *  weight 输出：文档-关键词权重矩阵（每行对应一个文档的各关键词权重）
 *  使用Redis的ZINTERSTORE命令计算交集，临时键"intersect"存储中间结果
 */
void queryPage::intersect(const vector<string> &keys, 
                         vector<string> &result, 
                         vector<vector<double>> &weight) {
    // 连接Redis倒排索引数据库（DB5，使用redis://协议格式）
    auto redis = Redis("tcp://127.0.0.1:6379/5");
    
    // 计算多个关键词对应有序集合的交集，结果存入临时键"intersect"
    // 交集文档需包含所有关键词，分数为各集合分数的和（ZINTERSTORE默认聚合方式）
    redis.zinterstore("intersect", keys.begin(), keys.end());
    
    // 获取交集结果中的文档ID（按分数降序排列，分数越高相关性越强）
    redis.zrange("intersect", 0, -1, back_inserter(result));

    // 提取每个文档在各关键词下的权重（TF-IDF归一化值）
    for (auto &elem : result) { // elem为文档ID字符串（如"456"）
        vector<double> wei; // 存储当前文档在所有关键词下的权重
        for (auto &key : keys) { // 遍历每个查询关键词
            // 获取文档在关键词对应有序集合中的分数（权重）
            auto score = redis.zscore(key, elem);
            // 处理可能的空值（文档包含关键词但无权重，理论上不应出现）
            wei.push_back(score ? *score : 0.0);
        }
        weight.push_back(wei); // 添加当前文档的权重向量
    }

    // 删除临时键，释放Redis内存
    vector<string> intersectKeys = {"intersect"};
    redis.del(intersectKeys.begin(), intersectKeys.end());
}

/**
 *  从Redis中提取文档内容，解析出URL、标题和内容
 *  qr 输出参数，存储解析后的网页信息
 *  idx 文档ID（整数，对应Redis中的键名如"1", "2"）
 *  使用字符串查找方法提取标签内容，避免正则表达式依赖
 */
void queryPage::xmlToStr(queryResult &qr, int idx) {
    // 连接Redis网页内容数据库（DB4，存储格式为<doc>标签包裹的字符串）
    auto redis1 = Redis("tcp://127.0.0.1:6379/4");
    // 根据文档ID获取内容（键名为字符串形式的ID，如"idx"对应"3"）
    auto contentOpt = redis1.get(std::to_string(idx));
    if (!contentOpt) return; // 文档不存在时直接返回

    string content = *contentOpt; // 解包可选值，获取文档内容字符串

    // 提取URL（通过标签解析函数）
    qr.link = extractTagContent(content, "<url>", "</url>");
    // 提取标题
    qr.title = extractTagContent(content, "<title>", "</title>");
    // 提取正文内容
    qr.content = extractTagContent(content, "<content>", "</content>");
}