"""
用于将 Locust 压测的 JSON 输出转换为 HTML 可视化报告。
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Any


def generate_html_report(json_data: dict[str, Any], output_file: str):
    """从性能数据生成 HTML 报告."""
    
    total_requests = json_data.get("total_requests", 0)
    total_failures = json_data.get("total_failures", 0)
    error_rate = json_data.get("error_rate_percent", 0)
    avg_latency = json_data.get("avg_latency_ms", 0)
    requests = json_data.get("requests", [])
    timestamp = json_data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # 准备数据用于图表
    endpoints = [r["endpoint"] for r in requests]
    avg_latencies = [r["avg_latency_ms"] for r in requests]
    p95_latencies = [r["p95_latency_ms"] for r in requests]
    error_rates = [r["error_rate"] for r in requests]
    
    # 生成 HTML
    html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>性能测试报告</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }}
        
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .timestamp {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .metric-card {{
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s;
        }}
        
        .metric-card:hover {{
            transform: translateY(-5px);
        }}
        
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }}
        
        .metric-label {{
            font-size: 0.9em;
            color: #555;
        }}
        
        .chart-section {{
            margin-bottom: 40px;
        }}
        
        .chart-section h2 {{
            font-size: 1.5em;
            margin-bottom: 20px;
            color: #333;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        
        .chart-container {{
            position: relative;
            height: 400px;
            margin-bottom: 30px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        
        thead {{
            background: #f5f7fa;
            color: #333;
        }}
        
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        tr:hover {{
            background: #f9f9f9;
        }}
        
        .footer {{
            background: #f5f7fa;
            padding: 20px;
            text-align: center;
            color: #999;
            font-size: 0.9em;
        }}
        
        .status-healthy {{
            color: #4caf50;
        }}
        
        .status-warning {{
            color: #ff9800;
        }}
        
        .status-critical {{
            color: #f44336;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚀 性能测试报告</h1>
            <p class="timestamp">生成时间: {timestamp}</p>
        </header>
        
        <div class="content">
            <!-- 关键指标卡片 -->
            <section class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">总请求数</div>
                    <div class="metric-value">{total_requests}</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">失败请求</div>
                    <div class="metric-value">{total_failures}</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">错误率</div>
                    <div class="metric-value status-{'healthy' if error_rate < 1 else 'warning' if error_rate < 5 else 'critical'}">{error_rate:.2f}%</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">平均延迟</div>
                    <div class="metric-value">{avg_latency:.1f}ms</div>
                </div>
            </section>
            
            <!-- 详细表格 -->
            <section class="chart-section">
                <h2>📋 详细指标表</h2>
                <table>
                    <thead>
                        <tr>
                            <th>端点</th>
                            <th>方法</th>
                            <th>请求数</th>
                            <th>错误数</th>
                            <th>错误率</th>
                            <th>平均延迟 (ms)</th>
                            <th>P50 (ms)</th>
                            <th>P95 (ms)</th>
                            <th>P99 (ms)</th>
                        </tr>
                    </thead>
                    <tbody>
"""
    
    for req in requests:
        error_rate_val = req.get("error_rate", 0)
        status_class = "status-healthy" if error_rate_val < 1 else "status-warning" if error_rate_val < 5 else "status-critical"
        html += f"""
                        <tr>
                            <td>{req['endpoint']}</td>
                            <td>{req['method']}</td>
                            <td>{req['requests']}</td>
                            <td>{req['failures']}</td>
                            <td class="{status_class}">{error_rate_val:.2f}%</td>
                            <td>{req['avg_latency_ms']:.1f}</td>
                            <td>{req['p50_latency_ms']:.1f}</td>
                            <td>{req['p95_latency_ms']:.1f}</td>
                            <td>{req['p99_latency_ms']:.1f}</td>
                        </tr>
"""
    
    html += """
                    </tbody>
                </table>
            </section>
        </div>
        
        <div class="footer">
            <p>💡 建议: 用于性能优化前后的对比分析。请保存两个报告副本进行对比。</p>
        </div>
    </div>
    
    <script>
        // 延迟对比图表
        const latencyCtx = document.getElementById('latencyChart').getContext('2d');
        new Chart(latencyCtx, {
            type: 'bar',
            data: {
                labels: """ + json.dumps(endpoints) + """,
                datasets: [
                    {
                        label: '平均延迟 (ms)',
                        data: """ + json.dumps(avg_latencies) + """,
                        backgroundColor: '#667eea',
                        borderColor: '#667eea',
                        borderWidth: 1,
                    },
                    {
                        label: 'P95 延迟 (ms)',
                        data: """ + json.dumps(p95_latencies) + """,
                        backgroundColor: '#764ba2',
                        borderColor: '#764ba2',
                        borderWidth: 1,
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: true },
                },
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
        
        // 错误率图表
        const errorCtx = document.getElementById('errorRateChart').getContext('2d');
        new Chart(errorCtx, {
            type: 'bar',
            data: {
                labels: """ + json.dumps(endpoints) + """,
                datasets: [{
                    label: '错误率 (%)',
                    data: """ + json.dumps(error_rates) + """,
                    backgroundColor: error_rates.map(rate => 
                        rate < 1 ? '#4caf50' : rate < 5 ? '#ff9800' : '#f44336'
                    ),
                    borderWidth: 0,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                },
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
    </script>
</body>
</html>
"""
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"✅ 报告已生成: {output_file}")
    print(f"   - 总请求数: {total_requests}")
    print(f"   - 失败请求: {total_failures}")
    print(f"   - 错误率: {error_rate:.2f}%")
    print(f"   - 平均延迟: {avg_latency:.1f}ms")


def main():
    if len(sys.argv) < 3:
        print("使用方法:")
        print(f"  python {sys.argv[0]} <input.json> <output.html>")
        print("\n示例:")
        print(f"  python {sys.argv[0]} reports/baseline.json reports/baseline_report.html")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    if not Path(input_file).exists():
        print(f"❌ 输入文件不存在: {input_file}")
        sys.exit(1)
    
    print(f"📖 读取性能数据: {input_file}")
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    print(f"📝 生成 HTML 报告...")
    generate_html_report(data, output_file)
    print(f"✨ 完成!")


if __name__ == "__main__":
    main()
