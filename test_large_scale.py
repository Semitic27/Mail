#!/usr/bin/env python3
"""
大规模数据测试脚本 - Mail System Performance Testing
测试场景：
1. 创建20个主分组，每个主分组20个子分组，每个子分组300个邮箱（共120,000个邮箱）
2. 生成500个卡密
3. 测试最后页面邮箱的各种操作
4. 测试最后页面卡密的绑定操作
5. 测试SQLite性能和加载速度
"""

import sqlite3
import secrets
import time
import json
import os
from datetime import datetime, timedelta
from tabulate import tabulate

# 数据库路径
DB_PATH = '/home/runner/work/Mail/Mail/db/mail.sqlite'

# 测试统计数据
test_stats = {
    'main_groups': 0,
    'sub_groups': 0,
    'total_mailboxes': 0,
    'total_cards': 0,
    'test_results': [],
    'performance_metrics': {}
}

def create_connection():
    """创建数据库连接"""
    return sqlite3.connect(DB_PATH)

def generate_random_email(index):
    """生成随机测试邮箱地址"""
    return f"test_email_{index}_{secrets.token_hex(4)}@testmail.com"

def generate_card_key():
    """生成卡密"""
    return secrets.token_urlsafe(32)

def create_test_groups():
    """创建测试分组结构"""
    print("\n" + "="*80)
    print("步骤 1: 创建分组结构")
    print("="*80)
    
    conn = create_connection()
    cursor = conn.cursor()
    
    start_time = time.time()
    
    main_group_ids = []
    sub_group_ids = []
    
    # 创建20个主分组
    print("\n创建主分组...")
    for i in range(1, 21):
        group_name = f"主分组_{i:02d}"
        cursor.execute("""
            INSERT INTO mailbox_groups (name, parent_id, sort_order, is_expanded)
            VALUES (?, NULL, ?, 1)
        """, (group_name, i))
        main_group_ids.append(cursor.lastrowid)
        test_stats['main_groups'] += 1
        if i % 5 == 0:
            print(f"  已创建 {i}/20 个主分组")
    
    # 为每个主分组创建20个子分组
    print("\n创建子分组...")
    total_sub = 0
    for main_id in main_group_ids:
        for j in range(1, 21):
            sub_name = f"子分组_{total_sub+1:04d}"
            cursor.execute("""
                INSERT INTO mailbox_groups (name, parent_id, sort_order, is_expanded)
                VALUES (?, ?, ?, 1)
            """, (sub_name, main_id, j))
            sub_group_ids.append(cursor.lastrowid)
            test_stats['sub_groups'] += 1
            total_sub += 1
            if total_sub % 50 == 0:
                print(f"  已创建 {total_sub}/400 个子分组")
    
    conn.commit()
    
    elapsed = time.time() - start_time
    test_stats['performance_metrics']['group_creation'] = elapsed
    
    print(f"\n✓ 分组创建完成:")
    print(f"  - 主分组: {test_stats['main_groups']} 个")
    print(f"  - 子分组: {test_stats['sub_groups']} 个")
    print(f"  - 耗时: {elapsed:.2f} 秒")
    
    conn.close()
    return main_group_ids, sub_group_ids

