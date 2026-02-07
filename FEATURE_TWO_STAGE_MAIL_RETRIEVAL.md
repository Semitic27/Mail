# Two-Stage Mail Retrieval Feature

## 问题描述 (Problem Description)

在原有的API取件页面中，客户使用API链接点击了获取邮件并且收到了邮件，但是客户直接关闭了页面，导致使用次数已经被扣除，但邮件内容没有被查看。

In the original API mail pickup page, when customers used the API link to click "get mail" and received the mail, but directly closed the page, the usage count was deducted even though the mail content was not viewed.

## 解决方案 (Solution)

实现了一个两阶段的邮件获取流程：

Implemented a two-stage mail retrieval flow:

### 第一阶段：邮件预览 (Stage 1: Mail Preview)
- 点击"获取邮件"按钮时，调用 `/api/preview_mail` 接口
- 只返回邮件的标题、发件人和时间
- **不扣除使用次数**

When clicking the "Get Mail" button, calls the `/api/preview_mail` endpoint
- Returns only the mail's subject, sender, and time
- **Does NOT deduct usage count**

### 第二阶段：查看完整邮件 (Stage 2: View Full Mail)
- 显示预览后，用户点击"查看完整邮件"按钮
- 调用 `/api/view_mail` 接口
- 返回完整的邮件内容（正文、附件、图片等）
- **只有当邮件是新邮件时才扣除使用次数**

After showing the preview, user clicks "View Full Mail" button
- Calls the `/api/view_mail` endpoint
- Returns complete mail content (body, attachments, images, etc.)
- **Only deducts usage count if it's a NEW mail**

### 邮件比对逻辑 (Mail Comparison Logic)

为了判断是否是同一封邮件，系统使用以下优先级进行比较：

To determine if it's the same mail, the system uses the following priority for comparison:

1. **首选方式：Message-ID** (Preferred: Message-ID)
   - 使用邮件头部的 `Message-ID` 字段进行比较
   - 这是最可靠的方式，因为每封邮件都有唯一的 Message-ID
   
   Uses the `Message-ID` field from email headers for comparison
   This is the most reliable method as each email has a unique Message-ID

2. **降级方式：主题+时间** (Fallback: Subject + Date)
   - 如果 Message-ID 不可用，则使用邮件主题和时间的组合
   - 比较 `last_mail_subject` 和 `last_mail_date`
   
   If Message-ID is unavailable, uses combination of subject and date
   Compares `last_mail_subject` and `last_mail_date`

## 数据库变更 (Database Changes)

在 `cards` 表中添加了三个新字段：

Added three new columns to the `cards` table:

```sql
ALTER TABLE cards ADD COLUMN last_mail_subject TEXT DEFAULT '';
ALTER TABLE cards ADD COLUMN last_mail_date TEXT DEFAULT '';
ALTER TABLE cards ADD COLUMN last_mail_message_id TEXT DEFAULT '';
```

### 字段说明 (Column Description)

- `last_mail_subject`: 最后获取的邮件主题
- `last_mail_date`: 最后获取的邮件时间
- `last_mail_message_id`: 最后获取的邮件 Message-ID（用于精确比对）

## API 接口 (API Endpoints)

### 1. `/api/preview_mail` (POST)

预览邮件接口 - 不扣除使用次数

Preview mail endpoint - Does NOT deduct usage count

**请求参数 (Request Parameters):**
```json
{
  "email": "user@example.com",
  "card_key": "CARD_KEY_123"
}
```

**响应示例 (Response Example):**
```json
{
  "success": true,
  "preview": {
    "subject": "邮件主题",
    "from": "发件人 <sender@example.com>",
    "date": "2024-01-01 10:00:00"
  },
  "card_info": {
    "remaining_uses": 4,
    "total_uses": 5,
    "used_count": 1
  },
  "proxy": {
    "enabled": false
  }
}
```

### 2. `/api/view_mail` (POST)

查看完整邮件接口 - 仅对新邮件扣除使用次数

View full mail endpoint - Only deducts count for NEW mails

**请求参数 (Request Parameters):**
```json
{
  "email": "user@example.com",
  "card_key": "CARD_KEY_123"
}
```

