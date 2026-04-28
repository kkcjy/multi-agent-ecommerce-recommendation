# 测试脚本
# bash run_performance_test.sh
# HTML 报告 (可视化图表)
# open reports/baseline_report.html
# JSON 数据 (原始数据)
# cat reports/baseline.json | python -m json.tool

#!/bin/bash

# 🚀 性能测试一键脚本
# 用法: ./run_performance_test.sh

set -e  # 任何命令失败就停止

PROJECT_ROOT="/home/kkcjy/multi-agent-ecommerce-recommendation"
PYTHON_DIR="$PROJECT_ROOT/python"
HOST="http://localhost:8866"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}✗ $1${NC}"
}

# ============================================================================
# 第 1 步: 启动服务
# ============================================================================
log_info "Step 1/6: 启动服务..."
cd "$PYTHON_DIR"

# 检查 8866 端口是否已被占用
if lsof -Pi :8866 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    log_warning "端口 8866 已被占用，杀死现有进程..."
    kill $(lsof -t -i:8866) 2>/dev/null || true
    sleep 1
fi

# 启动服务（后台运行，重定向日志）
python main.py > /tmp/service.log 2>&1 &
SERVICE_PID=$!
log_success "服务已启动 (PID: $SERVICE_PID)"

# 等待服务启动
log_info "等待服务就绪..."
MAX_ATTEMPTS=30
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -s "$HOST/health" > /dev/null 2>&1; then
        log_success "服务已就绪"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
        log_error "服务启动超时"
        kill $SERVICE_PID 2>/dev/null || true
        tail -20 /tmp/service.log
        exit 1
    fi
    sleep 1
done

# ============================================================================
# 第 2 步: 验证服务健康
# ============================================================================
log_info "Step 2/6: 验证服务健康..."
HEALTH=$(curl -s "$HOST/health")
log_success "健康检查: $HEALTH"

# ============================================================================
# 第 3 步: 查看 Prometheus 指标 (示例)
# ============================================================================
log_info "Step 3/6: 查看 Prometheus 指标..."
METRICS=$(curl -s "$HOST/metrics" | head -5)
log_success "获取到 Prometheus 指标:"
echo "$METRICS"

# ============================================================================
# 第 4 步: 测试推荐 API
# ============================================================================
log_info "Step 4/6: 测试推荐 API..."
RESPONSE=$(curl -s -X POST "$HOST/api/v1/recommend" \
    -H "Content-Type: application/json" \
    -d '{"user_id":"test_user_001","scene":"home","num_items":5}')

# 检查响应是否包含 products
if echo "$RESPONSE" | grep -q "products"; then
    log_success "推荐 API 测试成功"
    # 打印简短的响应摘要
    echo "$RESPONSE" | python -m json.tool | head -20
else
    log_warning "推荐 API 返回: $RESPONSE"
fi

# ============================================================================
# 第 5 步: 运行压测
# ============================================================================
cd "$PROJECT_ROOT"
log_info "Step 5/6: 运行性能压测 (这可能需要 30-60 秒)..."

locust -f "$PYTHON_DIR/tests/load_test_locust.py" \
    --host="$HOST" \
    --users=50 \
    --spawn-rate=5 \
    --run-time=30s \
    --headless

log_success "压测完成"

# ============================================================================
# 第 6 步: 处理数据并生成报告
# ============================================================================
log_info "Step 6/6: 生成性能报告..."

# 找到最新的 JSON 报告
LATEST_JSON=$(ls -t reports/baseline.json 2>/dev/null | head -1)

if [ -n "$LATEST_JSON" ]; then
    log_success "找到压测数据: $LATEST_JSON"
    
    # 生成 HTML 报告
    python "$PYTHON_DIR/reports/generate_perf_report.py" \
        "$PROJECT_ROOT/reports/baseline.json" \
        "$PROJECT_ROOT/reports/baseline_report.html"
    
    log_success "HTML 报告已生成: $PROJECT_ROOT/reports/baseline_report.html"
    
    # 打印数据摘要
    echo ""
    echo -e "${BLUE}📊 性能数据摘要:${NC}"
    cat "$PROJECT_ROOT/reports/baseline.json" | python -m json.tool | grep -E '(total_requests|error_rate|avg_latency)' | head -5
else
    log_warning "未找到压测数据文件"
fi

# ============================================================================
# 清理 (可选：如果需要保持服务运行，注释掉下面的代码)
# ============================================================================
# log_info "清理..."
# if kill $SERVICE_PID 2>/dev/null; then
#     log_success "服务已停止"
# fi
#
# 服务保持运行，PID: $SERVICE_PID

# ============================================================================
# 完成
# ============================================================================
echo ""
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}✨ 性能测试完成！${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}📈 输出文件:${NC}"
echo "  • 原始数据: $PROJECT_ROOT/reports/baseline.json"
echo "  • HTML 报告: $PROJECT_ROOT/reports/baseline_report.html"
echo ""
echo -e "${BLUE}📝 后续操作:${NC}"
echo "  1. 打开 HTML 报告查看图表:"
echo "     open $PROJECT_ROOT/reports/baseline_report.html"
echo ""
echo "  2. 查看 JSON 数据:"
echo "     cat $PROJECT_ROOT/reports/baseline.json | python -m json.tool"
echo ""
