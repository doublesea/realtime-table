"""调试脚本：用于检查表格数据状态"""

import logging
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('table_debug.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def check_table_state(table_instance):
    """检查表格实例的状态"""
    if not hasattr(table_instance, 'logic'):
        logger.error("表格实例没有 logic 属性")
        return
    
    logic = table_instance.logic
    
    # 检查 DataFrame
    if not hasattr(logic, 'dataframe'):
        logger.error("DataTable 没有 dataframe 属性")
        return
    
    df = logic.dataframe
    logger.info(f"DataFrame 状态:")
    logger.info(f"  - 长度: {len(df)}")
    logger.info(f"  - 是否为空: {df.empty}")
    logger.info(f"  - 列数: {len(df.columns)}")
    logger.info(f"  - 列名: {list(df.columns)}")
    
    if len(df) > 0:
        logger.info(f"  - 前5行ID: {df['id'].head().tolist() if 'id' in df.columns else 'N/A'}")
        logger.info(f"  - 最后5行ID: {df['id'].tail().tolist() if 'id' in df.columns else 'N/A'}")
    
    # 检查列配置
    if hasattr(logic, 'columns_config'):
        logger.info(f"列配置数量: {len(logic.columns_config)}")
        for col in logic.columns_config[:5]:  # 只显示前5个
            logger.info(f"  - {col.prop}: {col.type}, filterable={col.filterable}")

if __name__ == "__main__":
    logger.info("调试脚本已启动")
    logger.info("请在代码中调用 check_table_state(table_instance) 来检查表格状态")