**响应示例 (Response Example):**
```json
{
  "success": true,
  "mail": {
    "subject": "邮件主题",
    "from": "发件人 <sender@example.com>",
    "to": "user@example.com",
    "date": "2024-01-01 10:00:00",
    "message_id": "<unique-message-id@example.com>",
    "body": "邮件正文内容",
    "body_type": "html",
    "images": [],
    "attachments": []
  },
  "card_info": {
    "remaining_uses": 3,
    "total_uses": 5,
    "used_count": 2,
    "count_deducted": true
  },
  "proxy": {
    "enabled": false
  }
}
```

**如果是同一封邮件 (If same mail):**
```json
{
  "card_info": {
    "remaining_uses": 3,
    "total_uses": 5,
    "used_count": 2,
    "count_deducted": false,
    "is_same_mail": true
  }
}
```

## 前端变更 (Frontend Changes)

### 1. 新增邮件预览卡片 (New Mail Preview Card)

```html
<div class="mail-preview" id="mailPreview">
  <div class="preview-header">
    <h3>📬 邮件预览</h3>
    <p class="preview-hint">点击"查看完整邮件"按钮将扣除使用次数（仅限新邮件）</p>
  </div>
  <div class="preview-content">
    <!-- 邮件主题、发件人、时间 -->
  </div>
  <div class="preview-actions">
    <button onclick="viewFullMail()">查看完整邮件</button>
  </div>
</div>
```

### 2. 更新的工作流程 (Updated Workflow)

1. 用户点击"获取邮件" → 显示邮件预览（无扣费）
2. 用户点击"查看完整邮件" → 显示完整邮件（新邮件才扣费）
3. 如果再次获取同一封邮件，系统识别后不再扣费

1. User clicks "Get Mail" → Show mail preview (no charge)
2. User clicks "View Full Mail" → Show complete mail (charge only for new mail)
3. If getting the same mail again, system recognizes and doesn't charge

## 测试 (Testing)

运行测试脚本验证功能：

Run test script to verify functionality:

```bash
python3 /tmp/test_mail_api.py
python3 /tmp/test_workflow.py
```

### 测试场景 (Test Scenarios)

1. ✅ 预览邮件不扣除使用次数
2. ✅ 首次查看邮件扣除使用次数
3. ✅ 再次查看同一封邮件不扣除使用次数
4. ✅ 查看不同邮件扣除使用次数
5. ✅ 数据库正确记录最后邮件信息

## 向后兼容性 (Backward Compatibility)

- 原有的 `/api/get_mail` 接口保持不变
- 数据库迁移自动添加新字段，不影响现有数据
- 旧卡密自动获得新字段，初始值为空字符串

The original `/api/get_mail` endpoint remains unchanged
Database migration automatically adds new columns without affecting existing data
Old cards automatically get new columns with empty string as initial value

## 安全性考虑 (Security Considerations)

1. 所有API接口都需要有效的卡密验证
2. 卡密状态、过期时间、使用次数限制仍然有效
3. 绑定邮箱的验证逻辑保持不变

All API endpoints require valid card key validation
Card status, expiration time, and usage limit checks remain in effect
Bound email validation logic remains unchanged

## 性能影响 (Performance Impact)

- 预览阶段只解析邮件头部，速度快
- 完整邮件加载与原来相同
- 数据库增加三个TEXT字段，影响微乎其微

Preview stage only parses email headers, which is fast
Full mail loading is the same as before
Database adds three TEXT columns with minimal impact

## 未来改进建议 (Future Improvements)

~~1. 可以考虑在预览阶段缓存邮件内容，减少第二次请求~~ ✅ **已实现**
~~2. 可以添加预览超时机制，超时后需重新获取~~ ✅ **已实现**
3. 可以添加统计功能，跟踪预览转化率

~~Consider caching mail content during preview stage to reduce second request~~ ✅ **Implemented**
~~Could add preview timeout mechanism requiring re-fetch after timeout~~ ✅ **Implemented**
Could add analytics to track preview-to-view conversion rate

---

## 邮件缓存机制 (Mail Caching Mechanism) - 新增功能

### 功能说明 (Feature Description)

为了优化性能和用户体验，系统在预览阶段缓存完整的邮件内容，当用户点击"查看完整邮件"时，如果缓存仍然有效，直接返回缓存的数据，避免重复请求邮件服务器。

