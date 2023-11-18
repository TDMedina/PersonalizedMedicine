
from datetime import datetime

import pandas as pd
from pandas import IndexSlice as idx
from pandas.api.extensions import register_dataframe_accessor
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

BAND_DICT = {"0-49": ["Under 1 year", "1 - 4 years", "5 - 9 years", "10 - 14 years",
                      "15 - 19 years", "20 - 24 years", "25 - 29 years",
                      "30 - 34 years", "35 - 39 years", "40 - 44 years",
                      "45 - 49 years"],
             "50-64": ["50 - 54 years", "55 - 59 years", "60 - 64 years"],
             "65-74": ["65 - 69 years", "70 - 74 years"],
             "75+": ["75 - 79 years", "80 - 84 years", "85 years and over"]}
AGE_BANDS = [band for bands in BAND_DICT.values() for band in bands]


@register_dataframe_accessor("survival_tools")
class SurvivalData:
    def __init__(self, pandas_obj):
        self._obj = pandas_obj

    @staticmethod
    def read_csv(survival_data):
        """Read NCRI survival data in CSV format."""
        survival_data = pd.read_csv(survival_data, sep=",")
        survival_data = survival_data.loc[survival_data.Dates != "2009-2013"]
        survival_data = (survival_data
                         .sort_values(by="Time (years)")
                         .sort_values(by="Dates", ascending=False, kind="stable"))
        survival_data["Net survival"] = survival_data["Net survival"] / 100
        return survival_data

    def plot(self):
        """Plot NCRI historic survival data."""
        survival_plot = px.line(self._obj, x="Time (years)", y="Net survival",
                                color="Dates", markers=True,
                                title=("Survival: All invasive cancers "
                                       "(except NMSC) in Ireland"),
                                width=750, height=500,
                                template="plotly_white")
        survival_plot.update_layout(legend_title="Date range", height=450, width=600)
        survival_plot.update_yaxes(tickformat=".0%", range=[0, 1])
        return survival_plot


@register_dataframe_accessor("population_tools")
class PopulationData:
    def __init__(self, pandas_obj):
        self._obj = pandas_obj

    @staticmethod
    def read_csv(population_csv, correct_errant_years=True):
        """Read CSO population estimates in CSV format."""
        pop_data = pd.read_csv(population_csv, sep=",", usecols=[1, 2, 3, 5])

        cols = list(pop_data.columns)
        cols[-1] = "Population"
        pop_data.columns = cols

        pop_data["Year"] = [datetime(x, 1, 1) for x in pop_data.Year]
        pop_data = pop_data.loc[(datetime(1994, 1, 1) <= pop_data.Year)
                                & (pop_data.Year < datetime(2020, 1, 1))]
        pop_data["Population"] = pop_data["Population"] * 1000

        pop_data = (pop_data
                    .sort_values("Age Group",
                                 key=lambda x: [y.replace("Under", "0") for y in x])
                    .sort_values("Sex", kind="stable")
                    .sort_values("Year", kind="stable"))
        pop_data.set_index(["Year", "Sex", "Age Group"], inplace=True)
        pop_data = pop_data.loc[idx[datetime(1994, 1, 1):datetime(2019, 1, 1), :, AGE_BANDS]]
        pop_data.rename(index={"Both sexes": "Both"}, level="Sex", inplace=True)

        if correct_errant_years:
            for i in range(2012, 2017):
                subset = pop_data.loc[idx[datetime(i, 1, 1), :, "1 - 4 years"]]
                correction = (subset.loc["Both"] - subset.loc["Male"]).Population
                pop_data.loc[idx[datetime(i, 1, 1), "Female", "1 - 4 years"]] = correction

        return pop_data

    def aggregate_cancer_age_groups(self):
        """Aggregate CSO age bands to match NCRI age bands."""
        aggregate = pd.DataFrame(columns=["Year", "Sex", "Population", "Age Group"])
        for i, (agg_band, bands) in enumerate(BAND_DICT.items()):
            sub_agg = self._obj.loc[idx[:, :, bands]].groupby(["Year", "Sex"]).agg(sum)
            sub_agg["Age Group"] = agg_band
            sub_agg.reset_index(inplace=True)
            aggregate = pd.concat([aggregate, sub_agg])
        aggregate.set_index(["Year", "Sex", "Age Group"], inplace=True)
        aggregate.sort_index(inplace=True)
        return aggregate

    def add_proportions(self):
        """Add column of population proportions per category."""
        data = self._obj
        year_aggregated = data.groupby(["Year", "Sex"]).agg(sum)
        data["Proportion"] = [pop / year_aggregated.loc[idx[year, sex]].Population
                              for (year, sex, age), pop in data.itertuples()]
        return data

    def plot(self, normalized=False, aggregate_cancer_groups=False):
        """Plot CSO population estimates over time.

        Age bands can be aggregated to match NCRI cancer bands. Plot can show raw
        counts or proportional contributions of each age band to total population
        per year.
        """
        data = self._obj
        if aggregate_cancer_groups:
            data = data.population_tools.aggregate_cancer_age_groups()
        if normalized:
            data = data.population_tools.add_proportions()
            y = "Proportion"
        else:
            y = "Population"
        data = data.loc[idx[:, "Both", :]]
        data = data.reset_index()
        fig = px.bar(data, x="Year", y=y, color="Age Group")
        fig.update_layout(bargap=0)
        return fig


