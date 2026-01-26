// Production Dashboard Application

class ProductionDashboard {
    constructor() {
        this.ws = null;
        this.reconnectDelay = 1000;
        this.maxReconnectDelay = 30000;
        this.currentPeriod = '7d';
        this.performanceChart = null;
        this.alertData = [];
        this.positionData = [];

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initChart();
        this.connectWebSocket();
        this.startPeriodicRefresh();
    }

    setupEventListeners() {
        // Chart period buttons
        document.querySelectorAll('.chart-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.chart-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.currentPeriod = e.target.dataset.period;
                this.loadHistoricalData();
            });
        });
    }

    connectWebSocket() {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/api/v1/dashboard/ws`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.updateConnectionStatus('connected');
            this.reconnectDelay = 1000;
        };

        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.updateMetrics(data);
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.updateConnectionStatus('disconnected');
            this.scheduleReconnect();
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    scheduleReconnect() {
        setTimeout(() => {
            console.log('Attempting to reconnect...');
            this.connectWebSocket();
        }, this.reconnectDelay);

        this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
    }

    updateConnectionStatus(status) {
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');

        statusDot.className = 'status-dot ' + status;

        if (status === 'connected') {
            statusText.textContent = 'Connected';
        } else if (status === 'disconnected') {
            statusText.textContent = 'Disconnected';
        } else {
            statusText.textContent = 'Connecting...';
        }
    }

    async updateMetrics(metrics) {
        // Update portfolio metrics
        this.updateElement('portfolioValue', this.formatCurrency(metrics.total_value));
        this.updateElement('buyingPower', this.formatCurrency(metrics.buying_power));
        this.updateElement('openPositions', metrics.open_positions);

        // Update daily P&L
        const dailyPnlEl = document.getElementById('dailyPnl');
        const dailyPnlValueEl = document.getElementById('dailyPnlValue');
        const dailyPnlPercentEl = document.getElementById('dailyPnlPercent');

        const pnlValue = parseFloat(metrics.daily_pnl);
        const pnlPercent = parseFloat(metrics.daily_pnl_pct);

        dailyPnlEl.className = 'metric-change ' + (pnlValue >= 0 ? 'positive' : 'negative');
        dailyPnlEl.querySelector('.change-icon').textContent = pnlValue >= 0 ? '▲' : '▼';
        dailyPnlEl.querySelector('.change-value').textContent =
            `${this.formatCurrency(pnlValue)} (${pnlPercent.toFixed(2)}%)`;

        dailyPnlValueEl.textContent = this.formatCurrency(pnlValue);
        dailyPnlValueEl.className = 'metric-value ' + (pnlValue >= 0 ? 'positive' : 'negative');
        dailyPnlPercentEl.textContent = `${pnlPercent.toFixed(2)}%`;
        dailyPnlPercentEl.className = 'metric-sublabel ' + (pnlPercent >= 0 ? 'positive' : 'negative');

        // Update system health
        this.updateElement('cpuUsage', `${metrics.cpu_percent.toFixed(1)}%`);
        document.getElementById('cpuBar').style.width = `${metrics.cpu_percent}%`;

        this.updateElement('memoryUsage', `${metrics.memory_mb.toFixed(0)} MB (${metrics.memory_percent.toFixed(1)}%)`);
        document.getElementById('memoryBar').style.width = `${metrics.memory_percent}%`;

        this.updateElement('uptime', this.formatUptime(metrics.uptime_seconds));

        // Update trading metrics
        this.updateElement('ordersToday', metrics.orders_today);
        this.updateElement('fillsToday', metrics.fills_today);
        this.updateElement('rejectsToday', metrics.rejects_today);
        this.updateElement('avgLatency', `${metrics.avg_latency_ms.toFixed(0)}ms`);

        // Update risk metrics
        this.updateElement('var1day', this.formatCurrency(metrics.var_1day));
        document.querySelector('#var1day').nextElementSibling.textContent =
            `Limit: ${this.formatCurrency(metrics.var_limit)}`;

        const varUtil = parseFloat(metrics.var_utilization_pct);
        this.updateElement('varUtilization', `${varUtil.toFixed(1)}%`);
        document.getElementById('varBar').style.width = `${Math.min(varUtil, 100)}%`;

        // Update alert status
        this.updateElement('activeAlerts', metrics.active_alerts);
        this.updateElement('alerts24h', metrics.alerts_last_24h);

        // Update last update time
        document.getElementById('lastUpdate').textContent =
            `Last update: ${new Date(metrics.timestamp).toLocaleTimeString()}`;
    }

    updateElement(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }

    async loadHistoricalData() {
        try {
            const response = await fetch(`/api/v1/dashboard/historical?period=${this.currentPeriod}`);
            const data = await response.json();
            this.updateChart(data);
        } catch (error) {
            console.error('Error loading historical data:', error);
        }
    }

    async loadPositions() {
        try {
            const response = await fetch('/api/v1/dashboard/positions');
            const data = await response.json();
            this.positionData = data;
            this.updatePositionsTable(data);
        } catch (error) {
            console.error('Error loading positions:', error);
        }
    }

    async loadAlertHistory() {
        try {
            const response = await fetch('/api/v1/dashboard/alerts?hours=24');
            const data = await response.json();
            this.alertData = data;
            this.updateAlertHistory(data);
        } catch (error) {
            console.error('Error loading alert history:', error);
        }
    }

    initChart() {
        const ctx = document.getElementById('performanceChart').getContext('2d');
        this.performanceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Portfolio Value',
                        data: [],
                        borderColor: '#2563eb',
                        backgroundColor: 'rgba(37, 99, 235, 0.1)',
                        fill: true,
                        tension: 0.4,
                    },
                    {
                        label: 'Daily P&L',
                        data: [],
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        fill: true,
                        tension: 0.4,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            color: '#94a3b8',
                        },
                    },
                },
                scales: {
                    x: {
                        ticks: {
                            color: '#94a3b8',
                        },
                        grid: {
                            color: '#334155',
                        },
                    },
                    y: {
                        ticks: {
                            color: '#94a3b8',
                            callback: (value) => '$' + value.toLocaleString(),
                        },
                        grid: {
                            color: '#334155',
                        },
                    },
                },
            },
        });

        this.loadHistoricalData();
    }

    updateChart(data) {
        if (!this.performanceChart) return;

        const labels = data.map(point => new Date(point.timestamp).toLocaleDateString());
        const portfolioValues = data.map(point => parseFloat(point.portfolio_value));
        const dailyPnls = data.map(point => parseFloat(point.daily_pnl));

        this.performanceChart.data.labels = labels;
        this.performanceChart.data.datasets[0].data = portfolioValues;
        this.performanceChart.data.datasets[1].data = dailyPnls;
        this.performanceChart.update();
    }

    updatePositionsTable(positions) {
        const tbody = document.querySelector('#positionsTable tbody');

        if (!positions || positions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="no-data">No positions</td></tr>';
            return;
        }

        tbody.innerHTML = positions.map(pos => {
            const pnlClass = parseFloat(pos.unrealized_pnl) >= 0 ? 'positive' : 'negative';
            return `
                <tr>
                    <td><strong>${pos.symbol}</strong></td>
                    <td>${pos.quantity}</td>
                    <td>${this.formatCurrency(pos.avg_price)}</td>
                    <td>${this.formatCurrency(pos.current_price)}</td>
                    <td>${this.formatCurrency(pos.market_value)}</td>
                    <td class="${pnlClass}">${this.formatCurrency(pos.unrealized_pnl)}</td>
                    <td class="${pnlClass}">${parseFloat(pos.unrealized_pnl_pct).toFixed(2)}%</td>
                </tr>
            `;
        }).join('');
    }

    updateAlertHistory(alerts) {
        const container = document.getElementById('alertHistory');

        if (!alerts || alerts.length === 0) {
            container.innerHTML = '<div class="no-alerts">No alerts in the last 24 hours</div>';
            return;
        }

        container.innerHTML = alerts.map(alert => `
            <div class="alert-item severity-${alert.severity}">
                <div class="alert-info">
                    <div class="alert-rule">${alert.rule_id}</div>
                    <div class="alert-message">${alert.message}</div>
                    <div class="alert-time">${new Date(alert.triggered_at).toLocaleString()}</div>
                </div>
                ${alert.status === 'active' ? `
                    <div class="alert-actions">
                        <button class="alert-btn acknowledge" onclick="dashboard.acknowledgeAlert('${alert.alert_id}')">Acknowledge</button>
                        <button class="alert-btn resolve" onclick="dashboard.resolveAlert('${alert.alert_id}')">Resolve</button>
                    </div>
                ` : `
                    <div class="alert-status resolved">Resolved</div>
                `}
            </div>
        `).join('');
    }

    async acknowledgeAlert(alertId) {
        try {
            const response = await fetch(`/api/v1/dashboard/alerts/${alertId}/acknowledge`, {
                method: 'POST',
            });
            if (response.ok) {
                this.loadAlertHistory();
            }
        } catch (error) {
            console.error('Error acknowledging alert:', error);
        }
    }

    async resolveAlert(alertId) {
        try {
            const response = await fetch(`/api/v1/dashboard/alerts/${alertId}/resolve`, {
                method: 'POST',
            });
            if (response.ok) {
                this.loadAlertHistory();
            }
        } catch (error) {
            console.error('Error resolving alert:', error);
        }
    }

    startPeriodicRefresh() {
        // Refresh positions and alerts every 30 seconds
        setInterval(() => {
            this.loadPositions();
            this.loadAlertHistory();
        }, 30000);

        // Initial load
        this.loadPositions();
        this.loadAlertHistory();
    }

    formatCurrency(value) {
        const num = parseFloat(value);
        if (isNaN(num)) return '$0.00';
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(num);
    }

    formatUptime(seconds) {
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${days}d ${hours}h ${minutes}m`;
    }
}

// Initialize dashboard when DOM is ready
let dashboard;
document.addEventListener('DOMContentLoaded', () => {
    dashboard = new ProductionDashboard();
});
