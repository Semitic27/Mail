# 邮件缓存存储位置说明 (Mail Cache Storage Location)

## 问题 (Question)

**用户问题**：收取到邮件的邮件内容缓存是保持在服务器的数据库里面吗？

**User Question**: Is the cached email content stored in the server's database?

---

## 答案 (Answer)

### ❌ 不是存储在数据库中 (NOT stored in database)

邮件内容缓存**不是**存储在数据库中，而是存储在 **Flask Session 文件系统**中。

The mail content cache is **NOT** stored in the database, but rather in the **Flask Session filesystem**.

---

## 详细说明 (Detailed Explanation)

### 1. 存储位置 (Storage Location)

邮件缓存使用 Flask Session，配置为文件系统存储模式：

```python
# app.py 配置
app.config['SESSION_TYPE'] = 'filesystem'  # ← 文件系统存储
app.config['SESSION_PERMANENT'] = False
```

**实际存储位置 (Actual storage location)**:
- 默认路径: `flask_session/` 目录
- 文件格式: 二进制 session 文件
- 示例文件名: `2029240f6d1128be89ddc32729463129`

### 2. 存储方式对比 (Storage Comparison)

| 存储方式 | 邮件缓存 | 卡密信息 | 邮箱账号 |
|---------|---------|---------|---------|
| **位置** | Flask Session (文件系统) | SQLite/MySQL 数据库 | SQLite/MySQL 数据库 |
| **路径** | `flask_session/` 目录 | `db/mail.sqlite` | `db/mail.sqlite` |
| **持久性** | 临时（会话结束后删除） | 永久 | 永久 |
| **超时** | 5分钟（可配置） | 无（除非卡密过期） | 无 |

### 3. 为什么不使用数据库？ (Why not use database?)

使用 Flask Session 而不是数据库的原因：

#### ✅ 优势 (Advantages)

1. **自动清理** - Session 会自动过期和清理，无需手动维护
2. **性能更好** - 读写文件比数据库操作更快
3. **隔离性强** - 每个用户的 session 完全隔离
4. **实现简单** - Flask 内置支持，无需额外表结构
5. **不占用数据库** - 避免在数据库中存储大量临时数据

#### ⚠️ 数据库存储的问题 (Database storage issues)

如果使用数据库存储缓存：
- ❌ 需要创建额外的缓存表
- ❌ 需要定期清理过期缓存
- ❌ 增加数据库大小和查询负担
- ❌ 可能影响数据库备份大小
- ❌ 缓存数据可能很大（包含附件等）

---

## 技术细节 (Technical Details)

### 缓存存储代码 (Cache storage code)

```python
# 在 /api/preview_mail 中缓存
cache_key = f"mail_cache_{card_key}_{email}"
session[cache_key] = {
    'mail_data': response_data,  # 完整邮件数据
    'timestamp': time.time()      # 缓存时间戳
}
```

### 缓存读取代码 (Cache retrieval code)

```python
# 在 /api/view_mail 中读取
cache_key = f"mail_cache_{card_key}_{email}"
cached_data = session.get(cache_key)  # 从 session 读取

if cached_data and 'mail_data' in cached_data:
    cache_age = time.time() - cached_data['timestamp']
    if cache_age < MAIL_PREVIEW_CACHE_TIMEOUT:
        use_cache = True  # 使用缓存
```

### Flask Session 文件系统结构 (Filesystem structure)

```
项目根目录/
├── app.py
├── db/
│   └── mail.sqlite          ← 数据库（卡密、邮箱账号等）
├── flask_session/           ← Session 存储目录（邮件缓存）
│   ├── 2029240f6d1128be89ddc32729463129
│   ├── 3f2d8e9c1a4b5d6e7f8a9b0c1d2e3f4g
│   └── ...
└── ...
```

---

## 数据生命周期 (Data Lifecycle)

### 邮件缓存 (Mail Cache - Session)

```
创建 → 5分钟有效期 → 自动过期 → Flask自动清理
  ↓
保存在 flask_session/ 目录
```

### 数据库数据 (Database Data)

```
创建 → 永久存储 → 手动删除
  ↓
保存在 db/mail.sqlite
```

---

## 查看缓存 (View Cache)

### 查看 Session 文件

```bash
# Session 文件位置
ls -lh flask_session/

# 文件内容是二进制加密的，无法直接查看
# Session files are binary and encrypted, cannot view directly
```

