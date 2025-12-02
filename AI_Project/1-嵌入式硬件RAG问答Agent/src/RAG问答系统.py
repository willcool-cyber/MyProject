"""
嵌入式RAG问答助手 - LLM集成模块
功能：结合向量检索和大语言模型实现智能问答
使用DashScope API（通义千问）作为LLM
⭐ 阶段3更新：集成LangChain工具链支持
"""

import os
import sys
from typing import List, Dict, Any, Optional

# 添加项目根目录到Python路径（以便导入tools模块）
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# DashScope LLM
import dashscope
from dashscope import Generation

# 导入向量数据库（会自动设置UTF-8编码）
try:
    from RAG数据库 import EmbeddingVectorDatabase
except ModuleNotFoundError:
    # 如果从项目根目录运行，使用相对导入
    from src.RAG数据库 import EmbeddingVectorDatabase

# LangChain工具链（自动检测，如果可用则启用工具功能）
try:
    # LangChain 1.0+版本使用LangGraph
    from langgraph.prebuilt import create_react_agent
    from langchain_core.prompts import PromptTemplate  
    from langchain_community.llms import Tongyi
    from tools.tool_manager import ToolManager
    LANGCHAIN_AVAILABLE = True
    USING_LANGGRAPH = True
    # print("✅ LangChain工具链加载成功")  # 调试信息（可选启用）
except ImportError as e:
    LANGCHAIN_AVAILABLE = False
    USING_LANGGRAPH = False
    _import_error = str(e)
    # print(f"⚠️  LangChain导入失败: {e}")  # 调试信息（可选启用）

# 缓存支持
try:
    from utils.cache_manager import get_query_cache
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    # print("⚠️  缓存模块未找到，将不使用查询缓存")