@register_dataframe_accessor("age_incidence_tools")
class AgeIncidenceData:
    def __init__(self, pandas_obj):
        self._obj = pandas_obj

    @staticmethod
    def read_csv(incidence_data):
        """Read NCRI cancer incidence by age group in CSV format."""
        data = pd.read_csv(incidence_data, sep=",")
        cols = list(data.columns)
        cols[0] = "Age Group"
        data.columns = cols
        data["Year"] = [datetime(x, 1, 1) for x in data.Year]
        data = (data
                .sort_values(by="Year")
                .sort_values(by="Age Group", ascending=False, kind="stable"))
        data.set_index(["Year", "Age Group"], inplace=True)
        return data

    def plot(self, raw_count=False, combined=False):
        """Plot NCRI cancer incidence by age group over time.

        Plot can show incidence per 100K people per age group, or raw counts per year,
         or both using combined=True. If combined=True, raw_count is ignored.
        """
        if combined:
            incidence_plot = self._plot_combined()
            return incidence_plot
        if raw_count:
            y = "Case numbers"
            y_title = "Cases per year"
        else:
            y = "Crude rate"
            y_title = "Cases per 100,000 per year"
        data = self._obj.reset_index()
        incidence_plot = px.line(data, x="Year", y=y,
                                 color="Age Group",
                                 markers=True, width=750, height=500,
                                 title=("Incidence by age: All invasive cancers "
                                        "(except NMSC) in Ireland"),
                                 template="plotly_white")
        incidence_plot = incidence_plot.update_layout(yaxis_title=y_title,
                                                      legend_title="Age Group")
        incidence_plot.update_xaxes(dtick="M60")
        return incidence_plot

    def _plot_combined(self):
        raw = self.plot(raw_count=True)
        rel = self.plot(raw_count=False)

        age_plot = make_subplots(rows=1, cols=2,
                                 subplot_titles=["a) Cases per age band",
                                                 "b) Cases per 100K in age band"],
                                 x_title="Year",
                                 y_title="Cases")
        for i, plot in enumerate([raw, rel], start=1):
            for trace in plot.data:
                age_plot.add_trace(trace, row=1, col=i)

        age_plot.update_traces(showlegend=False, col=2)
        age_plot.update_layout(title=raw.layout.title.text,
                               legend_title="Age Group",
                               template="plotly_white")
        age_plot.update_xaxes(dtick="M60")

        age_plot.layout.annotations[0].update(xanchor="left", xshift=-190)
        age_plot.layout.annotations[1].update(xanchor="left", xshift=-190)

        age_plot.update_layout(height=450, width=900)

        return age_plot

    def merge_with_population_table(self, population_df):
        pop_data = population_df.population_tools.aggregate_cancer_age_groups()
        pop_data = pop_data.loc[idx[:, "Both", :]].groupby(["Year", "Age Group"]).agg(sum)
        data = pd.merge(self._obj, pop_data, left_index=True, right_index=True)
        data["Relative numbers"] = data["Case numbers"] / data["Population"] * 100000
        return data


