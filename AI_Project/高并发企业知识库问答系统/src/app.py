"""
嵌入式RAG问答助手 - Streamlit Web UI
现代化的问答界面，基于Streamlit框架
"""

import os
import sys
import streamlit as st
from datetime import datetime
import time

# 页面配置（必须是第一个Streamlit命令）
st.set_page_config(
    page_title="嵌入式RAG问答助手",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "嵌入式硬件RAG智能问答助手 v3.0"
    }
)

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 导入RAG系统（添加错误处理）
try:
    from src.RAG问答系统 import RAGQASystem
    RAG_AVAILABLE = True
    import_error = None
except Exception as e:
    RAG_AVAILABLE = False
    import_error = str(e)

# 自定义CSS样式
st.markdown("""
<style>
    /* 主题色 */
    :root {
        --primary-color: #1f77b4;
        --background-color: #f0f2f6;
        --secondary-background: #ffffff;
    }
    
    /* 标题样式 */
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
        margin-bottom: 2rem;
    }
    
    /* 卡片样式 */
    .info-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    
    /* 消息气泡 */
    .user-message {
        background: #e3f2fd;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #1f77b4;
    }
    
    .assistant-message {
        background: #f5f5f5;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #4caf50;
    }
    
    /* 来源文档样式 */
    .source-doc {
        background: #fff3e0;
        padding: 0.8rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        font-size: 0.9rem;
        border-left: 3px solid #ff9800;
    }
    
    /* 统计卡片 */
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin: 0.5rem 0;
    }
    
    .stat-value {
        font-size: 2rem;
        font-weight: bold;
    }
    
    .stat-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    
    /* 按钮样式 */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3rem;
        font-weight: 600;
    }
    
    /* 隐藏Streamlit默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 侧边栏样式 */
    .css-1d391kg {
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)


# 初始化session state
if 'rag_system' not in st.session_state:
    st.session_state.rag_system = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'query_count' not in st.session_state:
    st.session_state.query_count = 0
if 'total_time' not in st.session_state:
    st.session_state.total_time = 0


def initialize_system():
    """初始化RAG系统"""
    if st.session_state.rag_system is not None:
        return True, "系统已初始化"
    
    try:
        with st.spinner("🚀 正在初始化RAG系统..."):
            # 检查BM25
            try:
                import rank_bm25
                import jieba
                use_hybrid = True
            except ImportError:
                use_hybrid = False
            
            st.session_state.rag_system = RAGQASystem(
                vector_db_path="./src/embedding向量库",
                llm_model="qwen-turbo",
                enable_tools=True,
                use_hybrid_search=use_hybrid
            )
            
            return True, "✅ 系统初始化成功！"
    except Exception as e:
        return False, f"❌ 初始化失败: {str(e)}"


def process_query(query: str, top_k: int, temperature: float, threshold: float):
    """处理用户查询"""
    if st.session_state.rag_system is None:
        return None, "请先初始化系统"
    
    try:
        start_time = time.time()
        
        # 调用RAG系统
        result = st.session_state.rag_system.ask(
            query=query,
            top_k=top_k,
            temperature=temperature,
            similarity_threshold=threshold,
            stream=True
        )
        
        elapsed_time = time.time() - start_time
        
        # 更新统计
        st.session_state.query_count += 1
        st.session_state.total_time += elapsed_time
        
        return result, None
    except Exception as e:
        return None, f"处理失败: {str(e)}"


def render_chat_message(role: str, content: str, sources: list = None):
    """渲染聊天消息"""
    if role == "user":
        st.markdown(f"""
        <div class="user-message">
            <strong>👤 您：</strong><br>
            {content}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="assistant-message">
            <strong>🤖 助手：</strong><br>
            {content}
        </div>
        """, unsafe_allow_html=True)
        
        # 显示来源文档
        if sources:
            with st.expander("📚 参考文档", expanded=False):
                for idx, source in enumerate(sources[:3], 1):
                    filename = source.get('filename', '未知')
                    score = source.get('similarity_score', 0)
                    
                    score_info = f"相似度: {score:.3f}"
                    if 'semantic_score' in source and 'bm25_score' in source:
                        score_info += f" (语义:{source['semantic_score']:.3f}, 关键词:{source['bm25_score']:.3f})"
                    if 'llm_rerank_score' in source:
                        score_info += f" [Rerank:{source['llm_rerank_score']:.1f}/10]"
                    
                    st.markdown(f"""
                    <div class="source-doc">
                        <strong>{idx}. {filename}</strong><br>
                        {score_info}
                    </div>
                    """, unsafe_allow_html=True)


def main():
    """主函数"""
    
    # 检查RAG系统是否成功导入
    if not RAG_AVAILABLE:
        st.error(f"❌ RAG系统导入失败")
        st.error(f"错误信息: {import_error}")
        st.info("💡 请检查：\n1. src/RAG问答系统.py 文件是否存在\n2. 依赖是否完整安装")
        st.stop()
    
    # 标题
    st.markdown('<h1 class="main-title">🤖 嵌入式硬件RAG智能问答助手</h1>', unsafe_allow_html=True)
    
    # 侧边栏
    with st.sidebar:
        st.markdown("## ⚙️ 系统控制")
        
        # 初始化按钮
        if st.button("🚀 初始化系统", use_container_width=True):
            success, message = initialize_system()
            if success:
                st.success(message)
            else:
                st.error(message)
        
        st.markdown("---")
        
        # 系统状态
        st.markdown("## 📊 系统状态")
        if st.session_state.rag_system:
            doc_count = len(st.session_state.rag_system.vector_db.documents)
            has_bm25 = hasattr(st.session_state.rag_system.vector_db, 'bm25') and \
                      st.session_state.rag_system.vector_db.bm25 is not None
            
            st.markdown(f"""
            <div class="info-card">
                ✅ <strong>运行中</strong><br>
                📄 文档块: {doc_count}<br>
                🔍 检索: {'混合检索' if has_bm25 else '语义检索'}<br>
                🤖 模型: {st.session_state.rag_system.llm_model}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ 系统未初始化")
        
        st.markdown("---")
        
        # 参数设置
        st.markdown("## 🎛️ 检索参数")
        
        top_k = st.slider(
            "检索文档数量",
            min_value=1,
            max_value=10,
            value=5,
            help="返回最相关的K个文档"
        )
        
        temperature = st.slider(
            "LLM温度",
            min_value=0.1,
            max_value=1.0,
            value=0.8,
            step=0.1,
            help="越高越随机，越低越确定"
        )
        
        threshold = st.slider(
            "相似度阈值",
            min_value=0.0,
            max_value=1.0,
            value=0.4,
            step=0.05,
            help="低于此值的文档会被过滤"
        )
        
        st.markdown("---")
        
        # 统计信息
        st.markdown("## 📈 使用统计")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{st.session_state.query_count}</div>
                <div class="stat-label">查询次数</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            avg_time = st.session_state.total_time / st.session_state.query_count if st.session_state.query_count > 0 else 0
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{avg_time:.1f}s</div>
                <div class="stat-label">平均响应</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 缓存统计
        if st.session_state.rag_system:
            st.markdown("## 💾 缓存统计")
            
            try:
                cache_stats = st.session_state.rag_system.get_cache_stats()
                
                # 查询缓存
                query_cache = cache_stats.get('query_cache', {})
                if query_cache.get('status') != '未启用':
                    col1, col2 = st.columns(2)
                    with col1:
                        hit_rate = query_cache.get('hit_rate', '0%')
                        st.markdown(f"""
                        <div class="stat-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                            <div class="stat-value">{hit_rate}</div>
                            <div class="stat-label">查询命中率</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        cache_size = query_cache.get('size', 0)
                        max_size = query_cache.get('max_size', 0)
                        st.markdown(f"""
                        <div class="stat-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                            <div class="stat-value">{cache_size}/{max_size}</div>
                            <div class="stat-label">缓存大小</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # 清空缓存按钮
                    if st.button("🧹 清空缓存", use_container_width=True):
                        st.session_state.rag_system.clear_cache()
                        st.success("✅ 缓存已清空")
                        st.rerun()
                else:
                    st.info("缓存功能未启用")
            except Exception as e:
                st.warning(f"获取缓存统计失败: {e}")
        
        st.markdown("---")
        
        # 对话历史信息
        if st.session_state.rag_system:
            st.markdown("## 💬 对话历史")
            
            history = st.session_state.rag_system.get_history()
            turns = len(history) // 2 if history else 0
            max_turns = st.session_state.rag_system.max_history_turns
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div class="stat-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                    <div class="stat-value">{turns}/{max_turns}</div>
                    <div class="stat-label">记忆轮数</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="stat-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                    <div class="stat-value">{len(history)}</div>
                    <div class="stat-label">消息数量</div>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 清空对话
        if st.button("🗑️ 清空对话", use_container_width=True):
            st.session_state.chat_history = []
            if st.session_state.rag_system:
                st.session_state.rag_system.clear_history()
            st.rerun()
    
    # 主内容区域
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # 对话历史
        st.markdown("### 💬 对话窗口")
        
        chat_container = st.container()
        with chat_container:
            if not st.session_state.chat_history:
                st.info("👋 欢迎使用！请在下方输入您的问题。")
            else:
                for msg in st.session_state.chat_history:
                    render_chat_message(
                        msg['role'],
                        msg['content'],
                        msg.get('sources')
                    )
        
        # 输入区域
        st.markdown("---")
        with st.form(key="query_form", clear_on_submit=True):
            col_input, col_button = st.columns([4, 1])
            
            with col_input:
                user_input = st.text_input(
                    "输入问题",
                    placeholder="例如：激光雷达的测距范围是多少？",
                    label_visibility="collapsed"
                )
            
            with col_button:
                submit = st.form_submit_button("🚀 发送", use_container_width=True)
        
        if submit and user_input:
            if st.session_state.rag_system is None:
                st.error("❌ 请先初始化系统！")
            else:
                # 添加用户消息
                st.session_state.chat_history.append({
                    'role': 'user',
                    'content': user_input
                })
                
                # 处理查询
                with st.spinner("🤔 思考中..."):
                    result, error = process_query(user_input, top_k, temperature, threshold)
                
                if error:
                    st.error(error)
                else:
                    # 添加助手回复
                    st.session_state.chat_history.append({
                        'role': 'assistant',
                        'content': result['answer'],
                        'sources': result.get('sources', [])
                    })
                
                st.rerun()
    
    with col2:
        # 快速问题
        st.markdown("### 💡 快速问题")
        
        example_questions = [
            "激光雷达的测距范围是多少？",
            "ADS6311芯片的主要特性",
            "Hawk模组的工作电压",
            "产品的尺寸规格",
            "如何进行系统调试？"
        ]
        
        for question in example_questions:
            if st.button(question, use_container_width=True, key=f"ex_{question}"):
                if st.session_state.rag_system is None:
                    st.error("❌ 请先初始化系统！")
                else:
                    # 添加用户消息
                    st.session_state.chat_history.append({
                        'role': 'user',
                        'content': question
                    })
                    
                    # 处理查询
                    with st.spinner("🤔 思考中..."):
                        result, error = process_query(question, top_k, temperature, threshold)
                    
                    if not error:
                        st.session_state.chat_history.append({
                            'role': 'assistant',
                            'content': result['answer'],
                            'sources': result.get('sources', [])
                        })
                    
                    st.rerun()
    
    # 底部信息
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9rem;">
        💡 提示：调整侧边栏参数可以优化检索效果 | 
        📚 基于DashScope API + FAISS向量检索 | 
        🔒 本地部署，数据安全
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
