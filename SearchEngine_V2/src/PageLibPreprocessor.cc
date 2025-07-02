#include "../include/PageLibPreprocessor.h"
#include "../include/simhash/Simhasher.hpp"
#include <math.h>
#include <fstream>
#include <sw/redis++/redis++.h>

using namespace simhash;
using std::ofstream;
using namespace sw::redis;

/**
 * 网页库预处理器构造函数
 *  pl 引用已构建的网页库对象（PageLib）
 */
PageLibPreprocessor::PageLibPreprocessor(PageLib &pagelib)
: m_pagelib(pagelib){}
    // 初始化预处理器，关联到现有网页库


/**
 * 去除网页库中的重复页面，并构建倒排索引表
 * 使用Simhash算法计算文本相似度，实现网页去重
 */
void PageLibPreprocessor::cutRedundantPages()
{
    // 初始化Simhash分词器，加载必要的词典文件
    Simhasher simhasher("../include/simhash/dict/jieba.dict.utf8",
                        "../include/simhash/dict/hmm_model.utf8",
                        "../include/simhash/dict/idf.utf8",
                        "../include/simhash/dict/stop_words.utf8");

    vector<uint64_t> simhashList;  // 存储已处理网页的Simhash值
    vector<pair<string,int>> &files = *(m_pagelib.getFiles());  // 获取网页库内容
    
    // 遍历所有网页
    for(int i = 0; i < files.size(); ++i)
    {
        size_t topN = 300;  // 提取前300个关键词
        uint64_t u64 = 0;   // 存储当前网页的Simhash值
        vector<pair<string,double>> res;  // 存储关键词及其权重
        
        // 从网页内容中提取关键词及其权重
        simhasher.extract(files[i].first, res, topN);
        // 计算当前网页的Simhash值
        simhasher.make(files[i].first, topN, u64);

        bool isequal = false;  // 标记是否与已有网页相似
        
        // 检查当前网页是否与已处理的网页相似
        for(auto it = simhashList.begin(); it != simhashList.end(); ++it)
        {
            if(Simhasher::isEqual(u64, *it))  // 使用Simhash比较相似度
            {
                isequal = true;
                files[i].second = 1;  // 标记为重复页面(second=1表示重复)
                break;
            }
        }
        
        // 如果是新网页(不重复)
        if(!isequal)
        {
            simhashList.push_back(u64);  // 添加新网页的Simhash值
            
            // 计算向量模长(用于TF-IDF归一化)
            double sql = 0;
            for(auto itres = res.begin(); itres != res.end(); ++itres)
            {
                sql += (itres->second) * (itres->second);  // 权重平方和
            }
            sql = sqrt(sql);  // 开方得到模长
            
            // 构建倒排索引表: 关键词 -> (文档ID, 归一化权重)
            for(auto &elem : res)
            {
                InvertIndexTable[elem.first].push_back(std::make_pair(i+1, elem.second/sql));
            }
        }
    }
}

/**
 * 将倒排索引表写入文件和Redis数据库
 * 倒排索引结构: 关键词 -> [(文档ID1, 权重1), (文档ID2, 权重2), ...]
 */
void PageLibPreprocessor::buildInvertIndexMap()
{
    // 打开倒排索引数据文件
    ofstream ofs("../data/invertIndex.dat");
    // 连接Redis数据库(索引存储在DB5)
    auto redis = Redis("tcp://127.0.0.1:6379/5");
    redis.flushdb();  // 清空当前数据库

    // 遍历倒排索引表中的每个关键词
    for(auto &elem : InvertIndexTable)
    {
        ofs << elem.first << "  ";  // 写入关键词
        
        // 遍历该关键词出现的所有文档及对应的权重
        for(auto it = elem.second.begin(); it != elem.second.end(); ++it)
        {
            ofs << it->first << "  " << it->second << "  ";  // 写入: 文档ID 权重
            
            // 将文档ID和权重存入Redis的有序集合(关键词作为键)
            redis.zadd(elem.first, std::to_string(it->first), it->second);
        }
        ofs << endl;  // 结束当前关键词的记录
    }
}