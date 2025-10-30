"""Unit tests for utils.message_handler.MessageHandler and Message."""
from utils.message_handler import Message, MessageHandler


def test_add_and_pop_unresolved_behaviour():
    mh = MessageHandler()

    m1 = Message(player_id="p1", to_email="a@example.com", subject="S1", body="B1")
    m2 = Message(player_id="p2", to_email="b@example.com", subject="S2", body="B2")
    m3 = Message(player_id="p1", to_email="a@example.com", subject="S3", body="B3")

    mh.add(m1)
    mh.add(m2)
    mh.add(m3)

    # LIFO: most recently added unresolved should be returned first
    popped = mh.pop_unresolved()
    assert popped is not None
    assert popped.id == m3.id

    # resolve m2 by id
    assert mh.resolve(m2.id, "resp B2") is True
    assert m2.resolved is True
    assert m2.response == "resp B2"

    # remaining unresolved should be only m1
    unresolved = mh.get_unresolved()
    assert len(unresolved) == 1
    assert unresolved[0].id == m1.id


def test_find_by_player_and_len():
    mh = MessageHandler()
    m1 = Message(player_id="p1", to_email="a@example.com", subject="S1", body="B1")
    m2 = Message(player_id="p2", to_email="b@example.com", subject="S2", body="B2")
    mh.add(m1)
    mh.add(m2)

    assert len(mh) == 2
    p1_msgs = mh.find_by_player("p1")
    assert len(p1_msgs) == 1 and p1_msgs[0].player_id == "p1"

    # resolving decreases length
    mh.resolve(m1.id, "ok")
    assert len(mh) == 1


def test_player_can_send_message_to_handler():
    from game.player import Player
    mh = MessageHandler()
    p = Player("Gina", "gina@example.com")

    msg = p.send_message(mh, "dest@example.com", "Question", "What is 2+2?")
    # handler length should reflect the added unresolved message
    assert len(mh) == 1
    # message should be associated with player's player_id
    assert msg.player_id == p.player_id
    # the message should be findable via handler
    found = mh.find_by_player(p.player_id)
    assert len(found) == 1 and found[0].id == msg.id


def test_resolve_requires_correct_number_of_ints():
    mh = MessageHandler()
    m = Message(player_id="p1", to_email="a@example.com", subject="Nums", body="Please reply", required_ints=2)
    mh.add(m)

    # invalid (only one int) without reopen -> should return False, but a
    # follow-up message is automatically created and the original is closed
    assert mh.resolve(m.id, "42") is False
    assert m.resolved is True

    # there should now be a fresh unresolved message for this player
    p_msgs = mh.find_by_player("p1")
    assert len(p_msgs) == 1
    assert p_msgs[0].id != m.id

    # valid response with two ints on the fresh message
    new_msg = p_msgs[0]
    assert mh.resolve(new_msg.id, "3 4") is True
    assert new_msg.resolved is True
    assert new_msg.response == "3 4"


def test_reopen_on_invalid_creates_new_message():
    mh = MessageHandler()
    m = Message(player_id="p1", to_email="a@example.com", subject="Nums", body="Please reply", required_ints=2)
    mh.add(m)

    # invalid response should close the original and add a new unresolved follow-up
    result = mh.resolve(m.id, "not numbers", reopen_on_invalid=True)
    assert result is False
    assert m.resolved is True
    # there should be a new unresolved message for same player
    p_msgs = mh.find_by_player("p1")
    assert len(p_msgs) == 1
    assert p_msgs[0].id != m.id


def test_messages_can_be_resolved_in_any_order():
    mh = MessageHandler()
    m1 = Message(player_id="p1", to_email="a@example.com", subject="A", body="B")
    m2 = Message(player_id="p2", to_email="b@example.com", subject="C", body="D")
    m3 = Message(player_id="p3", to_email="c@example.com", subject="E", body="F")
    mh.add(m1)
    mh.add(m2)
    mh.add(m3)

    # resolve middle message first
    assert mh.resolve(m2.id, "ok") is True
    assert m2.resolved is True

    # pop_unresolved should skip resolved and return the most recent unresolved (m3)
    popped = mh.pop_unresolved()
    assert popped.id == m3.id
    # now resolve remaining m1
    assert mh.resolve(m1.id, "ok") is True
    assert m1.resolved is True


def test_batch_callback_invoked_when_all_resolved():
    mh = MessageHandler()
    called = {}

    def cb(msgs):
        called['msgs'] = msgs

    m1 = Message(player_id="p1", to_email="a@example.com", subject="A", body="B", batch_id="batch1")
    m2 = Message(player_id="p2", to_email="b@example.com", subject="C", body="D", batch_id="batch1")
    mh.add(m1)
    mh.add(m2)
    mh.register_callback("batch1", cb)

    # resolve in any order
    assert mh.resolve(m2.id, "ok") is True
    assert 'msgs' not in called
    assert mh.resolve(m1.id, "ok") is True
    # now callback should have been invoked
    assert 'msgs' in called
    msgs = called['msgs']
    assert len(msgs) == 2
    assert all(m.resolved for m in msgs)
