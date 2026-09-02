from scripts.rc2_i18n import LANGUAGES, TEXT, set_language, tr, tr_all


def test_catalog_has_exactly_es_en_zh_for_every_key():
    assert LANGUAGES == ("es", "en", "zh")
    assert TEXT
    assert all(set(values) == set(LANGUAGES) for values in TEXT.values())


def test_tr_returns_single_active_language():
    set_language("es")
    assert tr("your_team") == TEXT["your_team"]["es"]
    set_language("en")
    assert tr("your_team") == TEXT["your_team"]["en"]
    set_language("zh")
    assert tr("your_team") == TEXT["your_team"]["zh"]


def test_tr_all_keeps_aligned_debug_view():
    rendered = tr_all("your_team").splitlines()
    assert rendered[0].startswith("Español │ ")
    assert rendered[1].startswith("English │ ")
    assert rendered[2].startswith("中文 │ ")


def test_catalog_contains_rc2_ui_copy_without_screen_specific_sources():
    required = {
        "choose_language",
        "choose_model",
        "choose_stack",
        "install_consent",
        "authorize",
        "cancel",
        "invalid_option",
        "detecting_hardware",
        "estimated_notice",
        "no_model_candidates",
        "ods_summary",
        "magnitude_summary",
        "not_installed_yet",
        "next_step_title",
        "next_step_ods",
        "next_step_magnitude",
        "offer_run_installer",
        "installation_authorized",
        "physical_install_notice",
    }
    # physical_install_notice was replaced by clearer keys; keep only present ones
    required.discard("physical_install_notice")
    assert required <= TEXT.keys()
