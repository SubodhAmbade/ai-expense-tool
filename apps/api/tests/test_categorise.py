import numpy as np

from app.categorise import CATEGORIES, by_description, by_examples, by_rules


def test_rules_use_merchant_name_then_items() -> None:
    by_name = by_rules("AIK HUAT HARDWARE ENTERPRISE\nNO 1 JALAN SETIA\nTOTAL 12.00")
    by_items = by_rules(
        "UNIHAKKA INTERNATIONAL SDN BHD\nNASI LEMAK 6.50\nTEH TARIK 2.00\nTOTAL 8.50"
    )
    unknown = by_rules("ABC HO TRADING\nTOTAL 5.00")
    assert (by_name.category, by_name.confidence) == ("repairs_maintenance", 0.9)
    assert (by_items.category, by_items.confidence) == ("meals", 0.6)
    assert (unknown.category, unknown.confidence) == ("other", 0.0)


def test_description_picks_closest_category_with_gap_as_confidence() -> None:
    category_vectors = np.eye(len(CATEGORIES))
    vector = np.zeros(len(CATEGORIES))
    vector[1], vector[0] = 1.0, 0.95  # groceries just ahead of meals
    result = by_description(vector, category_vectors)
    assert result.category == "groceries"
    assert result.confidence == 0.5


def test_examples_vote_among_nearest_neighbours() -> None:
    examples = np.array([[1.0, 0.0], [0.9, 0.1], [0.8, 0.2], [0.0, 1.0], [0.1, 0.9]])
    labels = ["meals", "meals", "groceries", "transport", "transport"]
    result = by_examples(np.array([1.0, 0.0]), examples, labels, k=3)
    assert (result.category, result.confidence) == ("meals", 0.667)
