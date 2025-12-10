"""测试列顺序修复功能

验证 update_dataframe 方法在更新列时能够保持传入的列顺序
"""

import pandas as pd
import sys
import os

# 添加 backend 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from data_table import DataTable, ColumnConfig

def test_column_order_preservation():
    """测试列顺序保持功能"""
    print("=" * 60)
    print("测试 1: 基本列顺序保持")
    print("=" * 60)
    
    # 创建初始数据，列顺序为: id, name, age
    initial_data = pd.DataFrame({
        'id': [1, 2, 3],
        'name': ['Alice', 'Bob', 'Charlie'],
        'age': [25, 30, 35]
    })
    
    # 创建初始列配置
    initial_columns = [
        ColumnConfig(prop='id', label='ID', type='number'),
        ColumnConfig(prop='name', label='Name', type='string'),
        ColumnConfig(prop='age', label='Age', type='number')
    ]
    
    # 创建 DataTable 实例
    table = DataTable(initial_data, initial_columns)
    
    # 获取初始列顺序
    initial_config = table.get_columns_config()
    initial_order = [col['prop'] for col in initial_config['columns']]
    print(f"初始列顺序: {initial_order}")
    assert initial_order == ['id', 'name', 'age'], f"初始顺序错误: {initial_order}"
    
    # 更新 DataFrame，改变列顺序为: age, name, id
    new_data = pd.DataFrame({
        'age': [25, 30, 35],
        'name': ['Alice', 'Bob', 'Charlie'],
        'id': [1, 2, 3]
    })
    
    result = table.update_dataframe(new_data)
    print(f"更新结果: {result}")
    
    # 获取更新后的列顺序
    updated_config = table.get_columns_config()
    updated_order = [col['prop'] for col in updated_config['columns']]
    print(f"更新后列顺序: {updated_order}")
    
    # 验证列顺序与传入的 DataFrame 列顺序一致
    expected_order = list(new_data.columns)
    assert updated_order == expected_order, f"列顺序不匹配！期望: {expected_order}, 实际: {updated_order}"
    print("✓ 测试通过：列顺序与传入的 DataFrame 列顺序一致\n")


def test_add_new_columns():
    """测试添加新列时的顺序"""
    print("=" * 60)
    print("测试 2: 添加新列时的顺序保持")
    print("=" * 60)
    
    # 创建初始数据
    initial_data = pd.DataFrame({
        'id': [1, 2, 3],
        'name': ['Alice', 'Bob', 'Charlie']
    })
    
    initial_columns = [
        ColumnConfig(prop='id', label='ID', type='number'),
        ColumnConfig(prop='name', label='Name', type='string')
    ]
    
    table = DataTable(initial_data, initial_columns)
    
    # 添加新列，顺序为: email, id, name, age
    new_data = pd.DataFrame({
        'email': ['alice@test.com', 'bob@test.com', 'charlie@test.com'],
        'id': [1, 2, 3],
        'name': ['Alice', 'Bob', 'Charlie'],
        'age': [25, 30, 35]
    })
    
    result = table.update_dataframe(new_data)
    print(f"更新结果: {result}")
    print(f"添加的列: {result.get('added_columns', 'N/A')}")
    
    # 获取更新后的列顺序
    updated_config = table.get_columns_config()
    updated_order = [col['prop'] for col in updated_config['columns']]
    print(f"更新后列顺序: {updated_order}")
    
    # 验证列顺序
    expected_order = list(new_data.columns)
    assert updated_order == expected_order, f"列顺序不匹配！期望: {expected_order}, 实际: {updated_order}"
    print("✓ 测试通过：新列按传入顺序正确添加\n")


