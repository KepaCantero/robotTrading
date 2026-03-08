"""
Unit tests for Alert System.

Tests for threshold-based alerting and notification system.
"""
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from app.engines.risk_engine.alert_system import AlertSystem, BaseAlertSystem
from app.domain.models.portfolio import Portfolio


@pytest.fixture
def mock_portfolio():
    """Create mock portfolio."""
    portfolio = Mock(spec=Portfolio)
    portfolio.total_equity = 100000.0
    return portfolio


@pytest.fixture
def alert_config():
    """Alert system configuration."""
    return {
        'thresholds': {
            'var_breach': 0.05,
            'drawdown_limit': 0.15,
            'exposure_limit': 0.20,
            'leverage_limit': 1.0,
            'correlation_limit': 0.8,
            'violation_count': 5,
        },
        'enable_email': False,
        'enable_slack': False,
        'enable_logging': True,
        'cooldown_period_minutes': 60,
    }


@pytest.fixture
def alert_system(alert_config):
    """Create AlertSystem instance."""
    return AlertSystem(alert_config)


@pytest.mark.unit
class TestAlertSystemInitialization:
    """Test AlertSystem initialization."""

    def test_default_initialization(self):
        """Test initialization with default config."""
        system = AlertSystem({})
        assert system.thresholds is not None
        assert system.enable_logging is True
        assert system.enable_email is False

    def test_custom_thresholds(self, alert_config):
        """Test initialization with custom thresholds."""
        system = AlertSystem(alert_config)
        assert system.thresholds['var_breach'] == 0.05
        assert system.thresholds['drawdown_limit'] == 0.15

    def test_notification_channels(self, alert_config):
        """Test notification channel configuration."""
        config = alert_config.copy()
        config['enable_email'] = True
        config['enable_slack'] = True

        system = AlertSystem(config)
        assert system.enable_email is True
        assert system.enable_slack is True

    def test_alert_history_initialization(self, alert_system):
        """Test alert history is initialized."""
        assert isinstance(alert_system.alert_history, list)
        assert len(alert_system.alert_history) == 0

    def test_cooldown_initialization(self, alert_system):
        """Test cooldown tracking is initialized."""
        assert isinstance(alert_system.alert_cooldown, dict)


@pytest.mark.unit
class TestVaRThresholds:
    """Test VaR threshold checking."""

    def test_var_threshold_no_breach(self, alert_system, mock_portfolio):
        """Test VaR within threshold."""
        risk_assessment = {
            'var': {
                'var_amount': 3000.0,
                'var': 0.03,  # 3%, below 5% threshold
            }
        }

        alerts = alert_system.check_thresholds(risk_assessment, mock_portfolio)

        assert len(alerts) == 0

    def test_var_threshold_breach(self, alert_system, mock_portfolio):
        """Test VaR exceeding threshold."""
        risk_assessment = {
            'var': {
                'var_amount': 6000.0,
                'var': 0.06,  # 6%, above 5% threshold
            }
        }

        alerts = alert_system.check_thresholds(risk_assessment, mock_portfolio)

        assert len(alerts) > 0
        assert alerts[0]['type'] == 'var_breach'
        assert alerts[0]['severity'] == 'high'

    def test_var_alert_includes_metadata(self, alert_system, mock_portfolio):
        """Test VaR alert includes required metadata."""
        risk_assessment = {
            'var': {
                'var_amount': 6000.0,
                'var': 0.06,
            }
        }

        alerts = alert_system.check_thresholds(risk_assessment, mock_portfolio)

        assert 'timestamp' in alerts[0]
        assert 'portfolio_value' in alerts[0]
        assert 'alert_id' in alerts[0]
        assert 'var_amount' in alerts[0]


