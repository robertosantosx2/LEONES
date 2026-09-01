from scripts.rc2_i18n import LANGUAGES, TEXT, tr


def test_catalog_has_exactly_es_en_zh_for_every_key():
    assert LANGUAGES == ("es", "en", "zh")
    assert TEXT
    assert all(set(values) == set(LANGUAGES) for values in TEXT.values())


def test_translations_are_tabulated_and_ordered():
    rendered = tr("your_team").splitlines()
    assert rendered[0].startswith("ES │ ")
    assert rendered[1].startswith("EN │ ")
    assert rendered[2].startswith("ZH │ ")
    assert rendered[0] != rendered[1] != rendered[2]


def test_catalog_contains_rc2_ui_copy_without_screen_specific_sources():
    required = {
        "choose_model",
        "choose_stack",
        "install_consent",
        "authorize",
        "cancel",
        "invalid_option",
        "detecting_hardware",
        "estimated_notice",
        "no_model_candidates",
        "ods_capability_1",
        "magnitude_capability_1",
        "installation_authorized",
        "physical_install_notice",
    }
    assert required <= TEXT.keys()
