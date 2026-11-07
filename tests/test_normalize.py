from rdcap.normalize import Normalizer, clean_text, to_iso_date, to_number


def test_clean_text_removes_accents_case_and_spaces():
    assert clean_text("  Résine  PVC Pâte ") == "resine pvc pate"


def test_to_number_handles_decimal_comma_and_missing():
    assert to_number("1,5") == 1.5
    assert to_number(60) == 60.0
    assert to_number("n.d.") is None
    assert to_number(None) is None


def test_dates_in_several_formats():
    assert to_iso_date("12/03/2024") == "2024-03-12"
    assert to_iso_date("2021-06-05") == "2021-06-05"
    assert to_iso_date("pas une date") is None


def test_component_aliases_map_to_one_name():
    norm = Normalizer()
    for raw in ["DINP", "Dinp", "plastifiant DINP", "DINP "]:
        assert norm.component(raw) == ("DINP", "plastifiant")
    assert norm.component("plastifant DINP") == (None, None)   # typo is not guessed


def test_unit_conversions():
    norm = Normalizer()
    m = norm.measurement("Visco 1h", 4.5, "Pa.s")
    assert m["property"] == "viscosite_1h" and m["value"] == 4500 and m["unit"] == "mPa.s"
    m = norm.measurement("Temps de stabilité", 1200, "s")
    assert m["property"] == "stabilite_thermique" and m["value"] == 20
