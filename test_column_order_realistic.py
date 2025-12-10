"""实际场景测试：模拟真实使用情况

测试在实际使用中可能遇到的各种列顺序场景
"""

import pandas as pd
import sys
import os

# 添加 backend 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from data_table import DataTable, ColumnConfig

def test_realistic_scenario():
    """测试实际场景：从不同数据源更新，列顺序不同"""
    print("=" * 60)
    print("实际场景测试：不同数据源的列顺序")
    print("=" * 60)
    
    # 场景：初始数据来自数据库查询，列顺序为: id, timestamp, status, value
    print("\n步骤 1: 初始化数据（数据库查询结果）")
    initial_data = pd.DataFrame({
        'id': [1, 2, 3, 4, 5],
        'timestamp': [1609459200.0, 1609545600.0, 1609632000.0, 1609718400.0, 1609804800.0],
        'status': ['active', 'inactive', 'active', 'pending', 'active'],
        'value': [100.5, 200.3, 150.7, 180.2, 120.9]
    })
    
    initial_columns = [
        ColumnConfig(prop='id', label='ID', type='number'),
        ColumnConfig(prop='timestamp', label='Timestamp', type='date'),
        ColumnConfig(prop='status', label='Status', type='string'),
        ColumnConfig(prop='value', label='Value', type='number')
    ]
    
    table = DataTable(initial_data, initial_columns)
    initial_config = table.get_columns_config()
    initial_order = [col['prop'] for col in initial_config['columns']]
    print(f"  初始列顺序: {initial_order}")
    
    # 场景：从 CSV 文件导入新数据，列顺序不同: value, status, id, timestamp
    print("\n步骤 2: 从 CSV 导入数据（列顺序不同）")
    csv_data = pd.DataFrame({
        'value': [300.1, 400.2, 500.3],
        'status': ['active', 'inactive', 'active'],
        'id': [6, 7, 8],
        'timestamp': [1609891200.0, 1609977600.0, 1610064000.0]
    })
    
    result = table.update_dataframe(csv_data)
    updated_config = table.get_columns_config()
    updated_order = [col['prop'] for col in updated_config['columns']]
    print(f"  更新后列顺序: {updated_order}")
    print(f"  CSV 数据列顺序: {list(csv_data.columns)}")
    
    # 验证：列顺序应该与 CSV 数据的列顺序一致
    assert updated_order == list(csv_data.columns), \
        f"列顺序应该与 CSV 数据一致！期望: {list(csv_data.columns)}, 实际: {updated_order}"
    print("  ✓ 列顺序与 CSV 数据一致")
    
    # 场景：从 API 获取数据，列顺序又不同: timestamp, id, value, status
    print("\n步骤 3: 从 API 获取数据（列顺序再次不同）")
    api_data = pd.DataFrame({
        'timestamp': [1610150400.0, 1610236800.0],
        'id': [9, 10],
        'value': [600.4, 700.5],
        'status': ['pending', 'active']
    })
    
    result = table.update_dataframe(api_data)
    updated_config = table.get_columns_config()
    updated_order = [col['prop'] for col in updated_config['columns']]
    print(f"  更新后列顺序: {updated_order}")
    print(f"  API 数据列顺序: {list(api_data.columns)}")
    
    # 验证：列顺序应该与 API 数据的列顺序一致
    assert updated_order == list(api_data.columns), \
        f"列顺序应该与 API 数据一致！期望: {list(api_data.columns)}, 实际: {updated_order}"
    print("  ✓ 列顺序与 API 数据一致")
    
    # 场景：添加新列并重排序
    print("\n步骤 4: 添加新列并重排序")
    extended_data = pd.DataFrame({
        'priority': ['high', 'low', 'medium'],
        'timestamp': [1610323200.0, 1610409600.0, 1610496000.0],
        'id': [11, 12, 13],
        'value': [800.6, 900.7, 1000.8],
        'status': ['active', 'inactive', 'active']
    })
    
    result = table.update_dataframe(extended_data)
    updated_config = table.get_columns_config()
    updated_order = [col['prop'] for col in updated_config['columns']]
    print(f"  更新后列顺序: {updated_order}")
    print(f"  扩展数据列顺序: {list(extended_data.columns)}")
    
    # 验证：新列应该按传入顺序添加
    assert updated_order == list(extended_data.columns), \
        f"列顺序应该与扩展数据一致！期望: {list(extended_data.columns)}, 实际: {updated_order}"
    assert 'priority' in updated_order, "新列 priority 应该存在"
    print("  ✓ 新列按传入顺序正确添加")
    
    print("\n" + "=" * 60)
    print("实际场景测试通过！✓")
    print("=" * 60)


def test_edge_cases():
    """测试边界情况"""
    print("\n" + "=" * 60)
    print("边界情况测试")
    print("=" * 60)
    
    # 测试：单列数据
    print("\n测试 1: 单列数据")
    single_col_data = pd.DataFrame({'id': [1, 2, 3]})
    single_col_config = [ColumnConfig(prop='id', label='ID', type='number')]
    table = DataTable(single_col_data, single_col_config)
    config = table.get_columns_config()
    assert [col['prop'] for col in config['columns']] == ['id'], "单列顺序错误"
    print("  ✓ 单列数据测试通过")
    
    # 测试：空 DataFrame（但有列结构）
    print("\n测试 2: 空 DataFrame")
    empty_data = pd.DataFrame(columns=['id', 'name'])
    empty_config = [
        ColumnConfig(prop='id', label='ID', type='number'),
        ColumnConfig(prop='name', label='Name', type='string')
    ]
    table = DataTable(empty_data, empty_config)
    config = table.get_columns_config()
    assert [col['prop'] for col in config['columns']] == ['id', 'name'], "空 DataFrame 列顺序错误"
    print("  ✓ 空 DataFrame 测试通过")
    
    # 测试：完全不同的列（全部替换）
    print("\n测试 3: 完全替换列")
    old_data = pd.DataFrame({'old_col1': [1, 2], 'old_col2': ['a', 'b']})
    old_config = [
        ColumnConfig(prop='old_col1', label='Old1', type='number'),
        ColumnConfig(prop='old_col2', label='Old2', type='string')
    ]
    table = DataTable(old_data, old_config)
    
    new_data = pd.DataFrame({'new_col1': [3, 4], 'new_col2': ['c', 'd']})
    result = table.update_dataframe(new_data)
    config = table.get_columns_config()
    new_order = [col['prop'] for col in config['columns']]
    assert new_order == ['new_col1', 'new_col2'], f"完全替换后列顺序错误: {new_order}"
    assert 'old_col1' not in new_order and 'old_col2' not in new_order, "旧列应该被删除"
    print("  ✓ 完全替换列测试通过")
    
    print("\n" + "=" * 60)
    print("边界情况测试通过！✓")
    print("=" * 60)


if __name__ == '__main__':
    print("\n开始实际场景测试...\n")
    
    try:
        test_realistic_scenario()
        test_edge_cases()
        
        print("\n" + "=" * 60)
        print("所有实际场景测试通过！✓")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

