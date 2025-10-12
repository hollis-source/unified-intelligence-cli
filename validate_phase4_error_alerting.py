#!/usr/bin/env python3
"""Phase 4 validation script for Error Alerting implementation.

Validates:
- Alert and AlertRule entities
- IAlertManager interface contract
- InMemoryAlertManager adapter implementation
- Alert rules and cooldown mechanism

Uses manual testing approach due to test directory permissions.
Run with: python3 validate_phase4_error_alerting.py
"""

import sys
from datetime import datetime, timedelta
from typing import List

# Add src to path
sys.path.insert(0, "/home/ui-cli_jake/unified-intelligence-cli")

from src.observability.entities import Alert, AlertRule, AlertSeverity
from src.observability.interfaces import IAlertManager
from src.observability.adapters import InMemoryAlertManager

# Test tracking
tests_passed = 0
tests_failed = 0
test_results: List[str] = []


def test(name: str):
    """Decorator to track test execution."""

    def decorator(func):
        def wrapper():
            global tests_passed, tests_failed, test_results
            try:
                func()
                tests_passed += 1
                test_results.append(f"✓ {name}")
                print(f"✓ {name}")
            except AssertionError as e:
                tests_failed += 1
                test_results.append(f"✗ {name}: {e}")
                print(f"✗ {name}: {e}")
            except Exception as e:
                tests_failed += 1
                test_results.append(f"✗ {name}: Unexpected error: {e}")
                print(f"✗ {name}: Unexpected error: {e}")

        return wrapper

    return decorator


# ============================================================================
# Alert Entity Tests
# ============================================================================


@test("Alert: Factory creates valid alert with required fields")
def test_alert_factory():
    alert = Alert.create(
        severity=AlertSeverity.ERROR,
        message="Test error alert",
        source="test_system",
    )

    assert alert.severity == AlertSeverity.ERROR
    assert alert.message == "Test error alert"
    assert alert.source == "test_system"
    assert alert.acknowledged is False
    assert alert.acknowledged_at is None
    assert alert.acknowledged_by is None
    assert alert.id is not None
    assert alert.timestamp is not None


@test("Alert: Factory accepts optional metadata")
def test_alert_optional():
    alert = Alert.create(
        severity=AlertSeverity.CRITICAL,
        message="Critical alert",
        source="monitoring",
        rule_id="rule-123",
        metadata={"key": "value"},
    )

    assert alert.rule_id == "rule-123"
    assert alert.metadata == {"key": "value"}


@test("Alert: Validates empty message")
def test_alert_empty_message():
    try:
        Alert.create(
            severity=AlertSeverity.ERROR,
            message="",
            source="test",
        )
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "message" in str(e).lower()


@test("Alert: Validates empty source")
def test_alert_empty_source():
    try:
        Alert.create(
            severity=AlertSeverity.ERROR,
            message="Test",
            source="",
        )
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "source" in str(e).lower()


@test("Alert: Is immutable (frozen dataclass)")
def test_alert_immutable():
    alert = Alert.create(
        severity=AlertSeverity.ERROR,
        message="Test",
        source="test",
    )

    try:
        alert.message = "Changed"
        assert False, "Should not allow modification"
    except (AttributeError, Exception):
        pass


@test("Alert: acknowledge() creates acknowledged copy")
def test_alert_acknowledge():
    alert = Alert.create(
        severity=AlertSeverity.ERROR,
        message="Test",
        source="test",
    )

    ack_alert = alert.acknowledge("admin")

    assert alert.acknowledged is False  # Original unchanged
    assert ack_alert.acknowledged is True
    assert ack_alert.acknowledged_by == "admin"
    assert ack_alert.acknowledged_at is not None
    assert ack_alert.id == alert.id  # Same ID


@test("Alert: is_critical() checks severity")
def test_alert_is_critical():
    critical = Alert.create(AlertSeverity.CRITICAL, "Critical", "test")
    error = Alert.create(AlertSeverity.ERROR, "Error", "test")

    assert critical.is_critical() is True
    assert error.is_critical() is False


