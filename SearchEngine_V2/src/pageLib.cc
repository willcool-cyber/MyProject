#include "../include/pageLib.h"
#include "../include/tinyxml2/tinyxml2.h"
#include <sw/redis++/redis++.h>
#include <iostream>
#include <fstream>
#include <string.h>
#include <dirent.h>

using std::ofstream;
using std::cout;
using std::endl;
using std::cerr;
using std::to_string;
using namespace tinyxml2;
using namespace sw::redis;

/**
 * 存储从RSS源解析出来的文章信息
 */
struct RssItem{
    string url;      // 文章链接
    string title;    // 文章标题
    string content;  // 文章内容
};

/**
 * 从字符串中移除所有HTML标签
 *  input 包含HTML标签的字符串
 *  return 移除标签后的纯文本
 */
string removeHtmlTags(const string &input){
    string result;
    bool inTag = false;  // 标记是否在标签内部
    
    for (char c : input) {
        if (c == '<') {
            inTag = true;  // 进入标签
            continue;
        }
        if (c == '>') {
            inTag = false;  // 离开标签
            continue;
        }
        if (!inTag) {
            result += c;  // 不在标签内的字符添加到结果
        }
    }
    
    return result;
}

/**
 * 扫描指定目录下的所有XML文件
 */
void PageLib::scanXml(){
    DIR *dirp = opendir(m_pwd.c_str());  // 打开目录
    if(nullptr == dirp)
    {
        perror("opendir");
    }
    
    struct dirent *pdirent;
    // 遍历目录中的所有条目
    while((pdirent = readdir(dirp)) != nullptr)
    {
        // 跳过当前目录和上级目录
        if(strcmp(pdirent->d_name, ".") == 0 || strcmp(pdirent->d_name, "..") == 0)
        {
            continue;
        }
        string pwd = m_pwd + pdirent->d_name;  // 构建完整文件路径
        m_dirScanner.push_back(pwd);  // 将文件路径添加到扫描结果列表
    }

    closedir(dirp);  // 关闭目录
}


PageLib::PageLib(string pwd)
: m_pwd(pwd)
, m_files(new vector<pair<string, int>>){}  // 初始化文件内容存储容器

/**
 * 从XML文件中提取内容并创建网页库
 */
void PageLib::create(){
    int docid = 1;  // 文档ID计数器
    
    // 遍历所有XML文件
    for(auto it = m_dirScanner.begin(); it != m_dirScanner.end(); ++it)
    {
        XMLDocument doc;
        // 加载XML文件
        if(doc.LoadFile(it->c_str()) != 0)
        {
            cout << "load xml file failed" << endl;
            return;
        }
        
        XMLElement *root = doc.RootElement();  // 获取根元素
        XMLElement *channel = root->FirstChildElement("channel");  // 获取channel元素

        XMLElement *item = channel->FirstChildElement("item");  // 获取第一个item元素
        
        // 遍历所有item元素
        while(item != nullptr)
        {
            // 获取文章标题、链接和内容元素
            XMLElement *title = item->FirstChildElement("title");
            XMLElement *url = item->FirstChildElement("link");
            XMLElement *content = item->FirstChildElement("description");
            
            RssItem node;
            node.title = title->GetText();  // 获取标题文本
            node.url = url->GetText();      // 获取链接文本
            
            // 获取内容文本并移除HTML标签
            if(content != nullptr)
            {
                node.content = removeHtmlTags(content->GetText());
            }

            // 构建格式化的文档字符串
            string fmtTxt = "<doc><docid>" + to_string(docid) +
                            "</docid><url>" + node.url +
                            "</url><title>" + node.title +
                            "</title><content>" + node.content +
                            "</content></doc>";
            
            // 将格式化文档添加到文件内容列表，第二个参数0表示未处理状态
            m_files->push_back(std::make_pair(fmtTxt, 0));
            
            ++docid;  // 增加文档ID

            item = item->NextSiblingElement();  // 移动到下一个item元素
        }
    }
}

/**
 * 将处理后的网页库存储到文件和Redis中
 */
void PageLib::store(){
    // 打开网页库数据文件
    ofstream ofs("../data/ripepage.dat");
    if(!ofs.good()){
        cerr << "ofstream open file faild!" << endl;
        return;
    }
    
    // 连接Redis数据库
    auto redis = Redis("tcp://127.0.0.1:6379/4");
    redis.flushdb();  // 清空数据库

    // 将所有文档写入文件并存储到Redis
    for(int i = 0; i < (*m_files).size(); ++i)
    {
        if(0 == (*m_files)[i].second)  // 只处理未处理的文档
        {
            ofs << (*m_files)[i].first;  // 写入文件
            redis.set(std::to_string(i+1), (*m_files)[i].first);  // 存储到Redis
        }
    }
    ofs.close();  // 关闭文件

    // 打开偏移量数据文件
    ofstream ofs2("../data/offset.dat");
    int flag = 0;  // 当前文档在文件中的起始位置
    int i = 1;     // 文档ID
    
    // 生成并存储文档偏移量信息
    for(auto it = m_files->begin(); it != m_files->end(); ++it)
    {
        if(0 == it->second)  // 只处理未处理的文档
        {
            // 存储文档ID、起始位置和长度
            m_officeLib.insert(std::make_pair(i, std::make_pair(flag, it->first.size())));       
            flag += it->first.size();  // 更新下一个文档的起始位置
        }
        ++i;  // 增加文档ID
    }
    
    // 将偏移量信息写入文件
    for(auto &elem : m_officeLib)
    {
        ofs2 << elem.first << " " << elem.second.first << " " << elem.second.second << endl;
    }
    ofs2.close();  // 关闭文件
}

/**
 * 获取处理后的文件内容
 * return 指向文件内容向量的共享指针的引用
 */
shared_ptr<vector<pair<string, int>>> &PageLib::getFiles(){
    return m_files;
}