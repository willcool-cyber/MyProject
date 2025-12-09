"""
基础工具集 - LangChain Tool实现
包含计算器、单位转换、参数提取等常用工具
"""

from langchain.tools import BaseTool
from typing import Optional, Type, Any, Dict, List, ClassVar
from pydantic import BaseModel, Field
import re
import json


# ==================== 计算器工具 ====================

class CalculatorInput(BaseModel):
    """计算器输入参数"""
    expression: str = Field(description="要计算的数学表达式，例如：'2 + 3 * 4' 或 '(10 + 5) / 3'")


class CalculatorTool(BaseTool):
    """
    计算器工具 - 执行数学计算
    
    使用场景：
    - 参数计算（如功率、频率、距离等）
    - 数值对比
    - 简单数学运算
    """
    name: str = "calculator"
    description: str = """
    数学计算器工具。当需要进行数学计算时使用此工具。
    
    输入参数：
    - expression: 数学表达式字符串
    
    示例：expression="2 + 3", expression="10 * 5", expression="(100 - 20) / 4"
    """
    args_schema: Type[BaseModel] = CalculatorInput
    
    def _run(self, expression: str) -> str:
        """执行计算"""
        try:
            # 清理表达式，只保留安全字符
            safe_expr = re.sub(r'[^0-9+\-*/().\s]', '', expression)
            if not safe_expr:
                return "错误：无效的数学表达式"
            
            # 计算结果
            result = eval(safe_expr)
            return f"计算结果：{expression} = {result}"
        except Exception as e:
            return f"计算错误：{str(e)}"
    
    async def _arun(self, expression: str) -> str:
        """异步执行（调用同步版本）"""
        return self._run(expression)


# ==================== 单位转换工具 ====================

class UnitConverterInput(BaseModel):
    """单位转换输入参数"""
    value: float = Field(description="要转换的数值")
    from_unit: str = Field(description="源单位，如：'m', 'cm', 'mm', 'km', 'MHz', 'GHz'等")
    to_unit: str = Field(description="目标单位，如：'m', 'cm', 'mm', 'km', 'MHz', 'GHz'等")


class UnitConverterTool(BaseTool):
    """
    单位转换工具 - 支持长度、频率等单位转换
    
    使用场景：
    - 长度单位转换（米、厘米、毫米等）
    - 频率单位转换（Hz、kHz、MHz、GHz）
    - 时间单位转换
    """
    name: str = "unit_converter"
    description: str = """
    单位转换工具。用于转换不同单位之间的数值。
    
    支持的单位类型：
    - 长度：m, cm, mm, km, um, nm
    - 频率：Hz, kHz, MHz, GHz
    - 时间：s, ms, us, ns
    
    输入参数：
    - value: 数值（浮点数）
    - from_unit: 源单位（字符串）
    - to_unit: 目标单位（字符串）
    
    示例：value=100, from_unit="m", to_unit="cm"
    """
    args_schema: Type[BaseModel] = UnitConverterInput
    
    # 单位转换系数（转换为基本单位）
    LENGTH_UNITS: ClassVar[Dict[str, float]] = {
        'km': 1000, 'm': 1, 'cm': 0.01, 'mm': 0.001, 
        'um': 1e-6, 'nm': 1e-9
    }
    
    FREQUENCY_UNITS: ClassVar[Dict[str, float]] = {
        'GHz': 1e9, 'MHz': 1e6, 'kHz': 1e3, 'Hz': 1
    }
    
    TIME_UNITS: ClassVar[Dict[str, float]] = {
        's': 1, 'ms': 1e-3, 'us': 1e-6, 'ns': 1e-9
    }
    
    def _run(self, value: float, from_unit: str, to_unit: str) -> str:
        """执行单位转换"""
        try:
            # 确定单位类型
            unit_map = None
            if from_unit in self.LENGTH_UNITS and to_unit in self.LENGTH_UNITS:
                unit_map = self.LENGTH_UNITS
                unit_type = "长度"
            elif from_unit in self.FREQUENCY_UNITS and to_unit in self.FREQUENCY_UNITS:
                unit_map = self.FREQUENCY_UNITS
                unit_type = "频率"
            elif from_unit in self.TIME_UNITS and to_unit in self.TIME_UNITS:
                unit_map = self.TIME_UNITS
                unit_type = "时间"
            else:
                return f"错误：不支持的单位转换 {from_unit} -> {to_unit}"
            
            # 转换计算
            base_value = value * unit_map[from_unit]
            result = base_value / unit_map[to_unit]
            
            return f"单位转换结果：{value} {from_unit} = {result} {to_unit}"
        except Exception as e:
            return f"转换错误：{str(e)}"
    
    async def _arun(self, value: float, from_unit: str, to_unit: str) -> str:
        """异步执行"""
        return self._run(value, from_unit, to_unit)


