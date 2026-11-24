from kitchencompass.service import get_catalog


def test_catalog_cache_key_distinguishes_data_and_config_versions():
    get_catalog.cache_clear()
    first = get_catalog(("2.0", "0.4.0", "manifest-a"))
    assert get_catalog(("2.0", "0.4.0", "manifest-a")) is first

    changed_data = get_catalog(("2.1", "0.4.0", "manifest-a"))
    assert changed_data is not first

    changed_config = get_catalog(("2.0", "0.4.1", "manifest-a"))
    assert changed_config is not first
    get_catalog.cache_clear()
