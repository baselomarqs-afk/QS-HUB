def test_readiness_static_checks_pass():
    import production_readiness as readiness

    errors = []
    errors.extend(readiness.check_files())
    errors.extend(readiness.check_secret_leaks())

    assert errors == []
