"""Unit tests for RC4 component inventory and independent uninstall offers."""

from __future__ import annotations

from scripts import rc4_component_inventory as inv


def test_catalog_has_leones_last_and_core_ids():
    ids = [c["component_id"] for c in inv.CATALOG]
    assert "fitllm" in ids
    assert "magnitude" in ids
    assert "ods" in ids
    assert "hermes" in ids
    assert "omh" in ids
    assert "llms" in ids
    assert "leones" in ids
    assert ids[-1] == "leones"
    assert inv.CATALOG[-1].get("offer_last") is True


def test_inventory_schema_and_rules(monkeypatch):
    monkeypatch.setattr(inv, "_cmd_present", lambda name: None)
    monkeypatch.setattr(inv, "_ollama_models", lambda: [])
    monkeypatch.setattr(inv.Path, "exists", lambda self: False)

    result = inv.inventory()
    assert result["schema"] == inv.SCHEMA
    assert result["rules"]["independent_uninstall"] is True
    assert result["rules"]["leones_offered_last"] is True
    assert result["rules"]["no_implicit_all"] is True
    assert result["rules"]["evidence_not_deleted_by_default"] is True
    assert isinstance(result["components"], list)
    assert len(result["components"]) == len(inv.CATALOG)


def test_uninstall_offers_only_installed_and_leones_last(monkeypatch):
    def fake_probe(entry):
        cid = entry["component_id"]
        installed = cid in {"fitllm", "ods", "leones"}
        return {
            "component_id": cid,
            "display_name": entry["display_name"],
            "group": entry["group"],
            "installed": installed,
            "path": f"/fake/{cid}" if installed else None,
            "detected_via": "command" if installed else None,
            "version": None,
            "uninstall_flag": entry.get("uninstall_flag"),
            "uninstallable": entry.get("uninstall_flag") is not None,
            "notes": entry.get("notes", ""),
            "offer_last": bool(entry.get("offer_last")),
        }

    monkeypatch.setattr(inv, "probe_component", fake_probe)
    result = inv.inventory()
    offers = result["uninstall_offers"]
    ids = [o["component_id"] for o in offers]
    assert ids == ["fitllm", "ods", "leones"]
    assert offers[-1]["component_id"] == "leones"
    assert all(o["opt_in_required"] is True for o in offers)
    assert all(o["independent"] is True for o in offers)


def test_render_ascii_contains_panel(monkeypatch):
    monkeypatch.setattr(inv, "_cmd_present", lambda name: None)
    monkeypatch.setattr(inv, "_ollama_models", lambda: [])
    monkeypatch.setattr(inv.Path, "exists", lambda self: False)
    text = inv.render_ascii(inv.inventory())
    assert "INVENTARIO DE COMPONENTES" in text
    assert "DESINSTALACIÓN INDEPENDIENTE" in text
    assert "╔" in text


def test_ollama_runtime_not_uninstallable_by_default():
    ollama = next(c for c in inv.CATALOG if c["component_id"] == "ollama")
    assert ollama["uninstall_flag"] is None
