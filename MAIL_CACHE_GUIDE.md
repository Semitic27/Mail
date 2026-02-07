# 邮件缓存功能使用指南

## 功能概述

邮件缓存功能在预览阶段缓存完整邮件内容，当用户查看完整邮件时，如果缓存仍有效，直接返回缓存数据，避免重复请求邮件服务器。

## 使用流程

### 1. 预览邮件（缓存内容）

```bash
# 请求预览
POST /api/preview_mail
{
    "email": "user@example.com",
    "card_key": "YOUR_CARD_KEY"
}

# 响应（包含 cached: true 表示已缓存）
{
    "success": true,
    "preview": {
        "subject": "邮件主题",
        "from": "发件人 <sender@example.com>",
        "date": "2024-01-01 10:00:00"
    },
    "cached": true,  // 标识已缓存完整内容
    "card_info": {
        "remaining_uses": 4,
        "total_uses": 5
    }
}
```

### 2. 查看完整邮件（使用缓存）

```bash
# 请求查看（5分钟内）
POST /api/view_mail
{
    "email": "user@example.com",
    "card_key": "YOUR_CARD_KEY"
}

# 响应（from_cache: true 表示使用了缓存）
{
    "success": true,
    "mail": {
        "subject": "邮件主题",
        "from": "发件人 <sender@example.com>",
        "body": "完整邮件内容...",
        "attachments": [...]
    },
    "card_info": {
        "remaining_uses": 3,
        "from_cache": true,  // 标识使用了缓存，响应更快
        "count_deducted": true
    }
}
```

### 3. 缓存过期后（重新获取）

```bash
# 5分钟后再次请求查看
POST /api/view_mail
{
    "email": "user@example.com",
    "card_key": "YOUR_CARD_KEY"
}

# 响应（from_cache: false 表示重新获取）
{
    "success": true,
    "mail": { ... },
    "card_info": {
        "from_cache": false,  // 缓存过期，重新从服务器获取
        "count_deducted": false,  // 如果是同一封邮件，仍不扣费
        "is_same_mail": true
    }
}
```

## 配置选项

### 设置缓存超时时间

通过环境变量配置缓存超时时间（单位：秒）：

```bash
# 设置为10分钟
export MAIL_PREVIEW_CACHE_TIMEOUT=600

# 设置为30秒（用于测试）
export MAIL_PREVIEW_CACHE_TIMEOUT=30

# 默认值：300秒（5分钟）
```

### Docker 部署配置

在 docker-compose.yml 中添加环境变量：

```yaml
services:
  mail-app:
    image: your-mail-app
    environment:
      - MAIL_PREVIEW_CACHE_TIMEOUT=600  # 10分钟
```

## 性能对比

| 操作 | 无缓存 | 有缓存 | 提升 |
|------|--------|--------|------|
| 预览邮件 | ~2-3秒 | ~2-3秒 | - |
| 查看完整邮件 | ~2-3秒 | ~0.1秒 | 20-30倍 |
| 总体用户体验 | 4-6秒 | 2-3秒 | 快50%+ |

## 缓存行为说明

### 何时创建缓存？
- 调用 `/api/preview_mail` 时自动创建

### 何时使用缓存？
- 调用 `/api/view_mail` 时，如果缓存存在且未过期

### 何时清除缓存？
- 缓存过期后（超过配置的超时时间）
- Flask session 生命周期结束时
- 手动调用预览接口时会刷新缓存

### 缓存隔离
- 每个 `card_key` + `email` 组合有独立的缓存
- 不同用户的缓存完全隔离
- 同一用户不同邮箱的缓存也是独立的

## 日志示例

系统会自动记录缓存使用情况：

```log
INFO: Using cached mail content for CARD123, age: 45.2s
INFO: Cache expired for CARD456, age: 310.5s  
INFO: Fetching mail from server for CARD789
```

## 故障排查

### 问题：缓存未生效

**检查项：**
1. 确认先调用了 `/api/preview_mail`
2. 确认 `card_key` 和 `email` 参数一致
3. 检查缓存是否过期（查看日志）
4. 确认 Flask session 配置正确

### 问题：缓存时间太短/太长

**解决方案：**
调整 `MAIL_PREVIEW_CACHE_TIMEOUT` 环境变量

```bash
# 查看当前配置
python3 -c "from app import MAIL_PREVIEW_CACHE_TIMEOUT; print(f'Timeout: {MAIL_PREVIEW_CACHE_TIMEOUT}s')"

# 临时修改（当前会话）
export MAIL_PREVIEW_CACHE_TIMEOUT=600

# 永久修改（添加到 .env 或系统环境变量）
echo "MAIL_PREVIEW_CACHE_TIMEOUT=600" >> .env
```

## 最佳实践

1. **合理设置超时时间**
   - 开发环境：30-60秒（便于测试）
   - 生产环境：300-600秒（5-10分钟）

2. **监控缓存效果**
   - 定期查看日志中的缓存命中率
   - 根据实际情况调整超时时间

3. **用户提示**
   - 在前端显示"使用缓存"提示，让用户知道响应快的原因
   - 提示用户在缓存有效期内查看邮件可获得更快响应

## 技术细节

### 缓存存储
- 使用 Flask session（filesystem 模式）
- 每个 session 独立存储
- 自动序列化/反序列化

### 缓存键格式
```python
cache_key = f"mail_cache_{card_key}_{email}"
# 例如: mail_cache_ABC123_user@example.com
```

### 缓存数据结构
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

## 安全性

1. **Session 隔离**：每个用户的缓存独立，不会互相访问
2. **自动过期**：防止显示过时内容
3. **卡密绑定**：缓存键包含卡密，确保访问权限
4. **无跨用户风险**：Flask session 机制保证安全性

## 更新历史

- **v1.1.0** (2024-02): 新增邮件缓存功能
  - 支持预览阶段缓存
  - 支持自定义超时时间
  - 优化响应速度 20-30倍