### 查看数据库

```bash
# 数据库可以直接查看
sqlite3 db/mail.sqlite "SELECT * FROM cards LIMIT 5;"
```

---

## 配置选项 (Configuration Options)

### 修改缓存超时时间

```bash
# 环境变量配置
export MAIL_PREVIEW_CACHE_TIMEOUT=600  # 10分钟

# 或在 docker-compose.yml
environment:
  - MAIL_PREVIEW_CACHE_TIMEOUT=600
```

### 修改 Session 存储位置

如果需要修改 session 存储位置（高级用户）：

```python
# app.py
app.config['SESSION_FILE_DIR'] = '/path/to/custom/session/dir'
```

---

## 安全性说明 (Security Notes)

### Session 存储安全性

1. **加密**: Session 内容使用 `SECRET_KEY` 加密
2. **权限**: Session 文件只有服务器可以访问
3. **隔离**: 不同用户的 session 完全隔离
4. **自动清理**: 过期 session 自动删除

### 不会泄露数据

- ✅ 客户端无法直接访问 session 文件
- ✅ Session 文件存储在服务器内部
- ✅ 即使获取文件也无法解密（需要 SECRET_KEY）
- ✅ 缓存会自动过期，不会长期保存

---

## 总结 (Summary)

### 关键点 (Key Points)

1. **邮件缓存**: 存储在 Flask Session 文件系统（`flask_session/` 目录）
2. **不在数据库**: 不占用数据库空间
3. **临时存储**: 5分钟后自动过期
4. **自动清理**: Flask 自动管理 session 生命周期
5. **安全可靠**: 加密存储，用户隔离

### 架构对比 (Architecture Comparison)

```
┌─────────────────────────────────────────────┐
│             邮件系统架构                     │
├─────────────────────────────────────────────┤
│                                             │
│  临时数据（缓存）                            │
│  └─ Flask Session (文件系统)                │
│     └─ flask_session/ 目录                  │
│        └─ 邮件内容缓存（5分钟）              │
│                                             │
│  永久数据（数据库）                          │
│  └─ SQLite/MySQL 数据库                     │
│     └─ db/mail.sqlite                       │
│        ├─ 卡密信息（cards 表）              │
│        ├─ 邮箱账号（mail_accounts 表）      │
│        ├─ 使用日志（card_logs 表）          │
│        └─ 最后邮件信息（cards 表字段）      │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 常见问题 (FAQ)

### Q1: 如果服务器重启，缓存会丢失吗？

**A**: 是的，服务器重启后，Flask session 文件会被清理，缓存会丢失。但这不影响功能，因为：
- 卡密信息在数据库中，不会丢失
- 最后邮件信息也在数据库中（`last_mail_subject`、`last_mail_date`）
- 重启后重新获取邮件即可，只是第一次会慢一点

### Q2: 缓存会占用多少磁盘空间？

**A**: 
- 每封邮件缓存: 约 10KB - 1MB（取决于邮件大小）
- Session 文件会自动清理
- 建议监控 `flask_session/` 目录大小

### Q3: 可以改为存储在数据库吗？

**A**: 技术上可以，但不推荐：

```python
# 可以改为数据库存储（不推荐）
app.config['SESSION_TYPE'] = 'sqlalchemy'
```

但这会带来前面提到的所有问题。

### Q4: 缓存文件在哪里？

**A**: 
```bash
# 查看缓存文件
ls -lh flask_session/

# 输出示例:
# -rw-r--r-- 1 user user 45K Feb  7 10:30 2029240f6d1128be89ddc32729463129
# -rw-r--r-- 1 user user 32K Feb  7 10:35 3f2d8e9c1a4b5d6e7f8a9b0c1d2e3f4g
```

---

## 参考文档 (References)

- [Flask Session 官方文档](https://flask.palletsprojects.com/en/latest/quickstart/#sessions)
- [Flask-Session 扩展文档](https://flask-session.readthedocs.io/)
- 相关文档:
  - `FEATURE_TWO_STAGE_MAIL_RETRIEVAL.md` - 两阶段邮件获取功能
  - `MAIL_CACHE_GUIDE.md` - 邮件缓存使用指南
  - `CACHE_IMPLEMENTATION_SUMMARY.md` - 缓存实现总结

---

**创建日期**: 2024-02-07  
**最后更新**: 2024-02-07
