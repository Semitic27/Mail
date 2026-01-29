#!/usr/bin/env python3
"""
Web界面测试脚本 - 使用Playwright测试Web界面功能
"""

import subprocess
import time
import json
import sys

def start_flask_server():
    """启动Flask服务器"""
    print("启动Flask服务器...")
    proc = subprocess.Popen(
        ['python', 'app.py'],
        cwd='/home/runner/work/Mail/Mail',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    # 等待服务器启动
    time.sleep(5)
    return proc

def test_with_browser():
    """使用浏览器测试（如果有Playwright的话）"""
    print("\n尝试使用浏览器测试...")
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # 测试管理后台登录
            print("测试管理后台...")
            page.goto('http://localhost:8005/admin')
            page.screenshot(path='/home/runner/work/Mail/Mail/screenshots/admin_login.png')
            
            # 登录
            page.fill('input[name="username"]', 'admin')
            page.fill('input[name="password"]', 'admin')
            page.click('button[type="submit"]')
            time.sleep(2)
            
            # 测试邮箱列表页
            print("测试邮箱列表页...")
            page.goto('http://localhost:8005/admin/mailbox')
            page.screenshot(path='/home/runner/work/Mail/Mail/screenshots/mailbox_list.png')
            
            # 测试卡密列表页
            print("测试卡密列表页...")
            page.goto('http://localhost:8005/admin/kami')
            page.screenshot(path='/home/runner/work/Mail/Mail/screenshots/kami_list.png')
            
            browser.close()
            print("✓ 浏览器测试完成")
            return True
    except ImportError:
        print("⚠ Playwright未安装，跳过浏览器测试")
        return False
    except Exception as e:
        print(f"⚠ 浏览器测试失败: {str(e)}")
        return False

def main():
    """主函数"""
    print("="*80)
    print("Web界面功能测试")
    print("="*80)
    
    # 启动服务器
    server_proc = start_flask_server()
    
    try:
        # 测试浏览器
        test_with_browser()
        
    finally:
        # 停止服务器
        print("\n停止Flask服务器...")
        server_proc.terminate()
        server_proc.wait()
    
    print("\n测试完成")

if __name__ == '__main__':
    main()
