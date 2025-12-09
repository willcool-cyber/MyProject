"""
Prompt模板管理
集中管理所有的Prompt模板
"""


# ==================== 问答Prompt ====================

QA_SYSTEM_PROMPT = """你是一个专业的嵌入式硬件技术专家助手，擅长解答关于硬件规格、技术参数、使用方法等问题。

你的职责：
1. 基于提供的文档内容准确回答用户问题
2. 如果文档中没有相关信息，明确告知用户
3. 回答要专业、准确、条理清晰
4. 必要时可以引用文档来源

回答要求：
- 使用专业术语，但要易于理解
- 结构化呈现信息（使用列表、表格等）
- 如有多个答案，按重要性排序
- 提供具体的数值、参数、型号等信息
- 如果用户提问的问题和文档无关，请回答：“我不知道”
"""

QA_USER_PROMPT_TEMPLATE = """请根据以下参考文档回答问题：

参考文档：
{context}

用户问题：{question}

请提供详细、准确的回答："""


# ==================== 搜索Prompt ====================

SEARCH_QUERY_REWRITE_PROMPT = """你是一个查询优化助手，负责改写用户的搜索查询以提高检索效果。

任务：将用户的口语化问题改写为更适合语义检索的查询语句。

要求：
1. 提取关键技术术语
2. 去除口语化表达
3. 补充相关的技术概念
4. 保持查询简洁明确

用户问题：{question}

改写后的查询（只输出改写结果，不要解释）："""


# ==================== 分析Prompt ====================

SUMMARY_PROMPT_TEMPLATE = """请根据以下文档内容生成简洁的摘要：

文档内容：
{content}

摘要要求：
- 控制在200字以内
- 突出核心信息和关键参数
- 使用专业术语
- 结构清晰

摘要："""


COMPARISON_PROMPT_TEMPLATE = """请比较以下两个产品/技术的异同：

产品/技术A：
{content_a}

产品/技术B：
{content_b}

请从以下维度进行比较：
1. 主要功能和特性
2. 技术参数差异
3. 适用场景
4. 优缺点分析

比较结果："""


# ==================== 信息提取Prompt ====================

PARAMETER_EXTRACTION_PROMPT = """从以下文档中提取技术参数信息：

文档内容：
{content}

请提取以下类型的参数（如有）：
- 尺寸规格
- 电气参数
- 性能指标
- 工作条件
- 接口定义

以JSON格式输出："""


# ==================== 对话Prompt ====================

CHAT_SYSTEM_PROMPT = """你是一个友好、专业的嵌入式硬件技术助手。

对话风格：
- 专业但不失亲和力
- 耐心解答用户疑问
- 主动提供相关建议
- 鼓励用户深入探讨

当前对话历史：
{chat_history}

参考文档：
{context}

请继续对话："""


# ==================== 澄清Prompt ====================

CLARIFICATION_PROMPT = """用户的问题不够明确，需要进一步澄清。

用户问题：{question}

可能的歧义点：
{ambiguity}

请生成1-3个澄清性问题，帮助理解用户的真实需求："""


# ==================== 评估Prompt ====================

ANSWER_QUALITY_CHECK_PROMPT = """评估以下回答的质量：

问题：{question}
回答：{answer}
参考文档：{context}

评估维度：
1. 准确性（是否基于文档）
2. 完整性（是否充分回答）
3. 清晰性（表达是否清楚）
4. 相关性（是否切题）

评分（1-5分）和改进建议："""


# ==================== 工具函数 ====================

def format_context(contexts: list[dict]) -> str:
    """格式化检索到的上下文"""
    formatted = []
    for i, ctx in enumerate(contexts, 1):
        source = ctx.get('filename', '未知文档')
        content = ctx.get('text', '')
        formatted.append(f"【文档{i}】来源：{source}\n内容：{content}")
    return "\n\n".join(formatted)


def format_chat_history(messages: list[dict]) -> str:
    """格式化对话历史"""
    formatted = []
    for msg in messages:
        role = msg.get('role', 'user')
        content = msg.get('content', '')
        prefix = "用户：" if role == "user" else "助手："
        formatted.append(f"{prefix}{content}")
    return "\n".join(formatted)


def build_qa_prompt(question: str, contexts: list[dict]) -> dict:
    """构建问答Prompt"""
    context_str = format_context(contexts)
    
    return {
        "system": QA_SYSTEM_PROMPT,
        "user": QA_USER_PROMPT_TEMPLATE.format(
            context=context_str,
            question=question
        )
    }


def build_chat_prompt(question: str, contexts: list[dict], chat_history: list[dict]) -> str:
    """构建对话Prompt"""
    context_str = format_context(contexts)
    history_str = format_chat_history(chat_history)
    
    return CHAT_SYSTEM_PROMPT.format(
        chat_history=history_str,
        context=context_str
    ) + f"\n\n用户：{question}\n助手："


# ==================== Prompt模板字典 ====================

PROMPT_TEMPLATES = {
    "qa_system": QA_SYSTEM_PROMPT,
    "qa_user": QA_USER_PROMPT_TEMPLATE,
    "search_rewrite": SEARCH_QUERY_REWRITE_PROMPT,
    "summary": SUMMARY_PROMPT_TEMPLATE,
    "comparison": COMPARISON_PROMPT_TEMPLATE,
    "parameter_extraction": PARAMETER_EXTRACTION_PROMPT,
    "chat_system": CHAT_SYSTEM_PROMPT,
    "clarification": CLARIFICATION_PROMPT,
    "quality_check": ANSWER_QUALITY_CHECK_PROMPT,
}


def get_prompt(prompt_name: str, **kwargs) -> str:
    """获取并格式化Prompt模板"""
    template = PROMPT_TEMPLATES.get(prompt_name)
    if not template:
        raise ValueError(f"未找到Prompt模板: {prompt_name}")
    
    try:
        return template.format(**kwargs)
    except KeyError as e:
        raise ValueError(f"Prompt模板缺少参数: {e}")


if __name__ == "__main__":
    # 测试Prompt构建
    print("=" * 60)
    print("测试Prompt模板")
    print("=" * 60)
    
    # 测试问答Prompt
    test_contexts = [
        {"filename": "test.pdf", "text": "这是测试内容1"},
        {"filename": "demo.pdf", "text": "这是测试内容2"}
    ]
    
    qa_prompt = build_qa_prompt("测试问题", test_contexts)
    print("\n问答Prompt:")
    print("-" * 60)
    print(qa_prompt["user"])
    
    # 测试对话Prompt
    test_history = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好，有什么可以帮你的？"}
    ]
    
    chat_prompt = build_chat_prompt("继续问题", test_contexts, test_history)
    print("\n\n对话Prompt:")
    print("-" * 60)
    print(chat_prompt[:300] + "...")

