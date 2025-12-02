"""
全局配置管理
统一管理所有系统配置参数
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class Settings:
    """系统配置类"""
    
    # ==================== 路径配置 ====================
    # 项目根目录
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    
    # 数据目录
    DATA_DIR: Path = PROJECT_ROOT / "data"
    VECTOR_DB_DIR: Path = PROJECT_ROOT / "src" / "embedding向量库"  # 向量库在src目录中
    LOG_DIR: Path = PROJECT_ROOT / "logs"
    
    # ==================== API配置 ====================
    # DashScope API
    DASHSCOPE_API_KEY: Optional[str] = os.getenv("DASHSCOPE_API_KEY")
    
    # ==================== 模型配置 ====================
    # LLM模型
    LLM_MODEL: str = "qwen-turbo"  # qwen-turbo, qwen-plus, qwen-max
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2000
    
    # Embedding模型
    EMBEDDING_MODEL: str = "text-embedding-v2"
    EMBEDDING_DIMENSION: int = 1536
    
    # ==================== RAG配置 ====================
    # 文本分块
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    
    # 检索配置
    TOP_K: int = 5  # 检索返回的文档数量
    SIMILARITY_THRESHOLD: float = 0.7  # 相似度阈值
    
    # ==================== 系统配置 ====================
    # 日志级别
    LOG_LEVEL: str = "INFO"
    
    # 批处理配置
    BATCH_SIZE: int = 10
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 1  # 秒
    
    # ==================== UI配置 ====================
    # Streamlit配置
    UI_TITLE: str = "🤖 嵌入式硬件RAG智能助手"
    UI_PAGE_ICON: str = "🔧"
    
    def __post_init__(self):
        """初始化后检查"""
        # 创建必要的目录
        self.LOG_DIR.mkdir(exist_ok=True)
        self.VECTOR_DB_DIR.mkdir(exist_ok=True)
        
        # 检查API Key
        if not self.DASHSCOPE_API_KEY:
            print("⚠️  警告: 未设置 DASHSCOPE_API_KEY 环境变量")
    
    def validate(self) -> bool:
        """验证配置是否有效"""
        if not self.DASHSCOPE_API_KEY:
            print("❌ 错误: DASHSCOPE_API_KEY 未设置")
            return False
        
        if not self.DATA_DIR.exists():
            print(f"❌ 错误: 数据目录不存在 {self.DATA_DIR}")
            return False
        
        return True


# 全局配置实例
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """获取全局配置实例（单例模式）"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# 便捷函数
def get_api_key() -> str:
    """获取API Key"""
    settings = get_settings()
    if not settings.DASHSCOPE_API_KEY:
        raise ValueError("DASHSCOPE_API_KEY 未设置，请在环境变量中配置")
    return settings.DASHSCOPE_API_KEY


if __name__ == "__main__":
    # 测试配置
    settings = get_settings()
    print("=" * 60)
    print("配置信息：")
    print("=" * 60)
    print(f"项目根目录: {settings.PROJECT_ROOT}")
    print(f"数据目录: {settings.DATA_DIR}")
    print(f"向量库目录: {settings.VECTOR_DB_DIR}")
    print(f"LLM模型: {settings.LLM_MODEL}")
    print(f"Embedding模型: {settings.EMBEDDING_MODEL}")
    print(f"分块大小: {settings.CHUNK_SIZE}")
    print(f"Top-K: {settings.TOP_K}")
    print("=" * 60)
    
    # 验证配置
    if settings.validate():
        print("✅ 配置验证通过")
    else:
        print("❌ 配置验证失败")