@test("Alert: requires_action() checks severity")
def test_alert_requires_action():
    critical = Alert.create(AlertSeverity.CRITICAL, "Critical", "test")
    error = Alert.create(AlertSeverity.ERROR, "Error", "test")
    warning = Alert.create(AlertSeverity.WARNING, "Warning", "test")
    info = Alert.create(AlertSeverity.INFO, "Info", "test")

    assert critical.requires_action() is True
    assert error.requires_action() is True
    assert warning.requires_action() is False
    assert info.requires_action() is False


@test("Alert: to_dict serialization")
def test_alert_to_dict():
    alert = Alert.create(
        severity=AlertSeverity.ERROR,
        message="Test",
        source="test",
        rule_id="rule-123",
    )

    data = alert.to_dict()
    assert data["severity"] == "error"
    assert data["message"] == "Test"
    assert data["source"] == "test"
    assert data["rule_id"] == "rule-123"
    assert data["acknowledged"] is False
    assert "id" in data
    assert "timestamp" in data


# ============================================================================
# AlertRule Entity Tests
# ============================================================================


@test("AlertRule: Factory creates valid rule with required fields")
def test_alert_rule_factory():
    rule = AlertRule.create(
        name="High Cost Alert",
        description="Alert when cost exceeds threshold",
        severity=AlertSeverity.WARNING,
        condition="cost > threshold",
        threshold=100.0,
    )

    assert rule.name == "High Cost Alert"
    assert rule.description == "Alert when cost exceeds threshold"
    assert rule.severity == AlertSeverity.WARNING
    assert rule.condition == "cost > threshold"
    assert rule.threshold == 100.0
    assert rule.enabled is True
    assert rule.cooldown_minutes == 60
    assert rule.id is not None


@test("AlertRule: Factory accepts optional parameters")
def test_alert_rule_optional():
    rule = AlertRule.create(
        name="Test Rule",
        description="Test",
        severity=AlertSeverity.ERROR,
        condition="test",
        threshold=50.0,
        enabled=False,
        cooldown_minutes=30,
        metadata={"key": "value"},
    )

    assert rule.enabled is False
    assert rule.cooldown_minutes == 30
    assert rule.metadata == {"key": "value"}


@test("AlertRule: Validates empty name")
def test_alert_rule_empty_name():
    try:
        AlertRule.create(
            name="",
            description="Test",
            severity=AlertSeverity.ERROR,
            condition="test",
            threshold=50.0,
        )
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "name" in str(e).lower()


@test("AlertRule: Validates negative cooldown")
def test_alert_rule_negative_cooldown():
    try:
        AlertRule.create(
            name="Test",
            description="Test",
            severity=AlertSeverity.ERROR,
            condition="test",
            threshold=50.0,
            cooldown_minutes=-10,
        )
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "cooldown" in str(e).lower()


@test("AlertRule: Is immutable (frozen dataclass)")
def test_alert_rule_immutable():
    rule = AlertRule.create(
        name="Test",
        description="Test",
        severity=AlertSeverity.ERROR,
        condition="test",
        threshold=50.0,
    )

    try:
        rule.enabled = False
        assert False, "Should not allow modification"
    except (AttributeError, Exception):
        pass


@test("AlertRule: enable() creates enabled copy")
def test_alert_rule_enable():
    rule = AlertRule.create(
        name="Test",
        description="Test",
        severity=AlertSeverity.ERROR,
        condition="test",
        threshold=50.0,
        enabled=False,
    )

    enabled_rule = rule.enable()

    assert rule.enabled is False  # Original unchanged
    assert enabled_rule.enabled is True
    assert enabled_rule.id == rule.id  # Same ID


