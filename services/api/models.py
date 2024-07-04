"""Hex API Models."""
import datetime

from typing import Dict
from typing import List
# from typing import Union
from typing_extensions import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

# pylint: disable=line-too-long


class Book(BaseModel):
    """Book class."""
    id: str
    amazon_link: str
    code: str
    date: str
    isbn_10: str = Field(alias="isbn-10", validation_alias="isbn-10")
    isbn_13: str = Field(alias="isbn-13", validation_alias="isbn-13")
    notes: str
    publisher: str
    source: str
    title: str

    model_config = ConfigDict(extra="forbid")


class ClueGroupSettings(BaseModel):
    """Clue Group Settings class."""
    reverse_grid_entries: bool | None = None
    show_enumerations: str | None = None
    show_grid_entries: bool | None = None
    show_grid_labels: bool | None = None

    model_config = ConfigDict(extra="forbid")


class ClueGroup(BaseModel):
    """ClueGroup class."""
    name: str
    clues: list
    settings: ClueGroupSettings | None = None

    reverse_grid_entries: bool | None = None
    show_enumerations: str | None = None
    show_grid_entries: bool | None = None
    show_grid_labels: bool | None = None

    model_config = ConfigDict(extra="forbid")


class GridStyle(BaseModel):
    """Grid Style class."""
    background_color: str | None = Field(default=None, alias="background-color", validation_alias="background-color")
    fill: str | None = None
    shape: Literal["circle", "shadesquare", "x"] | None = None
    stroke: str | None = None

    model_config = ConfigDict(extra="forbid")


class Grid(BaseModel):
    """Grid class."""
    columns: list
    rows: list

    entry_columns: List[str] | None = []
    entry_rows: List[str] | None = []

    solution_rows: List[str]
    solution_columns: List[str]
    solution_style: List[str]

    style: List[str]
    styles: Dict[str, GridStyle]

    model_config = ConfigDict(extra="forbid")


class HexGridSettings(BaseModel):
    """Hex Grid Settings."""
    clue_columns: int | None = None
    show_enumerations: Literal["answers", "entries"] | bool | None = None
    show_grid_bars: Literal["all", "solution"] | bool | None = None
    show_grid_border: bool | None = None
    show_grid_entries: bool | None = None
    show_grid_labels: bool | None = None
    show_grid_lines: bool | None = None
    show_starred_entries_in_grid: bool | None = None
    status: Literal["draft", "published"] | None = None

    model_config = ConfigDict(extra="forbid")


class Hexgrid(BaseModel):
    """Hexgrid class."""
    id: str
    title: str
    author: str
    editor: str | None = None

    date: str
    month: int | None = None
    year: int | None = None

    publication: str
    issue: str
    num: int | None = None
    number: int | None = None

    instructions: str
    solution: str

    clue_groups: List[ClueGroup]
    grid: Grid
    shape: None = None
    unclued: List[str]

    books: List[str] | None = None
    files: Dict[str, str] | None = None
    links: Dict[str, str | None] | None = None
    settings: HexGridSettings

    model_config = ConfigDict(extra="forbid")


class Publication(BaseModel):
    """Publication class."""
    id: str
    name: str
    code: str
    url: str

    model_config = ConfigDict(extra="forbid")


class Puzzle(BaseModel):
    """Puzzle class."""
    id: str
    title: str
    shape: str | None = None

    date: datetime.datetime
    year: int | None = None
    month: int | None = None

    pub: str | None = None
    issue: str | None = None
    num: int | None = None

    books: List[str] | None = []

    answer_link: str | None = None
    googledoc_link: str | None = None
    puzzle_link: str | None = None
    puzzleme_link: str | None = None
    web_link: str | None = None

    model_config = ConfigDict(extra="forbid")

    def __init__(self, **data):
        """Initialize a Puzzle object."""
        if "num" in data and not data["num"]:
            data["num"] = None
        super().__init__(**data)


class User(BaseModel):
    """User class."""
    id: str

    model_config = ConfigDict(extra="forbid")