# ==================== 参数提取工具 ====================

class ParameterExtractorInput(BaseModel):
    """参数提取输入"""
    text: str = Field(description="包含参数信息的文本")
    param_type: str = Field(description="要提取的参数类型，如：'测距范围', '频率', '尺寸'等")


class ParameterExtractorTool(BaseTool):
    """
    参数提取工具 - 从文本中提取技术参数
    
    使用场景：
    - 从文档中提取规格参数
    - 识别数值和单位
    - 结构化技术信息
    """
    name: str = "parameter_extractor"
    description: str = """
    参数提取工具。从技术文档文本中提取特定的技术参数。
    可以识别数值、单位、范围等信息。
    
    输入参数：
    - text: 包含参数的文本内容
    - param_type: 参数类型（如：'测距范围'、'频率'、'尺寸'、'电压'等）
    
    使用方法：直接传入两个参数，不要使用JSON格式
    正确示例：text="测距范围0.1-30米", param_type="测距范围"
    """
    args_schema: Type[BaseModel] = ParameterExtractorInput
    
    def _run(self, text: str, param_type: str) -> str:
        """执行参数提取"""
        try:
            # 通用数值+单位模式
            patterns = {
                '测距范围': r'(\d+\.?\d*)\s*[-~至到]\s*(\d+\.?\d*)\s*(m|cm|mm|米|厘米|毫米)',
                '频率': r'(\d+\.?\d*)\s*(GHz|MHz|kHz|Hz)',
                '尺寸': r'(\d+\.?\d*)\s*[x×*]\s*(\d+\.?\d*)\s*[x×*]?\s*(\d+\.?\d*)?\s*(mm|cm|m)',
                '电压': r'(\d+\.?\d*)\s*(V|v|伏)',
                '功率': r'(\d+\.?\d*)\s*(W|w|瓦|mW)',
                '精度': r'[±]\s*(\d+\.?\d*)\s*(mm|cm|%)',
            }
            
            # 尝试匹配
            pattern = patterns.get(param_type, r'(\d+\.?\d*)\s*(\w+)')
            matches = re.findall(pattern, text, re.IGNORECASE)
            
            if matches:
                result = f"提取到的{param_type}参数：\n"
                for match in matches[:5]:  # 最多显示5个
                    result += f"  - {' '.join(match)}\n"
                return result.strip()
            else:
                return f"未找到{param_type}相关参数"
                
        except Exception as e:
            return f"提取错误：{str(e)}"
    
    async def _arun(self, text: str, param_type: str) -> str:
        """异步执行"""
        return self._run(text, param_type)


# ==================== 表格生成工具 ====================

class TableGeneratorInput(BaseModel):
    """表格生成输入"""
    data: str = Field(description="JSON格式的数据，用于生成表格")
    table_type: str = Field(default="comparison", description="表格类型：comparison(对比), specs(规格)")


class TableGeneratorTool(BaseTool):
    """
    表格生成工具 - 生成Markdown格式的对比表格
    
    使用场景：
    - 产品参数对比
    - 规格表格展示
    - 数据可视化
    """
    name: str = "table_generator"
    description: str = """
    表格生成工具。根据数据生成Markdown格式的表格。
    
    输入参数：
    - data: JSON格式的字符串数据
    - table_type: 表格类型（'comparison' 或 'specs'）
    
    示例：data='{"产品A": {"参数1": "值1"}, "产品B": {"参数1": "值2"}}', table_type="comparison"
    """
    args_schema: Type[BaseModel] = TableGeneratorInput
    
    def _run(self, data: str, table_type: str = "comparison") -> str:
        """生成表格"""
        try:
            # 解析JSON数据
            data_dict = json.loads(data) if isinstance(data, str) else data
            
            if table_type == "comparison":
                return self._generate_comparison_table(data_dict)
            elif table_type == "specs":
                return self._generate_specs_table(data_dict)
            else:
                return "错误：不支持的表格类型"
                
        except json.JSONDecodeError:
            return "错误：无效的JSON格式"
        except Exception as e:
            return f"表格生成错误：{str(e)}"
    
    def _generate_comparison_table(self, data: Dict) -> str:
        """生成对比表格"""
        if not data:
            return "错误：数据为空"
        
        # 获取所有参数名
        all_params = set()
        for item_data in data.values():
            if isinstance(item_data, dict):
                all_params.update(item_data.keys())
        
        # 生成表格
        headers = ["参数"] + list(data.keys())
        table = "| " + " | ".join(headers) + " |\n"
        table += "|" + "---|" * len(headers) + "\n"
        
        for param in all_params:
            row = [param]
            for item_name, item_data in data.items():
                value = item_data.get(param, "-") if isinstance(item_data, dict) else "-"
                row.append(str(value))
            table += "| " + " | ".join(row) + " |\n"
        
        return f"生成的对比表格：\n{table}"
    
    def _generate_specs_table(self, data: Dict) -> str:
        """生成规格表格"""
        table = "| 规格项 | 参数值 |\n"
        table += "|-------|-------|\n"
        
        for key, value in data.items():
            table += f"| {key} | {value} |\n"
        
        return f"生成的规格表格：\n{table}"
    
    async def _arun(self, data: str, table_type: str = "comparison") -> str:
        """异步执行"""
        return self._run(data, table_type)


