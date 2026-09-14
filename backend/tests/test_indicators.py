from app.api.indicator_routes import formula_engine


def test_custom_indicator_formula_is_validated_before_persistence() -> None:
    assert formula_engine.validate("(par30 * 0.5) + par90") == []
    assert formula_engine.validate("__import__('os').system('whoami')")