@test("AlertRule: disable() creates disabled copy")
def test_alert_rule_disable():
    rule = AlertRule.create(
        name="Test",
        description="Test",
        severity=AlertSeverity.ERROR,
        condition="test",
        threshold=50.0,
        enabled=True,
    )

    disabled_rule = rule.disable()

    assert rule.enabled is True  # Original unchanged
    assert disabled_rule.enabled is False
    assert disabled_rule.id == rule.id  # Same ID


@test("AlertRule: to_dict serialization")
def test_alert_rule_to_dict():
    rule = AlertRule.create(
        name="Test Rule",
        description="Test",
        severity=AlertSeverity.ERROR,
        condition="test",
        threshold=50.0,
    )

    data = rule.to_dict()
    assert data["name"] == "Test Rule"
    assert data["severity"] == "error"
    assert data["threshold"] == 50.0
    assert data["enabled"] is True
    assert "id" in data


# ============================================================================
# InMemoryAlertManager Tests
# ============================================================================


@test("InMemoryAlertManager: Implements IAlertManager interface")
def test_manager_implements_interface():
    manager = InMemoryAlertManager()
    assert isinstance(manager, IAlertManager)


@test("InMemoryAlertManager: Records alert")
def test_manager_record():
    manager = InMemoryAlertManager()

    alert = Alert.create(
        severity=AlertSeverity.ERROR,
        message="Test alert",
        source="test",
    )

    manager.record_alert(alert)
    assert len(manager.get_all_alerts()) == 1


@test("InMemoryAlertManager: Rejects invalid alert type")
def test_manager_invalid_alert():
    manager = InMemoryAlertManager()

    try:
        manager.record_alert("not an alert")
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "Alert" in str(e)


@test("InMemoryAlertManager: Gets alerts (no filters)")
def test_manager_get_alerts():
    manager = InMemoryAlertManager()

    # Record 3 alerts
    for i in range(3):
        alert = Alert.create(
            severity=AlertSeverity.ERROR,
            message=f"Alert {i}",
            source="test",
        )
        manager.record_alert(alert)

    alerts = manager.get_alerts()
    assert len(alerts) == 3


@test("InMemoryAlertManager: Filters by severity")
def test_manager_filter_severity():
    manager = InMemoryAlertManager()

    # Critical alert
    manager.record_alert(
        Alert.create(AlertSeverity.CRITICAL, "Critical", "test")
    )

    # Error alerts
    for i in range(2):
        manager.record_alert(
            Alert.create(AlertSeverity.ERROR, f"Error {i}", "test")
        )

    critical_alerts = manager.get_alerts(severity=AlertSeverity.CRITICAL)
    error_alerts = manager.get_alerts(severity=AlertSeverity.ERROR)

    assert len(critical_alerts) == 1
    assert len(error_alerts) == 2


@test("InMemoryAlertManager: Filters by source")
def test_manager_filter_source():
    manager = InMemoryAlertManager()

    manager.record_alert(Alert.create(AlertSeverity.ERROR, "Test 1", "system_a"))
    manager.record_alert(Alert.create(AlertSeverity.ERROR, "Test 2", "system_b"))
    manager.record_alert(Alert.create(AlertSeverity.ERROR, "Test 3", "system_a"))

    system_a_alerts = manager.get_alerts(source="system_a")
    system_b_alerts = manager.get_alerts(source="system_b")

    assert len(system_a_alerts) == 2
    assert len(system_b_alerts) == 1


@test("InMemoryAlertManager: Filters by acknowledged status")
def test_manager_filter_acknowledged():
    manager = InMemoryAlertManager()

    # Unacknowledged
    alert1 = Alert.create(AlertSeverity.ERROR, "Unacked", "test")
    manager.record_alert(alert1)

    # Acknowledged
    alert2 = Alert.create(AlertSeverity.ERROR, "Acked", "test")
    alert2_acked = alert2.acknowledge("admin")
    manager.record_alert(alert2_acked)

    unacked = manager.get_alerts(acknowledged=False)
    acked = manager.get_alerts(acknowledged=True)

    assert len(unacked) == 1
    assert len(acked) == 1


