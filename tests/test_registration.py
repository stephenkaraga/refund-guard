from tau2.registry import registry

from merchant_ops.register import BASELINE_AGENT, GUARDED_AGENT, register


def test_register_is_idempotent():
    register()
    register()
    assert "merchant_ops" in registry.get_domains()
    assert {BASELINE_AGENT, GUARDED_AGENT} <= set(registry.get_agents())


def test_agent_builds_from_factory():
    register()
    env = registry.get_env_constructor("merchant_ops")()
    factory = registry.get_agent_factory(GUARDED_AGENT)
    agent = factory(env.get_tools(), env.get_policy(), llm="fake/model")
    state = agent.get_init_state()
    assert "Merchant Support Agent Policy" in state.system_messages[0].content
