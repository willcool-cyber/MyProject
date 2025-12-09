# -*- coding: utf-8 -*-
"""
嵌入式硬件RAG问答助手 - 主启动脚本
统一的项目启动入口
"""

import os
import sys
import subprocess
from pathlib import Path

# 添加项目路径到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import get_settings


def validate_environment():
    """验证运行环境"""
    print("\n" + "=" * 60)
    print("🔍 验证运行环境...")
    print("=" * 60)
    
    # 检查API Key
    settings = get_settings()
    if not settings.DASHSCOPE_API_KEY:
        print("❌ 错误: DASHSCOPE_API_KEY 未设置")
        print("   请运行: set DASHSCOPE_API_KEY=your_api_key_here")
        return False
    
    print(f"✅ API Key: {settings.DASHSCOPE_API_KEY[:10]}...{settings.DASHSCOPE_API_KEY[-5:]}")
    
    # 检查数据目录
    if not settings.DATA_DIR.exists():
        print(f"❌ 错误: 数据目录不存在 {settings.DATA_DIR}")
        return False
    
    print(f"✅ 数据目录: {settings.DATA_DIR}")
    
    # 检查向量库目录
    if not settings.VECTOR_DB_DIR.exists():
        print(f"⚠️  向量库目录不存在，将在启动时创建: {settings.VECTOR_DB_DIR}")
    else:
        print(f"✅ 向量库目录: {settings.VECTOR_DB_DIR}")
    
    # 检查日志目录
    settings.LOG_DIR.mkdir(exist_ok=True)
    print(f"✅ 日志目录: {settings.LOG_DIR}")
    
    return True


def check_dependencies():
    """检查必要的依赖"""
    print("\n" + "=" * 60)
    print("📦 检查依赖...")
    print("=" * 60)
    
    dependencies = {
        'streamlit': 'Streamlit',
        'dashscope': 'DashScope API',
        'faiss': 'FAISS向量库',
        'numpy': 'NumPy',
        'pandas': 'Pandas'
    }
    
    missing = []
    for pkg, name in dependencies.items():
        try:
            __import__(pkg)
            print(f"✅ {name}")
        except ImportError:
            print(f"❌ {name} 未安装")
            missing.append(pkg)
    
    if missing:
        print(f"\n⚠️  缺少依赖，请运行:")
        print(f"   pip install {' '.join(missing)}")
        return False
    
    return True