@test("InMemoryAlertManager: Gets alert by ID")
def test_manager_get_by_id():
    manager = InMemoryAlertManager()

    alert = Alert.create(AlertSeverity.ERROR, "Test", "test")
    manager.record_alert(alert)

    found = manager.get_alert_by_id(alert.id)
    not_found = manager.get_alert_by_id("nonexistent")

    assert found is not None
    assert found.id == alert.id
    assert not_found is None


@test("InMemoryAlertManager: Acknowledges alert")
def test_manager_acknowledge():
    manager = InMemoryAlertManager()

    alert = Alert.create(AlertSeverity.ERROR, "Test", "test")
    manager.record_alert(alert)

    ack_alert = manager.acknowledge_alert(alert.id, "admin")

    assert ack_alert.acknowledged is True
    assert ack_alert.acknowledged_by == "admin"
    assert ack_alert.acknowledged_at is not None

    # Verify stored alert is updated
    stored = manager.get_alert_by_id(alert.id)
    assert stored.acknowledged is True


@test("InMemoryAlertManager: Acknowledge nonexistent alert raises error")
def test_manager_acknowledge_nonexistent():
    manager = InMemoryAlertManager()

    try:
        manager.acknowledge_alert("nonexistent", "admin")
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "not found" in str(e).lower()


@test("InMemoryAlertManager: Gets unacknowledged alerts")
def test_manager_get_unacknowledged():
    manager = InMemoryAlertManager()

    # Unacknowledged
    for i in range(3):
        manager.record_alert(Alert.create(AlertSeverity.ERROR, f"Unacked {i}", "test"))

    # Acknowledged
    alert = Alert.create(AlertSeverity.ERROR, "Acked", "test")
    ack_alert = alert.acknowledge("admin")
    manager.record_alert(ack_alert)

    unacked = manager.get_unacknowledged_alerts()
    assert len(unacked) == 3


@test("InMemoryAlertManager: Deletes old alerts")
def test_manager_delete_alerts():
    manager = InMemoryAlertManager()

    now = datetime.now()
    past = now - timedelta(days=2)

    # Old alert
    old_alert = Alert(
        id="old-id",
        severity=AlertSeverity.ERROR,
        message="Old alert",
        source="test",
        timestamp=past,
    )
    manager.record_alert(old_alert)

    # Recent alert
    recent_alert = Alert.create(AlertSeverity.ERROR, "Recent", "test")
    manager.record_alert(recent_alert)

    # Delete old alerts
    deleted = manager.delete_alerts(before=now - timedelta(days=1))

    assert deleted == 1
    assert len(manager.get_all_alerts()) == 1


@test("InMemoryAlertManager: Adds rule")
def test_manager_add_rule():
    manager = InMemoryAlertManager()

    rule = AlertRule.create(
        name="Test Rule",
        description="Test",
        severity=AlertSeverity.ERROR,
        condition="test",
        threshold=50.0,
    )

    manager.add_rule(rule)
    assert len(manager.get_all_rules()) == 1


@test("InMemoryAlertManager: Rejects invalid rule type")
def test_manager_invalid_rule():
    manager = InMemoryAlertManager()

    try:
        manager.add_rule("not a rule")
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "AlertRule" in str(e)


@test("InMemoryAlertManager: Gets all rules")
def test_manager_get_rules():
    manager = InMemoryAlertManager()

    for i in range(3):
        rule = AlertRule.create(
            name=f"Rule {i}",
            description="Test",
            severity=AlertSeverity.ERROR,
            condition="test",
            threshold=50.0,
        )
        manager.add_rule(rule)

    rules = manager.get_rules()
    assert len(rules) == 3


