#include <iostream>
#include <cppjieba/Jieba.hpp>
#include<vector>
#include<fstream>
using std::cout;
using std::endl;
using std::string;
using std::vector;

const char* const JIEBA_DICT_PATH = "./dict/jieba.dict.utf8";
const char* const HMM_MODLE_PATH  = "./dict/hmm_model.utf8";
const char* const USER_DICT_PATH  = "./dict/user.dict.utf8";
const char* const IDF_PATH = "./dict/idf.utf8";
const char* const STOP_WORDS_PATH = "./dict/stop_words.utf8";

void print_words(const string &title,const vector<string> &words){
    cout<<"["<<title<<"]";
    for(auto &w : words){
        cout<<w<<"/ ";
    }
    cout<<endl;
}

int main(int argc,char **argv)
{
    cppjieba::Jieba tokenizer{
        JIEBA_DICT_PATH,
        HMM_MODLE_PATH,
        USER_DICT_PATH,
        IDF_PATH,
        STOP_WORDS_PATH
    };

    string s = "你可以将'流'想象成一条自动运行的流水线，或者一条小溪，在流中数据是自动流动的，作为程序员既不需要考虑数据的来源，也不需要考虑数据的最终目的地，更不需要考虑数据如何'流动'。只需要使用一些简单固定的API即可实现此过程的数据处理。";

    /* std::ifstream filename{"./yuliao/english.txt"}; */
    /* std::ifstream filename{"./yuliao/stop_words_eng.txt"}; */
    /* std::ifstream filename{"./yuliao/stop_words_zh.txt"}; */
    /* std::ifstream filename{"./yuliao/The_Holy_Bible.txt"}; */
    std::ifstream filename{"./yuliao/C3-Art0019.txt"};
    if(!filename.is_open())
    {
        std::cerr<<"Error: Failed to open file!"<<endl;
        return 1;
    }
    vector<string> token;
    token.reserve(100);
    string line;
    while(getline(filename,line)){
        token.clear();
        tokenizer.Cut(line,token);
        print_words("MIX",token);
    }

 


    vector<string> words;
    tokenizer.Cut(s,words);
    print_words("MIX",words);


    tokenizer.Cut(s,words,false);
    print_words("MP",words);

    tokenizer.CutHMM(s,words);
    print_words("HHM",words);


    return 0;
}


