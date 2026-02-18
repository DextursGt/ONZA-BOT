"""Tests for fraud detection logic."""
import pytest
import datetime
from unittest.mock import Mock
from events.cogs.invite_tracker import InviteTracker


def make_member(member_id: int, account_days_old: int = 30):
    member = Mock()
    member.id = member_id
    member.created_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=account_days_old)
    return member


def make_invite(code: str, inviter_id: int):
    invite = Mock()
    invite.code = code
    invite.inviter = Mock()
    invite.inviter.id = inviter_id
    return invite


def test_self_invite_detected():
    """Test self-invite is flagged as fraud."""
    bot = Mock()
    tracker = InviteTracker(bot)

    member = make_member(member_id=999)
    invite = make_invite("abc", inviter_id=999)  # Same ID

    is_fraud, reason = tracker._check_fraud(member, invite, inviter_id="999")
    assert is_fraud is True
    assert reason == "self_invite"


def test_new_account_detected():
    """Test account < 7 days old is flagged as fraud."""
    bot = Mock()
    tracker = InviteTracker(bot)

    member = make_member(member_id=123, account_days_old=3)
    invite = make_invite("abc", inviter_id=456)

    is_fraud, reason = tracker._check_fraud(member, invite, inviter_id="456")
    assert is_fraud is True
    assert reason == "new_account"


def test_legitimate_invite_passes():
    """Test normal invite is not flagged."""
    bot = Mock()
    tracker = InviteTracker(bot)

    member = make_member(member_id=123, account_days_old=30)
    invite = make_invite("abc", inviter_id=456)

    is_fraud, reason = tracker._check_fraud(member, invite, inviter_id="456")
    assert is_fraud is False
    assert reason is None


def test_exactly_7_days_old_passes():
    """Test account exactly 7 days old passes (boundary)."""
    bot = Mock()
    tracker = InviteTracker(bot)

    member = make_member(member_id=123, account_days_old=7)
    invite = make_invite("abc", inviter_id=456)

    is_fraud, reason = tracker._check_fraud(member, invite, inviter_id="456")
    assert is_fraud is False
