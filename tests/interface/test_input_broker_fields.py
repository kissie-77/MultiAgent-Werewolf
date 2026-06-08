import asyncio

from llm_werewolf.interface.api.services.human_input import HumanInputBroker


class _CaptureBroadcaster:
    def __init__(self):
        self.events = []

    def publish(self, event):
        self.events.append(event)


def test_request_publishes_structured_fields():
    cap = _CaptureBroadcaster()
    broker = HumanInputBroker(run_id="r1", seat=1, broadcaster=cap)

    async def drive():
        task = asyncio.create_task(
            broker.request(
                kind="witch",
                prompt="p",
                valid_targets=[2, 4],
                fallback="none",
                deadline=0.2,
                ui_hint="h",
                title="女巫行动",
                allow_skip=False,
                allow_witch_save=True,
                multi_count=0,
                self_role="Witch",
                kill_target_seat=3,
                remaining_potions={"save": True, "poison": True},
                question="今夜 3 号被狼人袭击，是否用解药？",
                target_meta=[{"seat": 2, "name": "Player2"}],
            )
        )
        await asyncio.sleep(0.01)
        rid = next(iter(broker.pending_ids()))
        broker.submit(request_id=rid, payload="none")
        return await task

    asyncio.run(drive())
    awaiting = [e for e in cap.events if e.get("event_type") == "awaiting_input"][0]
    assert awaiting["self_role"] == "Witch"
    assert awaiting["kill_target_seat"] == 3
    assert awaiting["remaining_potions"] == {"save": True, "poison": True}
    assert awaiting["question"] == "今夜 3 号被狼人袭击，是否用解药？"
    assert awaiting["target_meta"] == [{"seat": 2, "name": "Player2"}]
