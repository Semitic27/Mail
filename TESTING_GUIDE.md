# 性能优化测试指南

## 测试前准备

### 1. 备份数据库
在测试前，请先备份您的数据库：

```bash
# SQLite
cp mail.db mail.db.backup

# MySQL
mysqldump -u username -p database_name > backup.sql

# PostgreSQL
pg_dump -U username database_name > backup.sql
```

### 2. 更新代码
```bash
git pull origin main
```

### 3. 重启应用
```bash
# 如果使用Docker
docker-compose restart

# 如果直接运行
python app.py
```

## 测试场景

### 场景1: 大量邮箱账号（推荐10,000+条测试）

#### 测试步骤：
1. 访问邮箱管理页面
2. 观察页面加载速度
3. 在搜索框中输入搜索内容
4. 观察搜索响应速度
5. 点击"编辑"按钮，观察邮箱选择模态框打开速度
6. 在邮箱选择模态框中搜索邮箱

#### 预期结果：
- ✅ 页面加载时间 < 0.5秒
- ✅ 搜索响应时间 < 0.3秒
- ✅ 模态框打开时间 < 0.1秒
- ✅ 模态框搜索响应时间 < 0.3秒

#### 实际测试记录：
```
测试日期: __________
数据量: __________ 条邮箱
页面加载: __________ 秒
搜索响应: __________ 秒
模态框打开: __________ 秒
模态框搜索: __________ 秒
```

### 场景2: 大量卡密（推荐5,000+条测试）

#### 测试步骤：
1. 访问卡密管理页面
2. 观察页面加载速度
3. 点击"编辑"按钮
4. 点击"选择邮箱"按钮
5. 在邮箱选择框中搜索并选择邮箱

#### 预期结果：
- ✅ 卡密列表加载时间 < 0.5秒
- ✅ 编辑弹窗打开时间 < 0.2秒
- ✅ 邮箱选择模态框打开时间 < 0.1秒
- ✅ 邮箱搜索响应时间 < 0.3秒

#### 实际测试记录：
```
测试日期: __________
数据量: __________ 条卡密
列表加载: __________ 秒
编辑弹窗: __________ 秒
选择邮箱: __________ 秒
搜索响应: __________ 秒
```

### 场景3: 大量代理（推荐1,000+条测试）

#### 测试步骤：
1. 访问代理池管理页面
2. 观察HTTP代理列表加载速度
3. 观察SOCKS5代理列表加载速度
4. 测试搜索功能

#### 预期结果：
- ✅ HTTP代理列表加载 < 0.4秒
- ✅ SOCKS5代理列表加载 < 0.4秒
- ✅ 搜索响应时间 < 0.3秒

#### 实际测试记录：
```
测试日期: __________
HTTP代理数量: __________
SOCKS5代理数量: __________
HTTP列表加载: __________ 秒
SOCKS5列表加载: __________ 秒
搜索响应: __________ 秒
```

## 数据库索引验证

### SQLite
```sql
-- 查看mail_accounts表的索引
SELECT name, sql FROM sqlite_master 
WHERE type='index' AND tbl_name='mail_accounts';

-- 预期看到以下索引：
-- idx_mail_accounts_email
-- idx_mail_accounts_id_email
-- idx_mail_accounts_server_status
-- idx_mail_accounts_search
-- 等等
```

### MySQL
```sql
-- 查看mail_accounts表的索引
SHOW INDEX FROM mail_accounts;

-- 预期看到优化索引
```

### PostgreSQL
```sql
-- 查看mail_accounts表的索引
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'mail_accounts';
```

## 性能对比测试

### 使用浏览器开发者工具

1. 打开浏览器开发者工具 (F12)
2. 切换到 Network 标签
3. 清除缓存并刷新页面
4. 记录以下数据：

#### API请求耗时
```
/admin/api/mailbox?fast=1&per_page=100
- 请求耗时: __________ ms
- 数据大小: __________ KB

/admin/api/mailbox/search?q=test
- 请求耗时: __________ ms
- 数据大小: __________ KB

/admin/api/cards?page=1&per_page=30
- 请求耗时: __________ ms
- 数据大小: __________ KB
```

## 压力测试（可选）

使用Apache Bench (ab) 进行压力测试：

```bash
# 测试邮箱列表API
ab -n 100 -c 10 "http://localhost:8005/admin/api/mailbox?fast=1&per_page=100"

# 测试邮箱搜索API
ab -n 100 -c 10 "http://localhost:8005/admin/api/mailbox/search?q=test"

# 测试卡密列表API
ab -n 100 -c 10 "http://localhost:8005/admin/api/cards?page=1&per_page=30"
```

### 预期结果：
- 平均响应时间 < 200ms
- 95%请求完成时间 < 500ms
- 无失败请求

## 回滚方案

如果测试发现问题，可以使用以下方式回滚：

### 1. 恢复代码
```bash
git checkout main
```

### 2. 恢复数据库
```bash
# SQLite
cp mail.db.backup mail.db

# MySQL
mysql -u username -p database_name < backup.sql

# PostgreSQL
psql -U username -d database_name < backup.sql
```

### 3. 重启应用
```bash
python app.py
```

## 常见问题排查

### 问题1: 索引未创建成功
**检查方法：**
```bash
# 查看应用日志
tail -f logs/app.log

# 查找索引创建日志
grep "index" logs/app.log
```

**解决方法：**
手动执行 `db/upgrade_performance.sql` 脚本

### 问题2: 查询仍然缓慢
**可能原因：**
- 数据库文件碎片化
- 磁盘IO瓶颈
- 内存不足

**解决方法：**
```sql
-- SQLite
VACUUM;
ANALYZE;

-- 或考虑迁移到MySQL/PostgreSQL
```

### 问题3: 搜索功能不工作
**检查方法：**
```bash
# 测试搜索API
curl "http://localhost:8005/admin/api/mailbox/search?q=test"
```

**预期返回：**
```json
{
  "success": true,
  "data": [...],
  "pagination": {...}
}
```

## 性能监控建议

### 长期监控指标
1. **API响应时间**
   - 目标: 95%请求 < 500ms
   - 监控工具: New Relic, Datadog, 或自建监控

2. **数据库查询时间**
   - 目标: 平均查询 < 100ms
   - 监控方法: 数据库慢查询日志

3. **页面加载时间**
   - 目标: < 1秒
   - 监控工具: Google Analytics, 浏览器性能API

### 定期维护
- 每周: 检查慢查询日志
- 每月: 执行 VACUUM ANALYZE (SQLite)
- 每季度: 评估是否需要添加新索引或优化现有查询

## 反馈与改进

测试完成后，请记录您的反馈：

### 性能改善
```
□ 页面加载速度明显提升
□ 搜索响应速度明显提升
□ 编辑操作更加流畅
□ 整体用户体验改善
```

### 遇到的问题
```
1. __________________________________________
2. __________________________________________
3. __________________________________________
```

### 改进建议
```
1. __________________________________________
2. __________________________________________
3. __________________________________________
```

---
测试完成日期: __________
测试人员: __________
签名: __________