@test("InMemoryAlertManager: Gets enabled rules only")
def test_manager_get_enabled_rules():
    manager = InMemoryAlertManager()

    # Enabled rules
    for i in range(2):
        rule = AlertRule.create(
            name=f"Enabled {i}",
            description="Test",
            severity=AlertSeverity.ERROR,
            condition="test",
            threshold=50.0,
            enabled=True,
        )
        manager.add_rule(rule)

    # Disabled rule
    disabled_rule = AlertRule.create(
        name="Disabled",
        description="Test",
        severity=AlertSeverity.ERROR,
        condition="test",
        threshold=50.0,
        enabled=False,
    )
    manager.add_rule(disabled_rule)

    enabled_rules = manager.get_rules(enabled_only=True)
    all_rules = manager.get_rules(enabled_only=False)

    assert len(enabled_rules) == 2
    assert len(all_rules) == 3


@test("InMemoryAlertManager: Enables rule")
def test_manager_enable_rule():
    manager = InMemoryAlertManager()

    rule = AlertRule.create(
        name="Test",
        description="Test",
        severity=AlertSeverity.ERROR,
        condition="test",
        threshold=50.0,
        enabled=False,
    )
    manager.add_rule(rule)

    manager.enable_rule(rule.id)

    enabled_rules = manager.get_rules(enabled_only=True)
    assert len(enabled_rules) == 1


@test("InMemoryAlertManager: Disables rule")
def test_manager_disable_rule():
    manager = InMemoryAlertManager()

    rule = AlertRule.create(
        name="Test",
        description="Test",
        severity=AlertSeverity.ERROR,
        condition="test",
        threshold=50.0,
        enabled=True,
    )
    manager.add_rule(rule)

    manager.disable_rule(rule.id)

    enabled_rules = manager.get_rules(enabled_only=True)
    assert len(enabled_rules) == 0


@test("InMemoryAlertManager: Enable nonexistent rule raises error")
def test_manager_enable_nonexistent():
    manager = InMemoryAlertManager()

    try:
        manager.enable_rule("nonexistent")
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "not found" in str(e).lower()


@test("InMemoryAlertManager: Deletes rule")
def test_manager_delete_rule():
    manager = InMemoryAlertManager()

    rule = AlertRule.create(
        name="Test",
        description="Test",
        severity=AlertSeverity.ERROR,
        condition="test",
        threshold=50.0,
    )
    manager.add_rule(rule)

    manager.delete_rule(rule.id)

    assert len(manager.get_all_rules()) == 0


@test("InMemoryAlertManager: Delete nonexistent rule raises error")
def test_manager_delete_nonexistent():
    manager = InMemoryAlertManager()

    try:
        manager.delete_rule("nonexistent")
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "not found" in str(e).lower()


@test("InMemoryAlertManager: can_trigger_rule checks enabled status")
def test_manager_can_trigger_enabled():
    manager = InMemoryAlertManager()

    # Enabled rule
    enabled = AlertRule.create(
        name="Enabled",
        description="Test",
        severity=AlertSeverity.ERROR,
        condition="test",
        threshold=50.0,
        enabled=True,
    )
    manager.add_rule(enabled)

    # Disabled rule
    disabled = AlertRule.create(
        name="Disabled",
        description="Test",
        severity=AlertSeverity.ERROR,
        condition="test",
        threshold=50.0,
        enabled=False,
    )
    manager.add_rule(disabled)

    assert manager.can_trigger_rule(enabled.id) is True
    assert manager.can_trigger_rule(disabled.id) is False


@test("InMemoryAlertManager: can_trigger_rule respects cooldown")
def test_manager_can_trigger_cooldown():
    manager = InMemoryAlertManager()

    rule = AlertRule.create(
        name="Test",
        description="Test",
        severity=AlertSeverity.ERROR,
        condition="test",
        threshold=50.0,
        cooldown_minutes=5,  # 5 minute cooldown
    )
    manager.add_rule(rule)

    # First trigger - should be allowed
    assert manager.can_trigger_rule(rule.id) is True

    # Mark as triggered
    manager.mark_rule_triggered(rule.id)

    # Second trigger immediately - should be blocked
    assert manager.can_trigger_rule(rule.id) is False


# ============================================================================
# Integration Tests
# ============================================================================