def test_remove_columns():
    """测试删除列时的处理"""
    print("=" * 60)
    print("测试 3: 删除列时的处理")
    print("=" * 60)
    
    # 创建初始数据
    initial_data = pd.DataFrame({
        'id': [1, 2, 3],
        'name': ['Alice', 'Bob', 'Charlie'],
        'age': [25, 30, 35],
        'email': ['alice@test.com', 'bob@test.com', 'charlie@test.com']
    })
    
    initial_columns = [
        ColumnConfig(prop='id', label='ID', type='number'),
        ColumnConfig(prop='name', label='Name', type='string'),
        ColumnConfig(prop='age', label='Age', type='number'),
        ColumnConfig(prop='email', label='Email', type='string')
    ]
    
    table = DataTable(initial_data, initial_columns)
    
    # 删除 age 列，保留其他列，顺序为: email, id, name
    new_data = pd.DataFrame({
        'email': ['alice@test.com', 'bob@test.com', 'charlie@test.com'],
        'id': [1, 2, 3],
        'name': ['Alice', 'Bob', 'Charlie']
    })
    
    result = table.update_dataframe(new_data)
    print(f"更新结果: {result}")
    
    # 获取更新后的列顺序
    updated_config = table.get_columns_config()
    updated_order = [col['prop'] for col in updated_config['columns']]
    print(f"更新后列顺序: {updated_order}")
    
    # 验证列顺序
    expected_order = list(new_data.columns)
    assert updated_order == expected_order, f"列顺序不匹配！期望: {expected_order}, 实际: {updated_order}"
    
    # 验证 age 列已被删除
    assert 'age' not in updated_order, "age 列应该被删除"
    print("✓ 测试通过：删除列后顺序正确，已删除的列已移除\n")


def test_complex_scenario():
    """测试复杂场景：添加、删除、重排序同时进行"""
    print("=" * 60)
    print("测试 4: 复杂场景（添加、删除、重排序）")
    print("=" * 60)
    
    # 创建初始数据
    initial_data = pd.DataFrame({
        'id': [1, 2, 3],
        'name': ['Alice', 'Bob', 'Charlie'],
        'age': [25, 30, 35]
    })
    
    initial_columns = [
        ColumnConfig(prop='id', label='ID', type='number'),
        ColumnConfig(prop='name', label='Name', type='string'),
        ColumnConfig(prop='age', label='Age', type='number')
    ]
    
    table = DataTable(initial_data, initial_columns)
    
    # 复杂更新：删除 age，添加 email 和 phone，重排序为: phone, email, id, name
    new_data = pd.DataFrame({
        'phone': ['123-456-7890', '234-567-8901', '345-678-9012'],
        'email': ['alice@test.com', 'bob@test.com', 'charlie@test.com'],
        'id': [1, 2, 3],
        'name': ['Alice', 'Bob', 'Charlie']
    })
    
    result = table.update_dataframe(new_data)
    print(f"更新结果: {result}")
    
    # 获取更新后的列顺序
    updated_config = table.get_columns_config()
    updated_order = [col['prop'] for col in updated_config['columns']]
    print(f"更新后列顺序: {updated_order}")
    
    # 验证列顺序
    expected_order = list(new_data.columns)
    assert updated_order == expected_order, f"列顺序不匹配！期望: {expected_order}, 实际: {updated_order}"
    
    # 验证 age 列已被删除
    assert 'age' not in updated_order, "age 列应该被删除"
    
    # 验证新列已添加
    assert 'phone' in updated_order, "phone 列应该存在"
    assert 'email' in updated_order, "email 列应该存在"
    
    print("✓ 测试通过：复杂场景处理正确\n")


def test_get_columns_config_order():
    """测试 get_columns_config 返回的顺序"""
    print("=" * 60)
    print("测试 5: get_columns_config 返回顺序验证")
    print("=" * 60)
    
    # 创建数据，列顺序为: z_col, a_col, m_col
    data = pd.DataFrame({
        'z_col': [1, 2, 3],
        'a_col': ['A', 'B', 'C'],
        'm_col': [10, 20, 30]
    })
    
    columns = [
        ColumnConfig(prop='z_col', label='Z', type='number'),
        ColumnConfig(prop='a_col', label='A', type='string'),
        ColumnConfig(prop='m_col', label='M', type='number')
    ]
    
    table = DataTable(data, columns)
    
    # 获取列配置
    config = table.get_columns_config()
    config_order = [col['prop'] for col in config['columns']]
    print(f"get_columns_config 返回的列顺序: {config_order}")
    
    # 验证顺序与 DataFrame 列顺序一致
    expected_order = list(data.columns)
    assert config_order == expected_order, f"列顺序不匹配！期望: {expected_order}, 实际: {config_order}"
    print("✓ 测试通过：get_columns_config 返回顺序正确\n")


if __name__ == '__main__':
    print("\n开始测试列顺序修复功能...\n")
    
    try:
        test_column_order_preservation()
        test_add_new_columns()
        test_remove_columns()
        test_complex_scenario()
        test_get_columns_config_order()
        
        print("=" * 60)
        print("所有测试通过！✓")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