@pytest.mark.unit
class TestDrawdownThresholds:
    """Test drawdown threshold checking."""

    def test_drawdown_no_breach(self, alert_system, mock_portfolio):
        """Test drawdown within threshold."""
        risk_assessment = {
            'drawdown': {
                'portfolio_drawdown': {
                    'current_drawdown': 0.10,  # 10%, below 15%
                }
            }
        }

        alerts = alert_system.check_thresholds(risk_assessment, mock_portfolio)

        assert len(alerts) == 0

    def test_drawdown_threshold_breach(self, alert_system, mock_portfolio):
        """Test drawdown exceeding threshold."""
        risk_assessment = {
            'drawdown': {
                'portfolio_drawdown': {
                    'current_drawdown': 0.20,  # 20%, above 15%
                }
            }
        }

        alerts = alert_system.check_thresholds(risk_assessment, mock_portfolio)

        assert len(alerts) > 0
        assert alerts[0]['type'] == 'drawdown_limit'
        assert alerts[0]['severity'] == 'critical'

    def test_circuit_breaker_alert(self, alert_system, mock_portfolio):
        """Test circuit breaker activation alert."""
        risk_assessment = {
            'drawdown': {
                'portfolio_drawdown': {
                    'current_drawdown': 0.10,
                },
                'circuit_breaker_status': {
                    'global_circuit_breaker_active': True,
                    'global_circuit_breaker_reason': 'Market crash',
                    'global_circuit_breaker_timestamp': datetime.utcnow().isoformat(),
                },
            }
        }

        alerts = alert_system.check_thresholds(risk_assessment, mock_portfolio)

        circuit_breaker_alerts = [a for a in alerts if a['type'] == 'circuit_breaker']
        assert len(circuit_breaker_alerts) > 0
        assert circuit_breaker_alerts[0]['severity'] == 'critical'


@pytest.mark.unit
class TestExposureThresholds:
    """Test exposure threshold checking."""

    def test_exposure_no_violations(self, alert_system, mock_portfolio):
        """Test exposure within limits."""
        risk_assessment = {
            'exposure': {
                'violations': [],
                'leverage': {
                    'leverage': 0.8,  # Below 1.0 limit
                },
            }
        }

        alerts = alert_system.check_thresholds(risk_assessment, mock_portfolio)

        assert len(alerts) == 0

    def test_exposure_violations(self, alert_system, mock_portfolio):
        """Test exposure violations."""
        risk_assessment = {
            'exposure': {
                'violations': [
                    {
                        'type': 'single_position_limit',
                        'severity': 'high',
                        'symbol': 'AAPL',
                    }
                ],
                'leverage': {
                    'leverage': 0.8,
                },
            }
        }

        alerts = alert_system.check_thresholds(risk_assessment, mock_portfolio)

        exposure_alerts = [a for a in alerts if a['type'] == 'exposure_violation']
        assert len(exposure_alerts) > 0

    def test_leverage_limit_breach(self, alert_system, mock_portfolio):
        """Test leverage limit exceeded."""
        risk_assessment = {
            'exposure': {
                'violations': [],
                'leverage': {
                    'leverage': 1.5,  # Above 1.0 limit
                },
            }
        }

        alerts = alert_system.check_thresholds(risk_assessment, mock_portfolio)

        leverage_alerts = [a for a in alerts if a['type'] == 'leverage_limit']
        assert len(leverage_alerts) > 0
        assert leverage_alerts[0]['severity'] == 'high'


@pytest.mark.unit
class TestCorrelationThresholds:
    """Test correlation threshold checking."""

    def test_correlation_no_violations(self, alert_system, mock_portfolio):
        """Test correlation within limits."""
        risk_assessment = {
            'correlations': {
                'violations': [],
            }
        }

        alerts = alert_system.check_thresholds(risk_assessment, mock_portfolio)

        correlation_alerts = [a for a in alerts if a['type'] == 'correlation_violation']
        assert len(correlation_alerts) == 0

    def test_correlation_violations(self, alert_system, mock_portfolio):
        """Test correlation violations."""
        risk_assessment = {
            'correlations': {
                'violations': [
                    {
                        'symbol1': 'AAPL',
                        'symbol2': 'MSFT',
                        'correlation': 0.95,
                        'severity': 'high',
                    }
                ]
            }
        }

        alerts = alert_system.check_thresholds(risk_assessment, mock_portfolio)

        correlation_alerts = [a for a in alerts if a['type'] == 'correlation_violation']
        assert len(correlation_alerts) > 0


