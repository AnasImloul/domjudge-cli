def plan_infra_and_platform(config: dict) -> None:
    # Dummy logic for now
    print("🔍 PLAN: Checking infrastructure...")
    print(f"Will start services: {config.get('infra', {}).get('services', [])}")

    print("🔍 PLAN: Checking contests...")
    for contest in config.get("contests", []):
        print(f"Would create/update contest: {contest.get('name')}")
