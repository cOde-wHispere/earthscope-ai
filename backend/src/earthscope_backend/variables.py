"""Reviewed variable semantics; CSVs and request parameters cannot select conversions."""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from typing import Literal

from earthscope_backend.importer import kelvin_to_celsius

Variable = Literal["T2M", "PRECTOTCORR", "QV2M", "U10M", "V10M", "PS"]
Aggregation = Literal["equal_month_mean", "calendar_day_weighted_mean", "sum"]


@dataclass(frozen=True)
class VariableSpec:
    variable: Variable
    label: str
    collection: str
    product_native_units: str
    exported_units: str
    monthly_units: str
    annual_units: str
    minimum: float
    maximum: float
    fill_value: float
    conversion: str
    annual_aggregation: Aggregation
    limitation: str

    @property
    def filename(self) -> str:
        return f"giovanni_merra2_gambia_{self.variable.lower()}_1991_2025.csv"

    @property
    def data_id(self) -> str:
        return f"{self.collection}_5_12_4_{self.variable}"

    @property
    def value_column(self) -> str:
        return f"mean_{self.data_id}"

    def convert(self, value: float, time: date) -> float:
        if self.variable == "T2M":
            return kelvin_to_celsius(value)
        if self.variable == "PRECTOTCORR":
            return value * 86400 * monthrange(time.year, time.month)[1]
        if self.variable == "QV2M":
            return value * 1000
        return value


SPECS = {
    spec.variable: spec
    for spec in (
        VariableSpec(
            "T2M",
            "2-meter air temperature",
            "M2IMNXASM",
            "K",
            "K",
            "degC",
            "degC",
            150,
            350,
            1e15,
            "C = K - 273.15",
            "equal_month_mean",
            "Air temperature is not sea surface temperature.",
        ),
        VariableSpec(
            "PRECTOTCORR",
            "Bias-corrected total precipitation",
            "M2TMNXFLX",
            "kg m-2 s-1",
            "kg m-2 s-1",
            "mm/month",
            "mm/year",
            0,
            0.01,
            1e15,
            "mm/month = monthly mean flux * 86400 * calendar days in month",
            "sum",
            "Water-equivalent total precipitation; not a rain-only measurement. "
            "Multiplication of the exported monthly mean flux is not a new daily observation.",
        ),
        VariableSpec(
            "QV2M",
            "2-meter specific humidity",
            "M2IMNXASM",
            "kg/kg",
            "kg/kg",
            "g/kg",
            "g/kg",
            0,
            0.1,
            1e15,
            "g/kg = kg/kg * 1000",
            "calendar_day_weighted_mean",
            "Specific humidity is not relative humidity (%).",
        ),
        VariableSpec(
            "U10M",
            "10-meter eastward wind component",
            "M2TMNXSLV",
            "m/s",
            "m/s",
            "m/s",
            "m/s",
            -150,
            150,
            1e15,
            "Unchanged signed eastward component",
            "calendar_day_weighted_mean",
            "Positive is eastward; negative is westward. "
            "A monthly mean component is not wind speed, a gust or an operational forecast.",
        ),
        VariableSpec(
            "V10M",
            "10-meter northward wind component",
            "M2TMNXSLV",
            "m/s",
            "m/s",
            "m/s",
            "m/s",
            -150,
            150,
            1e15,
            "Unchanged signed northward component",
            "calendar_day_weighted_mean",
            "Positive is northward; negative is southward. "
            "Combining monthly mean components does not recover mean wind speed.",
        ),
        VariableSpec(
            "PS",
            "Surface pressure",
            "M2TMNXSLV",
            "Pa",
            "hPa",
            "hPa",
            "hPa",
            300,
            1100,
            999999986991104,
            "Exported hPa values unchanged; no division by 100",
            "calendar_day_weighted_mean",
            "This approved export is in hPa although the native "
            "NASA product is specified in Pa; it is not sea-level pressure.",
        ),
    )
}
