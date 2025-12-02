"""
工具管理器 - 管理和注册所有工具
"""

from typing import List, Dict, Any, Optional
from langchain.tools import BaseTool
from .base_tools import (
    CalculatorTool,
    UnitConverterTool,
    ParameterExtractorTool,
    TableGeneratorTool,
    DocumentSearchTool
)


class ToolManager:
    """
    工具管理器 - 统一管理所有LangChain工具
    
    功能：
    - 注册工具
    - 获取工具列表
    - 工具调用
    """
    
    def __init__(self, vector_db=None):
        """
        初始化工具管理器
        
        Args:
            vector_db: 向量数据库实例（用于DocumentSearchTool）
        """
        self.vector_db = vector_db
        self.tools: List[BaseTool] = []
        self._init_default_tools()
    
    def _init_default_tools(self):
        """初始化默认工具集"""
        # 1. 计算器工具
        self.register_tool(CalculatorTool())
        
        # 2. 单位转换工具
        self.register_tool(UnitConverterTool())
        
        # 3. 参数提取工具
        self.register_tool(ParameterExtractorTool())
        
        # 4. 表格生成工具
        self.register_tool(TableGeneratorTool())
        
        # 5. 文档搜索工具（如果有向量数据库）
        if self.vector_db:
            doc_search_tool = DocumentSearchTool(vector_db=self.vector_db)
            self.register_tool(doc_search_tool)
    
    def register_tool(self, tool: BaseTool):
        """注册新工具"""
        self.tools.append(tool)
        print(f"✅ 工具已注册: {tool.name}")
    
    def get_tools(self) -> List[BaseTool]:
        """获取所有工具"""
        return self.tools
    
    def get_tool_names(self) -> List[str]:
        """获取所有工具名称"""
        return [tool.name for tool in self.tools]
    
    def get_tool_descriptions(self) -> Dict[str, str]:
        """获取工具描述"""
        return {tool.name: tool.description for tool in self.tools}
    
    def get_tool_by_name(self, name: str) -> Optional[BaseTool]:
        """根据名称获取工具"""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None
    
    def print_tool_info(self):
        """打印所有工具信息"""
        print("\n" + "="*60)
        print("🔧 可用工具列表")
        print("="*60)
        
        for i, tool in enumerate(self.tools, 1):
            print(f"\n{i}. {tool.name}")
            print(f"   描述: {tool.description.strip()[:100]}...")
        
        print("\n" + "="*60)