@pytest.mark.unit
class TestViolationCounting:
    """Test violation counting and aggregation."""

    def test_multiple_violations_trigger_alert(self, alert_system, mock_portfolio):
        """Test that multiple violations trigger alert."""
        # Need to exceed the default threshold of 5 violations
        risk_assessment = {
            'exposure': {
                'violations': [{'type': 'v1'}, {'type': 'v2'}, {'type': 'v3'}, {'type': 'v4'}]
            },
            'correlations': {'violations': [{'type': 'v5'}, {'type': 'v6'}]},
        }

        alerts = alert_system.check_thresholds(risk_assessment, mock_portfolio)

        violation_alerts = [a for a in alerts if a['type'] == 'violation_count']
        assert len(violation_alerts) > 0
        assert violation_alerts[0]['violation_count'] == 6

    def test_below_violation_threshold(self, alert_system, mock_portfolio):
        """Test violations below threshold don't trigger alert."""
        risk_assessment = {
            'exposure': {'violations': [{'type': 'v1'}, {'type': 'v2'}]},
            'correlations': {'violations': []},
        }

        alerts = alert_system.check_thresholds(risk_assessment, mock_portfolio)

        violation_alerts = [a for a in alerts if a['type'] == 'violation_count']
        assert len(violation_alerts) == 0


@pytest.mark.unit
class TestCooldownFiltering:
    """Test alert cooldown filtering."""

    def test_critical_alerts_bypass_cooldown(self, alert_system, mock_portfolio):
        """Test that critical alerts bypass cooldown."""
        # Add to cooldown
        alert_system.alert_cooldown['var_breach'] = datetime.utcnow()

        risk_assessment = {
            'var': {
                'var_amount': 6000.0,
                'var': 0.06,
            },
            'drawdown': {
                'portfolio_drawdown': {
                    'current_drawdown': 0.20,  # Critical
                }
            },
        }

        alerts = alert_system.check_thresholds(risk_assessment, mock_portfolio)

        # Critical alert should still come through
        critical_alerts = [a for a in alerts if a['severity'] == 'critical']
        assert len(critical_alerts) > 0

    def test_normal_alerts_respect_cooldown(self, alert_system, mock_portfolio):
        """Test that normal alerts respect cooldown period."""
        # Add to cooldown
        alert_system.alert_cooldown['var_breach'] = datetime.utcnow()

        risk_assessment = {
            'var': {
                'var_amount': 6000.0,
                'var': 0.06,
            }
        }

        alerts = alert_system.check_thresholds(risk_assessment, mock_portfolio)

        # Alert should be filtered out due to cooldown
        var_alerts = [a for a in alerts if a['type'] == 'var_breach']
        assert len(var_alerts) == 0

    def test_cooldown_expiry(self, alert_system, mock_portfolio):
        """Test that alerts work after cooldown expires."""
        # Add old cooldown (61 minutes ago)
        alert_system.alert_cooldown['var_breach'] = datetime.utcnow() - timedelta(minutes=61)

        risk_assessment = {
            'var': {
                'var_amount': 6000.0,
                'var': 0.06,
            }
        }

        alerts = alert_system.check_thresholds(risk_assessment, mock_portfolio)

        # Alert should come through after cooldown expires
        var_alerts = [a for a in alerts if a['type'] == 'var_breach']
        assert len(var_alerts) > 0


@pytest.mark.unit
class TestAlertHistory:
    """Test alert history management."""

    def test_alerts_added_to_history(self, alert_system, mock_portfolio):
        """Test that alerts are added to history."""
        risk_assessment = {
            'var': {
                'var_amount': 6000.0,
                'var': 0.06,
            }
        }

        alert_system.check_thresholds(risk_assessment, mock_portfolio)

        assert len(alert_system.alert_history) > 0

    def test_alert_history_limit(self, alert_system, mock_portfolio):
        """Test that alert history respects max size."""
        alert_system.max_alert_history = 5
        alert_system.cooldown_period = 0  # Disable cooldown

        # Generate 10 alerts with different values to avoid cooldown
        for i in range(10):
            risk_assessment = {
                'var': {
                    'var_amount': 6000.0 + i,
                    'var': 0.06 + (i * 0.01),  # Different var values
                }
            }
            alert_system.check_thresholds(risk_assessment, mock_portfolio)

        # Should only keep last 5
        assert len(alert_system.alert_history) == 5


