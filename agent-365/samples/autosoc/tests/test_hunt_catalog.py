import pytest

from hunt_catalog import HUNT_CATALOG, eligible_hunts
from models import EntityType, IncidentContext


def test_catalog_eligibility_and_bounded_projection():
    context = IncidentContext(
        incident_id="1",
        entities={EntityType.IP_ADDRESS: ["192.0.2.1"]},
    )

    definitions = eligible_hunts(context)

    assert [definition.hunt_id for definition in definitions] == [
        "related_alerts",
        "threat_intelligence",
    ]
    for definition in definitions:
        query = definition.render(context)
        assert "| project" in query
        assert "| top 100" in query


def test_entity_text_is_encoded_as_dynamic_data():
    hostile_value = "host'); drop table SecurityEvent; //"
    context = IncidentContext(
        incident_id="1",
        entities={EntityType.HOSTNAME: [hostile_value]},
    )

    query = HUNT_CATALOG["windows_sign_in"].render(context)

    assert f'dynamic(["{hostile_value}"])' in query
    assert query.count(hostile_value) == 1


def test_ineligible_hunt_cannot_render():
    context = IncidentContext(incident_id="1")
    with pytest.raises(ValueError):
        HUNT_CATALOG["entra_sign_in"].render(context)
