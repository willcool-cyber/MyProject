#include "../include/pageLib.h"
#include "../include/PageLibPreprocessor.h"
#include "../include/queryPage.h"
#include "../include/queryPageWeb.h"
#include <iostream>
#include <string>
#include <vector>
#include <string.h>

#define PAGEPWD "../conf/page/" // 定义网页配置文件路径宏

using std::cerr;
using std::cout;
using std::endl;
using std::cin;
using std::string;
using std::vector;


int main(){
    // 初始化网页查询组件，传入网页配置路径
    querypageWeb qpw(PAGEPWD);
    // 启动网页库构建/预处理流程
    qpw.start(); 
    cout << "网页库建立完毕" << endl;
    
    // 无限循环：持续接受用户查询输入
    while(1)
    {
        vector<queryResult> qrs;  // 存储查询结果的动态数组
        string search;                 // 存储用户输入的查询词
        cin >> search;                 // 读取用户输入的查询词

        // 执行查询操作（传入查询词和结果存储容器）
        qpw.query(search,qrs);
        
        // 遍历并打印所有查询结果
        for(auto &elem : qrs)
        {
            cout << "标题：" << elem.title << endl;        // 打印结果标题
            cout << "摘要：" << elem.description << endl;  // 打印结果摘要
            cout << "链接：" << elem.link << endl;         // 打印结果链接
            // cout << "正文：" << elem.content << endl;    // 打印正文
        }
        cout << "==========================继续输入查询词(按ctrl+c退出):==========================" << endl;  
    }
    return 0;
}
