from typing import TYPE_CHECKING, OrderedDict

if TYPE_CHECKING:
    from .types import Snowflake


BUG_CENTER_ID: "Snowflake" = 595218682670481418
ASK_CHANNEL_ID = 870023524985761822
ASK_MESSAGE_ID = 870032630119276645

STAFF_ROLES: dict[str, "Snowflake"] = {
    "administrator": 713434163587579986,
    "assistant": 627445515159732224,
    "screening": 713452724603191367,
    "brillant": 713452621196820510,
    "normal": 627836152350769163,
}

HELP_CHANNELS_IDS: list["Snowflake"] = [
    692712497844584448,  # general_tech
    833077274458849340,  # tech_international
    870023524985761822,  # ask_for_help
]

TEST_CHANNELS_IDS: list["Snowflake"] = [
    595224241742413844,  # tests-1
    595224271132033024,  # tests-2
    595232117806333965,  # cmds-staff
    711599221220048989,  # cmds-admin
]

AUTHORIZED_CHANNELS_IDS: list["Snowflake"] = TEST_CHANNELS_IDS + HELP_CHANNELS_IDS

LANGUAGE_ROLES: OrderedDict["Snowflake", str] = OrderedDict(
    ((797581355785125889, "fr_FR"), (797581356749946930, "en_EN"))
)  # OrderedDict to make French in prior of English