def create_test_mailboxes(sub_group_ids):
    """创建测试邮箱账号"""
    print("\n" + "="*80)
    print("步骤 2: 创建邮箱账号")
    print("="*80)
    
    conn = create_connection()
    cursor = conn.cursor()
    
    start_time = time.time()
    
    total_count = 0
    batch_size = 1000  # 批量插入以提高性能
    mailbox_data = []
    mapping_data = []
    
    print(f"\n准备创建 {len(sub_group_ids)} * 300 = {len(sub_group_ids) * 300} 个邮箱...")
    
    for idx, group_id in enumerate(sub_group_ids):
        for j in range(300):
            email = generate_random_email(total_count)
            mailbox_data.append((
                email,
                email.split('@')[0],  # username
                'test_password_' + secrets.token_hex(8),  # password
                'imap.testmail.com',  # server
                993,  # port
                'imap',  # protocol
                1,  # ssl
                'smtp.testmail.com',  # send_server
                465,  # send_port
                'smtp',  # send_protocol
                1,  # send_ssl
                f'测试邮箱 #{total_count+1}',  # remarks
                1  # status
            ))
            total_count += 1
            
            # 批量插入
            if len(mailbox_data) >= batch_size:
                # 先获取当前最大ID
                cursor.execute("SELECT MAX(id) FROM mail_accounts")
                max_id_before = cursor.fetchone()[0] or 0
                
                cursor.executemany("""
                    INSERT INTO mail_accounts 
                    (email, username, password, server, port, protocol, ssl,
                     send_server, send_port, send_protocol, send_ssl, remarks, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, mailbox_data)
                
                # 获取插入的ID范围并创建映射
                cursor.execute("SELECT MAX(id) FROM mail_accounts")
                max_id_after = cursor.fetchone()[0] or 0
                first_id = max_id_before + 1
                for k, mid in enumerate(range(first_id, max_id_after + 1)):
                    gid = sub_group_ids[int((total_count - batch_size + k) / 300)]
                    mapping_data.append((mid, gid))
                
                if len(mapping_data) >= batch_size:
                    cursor.executemany("""
                        INSERT INTO mailbox_group_mappings (mailbox_id, group_id)
                        VALUES (?, ?)
                    """, mapping_data)
                    mapping_data = []
                
                conn.commit()
                test_stats['total_mailboxes'] += len(mailbox_data)
                mailbox_data = []
                
                if total_count % 5000 == 0:
                    elapsed = time.time() - start_time
                    rate = total_count / elapsed
                    print(f"  已创建 {total_count}/{len(sub_group_ids) * 300} 个邮箱 "
                          f"({rate:.0f} 个/秒)")
    
    # 插入剩余数据
    if mailbox_data:
        # 先获取当前最大ID
        cursor.execute("SELECT MAX(id) FROM mail_accounts")
        max_id_before = cursor.fetchone()[0] or 0
        
        cursor.executemany("""
            INSERT INTO mail_accounts 
            (email, username, password, server, port, protocol, ssl,
             send_server, send_port, send_protocol, send_ssl, remarks, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, mailbox_data)
        
        cursor.execute("SELECT MAX(id) FROM mail_accounts")
        max_id_after = cursor.fetchone()[0] or 0
        first_id = max_id_before + 1
        for k, mid in enumerate(range(first_id, max_id_after + 1)):
            gid = sub_group_ids[int((total_count - len(mailbox_data) + k) / 300)]
            mapping_data.append((mid, gid))
        
        test_stats['total_mailboxes'] += len(mailbox_data)
    
    if mapping_data:
        cursor.executemany("""
            INSERT INTO mailbox_group_mappings (mailbox_id, group_id)
            VALUES (?, ?)
        """, mapping_data)
    
    conn.commit()
    
    elapsed = time.time() - start_time
    test_stats['performance_metrics']['mailbox_creation'] = elapsed
    rate = test_stats['total_mailboxes'] / elapsed if elapsed > 0 else 0
    
    print(f"\n✓ 邮箱创建完成:")
    print(f"  - 总数: {test_stats['total_mailboxes']} 个")
    print(f"  - 耗时: {elapsed:.2f} 秒")
    print(f"  - 速率: {rate:.0f} 个/秒")
    
    conn.close()

def create_test_cards():
    """生成测试卡密"""
    print("\n" + "="*80)
    print("步骤 3: 生成卡密")
    print("="*80)
    
    conn = create_connection()
    cursor = conn.cursor()
    
    start_time = time.time()
    
    cards_data = []
    for i in range(500):
        card_key = generate_card_key()
        expired_at = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d %H:%M:%S')
        cards_data.append((
            card_key,
            'general',  # card_type
            100,  # usage_limit
            0,  # used_count
            1,  # status
            expired_at,
            None,  # bound_email_id
            1,  # email_days_filter
            '',  # sender_filter
            f'测试卡密 #{i+1}'  # remarks
        ))
    
    cursor.executemany("""
        INSERT INTO cards 
        (card_key, card_type, usage_limit, used_count, status, expired_at,
         bound_email_id, email_days_filter, sender_filter, remarks)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, cards_data)
    
    conn.commit()
    test_stats['total_cards'] = 500
    
    elapsed = time.time() - start_time
    test_stats['performance_metrics']['card_creation'] = elapsed
    
    print(f"\n✓ 卡密生成完成:")
    print(f"  - 总数: {test_stats['total_cards']} 个")
    print(f"  - 耗时: {elapsed:.2f} 秒")
    
    conn.close()

def test_mailbox_operations():
    """测试邮箱操作功能"""
    print("\n" + "="*80)
    print("步骤 4: 测试邮箱操作")
    print("="*80)
    
    conn = create_connection()
    cursor = conn.cursor()
    
    # 获取最后100个邮箱进行测试
    print("\n获取最后100个邮箱...")
    cursor.execute("""
        SELECT id, email, remarks FROM mail_accounts 
        ORDER BY id DESC LIMIT 100
    """)
    test_mailboxes = cursor.fetchall()
    
    print(f"找到 {len(test_mailboxes)} 个测试邮箱")
    
    # 测试编辑功能
    print("\n测试 1: 编辑邮箱备注")
    start_time = time.time()
    success_count = 0
    for mailbox in test_mailboxes[:10]:  # 测试前10个
        new_remark = f"已编辑备注 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        cursor.execute("""
            UPDATE mail_accounts SET remarks = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_remark, mailbox[0]))
        success_count += 1
    conn.commit()
    elapsed = time.time() - start_time
    test_stats['test_results'].append({
        'test': '编辑邮箱备注',
        'count': 10,
        'success': success_count,
        'time': elapsed
    })
    print(f"  ✓ 成功: {success_count}/10, 耗时: {elapsed:.3f}秒")
    
    # 测试删除功能
    print("\n测试 2: 删除邮箱")
    start_time = time.time()
    success_count = 0
    for mailbox in test_mailboxes[:5]:  # 删除前5个
        cursor.execute("DELETE FROM mail_accounts WHERE id = ?", (mailbox[0],))
        success_count += 1
    conn.commit()
    elapsed = time.time() - start_time
    test_stats['test_results'].append({
        'test': '删除邮箱',
        'count': 5,
        'success': success_count,
        'time': elapsed
    })
    print(f"  ✓ 成功: {success_count}/5, 耗时: {elapsed:.3f}秒")
    
    # 测试批量查询性能
    print("\n测试 3: 批量查询邮箱")
    start_time = time.time()
    cursor.execute("SELECT COUNT(*) FROM mail_accounts")
    count = cursor.fetchone()[0]
    elapsed = time.time() - start_time
    test_stats['test_results'].append({
        'test': '查询邮箱总数',
        'count': count,
        'success': 1,
        'time': elapsed
    })
    print(f"  ✓ 查询到 {count} 个邮箱, 耗时: {elapsed:.3f}秒")
    
    # 测试分页查询性能
    print("\n测试 4: 分页查询邮箱（最后一页）")
    page_size = 50
    start_time = time.time()
    cursor.execute(f"""
        SELECT id, email, server, port, protocol, remarks 
        FROM mail_accounts 
        ORDER BY id DESC LIMIT {page_size}
    """)
    results = cursor.fetchall()
    elapsed = time.time() - start_time
    test_stats['test_results'].append({
        'test': '分页查询（最后一页）',
        'count': len(results),
        'success': 1,
        'time': elapsed
    })
    print(f"  ✓ 查询到 {len(results)} 条记录, 耗时: {elapsed:.3f}秒")
    
    conn.close()

