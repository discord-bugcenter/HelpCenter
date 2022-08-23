from src.utils import ExtendedColor, constants


def test_constants():
    assert constants.NEW_REQUEST_CHANNEL_ID == 870023524985761822
    assert constants.REQUEST_MESSAGE_ID == 870032630119276645
    assert constants.BUG_CENTER_ID == 595218682670481418
    assert constants.REQUESTS_CHANNEL_ID == 1011603777138208858


def test_extended_color():
    assert ExtendedColor.default().to_matplotlib(0.0) == (0.0, 0.0, 0.0, 0.0)
