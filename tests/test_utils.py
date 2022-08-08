from src.utils import ExtendedColor, constants


def test_constants():
    assert constants.ASK_CHANNEL_ID == 870023524985761822
    assert constants.ASK_MESSAGE_ID == 870032630119276645
    assert constants.BUG_CENTER_ID == 595218682670481418


def test_extended_color():
    assert ExtendedColor.default().to_matplotlib(0.0) == (0.0, 0.0, 0.0, 0.0)