To optimize performance and user experience, the system caches complete mail content during the preview stage. When users click "View Full Mail", if the cache is still valid, the system returns cached data directly, avoiding redundant mail server requests.

### 缓存机制详情 (Cache Mechanism Details)

#### 1. 缓存时机 (When to Cache)
- 用户调用 `/api/preview_mail` 时，系统获取完整邮件内容并缓存
- 缓存存储在 Flask session 中，每个卡密+邮箱组合有独立的缓存
- When users call `/api/preview_mail`, the system fetches complete mail content and caches it
- Cache is stored in Flask session, each card+email combination has independent cache

#### 2. 缓存键格式 (Cache Key Format)
```python
cache_key = f"mail_cache_{card_key}_{email}"
# 例如: mail_cache_CARD123_user@example.com
```

#### 3. 缓存内容 (Cached Content)
```python
{
    'mail_data': {
        'success': True,
        'mail': { /* 完整邮件数据 */ },
        'proxy': { /* 代理信息 */ }
    },
    'timestamp': 1234567890.123  # Unix 时间戳
}
```

#### 4. 缓存超时 (Cache Timeout)
- **默认超时时间**: 5 分钟 (300 秒)
- **配置方式**: 通过环境变量 `MAIL_PREVIEW_CACHE_TIMEOUT` 设置
- **Default timeout**: 5 minutes (300 seconds)
- **Configuration**: Set via environment variable `MAIL_PREVIEW_CACHE_TIMEOUT`

```bash
# 设置缓存超时为10分钟
export MAIL_PREVIEW_CACHE_TIMEOUT=600
```

#### 5. 缓存验证 (Cache Validation)
在 `/api/view_mail` 中，系统会：
1. 检查缓存是否存在
2. 计算缓存年龄 (当前时间 - 缓存时间戳)
3. 如果缓存年龄 < 超时时间，使用缓存
4. 如果缓存过期，重新获取邮件并更新缓存

In `/api/view_mail`, the system will:
1. Check if cache exists
2. Calculate cache age (current time - cached timestamp)
3. Use cache if age < timeout
4. Re-fetch mail if cache expired

#### 6. 缓存清理 (Cache Cleanup)
- 过期的缓存会在检测时自动从 session 中删除
- Flask session 会自动管理session文件的生命周期
- Expired cache is automatically removed from session when detected
- Flask session automatically manages session file lifecycle

### API 响应变化 (API Response Changes)

#### `/api/preview_mail` 响应
新增 `cached` 字段表示内容已被缓存:
```json
{
    "success": true,
    "preview": { /* ... */ },
    "cached": true  // 新增：表示已缓存完整内容
}
```

#### `/api/view_mail` 响应
新增 `from_cache` 字段表示是否使用了缓存:
```json
{
    "success": true,
    "mail": { /* ... */ },
    "card_info": {
        "remaining_uses": 3,
        "from_cache": true  // 新增：true表示使用缓存，false表示重新获取
    }
}
```

### 性能优势 (Performance Benefits)

1. **减少服务器负载**: 避免重复连接邮件服务器
2. **加快响应速度**: 从session读取比从邮件服务器获取快得多
3. **改善用户体验**: 点击"查看完整邮件"后几乎瞬间显示内容

1. **Reduced server load**: Avoids repeated mail server connections
2. **Faster response**: Reading from session is much faster than fetching from mail server
3. **Better UX**: Almost instant display after clicking "View Full Mail"

### 日志记录 (Logging)

系统会记录缓存使用情况:
```
INFO: Using cached mail content for CARD123, age: 45.2s
INFO: Cache expired for CARD456, age: 310.5s
INFO: Fetching mail from server for CARD789
```

### 安全考虑 (Security Considerations)

1. **Session 隔离**: 每个用户的 session 是独立的，缓存不会跨用户共享
2. **自动过期**: 缓存有时间限制，防止显示过时内容
3. **卡密绑定**: 缓存键包含卡密，确保不同卡密不会互相访问缓存

1. **Session isolation**: Each user's session is independent, cache not shared across users
2. **Auto expiration**: Cache has time limit to prevent showing outdated content
3. **Card binding**: Cache key includes card key to ensure different cards don't access each other's cache