class RAGQASystem:
    """
    RAG问答系统：结合向量检索和LLM生成
    """
    
    def __init__(self,
                 vector_db_path: str = "./embedding向量库",
                 llm_model: str = "qwen-turbo",
                 vector_db: Optional[EmbeddingVectorDatabase] = None,
                 enable_tools: bool = True,
                 use_hybrid_search: bool = True):
        """
        初始化RAG问答系统
        
        Args:
            vector_db_path: 向量数据库路径
            llm_model: DashScope LLM模型名称
                       - qwen-turbo: 快速响应
                       - qwen-plus: 高质量回答
                       - qwen-max: 最强性能
            vector_db: 已初始化的向量数据库对象（可选）
            enable_tools: 是否启用工具调用功能（默认True，如果LangChain可用则自动启用）
            use_hybrid_search: 是否使用混合检索（语义+关键词+Rerank，默认True）
        """
        print("🚀 初始化RAG问答系统...")
        
        # 检查API Key
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError("❌ 未找到环境变量 DASHSCOPE_API_KEY，请先设置")
        
        dashscope.api_key = api_key
        self.api_key = api_key
        print("✅ DashScope API Key 已加载")
        
        # 初始化向量数据库
        if vector_db is None:
            print("📂 正在加载向量数据库...")
            self.vector_db = EmbeddingVectorDatabase(
                model_name="text-embedding-v2",
                vector_db_path=vector_db_path
            )
            if not self.vector_db.load_database():
                raise ValueError("❌ 向量数据库加载失败，请先运行 RAG数据库.py 构建数据库")
        else:
            self.vector_db = vector_db
        
        self.llm_model = llm_model
        self.use_hybrid_search = use_hybrid_search
        print(f"📊 使用LLM模型: {llm_model}")
        print(f"📊 向量库包含: {len(self.vector_db.documents)} 个文档块")
        
        # 检查混合检索可用性
        if use_hybrid_search:
            if hasattr(self.vector_db, 'bm25') and self.vector_db.bm25 is not None:
                print(f"🔍 检索模式: 混合检索（语义 + 关键词 + Rerank）")
            else:
                print(f"🔍 检索模式: 语义检索（BM25索引未构建）")
                self.use_hybrid_search = False
        else:
            print(f"🔍 检索模式: 语义检索")
        
        # 初始化工具系统（如果LangChain可用且enable_tools为True，则自动启用）
        self.enable_tools = enable_tools and LANGCHAIN_AVAILABLE
        self.tool_manager = None
        self.agent_executor = None
        
        if enable_tools and LANGCHAIN_AVAILABLE:
            self._init_tools()
        elif enable_tools and not LANGCHAIN_AVAILABLE:
            print("ℹ️  LangChain未安装，工具功能已禁用（使用普通问答模式）")
            self.enable_tools = False
        
        # 初始化查询缓存
        self.query_cache = None
        if CACHE_AVAILABLE:
            try:
                self.query_cache = get_query_cache()
                print("✅ 查询结果缓存已启用")
            except Exception as e:
                print(f"⚠️  查询缓存初始化失败: {e}")
        
        # 初始化对话历史
        self.chat_history = []  # 格式: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        self.max_history_turns = 5  # 最多保留最近的5轮对话（10条消息）
        print("✅ 对话历史功能已启用（最多保留 {} 轮对话）".format(self.max_history_turns))
        
        print("✅ RAG问答系统初始化完成\n")
    
    def _init_tools(self):
        """初始化工具系统（简化版本，不依赖LangGraph Agent）"""
        if not LANGCHAIN_AVAILABLE:
            print("❌ LangChain未安装，无法启用工具功能")
            print("   请运行: pip install langchain langchain-community")
            self.enable_tools = False
            return
        
        try:
            print("🔧 初始化工具系统...")
            
            # 初始化工具管理器
            self.tool_manager = ToolManager(vector_db=self.vector_db)
            tools = self.tool_manager.get_tools()
            print(f"✅ 已加载 {len(tools)} 个工具")
            print("✅ 工具系统初始化完成（简化模式）")
            
            # 不使用复杂的Agent，而是使用自定义的工具调用逻辑
            self.agent_executor = None  # 标记为简化模式
            
        except Exception as e:
            print(f"❌ 工具系统初始化失败: {e}")
            self.enable_tools = False
            self.tool_manager = None
            self.agent_executor = None
    
    def build_prompt(self, query: str, context_docs: List[Dict[str, Any]], has_relevant_context: bool = True, use_history: bool = True) -> str:
        """
        构建RAG Prompt，包含检索到的上下文和对话历史
        
        Args:
            query: 用户问题
            context_docs: 检索到的相关文档片段
            has_relevant_context: 是否有相关上下文
            use_history: 是否使用对话历史
            
        Returns:
            完整的Prompt字符串
        """
        # 构建对话历史部分
        history_text = ""
        if use_history and self.chat_history:
            history_text = "\n【对话历史】\n"
            # 只使用最近的对话历史
            recent_history = self.chat_history[-(self.max_history_turns * 2):]
            for msg in recent_history:
                role = "用户" if msg["role"] == "user" else "助手"
                history_text += f"{role}: {msg['content']}\n"
            history_text += "-" * 50 + "\n"
        
        # 如果没有相关文档，使用通用助手Prompt
        if not has_relevant_context:
            prompt = f"""你是一个专业且友好的嵌入式硬件技术助手。

我的知识库主要包含以下硬件文档：
- ADS6311 SPAD芯片技术文档
- F30激光雷达产品手册
- Hawk dTOF模组规格和Demo资料
- KP_06S SoC技术文档
{history_text}
【当前问题】
{query}

【回答要求】
1. 如果用户问到我的功能，请介绍你能基于上述文档回答的问题类型
2. 如果问题与文档无关但属于技术范畴，可以给出通用性建议
3. 结合对话历史理解用户意图（如有）
4. 保持专业、友好的语气
5. 使用中文回答

请回答："""
            return prompt
        
        # 有相关文档时，构建上下文
        context_text = ""
        for idx, doc in enumerate(context_docs, 1):
            context_text += f"\n【参考资料 {idx}】\n"
            context_text += f"文档来源: {doc['filename']}\n"
            context_text += f"相关内容: {doc['text']}\n"
            context_text += "-" * 50 + "\n"
        
        # 构建Prompt
        prompt = f"""你是一个专业的嵌入式硬件技术专家，正在基于技术文档回答用户的问题。
{history_text}
以下是从技术文档库中检索到的相关内容：
{context_text}

【当前问题】
{query}

【回答指导】
1. 结合对话历史理解用户的真实意图和上下文关系
2. 仔细阅读上述参考资料，提取与问题相关的关键信息
3. 用清晰、专业但易懂的语言组织答案
4. 如果资料中有具体的技术参数、数值、规格，务必准确引用
5. 可以适当补充技术背景知识，但要明确标注哪些是文档内容，哪些是通用知识
6. 如果参考资料不足以完整回答问题，诚实说明并提供已有的部分信息
7. 答案要结构清晰，可以使用分点、标题等方式组织
8. 使用中文回答

请开始回答："""
        
        return prompt
    
    def ask(self, 
            query: str, 
            top_k: int = 5,
            temperature: float = 0.8,
            max_tokens: int = 2000,
            similarity_threshold: float = 0.4,
            stream: bool = False,
            use_cache: bool = True,
            use_history: bool = True,
            save_history: bool = True) -> Dict[str, Any]:
        """
        执行RAG问答（支持流式输出、缓存和对话历史）
        
        Args:
            query: 用户问题
            top_k: 检索的文档片段数量
            temperature: LLM温度参数（0-1，越高越随机，推荐0.7-0.9）
            max_tokens: 最大生成token数
            similarity_threshold: 相似度阈值，低于此值的文档会被过滤
            stream: 是否使用流式输出（流式输出不使用缓存）
            use_cache: 是否使用缓存（默认True）
            use_history: 是否在Prompt中使用对话历史（默认True）
            save_history: 是否保存本次对话到历史（默认True）
            
        Returns:
            包含答案和相关信息的字典
        """
        print(f"🔍 问题: {query}")
        
        # 检查缓存（仅在非流式模式下使用）
        if not stream and use_cache and self.query_cache:
            cached_result = self.query_cache.get(query, top_k, temperature, similarity_threshold)
            if cached_result is not None:
                print("✅ 命中缓存，直接返回结果\n")
                return cached_result
        
        # 1. 选择检索策略
        if self.use_hybrid_search and hasattr(self.vector_db, 'hybrid_search'):
            print(f"📚 使用混合检索（语义+关键词+Rerank，Top {top_k}）...")
            search_results = self.vector_db.hybrid_search(
                query, 
                top_k=top_k,
                semantic_weight=0.7,
                keyword_weight=0.3,
                rerank=True
            )
        else:
            print(f"📚 使用语义检索（Top {top_k}）...")
            search_results = self.vector_db.search(query, top_k=top_k)
        
        # 2. 过滤低相似度文档
        filtered_results = [
            doc for doc in search_results 
            if doc['similarity_score'] >= similarity_threshold
        ]
        
        # 判断是否有相关文档
        has_relevant_context = len(filtered_results) > 0
        
        if filtered_results:
            print(f"✅ 检索到 {len(filtered_results)} 个相关文档片段（相似度 >= {similarity_threshold}）")
            for idx, result in enumerate(filtered_results[:3], 1):
                score_info = f"相似度: {result['similarity_score']:.3f}"
                # 显示混合检索的详细分数
                if 'semantic_score' in result and 'bm25_score' in result:
                    score_info += f" (语义:{result['semantic_score']:.3f}, 关键词:{result['bm25_score']:.3f})"
                if 'llm_rerank_score' in result:
                    score_info += f" [Rerank:{result['llm_rerank_score']:.1f}/10]"
                print(f"  [{idx}] {result['filename']} ({score_info})")
        else:
            print(f"⚠️  未找到高相关度文档（阈值: {similarity_threshold}），使用通用模式回答")
        
        # 3. 构建Prompt
        print("\n🤖 正在生成回答...")
        if stream:
            print("💬 ", end='', flush=True)
        
        prompt = self.build_prompt(
            query, 
            filtered_results if has_relevant_context else [], 
            has_relevant_context,
            use_history=use_history
        )
        
        # 4. 调用LLM
        try:
            if stream:
                # 流式输出
                answer_chunks = []
                responses = Generation.call(
                    model=self.llm_model,
                    prompt=prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                    incremental_output=True
                )
                
                for response in responses:
                    if response.status_code == 200:
                        chunk = response.output['text']
                        answer_chunks.append(chunk)
                        print(chunk, end='', flush=True)
                    else:
                        print(f"\n❌ 流式输出错误: {response.message}")
                        break
                
                print("\n")  # 换行
                answer = ''.join(answer_chunks)
            else:
                # 普通输出
                response = Generation.call(
                    model=self.llm_model,
                    prompt=prompt,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                if response.status_code == 200:
                    answer = response.output['text'].strip()
                else:
                    error_msg = f"LLM调用失败: {response.message}"
                    print(f"❌ {error_msg}\n")
                    return {
                        'query': query,
                        'answer': '抱歉，生成回答时出现错误。',
                        'sources': filtered_results,
                        'error': error_msg,
                        'has_relevant_context': has_relevant_context
                    }
            
            # 构建返回结果
            result = {
                'query': query,
                'answer': answer,
                'sources': [
                    {
                        'filename': doc['filename'],
                        'chunk_id': doc['chunk_id'],
                        'similarity_score': doc['similarity_score'],
                        'text_preview': doc['text'][:150] + '...'
                    }
                    for doc in filtered_results
                ] if filtered_results else [],
                'model': self.llm_model,
                'has_relevant_context': has_relevant_context,
                'filtered_count': len(filtered_results),
                'total_retrieved': len(search_results)
            }
            
            # 保存到缓存（仅在非流式模式下）
            if not stream and use_cache and self.query_cache:
                try:
                    self.query_cache.put(query, top_k, temperature, similarity_threshold, result)
                except Exception as e:
                    print(f"⚠️  保存缓存失败: {e}")
            
            # 保存到对话历史
            if save_history:
                self.add_to_history(query, answer)
            
            if not stream:
                print("✅ 回答生成完成\n")
            return result
                
        except Exception as e:
            error_msg = f"LLM调用异常: {str(e)}"
            print(f"\n❌ {error_msg}\n")
            import traceback
            traceback.print_exc()
            return {
                'query': query,
                'answer': '抱歉，生成回答时出现异常。',
                'sources': filtered_results,
                'error': error_msg,
                'has_relevant_context': has_relevant_context
            }
    
    def chat(self, 
             query: str,
             top_k: int = 5,
             temperature: float = 0.7,
             show_sources: bool = True) -> str:
        """
        简化的聊天接口，直接返回答案字符串
        
        Args:
            query: 用户问题
            top_k: 检索的文档片段数量
            temperature: LLM温度参数
            show_sources: 是否在答案后显示来源
            
        Returns:
            答案字符串
        """
        result = self.ask(query, top_k=top_k, temperature=temperature)
        
        answer = result['answer']
        
        if show_sources and result.get('sources'):
            answer += "\n\n【参考来源】\n"
            for idx, source in enumerate(result['sources'][:3], 1):
                answer += f"{idx}. {source['filename']} (相似度: {source['similarity_score']:.3f})\n"
        
        return answer
    
    def _should_use_tools(self, query: str) -> bool:
        """
        判断问题是否需要使用工具
        
        Args:
            query: 用户问题
            
        Returns:
            是否需要使用工具
        """
        # 工具相关关键词
        tool_keywords = {
            '计算': ['计算', '算', '加', '减', '乘', '除', '求和', '总共', '多少'],
            '转换': ['转换', '换算', '改为', '变成', '单位'],
            '对比': ['对比', '比较', '区别', '不同', '差异', '哪个更好'],
            '表格': ['表格', '列表', '整理', '汇总'],
            '搜索': ['搜索', '查找', '找一下'],
        }
        
        query_lower = query.lower()
        for category, keywords in tool_keywords.items():
            if any(kw in query_lower for kw in keywords):
                return True
        
        return False
    
    def _select_tool(self, query: str) -> Optional[str]:
        """
        根据问题选择合适的工具
        
        Args:
            query: 用户问题
            
        Returns:
            工具名称或 None
        """
        if not self.enable_tools or not self.tool_manager:
            return None
        
        query_lower = query.lower()
        
        # 计算器
        if any(kw in query_lower for kw in ['计算', '算', '加', '减', '乘', '除', '多少']):
            return 'calculator'
        
        # 单位转换
        if any(kw in query_lower for kw in ['转换', '换算', '改为', '变成']):
            return 'unit_converter'
        
        # 参数提取
        if any(kw in query_lower for kw in ['提取', '找出', '参数是']):
            return 'parameter_extractor'
        
        # 表格生成
        if any(kw in query_lower for kw in ['表格', '对比', '比较']):
            return 'table_generator'
        
        # 文档搜索
        if any(kw in query_lower for kw in ['搜索', '查找', '找一下']):
            return 'document_search'
        
        return None
    
    def _extract_tool_params(self, query: str, tool_name: str) -> Dict[str, Any]:
        """
        从问题中提取工具参数
        
        Args:
            query: 用户问题
            tool_name: 工具名称
            
        Returns:
            工具参数字典
        """
        import re
        params = {}
        
        if tool_name == 'calculator':
            # 提取数学表达式
            # 支持多种模式：
            # 1. "计算 10 + 5 * 2"
            # 2. "30米和0.1米的比值" -> "30 / 0.1"
            # 3. "10加5" -> "10 + 5"
            
            # 首先尝试提取现成的数学表达式
            expr_match = re.search(r'([\d.]+\s*[+\-*/]\s*[\d.]+(?:\s*[+\-*/]\s*[\d.]+)*)', query)
            if expr_match:
                params['expression'] = expr_match.group(1).strip()
            else:
                # 提取所有数字
                numbers = re.findall(r'\d+\.?\d*', query)
                if len(numbers) >= 2:
                    # 根据关键词判断运算符
                    if any(kw in query for kw in ['比值', '除以', '除', '商']):
                        params['expression'] = f"{numbers[0]} / {numbers[1]}"
                    elif any(kw in query for kw in ['和', '加', '总和', '求和', '相加']):
                        params['expression'] = f"{numbers[0]} + {numbers[1]}"
                    elif any(kw in query for kw in ['差', '减', '相减']):
                        params['expression'] = f"{numbers[0]} - {numbers[1]}"
                    elif any(kw in query for kw in ['积', '乘', '相乘', '倍']):
                        params['expression'] = f"{numbers[0]} * {numbers[1]}"
                    else:
                        # 默认加法
                        params['expression'] = f"{numbers[0]} + {numbers[1]}"
                elif len(numbers) == 1:
                    params['expression'] = numbers[0]
        
        elif tool_name == 'unit_converter':
            # 提取数值和单位
            # 支持多种模式：
            # 1. "将 100 米转换为厘米"
            # 2. "30米转成cm"
            # 3. "100m换算成厘米"
            
            # 单位映射表
            unit_map = {
                '米': 'm', 'm': 'm', '公尺': 'm',
                '厘米': 'cm', 'cm': 'cm', '公分': 'cm',
                '毫米': 'mm', 'mm': 'mm',
                '千米': 'km', 'km': 'km', '公里': 'km',
                '微米': 'um', 'um': 'um',
                '纳米': 'nm', 'nm': 'nm',
                'GHz': 'GHz', 'MHz': 'MHz', 'kHz': 'kHz', 'Hz': 'Hz',
                's': 's', 'ms': 'ms', 'us': 'us', 'ns': 'ns',
                '秒': 's', '毫秒': 'ms', '微秒': 'us', '纳秒': 'ns',
            }
            
            # 提取数值
            value_match = re.search(r'(\d+\.?\d*)', query)
            if value_match:
                params['value'] = float(value_match.group(1))
            
            # 提取源单位和目标单位
            # 模式1: "100 米 转换为 厘米"
            pattern1 = r'(\d+\.?\d*)\s*(米|厘米|毫米|千米|公里|m|cm|mm|km|um|nm|GHz|MHz|kHz|Hz).*?(?:转换为|转成|换算成|改为|变成|转为|到)\s*(米|厘米|毫米|千米|公里|m|cm|mm|km|um|nm|GHz|MHz|kHz|Hz)'
            match1 = re.search(pattern1, query)
            
            if match1:
                from_unit_raw = match1.group(2)
                to_unit_raw = match1.group(3)
                params['from_unit'] = unit_map.get(from_unit_raw, from_unit_raw)
                params['to_unit'] = unit_map.get(to_unit_raw, to_unit_raw)
            else:
                # 模式2: 尝试找到两个单位
                units_found = re.findall(r'(米|厘米|毫米|千米|公里|m|cm|mm|km|um|nm|GHz|MHz|kHz|Hz)', query)
                if len(units_found) >= 2:
                    params['from_unit'] = unit_map.get(units_found[0], units_found[0])
                    params['to_unit'] = unit_map.get(units_found[1], units_found[1])
                elif len(units_found) == 1:
                    # 只有一个单位，尝试推断另一个
                    unit = unit_map.get(units_found[0], units_found[0])
                    params['from_unit'] = unit
                    # 默认转换表
                    if unit == 'm':
                        params['to_unit'] = 'cm'
                    elif unit == 'cm':
                        params['to_unit'] = 'm'
                    else:
                        params['to_unit'] = unit
        
        elif tool_name == 'document_search':
            # 提取搜索关键词
            for prefix in ['搜索', '查找', '找一下']:
                if prefix in query:
                    params['query'] = query.replace(prefix, '').strip()
                    params['top_k'] = 3
                    break
            if 'query' not in params:
                params['query'] = query
                params['top_k'] = 3
        
        return params
    
    # Agent模式
    def ask_with_tools(self, 
                       query: str,
                       max_iterations: int = 3,
                       use_history: bool = True) -> Dict[str, Any]:
        """
        使用工具增强的问答（Agent 模式）
        
        实现简化版 ReAct 推理循环：
        1. 思考：判断是否需要工具
        2. 行动：调用相应工具
        3. 观察：分析工具结果
        4. 回答：基于工具结果和文档生成答案
        
        Args:
            query: 用户问题
            max_iterations: 最大迭代次数
            use_history: 是否使用对话历史
            
        Returns:
            包含答案、工具调用信息的字典
        """
        if not self.enable_tools or not self.tool_manager:
            # 工具未启用，使用普通RAG模式
            return self.ask(query, use_history=use_history)
        
        print(f"🤖 Agent模式: 分析问题...")
        
        # 1. 思考：是否需要使用工具
        should_use_tools = self._should_use_tools(query)
        
        if not should_use_tools:
            print("💭 判断：问题可以直接通过RAG回答，不需要工具")
            return self.ask(query, use_history=use_history)
        
        print("💭 判断：问题需要使用工具辅助")
        
        # 2. 选择工具
        tool_name = self._select_tool(query)
        if not tool_name:
            print("⚠️  未找到合适的工具，回退到RAG模式")
            return self.ask(query, use_history=use_history)
        
        print(f"🔧 选择工具: {tool_name}")
        
        # 3. 获取工具
        tool = self.tool_manager.get_tool_by_name(tool_name)
        if not tool:
            print(f"❌ 工具 {tool_name} 不存在")
            return self.ask(query, use_history=use_history)
        
        # 4. 提取参数并调用工具
        tool_params = self._extract_tool_params(query, tool_name)
        print(f"📋 工具参数: {tool_params}")
        
        try:
            print(f"⚙️  执行工具...")
            tool_result = tool._run(**tool_params)
            print(f"✅ 工具执行完成")
            print(f"📊 工具结果: {tool_result[:200]}...")
        except Exception as e:
            print(f"❌ 工具执行失败: {e}")
            tool_result = f"工具执行失败: {str(e)}"
        
        # 5. 结合工具结果和文档检索生成最终答案
        print(f"\n🤖 基于工具结果生成回答...")
        
        # 构建增强的查询
        enhanced_query = f"{query}\n\n工具执行结果：\n{tool_result}"
        
        # 调用RAG获取文档上下文
        result = self.ask(
            enhanced_query,
            use_history=use_history,
            save_history=False  # 暂不保存，后面统一保存
        )
        
        # 添加工具调用信息
        result['tool_used'] = tool_name
        result['tool_result'] = tool_result
        result['agent_mode'] = True
        
        # 保存到历史
        if use_history:
            self.add_to_history(query, result['answer'])
        
        return result
    
    def get_available_tools(self) -> List[str]:
        """获取可用工具列表（阶段3新增）"""
        if not self.enable_tools or self.tool_manager is None:
            return []
        return self.tool_manager.get_tool_names()
    
    def print_tool_info(self):
        """打印工具信息（阶段3新增）"""
        if not self.enable_tools or self.tool_manager is None:
            print("⚠️  工具功能未启用")
            return
        self.tool_manager.print_tool_info()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        stats = {}
        
        # 查询缓存统计
        if self.query_cache:
            stats['query_cache'] = self.query_cache.get_stats()
        else:
            stats['query_cache'] = {'status': '未启用'}
        
        # Embedding 缓存统计
        if hasattr(self.vector_db, 'embedding_cache') and self.vector_db.embedding_cache:
            stats['embedding_cache'] = self.vector_db.embedding_cache.get_stats()
        else:
            stats['embedding_cache'] = {'status': '未启用'}
        
        return stats
    
    def print_cache_stats(self):
        """打印缓存统计信息"""
        stats = self.get_cache_stats()
        
        print("\n" + "="*60)
        print("📊 缓存统计信息")
        print("="*60)
        
        # 查询缓存
        print("\n【查询结果缓存】")
        query_cache = stats.get('query_cache', {})
        if query_cache.get('status') == '未启用':
            print("  状态: 未启用")
        else:
            print(f"  当前大小: {query_cache.get('size', 0)} / {query_cache.get('max_size', 0)}")
            print(f"  缓存命中: {query_cache.get('hits', 0)} 次")
            print(f"  缓存未命中: {query_cache.get('misses', 0)} 次")
            print(f"  命中率: {query_cache.get('hit_rate', '0%')}")
            print(f"  过期时间: {query_cache.get('ttl_seconds', 0)} 秒")
        
        # Embedding 缓存
        print("\n【Embedding 缓存】")
        emb_cache = stats.get('embedding_cache', {})
        if emb_cache.get('status') == '未启用':
            print("  状态: 未启用")
        else:
            memory_cache = emb_cache.get('memory_cache', {})
            print(f"  内存缓存: {memory_cache.get('size', 0)} / {memory_cache.get('max_size', 0)}")
            print(f"  内存命中: {memory_cache.get('hits', 0)} 次")
            print(f"  内存未命中: {memory_cache.get('misses', 0)} 次")
            print(f"  内存命中率: {memory_cache.get('hit_rate', '0%')}")
            print(f"  磁盘缓存: {emb_cache.get('disk_cache_size', 0)} 个向量")
            print(f"  缓存目录: {emb_cache.get('cache_dir', 'N/A')}")
        
        print("\n" + "="*60)
    
    def clear_cache(self):
        """清空所有缓存"""
        if self.query_cache:
            self.query_cache.clear()
            print("✅ 查询缓存已清空")
        
        if hasattr(self.vector_db, 'embedding_cache') and self.vector_db.embedding_cache:
            self.vector_db.embedding_cache.clear()
            print("✅ Embedding 缓存已清空")
    
    def add_to_history(self, user_query: str, assistant_answer: str):
        """
        添加对话到历史记录
        
        Args:
            user_query: 用户问题
            assistant_answer: 助手回答
        """
        self.chat_history.append({
            "role": "user",
            "content": user_query
        })
        self.chat_history.append({
            "role": "assistant",
            "content": assistant_answer
        })
        
        # 限制历史长度（保留最近的 N 轮对话）
        max_messages = self.max_history_turns * 2  # 一轮对话包含用户和助手两条消息
        if len(self.chat_history) > max_messages:
            self.chat_history = self.chat_history[-max_messages:]
    
    def get_history(self) -> List[Dict[str, str]]:
        """获取对话历史"""
        return self.chat_history.copy()
    
    def clear_history(self):
        """清空对话历史"""
        self.chat_history = []
        print("✅ 对话历史已清空")
    
    def set_max_history_turns(self, turns: int):
        """
        设置最大保留对话轮数
        
        Args:
            turns: 对话轮数（每轮包含一个用户问题和一个助手回答）
        """
        self.max_history_turns = max(1, turns)
        print(f"✅ 已设置最大历史轮数: {self.max_history_turns}")
        
        # 裁剪当前历史
        max_messages = self.max_history_turns * 2
        if len(self.chat_history) > max_messages:
            self.chat_history = self.chat_history[-max_messages:]
    
    def print_history(self):
        """打印对话历史"""
        if not self.chat_history:
            print("📝 对话历史为空")
            return
        
        print("\n" + "="*60)
        print("📝 对话历史")
        print("="*60)
        
        for i, msg in enumerate(self.chat_history, 1):
            role = "👤 用户" if msg["role"] == "user" else "🤖 助手"
            content = msg["content"]
            
            # 限制显示长度
            if len(content) > 100:
                content = content[:100] + "..."
            
            print(f"\n[{i}] {role}:")
            print(f"    {content}")
        
        print("\n" + "="*60)
        print(f"共 {len(self.chat_history)} 条消息（{len(self.chat_history)//2} 轮对话）")
        print("="*60)


def main():
    """主函数：交互式RAG问答"""
    
    print("="*70)
    print("🤖 嵌入式RAG智能问答助手")
    print("="*70)
    print("📌 使用DashScope API（通义千问）")
    print("📌 基于向量检索的增强生成")
    if LANGCHAIN_AVAILABLE:
        print("📌 工具链已加载（计算、转换、参数提取等）")
    print("="*70 + "\n")
    
    # 初始化RAG系统
    try:
        # 使用脚本所在目录的绝对路径
        script_dir = os.path.dirname(os.path.abspath(__file__))
        vector_db_path = os.path.join(script_dir, "embedding向量库")
        
        rag = RAGQASystem(
            vector_db_path=vector_db_path,
            llm_model="qwen-turbo"  # 可改为 qwen-plus 或 qwen-max
        )
        
        # 显示可用工具（如果启用）
        if rag.enable_tools:
            tools = rag.get_available_tools()
            if tools:
                print(f"\n✅ 已加载 {len(tools)} 个工具: {', '.join(tools)}\n")
        
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return
    
    print("="*70)
    print("💬 开始交互式问答")
    print("="*70)
    print("💡 提示：")
    print("  - 输入问题后按回车")
    print("  - 输入 'quit' 或 'exit' 退出")
    print("  - 输入 'help' 查看帮助")
    if rag.enable_tools:
        print("  - 输入 'tools' 查看可用工具")
        print("  - 输入 '@tool <问题>' 使用 Agent 模式（自动调用工具）")
    if CACHE_AVAILABLE:
        print("  - 输入 'cache' 查看缓存统计")
        print("  - 输入 'clear' 清空缓存")
    print("  - 输入 'history' 查看对话历史")
    print("  - 输入 'reset' 清空对话历史")
    print("="*70 + "\n")
    
    # 交互循环
    while True:
        try:
            # 获取用户输入
            query = input("❓ 请输入问题: ").strip()
            
            if not query:
                print("⚠️  问题不能为空\n")
                continue
            
            if query.lower() in ['quit', 'exit', '退出']:
                print("\n👋 再见！")
                break
            
            if query.lower() == 'help':
                print("\n📖 帮助信息：")
                print("  - 可以询问硬件文档中的任何技术问题")
                print("  - 例如：'激光雷达的测距范围是多少？'")
                print("  - 例如：'ADS6311的主要特性是什么？'")
                print("  - 例如：'Hawk模组的规格参数有哪些？'")
                if rag.enable_tools:
                    print("\n  工具功能（可选）：")
                    print("  - 数学计算、单位转换、参数提取等")
                    print("  - 输入 'tools' 查看详细列表")
                if CACHE_AVAILABLE:
                    print("\n  缓存功能：")
                    print("  - 输入 'cache' 查看缓存命中率和使用情况")
                    print("  - 输入 'clear' 清空所有缓存")
                    print("  - 缓存可以加速相同问题的响应时间")
                print("\n  对话历史功能：")
                print("  - 输入 'history' 查看对话历史")
                print("  - 输入 'reset' 清空对话历史")
                print("  - 系统会自动记住最近的对话，理解上下文")
                print()
                continue
            
            if query.lower() == 'tools' and rag.enable_tools:
                print()
                rag.print_tool_info()
                continue
            
            if query.lower() == 'cache' and CACHE_AVAILABLE:
                rag.print_cache_stats()
                print()
                continue
            
            if query.lower() == 'clear' and CACHE_AVAILABLE:
                print()
                rag.clear_cache()
                print()
                continue
            
            if query.lower() == 'history':
                rag.print_history()
                print()
                continue
            
            if query.lower() == 'reset':
                print()
                rag.clear_history()
                print()
                continue
            
            # 检查是否使用 Agent 模式
            use_agent = False
            if query.startswith('@tool '):
                use_agent = True
                query = query[6:].strip()  # 移除 @tool 前缀
                print(f"🤖 切换到 Agent 模式")
            
            # 执行问答
            print()
            if use_agent and rag.enable_tools:
                # Agent 模式
                result = rag.ask_with_tools(
                    query,
                    use_history=True
                )
            else:
                # 普通 RAG 模式（启用流式输出）
                result = rag.ask(
                    query, 
                    top_k=5, 
                    temperature=0.8,  # 提高温度使回答更自然
                    similarity_threshold=0.4,  # 相似度阈值
                    stream=True  # 启用流式输出
                )
            
            # 显示来源和统计
            print("\n" + "="*70)
            
            # 显示 Agent 工具调用信息
            if result.get('agent_mode'):
                print("🤖 Agent 模式信息：")
                print(f"  使用工具: {result.get('tool_used', 'N/A')}")
                print(f"  工具结果: {result.get('tool_result', 'N/A')[:150]}...")
                print()
            
            if result.get('sources'):
                print("📚 参考文档：")
                for idx, source in enumerate(result['sources'][:3], 1):
                    print(f"  {idx}. {source['filename']}")
                    print(f"     相似度: {source['similarity_score']:.3f}")
                    print(f"     内容: {source['text_preview']}")
            else:
                print("💡 本次回答基于通用知识，未使用特定文档")
            
            # 显示统计信息
            if result.get('has_relevant_context') is not None:
                print(f"\n📊 检索统计: 找到{result.get('total_retrieved', 0)}个文档，"
                      f"过滤后{result.get('filtered_count', 0)}个相关")
            
            print("="*70 + "\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {e}\n")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()