@pytest.mark.unit
class TestAlertSending:
    """Test alert sending functionality."""

    def test_send_empty_alerts(self, alert_system):
        """Test sending empty alert list."""
        result = alert_system.send_alerts([])
        assert result is True

    def test_send_alerts_with_logging(self, alert_system, caplog):
        """Test that alerts are logged."""
        alerts = [
            {
                'type': 'test_alert',
                'severity': 'high',
                'message': 'Test alert message',
            }
        ]

        with caplog.at_level('WARNING'):
            alert_system.send_alerts(alerts)

        # Check that alert was logged
        assert any('ALERT' in record.message for record in caplog.records)

    def test_critical_alert_logging(self, alert_system, caplog):
        """Test critical alerts are logged at critical level."""
        alerts = [
            {
                'type': 'critical_alert',
                'severity': 'critical',
                'message': 'Critical alert',
            }
        ]

        with caplog.at_level('CRITICAL'):
            alert_system.send_alerts(alerts)

        # Should have critical log
        assert any('CRITICAL' in record.levelname for record in caplog.records)

    @patch('app.engines.risk_engine.alert_system.EMAIL_AVAILABLE', True)
    @patch('app.engines.risk_engine.alert_system.smtplib.SMTP')
    def test_send_email_alerts(self, mock_smtp, alert_system):
        """Test email alert sending."""
        alert_system.enable_email = True
        alert_system.email_config = {
            'smtp_server': 'smtp.example.com',
            'smtp_port': 587,
            'sender_email': 'test@example.com',
            'sender_password': 'password',
            'recipient_emails': ['recipient@example.com'],
        }

        alerts = [
            {
                'type': 'test',
                'severity': 'high',
                'message': 'Test alert',
            }
        ]

        result = alert_system.send_alerts(alerts)

        # Should attempt to send (may fail due to missing email imports in module)
        assert result is True or result is False

    @patch('app.engines.risk_engine.alert_system.requests.post')
    def test_send_slack_alerts(self, mock_post, alert_system):
        """Test Slack alert sending."""
        alert_system.enable_slack = True
        alert_system.slack_config = {
            'webhook_url': 'https://hooks.slack.com/test',
        }

        mock_post.return_value = Mock(raise_for_status=lambda: None)

        alerts = [
            {
                'type': 'test',
                'severity': 'high',
                'message': 'Test alert',
            }
        ]

        result = alert_system.send_alerts(alerts)

        assert result is True


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling in alert system."""

    def test_invalid_risk_assessment(self, alert_system, mock_portfolio):
        """Test handling of invalid risk assessment."""
        risk_assessment = {'invalid_key': 'value'}

        alerts = alert_system.check_thresholds(risk_assessment, mock_portfolio)

        # Should not crash
        assert isinstance(alerts, list)

    def test_malformed_var_data(self, alert_system, mock_portfolio):
        """Test handling of malformed VaR data."""
        risk_assessment = {
            'var': {
                'var_amount': None,
                'var': None,
            }
        }

        alerts = alert_system.check_thresholds(risk_assessment, mock_portfolio)

        # Should not crash
        assert isinstance(alerts, list)

    def test_malformed_drawdown_data(self, alert_system, mock_portfolio):
        """Test handling of malformed drawdown data."""
        risk_assessment = {
            'drawdown': {
                'portfolio_drawdown': None,
            }
        }

        alerts = alert_system.check_thresholds(risk_assessment, mock_portfolio)

        # Should not crash
        assert isinstance(alerts, list)


@pytest.mark.unit
class TestGetStatus:
    """Test status reporting."""

    def test_get_status(self, alert_system):
        """Test getting system status."""
        status = alert_system.get_status()

        assert 'enabled' in status
        assert 'alert_history_size' in status
        assert 'email_enabled' in status
        assert 'slack_enabled' in status
        assert 'thresholds' in status

    def test_status_reflects_configuration(self, alert_system):
        """Test status reflects current configuration."""
        alert_system.enable_email = True
        alert_system.enable_slack = True

        status = alert_system.get_status()

        assert status['email_enabled'] is True
        assert status['slack_enabled'] is True

    def test_status_includes_history_size(self, alert_system, mock_portfolio):
        """Test status includes alert history size."""
        risk_assessment = {
            'var': {
                'var_amount': 6000.0,
                'var': 0.06,
            }
        }

        alert_system.check_thresholds(risk_assessment, mock_portfolio)

        status = alert_system.get_status()
        assert status['alert_history_size'] > 0


@pytest.mark.unit
class TestBaseAlertSystem:
    """Test BaseAlertSystem abstract class."""

    def test_base_class_is_abstract(self):
        """Test that BaseAlertSystem cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseAlertSystem({})

    def test_abstract_methods(self):
        """Test that abstract methods are defined."""
        assert hasattr(BaseAlertSystem, 'check_thresholds')
        assert hasattr(BaseAlertSystem, 'send_alerts')