def build_vector_db_if_needed():
    """检查并构建向量数据库（如果需要）"""
    from config.settings import get_settings
    
    settings = get_settings()
    vector_db_path = settings.VECTOR_DB_DIR
    data_dir = settings.DATA_DIR
    
    # 检查向量库是否存在且完整
    # 支持两种格式：JSON格式和PKL格式
    required_files = ['faiss.index']
    metadata_files = ['metadata.json', 'metadata.pkl']
    config_file = 'config.json'
    
    missing_required = [f for f in required_files if not (vector_db_path / f).exists()]
    has_metadata = any((vector_db_path / f).exists() for f in metadata_files)
    has_config = (vector_db_path / config_file).exists()
    
    # 检查是否需要重建：缺少必要文件或配置文件
    needs_rebuild = missing_required or not has_metadata or not has_config
    
    if needs_rebuild:
        print("\n⚠️  向量数据库不完整或不存在")
        if missing_required:
            print(f"   缺少文件: {', '.join(missing_required)}")
        if not has_metadata:
            print(f"   缺少元数据文件")
        if not has_config:
            print(f"   缺少配置文件")
        
        print("\n🔄 正在构建向量数据库...")
        print("   这可能需要几分钟，请耐心等待...\n")
        
        try:
            from src.RAG数据库 import EmbeddingVectorDatabase
            
            # 构建向量数据库
            vector_db = EmbeddingVectorDatabase(
                model_name="text-embedding-v2",
                vector_db_path=str(vector_db_path)
            )
            
            # 使用绝对路径传递data_folder，禁用增量构建强制完全重建
            if vector_db.build_database(
                data_folder=str(data_dir),
                incremental=False  # 强制完全重建，确保所有文件都被处理
            ):
                print("\n✅ 向量数据库构建成功！\n")
                return True
            else:
                print("\n❌ 向量数据库构建失败")
                print("   请检查:")
                print("   1. 数据目录是否存在: " + str(data_dir))
                print("   2. 是否有文档文件（PDF、PPTX等）")
                print("   3. API Key是否正确设置")
                return False
                
        except Exception as e:
            print(f"\n❌ 构建失败: {str(e)}")
            print("\n💡 手动构建方法:")
            print("   cd src")
            print("   python RAG数据库.py")
            import traceback
            traceback.print_exc()
            return False
    else:
        # 向量库存在，检查是否有新文件需要处理
        print("\n✅ 向量数据库已存在，检查是否有新文件...")
        
        try:
            from src.RAG数据库 import EmbeddingVectorDatabase
            import json
            from pathlib import Path
            
            # 加载已处理文件记录
            config_path = vector_db_path / config_file
            with open(str(config_path), 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            processed_files = config.get('processed_files', {})
            
            # 检查data目录中是否有新文件
            supported_extensions = ['.pdf', '.pptx', '.xlsx', '.xls', '.docx']
            all_files = [f for f in Path(data_dir).iterdir() 
                        if f.is_file() and f.suffix.lower() in supported_extensions]
            
            new_files = [f for f in all_files if f.name not in processed_files]
            
            if new_files:
                print(f"\n📝 发现 {len(new_files)} 个新文件需要处理:")
                for f in new_files:
                    print(f"   • {f.name}")
                
                print("\n🔄 正在增量更新向量数据库...")
                
                # 使用增量构建处理新文件
                vector_db = EmbeddingVectorDatabase(
                    model_name="text-embedding-v2",
                    vector_db_path=str(vector_db_path)
                )
                
                if vector_db.load_database():
                    # 增量构建会自动检测新文件
                    vector_db.build_database(
                        data_folder=str(data_dir),
                        incremental=True
                    )
                    print("\n✅ 向量数据库更新成功！\n")
                    return True
                else:
                    print("\n⚠️  无法加载现有向量库，将进行完全重建...")
                    vector_db = EmbeddingVectorDatabase(
                        model_name="text-embedding-v2",
                        vector_db_path=str(vector_db_path)
                    )
                    if vector_db.build_database(
                        data_folder=str(data_dir),
                        incremental=False
                    ):
                        print("\n✅ 向量数据库重建成功！\n")
                        return True
                    else:
                        print("\n❌ 向量数据库重建失败\n")
                        return False
            else:
                print(f"✅ 所有文件都已处理，无需更新\n")
                return True
                
        except Exception as e:
            print(f"\n⚠️  检查新文件时出错: {str(e)}")
            print("   将继续启动应用...\n")
            return True  # 继续启动，不中断应用
    
    return True


def start_terminal_mode():
    """启动终端交互模式"""
    print("\n" + "=" * 60)
    print("💬 启动终端查询模式...")
    print("=" * 60)
    
    # 检查并构建向量库
    if not build_vector_db_if_needed():
        print("\n❌ 无法启动终端模式，向量数据库构建失败")
        return False
    
    try:
        from src.RAG问答系统 import RAGQASystem
        from config.settings import get_settings
        
        # 初始化RAG系统
        print("\n🔄 初始化RAG问答系统...")
        settings = get_settings()
        rag_system = RAGQASystem(vector_db_path=str(settings.VECTOR_DB_DIR))
        print("✅ RAG系统初始化完成\n")
        
        print("=" * 60)
        print("📝 使用说明:")
        print("  - 输入你的问题，系统会返回答案")
        print("  - 输入 'exit' 或 'quit' 退出")
        print("  - 输入 'clear' 清空屏幕")
        print("=" * 60 + "\n")
        
        # 交互循环
        query_count = 0
        while True:
            try:
                user_input = input("🤔 请输入问题: ").strip()
                
                if not user_input:
                    print("⚠️  请输入有效的问题\n")
                    continue
                
                if user_input.lower() in ['exit', 'quit']:
                    print("\n👋 感谢使用，再见！")
                    break
                
                if user_input.lower() == 'clear':
                    os.system('cls' if os.name == 'nt' else 'clear')
                    continue
                
                # 查询
                query_count += 1
                print(f"\n⏳ 正在查询 (第{query_count}个问题)...\n")
                
                # 使用流式输出，实现字一个字蹦出来的效果
                result = rag_system.ask(user_input, top_k=5, stream=True)
                
                # 显示参考文档
                if result.get('sources'):
                    print("\n" + "=" * 60)
                    print("📚 参考文档:")
                    print("=" * 60)
                    for i, ref in enumerate(result['sources'], 1):
                        print(f"  [{i}] {ref.get('filename', '未知来源')}")
                        if ref.get('similarity_score'):
                            print(f"      相似度: {ref['similarity_score']:.2%}")
                
                print("=" * 60 + "\n")
                
            except KeyboardInterrupt:
                print("\n\n⏹️  已停止查询")
                break
            except Exception as e:
                print(f"❌ 查询失败: {str(e)}\n")
        
        return True
        
    except Exception as e:
        print(f"❌ 启动失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def start_streamlit_app():
    """启动Streamlit应用"""
    print("\n" + "=" * 60)
    print("🚀 启动Web应用...")
    print("=" * 60)
    
    app_path = Path(__file__).parent / "src" / "app.py"
    
    if not app_path.exists():
        print(f"❌ 错误: 应用文件不存在 {app_path}")
        return False
    
    print(f"📍 应用文件: {app_path}")
    print(f"🌐 访问地址: http://localhost:8501")
    print("=" * 60)
    print("按 Ctrl+C 停止应用\n")
    
    try:
        # 启动Streamlit应用
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", str(app_path)],
            cwd=str(Path(__file__).parent)
        )
        return True
    except KeyboardInterrupt:
        print("\n⏹️  应用已停止")
        return True
    except Exception as e:
        print(f"❌ 启动失败: {str(e)}")
        return False


def select_mode():
    """选择运行模式"""
    print("\n" + "=" * 60)
    print("🎯 选择运行模式")
    print("=" * 60)
    print("1️⃣  终端查询模式 (💬 在命令行中交互)")
    print("2️⃣  Web页面模式 (🌐 在浏览器中使用)")
    print("0️⃣  退出")
    print("=" * 60)
    
    while True:
        choice = input("\n请选择 (1/2/0): ").strip()
        
        if choice == '1':
            return 'terminal'
        elif choice == '2':
            return 'web'
        elif choice == '0':
            return 'exit'
        else:
            print("❌ 无效的选择，请输入 1、2 或 0")



def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🤖 嵌入式硬件RAG智能问答助手")
    print("=" * 60)
    
    # 1. 检查依赖
    if not check_dependencies():
        print("\n❌ 依赖检查失败，请先安装缺失的依赖")
        return False
    
    # 2. 验证环境
    if not validate_environment():
        print("\n❌ 环境验证失败")
        return False
    
    # 3. 选择运行模式
    print("\n✅ 所有检查通过，准备启动应用...\n")
    mode = select_mode()
    
    if mode == 'exit':
        print("\n👋 已退出")
        return True
    elif mode == 'terminal':
        return start_terminal_mode()
    elif mode == 'web':
        return start_streamlit_app()
    else:
        print("\n❌ 无效的模式")
        return False


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  应用已停止")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