# ==================== 文档搜索工具 ====================

class DocumentSearchInput(BaseModel):
    """文档搜索输入"""
    query: str = Field(description="搜索查询关键词")
    top_k: int = Field(default=3, description="返回结果数量")


class DocumentSearchTool(BaseTool):
    """
    文档搜索工具 - 在向量数据库中搜索相关文档
    
    使用场景：
    - 查找相关技术文档
    - 检索产品规格
    - 获取参考资料
    """
    name: str = "document_search"
    description: str = """
    文档搜索工具。在向量数据库中搜索与查询相关的技术文档。
    
    输入参数：
    - query: 搜索关键词（字符串）
    - top_k: 返回文档数量（整数，默认3）
    
    示例：query="Hawk模组规格", top_k=3
    """
    args_schema: Type[BaseModel] = DocumentSearchInput
    vector_db: Optional[Any] = None  # 向量数据库引用
    
    def __init__(self, vector_db=None):
        """初始化，注入向量数据库"""
        super().__init__()
        self.vector_db = vector_db
    
    def _run(self, query: str, top_k: int = 3) -> str:
        """执行搜索"""
        try:
            if self.vector_db is None:
                return "错误：向量数据库未初始化"
            
            # 调用向量数据库搜索
            results = self.vector_db.search(query, top_k=top_k)
            
            if not results:
                return f"未找到与'{query}'相关的文档"
            
            # 格式化输出
            output = f"找到 {len(results)} 个相关文档：\n\n"
            for i, result in enumerate(results, 1):
                output += f"【文档 {i}】\n"
                output += f"来源：{result.get('filename', '未知')}\n"
                output += f"相似度：{result.get('similarity_score', 0):.3f}\n"
                output += f"内容：{result.get('text', '')[:200]}...\n\n"
            
            return output.strip()
            
        except Exception as e:
            return f"搜索错误：{str(e)}"
    
    async def _arun(self, query: str, top_k: int = 3) -> str:
        """异步执行"""
        return self._run(query, top_k)


# ==================== 联网搜索工具 ====================

class WebSearchInput(BaseModel):
    """联网搜索输入参数"""
    query: str = Field(description="搜索关键词或问题")
    max_results: int = Field(default=3, description="返回结果数量")


class WebSearchTool(BaseTool):
    """
    联网搜索工具 - 使用DuckDuckGo搜索引擎
    
    使用场景：
    - 文档库中找不到答案时
    - 需要最新信息或行业动态
    - 技术标准或通用知识查询
    """
    name: str = "web_search"
    description: str = """
    联网搜索工具。当文档库中找不到答案，或需要最新信息时使用。
    使用DuckDuckGo搜索引擎（无需API密钥）。
    
    输入参数：
    - query: 搜索关键词或问题（字符串）
    - max_results: 返回结果数量（整数，默认3）
    
    示例：query="LIDAR技术原理", max_results=3
    """
    args_schema: Type[BaseModel] = WebSearchInput
    
    def _run(self, query: str, max_results: int = 3) -> str:
        """执行联网搜索"""
        try:
            from duckduckgo_search import DDGS
            
            # 使用DuckDuckGo搜索
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            
            if not results:
                return f"未找到与'{query}'相关的网络信息"
            
            # 格式化输出
            output = f"🌐 网络搜索结果（共 {len(results)} 条）：\n\n"
            for i, result in enumerate(results, 1):
                title = result.get('title', '未知标题')
                body = result.get('body', '无描述')
                link = result.get('href', '')
                
                output += f"【结果 {i}】{title}\n"
                output += f"摘要：{body}\n"
                output += f"链接：{link}\n\n"
            
            return output.strip()
            
        except ImportError:
            return "错误：未安装duckduckgo-search库，请运行: pip install duckduckgo-search"
        except Exception as e:
            return f"搜索错误：{str(e)}"
    
    async def _arun(self, query: str, max_results: int = 3) -> str:
        """异步执行"""
        return self._run(query, max_results)