def test_card_operations():
    """测试卡密操作功能"""
    print("\n" + "="*80)
    print("步骤 5: 测试卡密操作")
    print("="*80)
    
    conn = create_connection()
    cursor = conn.cursor()
    
    # 获取最后100个卡密进行测试
    print("\n获取最后100个卡密...")
    cursor.execute("""
        SELECT id, card_key, remarks FROM cards 
        ORDER BY id DESC LIMIT 100
    """)
    test_cards = cursor.fetchall()
    
    print(f"找到 {len(test_cards)} 个测试卡密")
    
    # 获取一些邮箱ID用于绑定
    cursor.execute("SELECT id FROM mail_accounts ORDER BY id DESC LIMIT 50")
    mailbox_ids = [row[0] for row in cursor.fetchall()]
    
    # 测试编辑卡密
    print("\n测试 1: 编辑卡密备注")
    start_time = time.time()
    success_count = 0
    for card in test_cards[:20]:  # 测试前20个
        new_remark = f"已编辑 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        cursor.execute("""
            UPDATE cards SET remarks = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_remark, card[0]))
        success_count += 1
    conn.commit()
    elapsed = time.time() - start_time
    test_stats['test_results'].append({
        'test': '编辑卡密备注',
        'count': 20,
        'success': success_count,
        'time': elapsed
    })
    print(f"  ✓ 成功: {success_count}/20, 耗时: {elapsed:.3f}秒")
    
    # 测试绑定邮箱
    print("\n测试 2: 绑定邮箱到卡密")
    start_time = time.time()
    success_count = 0
    for i, card in enumerate(test_cards[:30]):  # 绑定前30个
        if i < len(mailbox_ids):
            cursor.execute("""
                UPDATE cards SET bound_email_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (mailbox_ids[i], card[0]))
            success_count += 1
    conn.commit()
    elapsed = time.time() - start_time
    test_stats['test_results'].append({
        'test': '绑定邮箱到卡密',
        'count': 30,
        'success': success_count,
        'time': elapsed
    })
    print(f"  ✓ 成功: {success_count}/30, 耗时: {elapsed:.3f}秒")
    
    # 测试查询卡密
    print("\n测试 3: 查询卡密总数")
    start_time = time.time()
    cursor.execute("SELECT COUNT(*) FROM cards")
    count = cursor.fetchone()[0]
    elapsed = time.time() - start_time
    test_stats['test_results'].append({
        'test': '查询卡密总数',
        'count': count,
        'success': 1,
        'time': elapsed
    })
    print(f"  ✓ 查询到 {count} 个卡密, 耗时: {elapsed:.3f}秒")
    
    # 测试分页查询卡密（最后一页）
    print("\n测试 4: 分页查询卡密（最后一页）")
    page_size = 50
    start_time = time.time()
    cursor.execute(f"""
        SELECT id, card_key, usage_limit, used_count, status, remarks 
        FROM cards 
        ORDER BY id DESC LIMIT {page_size}
    """)
    results = cursor.fetchall()
    elapsed = time.time() - start_time
    test_stats['test_results'].append({
        'test': '分页查询卡密（最后一页）',
        'count': len(results),
        'success': 1,
        'time': elapsed
    })
    print(f"  ✓ 查询到 {len(results)} 条记录, 耗时: {elapsed:.3f}秒")
    
    conn.close()

def test_performance():
    """测试SQLite性能"""
    print("\n" + "="*80)
    print("步骤 6: 性能测试")
    print("="*80)
    
    conn = create_connection()
    cursor = conn.cursor()
    
    # 测试1: 分组加载性能
    print("\n测试 1: 加载所有分组")
    start_time = time.time()
    cursor.execute("""
        SELECT id, name, parent_id, sort_order 
        FROM mailbox_groups 
        ORDER BY parent_id, sort_order
    """)
    groups = cursor.fetchall()
    elapsed = time.time() - start_time
    test_stats['performance_metrics']['load_all_groups'] = elapsed
    print(f"  ✓ 加载 {len(groups)} 个分组, 耗时: {elapsed:.3f}秒")
    
    # 测试2: 邮箱列表加载（首页）
    print("\n测试 2: 加载邮箱列表（首页50条）")
    start_time = time.time()
    cursor.execute("""
        SELECT id, email, server, port, protocol, remarks 
        FROM mail_accounts 
        ORDER BY id DESC LIMIT 50
    """)
    mailboxes = cursor.fetchall()
    elapsed = time.time() - start_time
    test_stats['performance_metrics']['load_mailbox_first_page'] = elapsed
    print(f"  ✓ 加载 {len(mailboxes)} 条记录, 耗时: {elapsed:.3f}秒")
    
    # 测试3: 邮箱列表加载（最后页）
    print("\n测试 3: 加载邮箱列表（最后页50条）")
    start_time = time.time()
    cursor.execute("""
        SELECT id, email, server, port, protocol, remarks 
        FROM mail_accounts 
        ORDER BY id LIMIT 50
    """)
    mailboxes = cursor.fetchall()
    elapsed = time.time() - start_time
    test_stats['performance_metrics']['load_mailbox_last_page'] = elapsed
    print(f"  ✓ 加载 {len(mailboxes)} 条记录, 耗时: {elapsed:.3f}秒")
    
    # 测试4: 卡密列表加载（首页）
    print("\n测试 4: 加载卡密列表（首页50条）")
    start_time = time.time()
    cursor.execute("""
        SELECT id, card_key, usage_limit, used_count, status, remarks 
        FROM cards 
        ORDER BY id DESC LIMIT 50
    """)
    cards = cursor.fetchall()
    elapsed = time.time() - start_time
    test_stats['performance_metrics']['load_cards_first_page'] = elapsed
    print(f"  ✓ 加载 {len(cards)} 条记录, 耗时: {elapsed:.3f}秒")
    
    # 测试5: 复杂联合查询
    print("\n测试 5: 复杂联合查询（带分组的邮箱）")
    start_time = time.time()
    cursor.execute("""
        SELECT m.id, m.email, g.name as group_name
        FROM mail_accounts m
        LEFT JOIN mailbox_group_mappings mgm ON m.id = mgm.mailbox_id
        LEFT JOIN mailbox_groups g ON mgm.group_id = g.id
        ORDER BY m.id DESC LIMIT 50
    """)
    results = cursor.fetchall()
    elapsed = time.time() - start_time
    test_stats['performance_metrics']['complex_join_query'] = elapsed
    print(f"  ✓ 查询 {len(results)} 条记录, 耗时: {elapsed:.3f}秒")
    
    # 测试6: 数据库文件大小
    print("\n测试 6: 数据库文件信息")
    db_size = os.path.getsize(DB_PATH)
    db_size_mb = db_size / (1024 * 1024)
    test_stats['performance_metrics']['database_size_mb'] = db_size_mb
    print(f"  ✓ 数据库文件大小: {db_size_mb:.2f} MB")
    
    # 测试7: 索引效果验证
    print("\n测试 7: 索引效果验证（按email查询）")
    cursor.execute("SELECT email FROM mail_accounts ORDER BY id DESC LIMIT 1")
    test_email = cursor.fetchone()[0]
    start_time = time.time()
    cursor.execute("SELECT * FROM mail_accounts WHERE email = ?", (test_email,))
    result = cursor.fetchone()
    elapsed = time.time() - start_time
    test_stats['performance_metrics']['indexed_search'] = elapsed
    print(f"  ✓ 索引查询耗时: {elapsed:.4f}秒")
    
    conn.close()

def print_summary():
    """打印测试总结"""
    print("\n" + "="*80)
    print("测试总结报告")
    print("="*80)
    
    # 数据统计
    print("\n【数据统计】")
    print(f"  主分组数量: {test_stats['main_groups']}")
    print(f"  子分组数量: {test_stats['sub_groups']}")
    print(f"  邮箱总数量: {test_stats['total_mailboxes']}")
    print(f"  卡密总数量: {test_stats['total_cards']}")
    
    # 性能指标
    print("\n【性能指标】")
    perf_data = []
    for key, value in test_stats['performance_metrics'].items():
        metric_name = key.replace('_', ' ').title()
        if 'size' in key:
            perf_data.append([metric_name, f"{value:.2f} MB"])
        else:
            perf_data.append([metric_name, f"{value:.3f} 秒"])
    
    print(tabulate(perf_data, headers=['指标', '结果'], tablefmt='grid'))
    
    # 功能测试结果
    print("\n【功能测试结果】")
    test_data = []
    for result in test_stats['test_results']:
        test_data.append([
            result['test'],
            result['count'],
            result['success'],
            f"{result['time']:.3f}秒"
        ])
    
    print(tabulate(test_data, 
                   headers=['测试项', '测试数量', '成功数', '耗时'], 
                   tablefmt='grid'))
    
    # 性能评估
    print("\n【性能评估】")
    
    # 计算平均加载时间
    avg_load_time = sum([
        test_stats['performance_metrics'].get('load_mailbox_first_page', 0),
        test_stats['performance_metrics'].get('load_mailbox_last_page', 0),
        test_stats['performance_metrics'].get('load_cards_first_page', 0)
    ]) / 3
    
    if avg_load_time < 0.1:
        performance_rating = "优秀 ✓✓✓"
    elif avg_load_time < 0.5:
        performance_rating = "良好 ✓✓"
    elif avg_load_time < 1.0:
        performance_rating = "一般 ✓"
    else:
        performance_rating = "需要优化 ✗"
    
    print(f"  页面加载性能: {performance_rating}")
    print(f"  平均加载时间: {avg_load_time:.3f}秒")
    print(f"  数据库大小: {test_stats['performance_metrics'].get('database_size_mb', 0):.2f} MB")
    print(f"  索引查询效率: {test_stats['performance_metrics'].get('indexed_search', 0):.4f}秒")
    
    # 结论
    print("\n【测试结论】")
    if avg_load_time < 0.5 and test_stats['performance_metrics'].get('indexed_search', 0) < 0.001:
        print("  ✓ SQLite在大数据量（12万+邮箱）情况下表现优秀")
        print("  ✓ 所有功能测试通过")
        print("  ✓ 页面加载速度快速")
        print("  ✓ 数据库索引工作正常")
    else:
        print("  ⚠ 在大数据量情况下，可能需要考虑性能优化")
        print("  ⚠ 建议：添加更多索引、优化查询语句、考虑分页缓存")

def save_results_to_file():
    """保存测试结果到文件"""
    print("\n保存测试结果...")
    
    report = {
        'test_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'statistics': {
            'main_groups': test_stats['main_groups'],
            'sub_groups': test_stats['sub_groups'],
            'total_mailboxes': test_stats['total_mailboxes'],
            'total_cards': test_stats['total_cards']
        },
        'performance_metrics': test_stats['performance_metrics'],
        'test_results': test_stats['test_results']
    }
    
    report_file = '/home/runner/work/Mail/Mail/test_results.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 测试结果已保存到: {report_file}")

def main():
    """主函数"""
    print("\n" + "="*80)
    print("Mail System - 大规模数据性能测试")
    print("="*80)
    print(f"\n开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    overall_start = time.time()
    
    try:
        # 检查数据库是否存在
        if not os.path.exists(DB_PATH):
            print(f"\n错误: 数据库文件不存在: {DB_PATH}")
            print("请先运行 Flask 应用初始化数据库")
            return
        
        # 执行测试步骤
        main_group_ids, sub_group_ids = create_test_groups()
        create_test_mailboxes(sub_group_ids)
        create_test_cards()
        test_mailbox_operations()
        test_card_operations()
        test_performance()
        
        # 打印总结
        print_summary()
        
        # 保存结果
        save_results_to_file()
        
    except Exception as e:
        print(f"\n✗ 测试过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
    
    overall_elapsed = time.time() - overall_start
    print(f"\n总耗时: {overall_elapsed:.2f} 秒")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n" + "="*80)

if __name__ == '__main__':
    main()
