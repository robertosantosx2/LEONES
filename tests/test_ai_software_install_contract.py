from pathlib import Path


ROOT = Path(__file__).parents[1]
INSTALLER = ROOT / "install.sh"
CONTRACT = ROOT / "docs" / "AI_SOFTWARE_INSTALL_CONTRACT_RC4.md"


COMPONENTS = {
    "fitllm": "install_fitllm",
    "ods": "install_ods",
    "magnitude": "install_magnitude",
    "hermes": "install_hermes",
    "omh": "install_omh",
}


def test_permanent_ai_software_install_contract_exists():
    text = CONTRACT.read_text(encoding="utf-8")
    for required in (
        "Instalación desde cero",
        "Detección de instalación rota",
        "Detección de versión actual",
        "Versión antigua → actualización real",
        "Verificación operacional posterior",
        "cualquier componente IA futuro",
    ):
        assert required in text


def test_installer_declares_update_semantics():
    text = INSTALLER.read_text(encoding="utf-8")
    assert "latest stable upstream release" in text
    assert "updates it when a newer version exists" in text


def test_current_ai_components_have_version_aware_paths():
    text = INSTALLER.read_text(encoding="utf-8")
    for component, function in COMPONENTS.items():
        start = text.index(f"{function}() {{")
        end = text.find("\n}\n", start)
        block = text[start : end + 3 if end != -1 else len(text)]
        assert "current" in block, component
        assert "latest" in block, component
        assert "require_latest_version" in block, component
        assert "operativo" in block or "operational" in block, component


def test_future_components_are_explicitly_required_to_follow_contract():
    text = CONTRACT.read_text(encoding="utf-8")
    assert "todo software IA que LEONES gestione" in text
    assert "cualquier componente IA futuro" in text
    assert "añadir pruebas" in text
