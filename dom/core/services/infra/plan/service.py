from dom.types.config import DomConfig


def plan_infra_and_platform(config: DomConfig) -> None:
    # Dummy logic for now
    print("🔍 PLAN: Checking infrastructure...")
    print(f"Will start services: {config.infra}")

    print("🔍 PLAN: Checking contests...")
    for contest in config.contests:
        print(f"Would create/update contest: {contest.get('name')}")