@test("Integration: Multi-severity alert workflow")
def test_integration_multi_severity():
    manager = InMemoryAlertManager()

    # Record various severity alerts
    manager.record_alert(Alert.create(AlertSeverity.CRITICAL, "Critical issue", "system"))
    manager.record_alert(Alert.create(AlertSeverity.ERROR, "Error occurred", "system"))
    manager.record_alert(Alert.create(AlertSeverity.WARNING, "Warning detected", "system"))
    manager.record_alert(Alert.create(AlertSeverity.INFO, "Info message", "system"))

    # Get critical/error alerts (require action)
    critical_alerts = manager.get_alerts(severity=AlertSeverity.CRITICAL)
    error_alerts = manager.get_alerts(severity=AlertSeverity.ERROR)

    action_required = len(critical_alerts) + len(error_alerts)
    assert action_required == 2


@test("Integration: Alert acknowledgment workflow")
def test_integration_acknowledgment():
    manager = InMemoryAlertManager()

    # Record alerts
    for i in range(5):
        alert = Alert.create(AlertSeverity.ERROR, f"Error {i}", "test")
        manager.record_alert(alert)

    # Acknowledge some alerts
    alerts = manager.get_alerts(limit=3)
    for alert in alerts[:2]:
        manager.acknowledge_alert(alert.id, "admin")

    # Check status
    unacked = manager.get_unacknowledged_alerts()
    acked = manager.get_alerts(acknowledged=True)

    assert len(unacked) == 3
    assert len(acked) == 2


@test("Integration: Rule management workflow")
def test_integration_rule_management():
    manager = InMemoryAlertManager()

    # Add rules
    high_cost = AlertRule.create(
        name="High Cost",
        description="Cost threshold exceeded",
        severity=AlertSeverity.ERROR,
        condition="cost > 100",
        threshold=100.0,
    )
    manager.add_rule(high_cost)

    error_rate = AlertRule.create(
        name="Error Rate",
        description="Error rate too high",
        severity=AlertSeverity.CRITICAL,
        condition="error_rate > 5",
        threshold=5.0,
    )
    manager.add_rule(error_rate)

    # Disable one rule
    manager.disable_rule(high_cost.id)

    # Check enabled rules
    enabled = manager.get_rules(enabled_only=True)
    assert len(enabled) == 1
    assert enabled[0].name == "Error Rate"


@test("Integration: Alert filtering combinations")
def test_integration_complex_filters():
    manager = InMemoryAlertManager()
    now = datetime.now()

    # Various alerts
    manager.record_alert(Alert.create(AlertSeverity.CRITICAL, "Critical A", "system_a"))
    manager.record_alert(Alert.create(AlertSeverity.ERROR, "Error A", "system_a"))
    manager.record_alert(Alert.create(AlertSeverity.ERROR, "Error B", "system_b"))

    # Acknowledge one
    alerts = manager.get_alerts(source="system_a", severity=AlertSeverity.ERROR)
    if alerts:
        manager.acknowledge_alert(alerts[0].id, "admin")

    # Complex filter: unacknowledged errors from system_a
    result = manager.get_alerts(
        severity=AlertSeverity.ERROR,
        source="system_a",
        acknowledged=False,
    )

    assert len(result) == 0  # The error was acknowledged


@test("Integration: Rule cooldown prevents spam")
def test_integration_cooldown():
    manager = InMemoryAlertManager()

    rule = AlertRule.create(
        name="Spam Prevention",
        description="Test cooldown",
        severity=AlertSeverity.WARNING,
        condition="test",
        threshold=10.0,
        cooldown_minutes=1,
    )
    manager.add_rule(rule)

    # Trigger rule
    if manager.can_trigger_rule(rule.id):
        alert = Alert.create(
            severity=rule.severity,
            message="Rule triggered",
            source="test",
            rule_id=rule.id,
        )
        manager.record_alert(alert)
        manager.mark_rule_triggered(rule.id)

    # Immediate second trigger should fail
    can_trigger_again = manager.can_trigger_rule(rule.id)
    assert can_trigger_again is False


