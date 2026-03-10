@echo off
chcp 65001 >nul
REM 股票分析报告定时清理任务
REM 将此脚本配置到 Windows 任务计划程序，设置每天 23:59:59 执行

cd /d "%~dp0"

REM 执行报告清理任务
python -m app.tasks.cleanup_reports
