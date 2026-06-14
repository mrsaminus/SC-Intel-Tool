from types import SimpleNamespace

from conftest import isolated_database, reload_module
from app.wikelo_client import WikeloItem, WikeloRequirement


def bind_wikelo_logic(tab_class):
    tab = SimpleNamespace()
    for name in (
        "build_wikelo_group",
        "checklist_material_key",
        "checklist_option_key",
        "group_wikelo_items",
        "grouped_requirement_rows",
        "unique_group_requirements",
        "wikelo_group_key",
    ):
        setattr(tab, name, getattr(tab_class, name).__get__(tab, object))
    return tab


def wikelo_item(name, mission, requirements, source_sheet="Ships 4.7", retired=False):
    return WikeloItem(
        item_id=f"{source_sheet}-{mission}-{name}",
        item_name=name,
        category="Ship",
        item_type="Reward",
        reward_method=mission,
        mission_name=mission,
        requirements=tuple(requirements),
        reward_item=name,
        location="Stanton",
        source_sheet=source_sheet,
        source_url="https://example.test/wikelo",
        notes="",
        updated="4.7",
        retired=retired,
    )


def test_wikelo_grouping_collapses_duplicate_reward_names(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    wikelo_tab = reload_module("app.gui.wikelo_tab")
    tab = bind_wikelo_logic(wikelo_tab.WikeloItemsTab)

    items = [
        wikelo_item(" Wikelo Favor ", "Pearl Exchange", [WikeloRequirement("Pearl", "12x")]),
        wikelo_item("wikelo favor", "Carnite Exchange", [WikeloRequirement("Carnite", "50x")]),
    ]

    grouped = tab.group_wikelo_items(items)

    assert len(grouped) == 1
    assert grouped[0].reward_method == "2 trade-in options"
    assert len(grouped[0].options) == 2
    assert {requirement.name for requirement in grouped[0].requirements} == {"Pearl", "Carnite"}


def test_wikelo_requirement_rows_keep_materials_under_one_option(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    wikelo_tab = reload_module("app.gui.wikelo_tab")
    tab = bind_wikelo_logic(wikelo_tab.WikeloItemsTab)
    item = wikelo_item(
        "Zeus ES",
        "Build a Mod Zeus",
        [
            WikeloRequirement("Wikelo Favor", "15x"),
            WikeloRequirement("DCHS-05 Comp-Board", "4x", "Salvage"),
        ],
    )
    group = tab.build_wikelo_group((item,))

    rows = tab.grouped_requirement_rows(group, "zeus-es", {})

    assert [row["type"] for row in rows] == ["option", "material", "material"]
    assert rows[0]["label"].startswith("Option 1 - Build a Mod Zeus")
    assert rows[1]["name"] == "Wikelo Favor"
    assert rows[2]["source"] == "Salvage"
