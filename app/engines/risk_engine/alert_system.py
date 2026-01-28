"""
Alert System

Implementa sistema de alertas y notificaciones:
- Threshold-based alerts
- Email/Slack notifications (estructure ready)
- Dashboard de riesgo en tiempo real
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List

from requests.exceptions import ConnectionError, HTTPError, RequestException

from app.models.portfolio import Portfolio

logger = logging.getLogger(__name__)

# Optional dependencies
try:
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    SMTPLIB_AVAILABLE = True
    EMAIL_AVAILABLE = True
except ImportError:
    SMTPLIB_AVAILABLE = False
    EMAIL_AVAILABLE = False


class BaseAlertSystem(ABC):
    """Clase base para sistemas de alerta."""

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar sistema de alerta.

        Args:
            config: Configuración del sistema
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def check_thresholds(
        self, risk_assessment: Dict[str, Any], portfolio: Portfolio
    ) -> List[Dict[str, Any]]:
        """
        Verificar umbrales y generar alertas.

        Args:
            risk_assessment: Evaluación de riesgo
            portfolio: Portfolio actual

        Returns:
            Lista de alertas generadas
        """

    @abstractmethod
    def send_alerts(self, alerts: List[Dict[str, Any]]) -> bool:
        """
        Enviar alertas.

        Args:
            alerts: Lista de alertas a enviar

        Returns:
            True si se enviaron exitosamente
        """


class AlertSystem(BaseAlertSystem):
    """
    Alert System principal.

    Sistema completo de alertas y notificaciones.
    """

    def __init__(self, config: Dict[str, Any]):
        """Inicializar alert system."""
        super().__init__(config)

        # Configuración de umbrales
        self.thresholds = config.get(
            'thresholds',
            {
                'var_breach': 0.05,  # VaR excedido en 5%
                'drawdown_limit': 0.15,  # Drawdown > 15%
                'exposure_limit': 0.20,  # Exposición > 20% por activo
                'leverage_limit': 1.0,  # Leverage > 1.0
                'correlation_limit': 0.8,  # Correlación > 80%
                'violation_count': 5,  # Más de 5 violaciones
            },
        )

        # Canales de notificación
        self.enable_email = config.get('enable_email', False)
        self.enable_slack = config.get('enable_slack', False)
        self.enable_logging = config.get('enable_logging', True)
        self.enable_dashboard = config.get('enable_dashboard', True)

        # Configuración de email
        self.email_config = config.get('email', {})

        # Configuración de Slack
        self.slack_config = config.get('slack', {})

        # Historial de alertas
        self.alert_history: List[Dict[str, Any]] = []
        self.max_alert_history = config.get('max_alert_history', 1000)

        # Rate limiting
        self.alert_cooldown: Dict[str, datetime] = {}
        self.cooldown_period = config.get('cooldown_period_minutes', 60)  # 1 hora

    def check_thresholds(
        self, risk_assessment: Dict[str, Any], portfolio: Portfolio
    ) -> List[Dict[str, Any]]:
        """
        Verificar umbrales y generar alertas.

        Args:
            risk_assessment: Evaluación de riesgo completa
            portfolio: Portfolio actual

        Returns:
            Lista de alertas generadas
        """
        alerts = []

        try:
            # Verificar VaR
            if 'var' in risk_assessment:
                var_alerts = self._check_var_thresholds(risk_assessment['var'])
                alerts.extend(var_alerts)

            # Verificar drawdown
            if 'drawdown' in risk_assessment:
                drawdown_alerts = self._check_drawdown_thresholds(risk_assessment['drawdown'])
                alerts.extend(drawdown_alerts)

            # Verificar exposición
            if 'exposure' in risk_assessment:
                exposure_alerts = self._check_exposure_thresholds(risk_assessment['exposure'])
                alerts.extend(exposure_alerts)

            # Verificar correlaciones
            if 'correlations' in risk_assessment:
                correlation_alerts = self._check_correlation_thresholds(
                    risk_assessment['correlations']
                )
                alerts.extend(correlation_alerts)

            # Verificar violaciones generales
            violation_alerts = self._check_violations(risk_assessment)
            alerts.extend(violation_alerts)

            # Filtrar alertas por rate limiting
            filtered_alerts = self._filter_by_cooldown(alerts)

            # Agregar timestamp y metadata
            for alert in filtered_alerts:
                alert['timestamp'] = datetime.utcnow().isoformat()
                alert['portfolio_value'] = float(portfolio.total_equity)
                alert['alert_id'] = f"{alert['type']}_{datetime.utcnow().timestamp()}"

            # Guardar en historial
            self.alert_history.extend(filtered_alerts)
            if len(self.alert_history) > self.max_alert_history:
                self.alert_history = self.alert_history[-self.max_alert_history :]

            return filtered_alerts

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            self.logger.error(f"Error verificando umbrales: {e}", exc_info=True)
            return []

    def _check_var_thresholds(self, var_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Verificar umbrales de VaR."""
        alerts = []

        var_amount = var_result.get('var_amount')
        var_percent = var_result.get('var')

        if var_amount and var_percent:
            threshold = self.thresholds.get('var_breach', 0.05)

            if abs(var_percent) > threshold:
                alerts.append(
                    {
                        'type': 'var_breach',
                        'severity': 'high',
                        'message': f"VaR excedido: {var_percent:.2%} > {threshold:.2%}",
                        'var_amount': var_amount,
                        'var_percent': var_percent,
                        'threshold': threshold,
                    }
                )

        return alerts

    def _check_drawdown_thresholds(self, drawdown_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Verificar umbrales de drawdown."""
        alerts = []

        portfolio_drawdown = drawdown_result.get('portfolio_drawdown', {})
        current_drawdown = portfolio_drawdown.get('current_drawdown', 0.0)

        threshold = self.thresholds.get('drawdown_limit', 0.15)

        if current_drawdown > threshold:
            alerts.append(
                {
                    'type': 'drawdown_limit',
                    'severity': 'critical',
                    'message': f"Drawdown excedido: {current_drawdown:.2%} > {threshold:.2%}",
                    'current_drawdown': current_drawdown,
                    'threshold': threshold,
                }
            )

        # Circuit breaker alerts
        circuit_breaker = drawdown_result.get('circuit_breaker_status', {})
        if circuit_breaker.get('global_circuit_breaker_active'):
            alerts.append(
                {
                    'type': 'circuit_breaker',
                    'severity': 'critical',
                    'message': f"CIRCUIT BREAKER ACTIVADO: {circuit_breaker.get('global_circuit_breaker_reason', 'Unknown')}",
                    'reason': circuit_breaker.get('global_circuit_breaker_reason'),
                    'timestamp': circuit_breaker.get('global_circuit_breaker_timestamp'),
                }
            )

        return alerts

    def _check_exposure_thresholds(self, exposure_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Verificar umbrales de exposición."""
        alerts = []

        # Check max single asset exposure
        max_single_exposure = exposure_result.get('max_single_exposure', 0.0)
        exposure_threshold = self.thresholds.get('exposure_limit', 0.20)

        if max_single_exposure > exposure_threshold:
            alerts.append(
                {
                    'type': 'exposure_limit',
                    'severity': 'high',
                    'message': f"Exposición máxima excedida: {max_single_exposure:.2%} > {exposure_threshold:.2%}",
                    'max_single_exposure': max_single_exposure,
                    'threshold': exposure_threshold,
                }
            )

        violations = exposure_result.get('violations', [])

        if violations:
            for violation in violations:
                alerts.append(
                    {
                        'type': 'exposure_violation',
                        'severity': violation.get('severity', 'medium'),
                        'message': f"Violación de exposición: {violation.get('type', 'unknown')}",
                        'violation': violation,
                    }
                )

        # Leverage alerts
        leverage = exposure_result.get('leverage', {})
        # Handle leverage being either a dict or a float value
        if isinstance(leverage, dict):
            leverage_value = leverage.get('leverage', 0.0)
        elif isinstance(leverage, (int, float)):
            leverage_value = leverage
        else:
            leverage_value = 0.0

        leverage_threshold = self.thresholds.get('leverage_limit', 1.0)

        if leverage_value > leverage_threshold:
            alerts.append(
                {
                    'type': 'leverage_limit',
                    'severity': 'high',
                    'message': f"Leverage excedido: {leverage_value:.2f} > {leverage_threshold:.2f}",
                    'leverage': leverage_value,
                    'threshold': leverage_threshold,
                }
            )

        return alerts

    def _check_correlation_thresholds(
        self, correlation_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Verificar umbrales de correlación."""
        alerts = []

        # Check max correlation value
        max_correlation = correlation_result.get('max_correlation', 0.0)
        correlation_threshold = self.thresholds.get('correlation_limit', 0.8)

        if max_correlation > correlation_threshold:
            alerts.append(
                {
                    'type': 'correlation_limit',
                    'severity': 'high',
                    'message': f"Correlación máxima excedida: {max_correlation:.2%} > {correlation_threshold:.2%}",
                    'max_correlation': max_correlation,
                    'threshold': correlation_threshold,
                }
            )

        # Check for specific violations
        violations = correlation_result.get('violations', [])

        if violations:
            for violation in violations:
                alerts.append(
                    {
                        'type': 'correlation_violation',
                        'severity': violation.get('severity', 'medium'),
                        'message': f"Correlación alta: {violation.get('symbol1', '')} - {violation.get('symbol2', '')}",
                        'violation': violation,
                    }
                )

        return alerts

    def _check_violations(self, risk_assessment: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Verificar violaciones generales."""
        alerts = []

        # Contar violaciones totales
        total_violations = 0

        if 'exposure' in risk_assessment:
            total_violations += len(risk_assessment['exposure'].get('violations', []))

        if 'correlations' in risk_assessment:
            total_violations += len(risk_assessment['correlations'].get('violations', []))

        threshold = self.thresholds.get('violation_count', 5)

        if total_violations > threshold:
            alerts.append(
                {
                    'type': 'violation_count',
                    'severity': 'high',
                    'message': f"Múltiples violaciones detectadas: {total_violations} > {threshold}",
                    'violation_count': total_violations,
                    'threshold': threshold,
                }
            )

        return alerts

    def _filter_by_cooldown(self, alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filtrar alertas por cooldown period."""
        filtered = []

        for alert in alerts:
            alert_type = alert.get('type')

            if alert_type in self.alert_cooldown:
                last_alert_time = self.alert_cooldown[alert_type]
                time_since_last = datetime.utcnow() - last_alert_time

                if time_since_last.total_seconds() < self.cooldown_period * 60:
                    # Skip alert (en cooldown)
                    continue

            # Alert crítico siempre pasa
            if alert.get('severity') == 'critical':
                filtered.append(alert)
                self.alert_cooldown[alert_type] = datetime.utcnow()
            else:
                # Alert normal pasa si no está en cooldown
                filtered.append(alert)
                self.alert_cooldown[alert_type] = datetime.utcnow()

        return filtered

    def send_alerts(self, alerts: List[Dict[str, Any]]) -> bool:
        """
        Enviar alertas por todos los canales configurados.

        Args:
            alerts: Lista de alertas a enviar

        Returns:
            True si se enviaron exitosamente
        """
        if not alerts:
            return True

        success = True

        # Logging
        if self.enable_logging:
            for alert in alerts:
                severity = alert.get('severity', 'medium')
                message = alert.get('message', 'Unknown alert')

                if severity == 'critical':
                    self.logger.critical(f"🚨 ALERT: {message}")
                elif severity == 'high':
                    self.logger.warning(f"⚠️ ALERT: {message}")
                else:
                    self.logger.info(f"ℹ️ ALERT: {message}")

        # Email
        if self.enable_email and EMAIL_AVAILABLE:
            try:
                self._send_email_alerts(alerts)
            except (RuntimeError, ValueError, TypeError, KeyError) as e:
                self.logger.error(f"Error enviando alertas por email: {e}")
                success = False

        # Slack
        if self.enable_slack:
            try:
                self._send_slack_alerts(alerts)
            except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
                self.logger.error(f"Error enviando alertas por Slack: {e}")
                success = False

        # Dashboard (registrar para dashboard)
        if self.enable_dashboard:
            # Las alertas ya están en alert_history
            pass

        return success

    def _send_email_alerts(self, alerts: List[Dict[str, Any]]) -> None:
        """Enviar alertas por email."""
        if not EMAIL_AVAILABLE:
            return

        # Implementación básica (requiere configuración SMTP)
        smtp_server = self.email_config.get('smtp_server')
        smtp_port = self.email_config.get('smtp_port', 587)
        sender_email = self.email_config.get('sender_email')
        sender_password = self.email_config.get('sender_password')
        recipient_emails = self.email_config.get('recipient_emails', [])

        if not all([smtp_server, sender_email, recipient_emails]):
            self.logger.warning("Configuración de email incompleta")
            return

        try:
            # Crear mensaje
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = ', '.join(recipient_emails)
            msg['Subject'] = f"Risk Alerts - {len(alerts)} alertas generadas"

            # Cuerpo del mensaje
            body = "Alertas de riesgo generadas:\n\n"
            for alert in alerts:
                body += f"- {alert.get('message', 'Unknown')}\n"
                body += f"  Severidad: {alert.get('severity', 'medium')}\n"
                body += f"  Tipo: {alert.get('type', 'unknown')}\n\n"

            msg.attach(MIMEText(body, 'plain'))

            # Enviar
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()

            self.logger.info(f"Alertas enviadas por email a {len(recipient_emails)} destinatarios")
        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            self.logger.error(f"Error enviando email: {e}", exc_info=True)

    def _send_slack_alerts(self, alerts: List[Dict[str, Any]]) -> None:
        """Enviar alertas por Slack."""
        webhook_url = self.slack_config.get('webhook_url')

        if not webhook_url:
            self.logger.warning("Webhook de Slack no configurado")
            return

        try:
            import requests
            from requests.exceptions import RequestException

            # Preparar mensaje
            text = f"🚨 *{len(alerts)} Alertas de Riesgo*\n\n"
            for alert in alerts:
                severity = alert.get('severity', 'medium')
                emoji = '🔴' if severity == 'critical' else '🟠' if severity == 'high' else '🟡'
                text += f"{emoji} {alert.get('message', 'Unknown')}\n"

            payload = {'text': text, 'username': 'Risk Alert System', 'icon_emoji': ':warning:'}

            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()

            self.logger.info("Alertas enviadas por Slack")

        except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
            self.logger.error(f"Error enviando Slack: {e}", exc_info=True)

    def get_status(self) -> Dict[str, Any]:
        """Obtener estado del sistema de alertas."""
        return {
            'enabled': True,
            'alert_history_size': len(self.alert_history),
            'email_enabled': self.enable_email,
            'slack_enabled': self.enable_slack,
            'dashboard_enabled': self.enable_dashboard,
            'cooldown_period_minutes': self.cooldown_period,
            'thresholds': self.thresholds,
        }
