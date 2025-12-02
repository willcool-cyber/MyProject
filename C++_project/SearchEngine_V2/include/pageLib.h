#ifndef _PAGELIB_H_
#define _PAGELIB_H_

#include <iostream>
#include <string>
#include <vector>
#include <map>
#include <utility>
#include <memory>

using std::string;
using std::vector;
using std::map;
using std::pair;
using std::shared_ptr;

class PageLib{
public:
    PageLib(string);  // 构造函数：接收工作目录路径初始化页面库对象

    void scanXml();   // 扫描指定目录下的XML文件，收集文件路径/基本信息到m_dirScanner

    void create();    // 根据扫描结果创建页面库核心数据（如解析XML内容生成文档数据）

    void store();     // 将页面库数据（如文档内容、索引）持久化存储（如写入磁盘文件）
    shared_ptr<vector<pair<string,int>>> &getFiles();
private:
    string m_pwd;
    vector<string> m_dirScanner; // 文件路径列表（中间结果）
    shared_ptr<vector<pair<string,int>>> m_files;// 存储最终文件信息的容器
    map<int,pair<int,int>> m_officeLib;  // 文档库元数据映射：键为文档ID，值为<起始位置, 长度>（用于快速定位存储中的文档内容）
};

#endif