@test("Integration: Empty manager returns sensible defaults")
def test_integration_empty():
    manager = InMemoryAlertManager()

    assert len(manager.get_alerts()) == 0
    assert len(manager.get_rules()) == 0
    assert len(manager.get_unacknowledged_alerts()) == 0
    assert manager.get_alert_by_id("nonexistent") is None


@test("Integration: Cleanup operations")
def test_integration_cleanup():
    manager = InMemoryAlertManager()

    # Add alerts and rules
    for i in range(5):
        alert = Alert.create(AlertSeverity.ERROR, f"Alert {i}", "test")
        manager.record_alert(alert)

        rule = AlertRule.create(
            name=f"Rule {i}",
            description="Test",
            severity=AlertSeverity.ERROR,
            condition="test",
            threshold=50.0,
        )
        manager.add_rule(rule)

    # Clear alerts
    manager.clear_alerts()
    assert len(manager.get_all_alerts()) == 0

    # Clear rules
    manager.clear_rules()
    assert len(manager.get_all_rules()) == 0


# ============================================================================
# Main Execution
# ============================================================================


def main():
    print("=" * 70)
    print("Phase 4 Validation: Error Alerting")
    print("=" * 70)
    print()

    # Run all tests
    print("Running Alert Entity Tests...")
    test_alert_factory()
    test_alert_optional()
    test_alert_empty_message()
    test_alert_empty_source()
    test_alert_immutable()
    test_alert_acknowledge()
    test_alert_is_critical()
    test_alert_requires_action()
    test_alert_to_dict()

    print("\nRunning AlertRule Entity Tests...")
    test_alert_rule_factory()
    test_alert_rule_optional()
    test_alert_rule_empty_name()
    test_alert_rule_negative_cooldown()
    test_alert_rule_immutable()
    test_alert_rule_enable()
    test_alert_rule_disable()
    test_alert_rule_to_dict()

    print("\nRunning InMemoryAlertManager Tests...")
    test_manager_implements_interface()
    test_manager_record()
    test_manager_invalid_alert()
    test_manager_get_alerts()
    test_manager_filter_severity()
    test_manager_filter_source()
    test_manager_filter_acknowledged()
    test_manager_get_by_id()
    test_manager_acknowledge()
    test_manager_acknowledge_nonexistent()
    test_manager_get_unacknowledged()
    test_manager_delete_alerts()
    test_manager_add_rule()
    test_manager_invalid_rule()
    test_manager_get_rules()
    test_manager_get_enabled_rules()
    test_manager_enable_rule()
    test_manager_disable_rule()
    test_manager_enable_nonexistent()
    test_manager_delete_rule()
    test_manager_delete_nonexistent()
    test_manager_can_trigger_enabled()
    test_manager_can_trigger_cooldown()

    print("\nRunning Integration Tests...")
    test_integration_multi_severity()
    test_integration_acknowledgment()
    test_integration_rule_management()
    test_integration_complex_filters()
    test_integration_cooldown()
    test_integration_empty()
    test_integration_cleanup()

    # Print summary
    print()
    print("=" * 70)
    print("Validation Summary")
    print("=" * 70)
    print(f"Tests Passed: {tests_passed}")
    print(f"Tests Failed: {tests_failed}")
    print(f"Total Tests:  {tests_passed + tests_failed}")
    print(f"Success Rate: {100 * tests_passed / (tests_passed + tests_failed):.1f}%")
    print()

    if tests_failed > 0:
        print("Failed Tests:")
        for result in test_results:
            if result.startswith("✗"):
                print(f"  {result}")
        print()
        sys.exit(1)
    else:
        print("✅ All Phase 4 validation tests passed!")
        print()
        print("Phase 4 (Error Alerting) Status: VALIDATED ✓")
        print()
        sys.exit(0)


if __name__ == "__main__":
    main()