@register_dataframe_accessor("sex_incidence_tools")
class SexIncidenceData:
    def __init__(self, pandas_obj):
        self._obj = pandas_obj

    @staticmethod
    def read_csv(sex_incidence_csv):
        """Read NCRI cancer incidence by sex in CSV format."""
        incidence = pd.read_csv(sex_incidence_csv)
        incidence["Year"] = [datetime(x, 1, 1) for x in incidence.Year]
        incidence.set_index(["Year", "Sex"], inplace=True)
        incidence.rename(index={"Males": "Male", "Females": "Female"},
                         level="Sex", inplace=True)
        return incidence

    def merge_with_population_table(self, population_df):
        """Add population totals column from formatted CSO data."""
        pop_data = population_df.groupby(["Year", "Sex"]).agg(sum)
        data = pd.merge(self._obj, pop_data, left_index=True, right_index=True)
        data["Relative numbers"] = data["Case numbers"] / data["Population"] * 100000
        return data

    def plot(self, raw_count=True, combined=False):
        """Plot NCRI cancer incidence by sex over time.

        Plot can show incidence per 100K per sex, or raw counts, or both. If
        combined=True, raw_count is ignored.
        """
        if combined:
            incidence_plot = self._plot_combined()
            return incidence_plot
        if raw_count:
            y = "Case numbers"
            y_title = "Cases per year"
        else:
            y = "Relative numbers"
            y_title = "Cases per 100,000 total population per year"
        data = self._obj.reset_index()
        incidence_plot = px.line(data, x="Year", y=y, color="Sex",
                                 markers=True, width=750, height=500,
                                 title=("Total incidence: All invasive cancers "
                                        "(except NMSC) in Ireland"),
                                 template="plotly_white")
        incidence_plot.update_layout(yaxis_title=y_title)
        incidence_plot.update_xaxes(dtick="M60")
        return incidence_plot

    def _plot_combined(self):
        raw = self.plot(raw_count=True)
        rel = self.plot(raw_count=False)

        sex_plot = make_subplots(rows=1, cols=2,
                                 subplot_titles=["a) Cases per sex",
                                                 "b) Cases per 100K of sex"],
                                 x_title="Year",
                                 y_title="Cases")
        for i, plot in enumerate([raw, rel], start=1):
            for trace in plot.data:
                sex_plot.add_trace(trace, row=1, col=i)

        sex_plot.update_traces(showlegend=False, col=2)
        sex_plot.update_layout(title=raw.layout.title.text,
                               legend_title="Sex",
                               template="plotly_white")
        sex_plot.update_xaxes(dtick="M60")

        sex_plot.layout.annotations[0].update(xanchor="left", xshift=-190)
        sex_plot.layout.annotations[1].update(xanchor="left", xshift=-190)

        sex_plot.update_layout(height=450, width=900)

        return sex_plot


def main(age_incidence_csv, sex_incidence_csv, population_csv, survival_csv):
    """Read relevant data and return plots."""
    age_incidence = AgeIncidenceData.read_csv(age_incidence_csv)
    sex_incidence = SexIncidenceData.read_csv(sex_incidence_csv)
    population = PopulationData.read_csv(population_csv)
    age_incidence = age_incidence.age_incidence_tools.merge_with_population_table(population)
    sex_incidence = sex_incidence.sex_incidence_tools.merge_with_population_table(population)
    survival = SurvivalData.read_csv(survival_csv)

    age_plot = age_incidence.age_incidence_tools.plot(combined=True)
    sex_plot = sex_incidence.sex_incidence_tools.plot(combined=True)
    survival_plot = survival.survival_tools.plot()
    return age_plot, sex_plot, survival_plot
