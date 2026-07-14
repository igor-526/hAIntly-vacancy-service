from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)


class Named(StrictModel):
    id: str
    name: str


class DictionaryValue(StrictModel):
    id: str | None = None
    code: str | None = None
    name: str | None = None

    @model_validator(mode="after")
    def complete(self):
        if self.id is None and self.code is None:
            raise ValueError("dictionary value has no identifier")
        if self.name is None and self.id is None:
            raise ValueError("dictionary value has no display name")
        return self


class Dictionaries(RootModel[dict[str, list[DictionaryValue]]]):
    @model_validator(mode="after")
    def non_empty(self):
        if not self.root or any(not values for values in self.root.values()):
            raise ValueError("incomplete dictionaries snapshot")
        return self


class Area(Named):
    areas: list[Area] = Field(default_factory=list)


class Industry(Named):
    industries: list[Industry] = Field(default_factory=list)


class RoleCategory(Named):
    roles: list[Named]


class ProfessionalRoles(StrictModel):
    categories: list[RoleCategory]

    @model_validator(mode="after")
    def non_empty(self):
        if not self.categories or any(not category.roles for category in self.categories):
            raise ValueError("incomplete professional roles snapshot")
        return self


class MetroStation(Named):
    lat: float | None = None
    lng: float | None = None
    order: int | None = None


class MetroLine(Named):
    stations: list[MetroStation]


class MetroCity(Named):
    lines: list[MetroLine]


class NamedList(RootModel[list[Named]]):
    @model_validator(mode="after")
    def non_empty(self):
        if not self.root:
            raise ValueError("empty snapshot")
        return self


class AreaList(RootModel[list[Area]]):
    @model_validator(mode="after")
    def non_empty(self):
        if not self.root:
            raise ValueError("empty areas snapshot")
        return self


class IndustryList(RootModel[list[Industry]]):
    @model_validator(mode="after")
    def non_empty(self):
        if not self.root:
            raise ValueError("empty industries snapshot")
        return self


class MetroCities(RootModel[list[Named]]):
    @model_validator(mode="after")
    def non_empty(self):
        if not self.root:
            raise ValueError("empty metro snapshot")
        return self
