#include "../include/queryPageWeb.h"
#include <iostream>

querypageWeb::querypageWeb(string pwd)
: m_pagelib(pwd)
, m_pagelibpreprocessor(m_pagelib)
, m_querypage(m_pagelib){}

void querypageWeb::start(){
    //扫描路径搜索xml文件
    m_pagelib.scanXml();

    //建立网页库和网页偏移库
    m_pagelib.create();

    //网页库去重
    m_pagelibpreprocessor.cutRedundantPages();

    //网页库和网页偏移库保存到硬盘
    m_pagelib.store();

    //建立倒排索引库并把倒排索引库保存到硬盘和redis服务器
    m_pagelibpreprocessor.buildInvertIndexMap();
}

void querypageWeb::query(string &s, vector<queryResult> &query){
    m_querypage.wordsSim(s,query);
}
